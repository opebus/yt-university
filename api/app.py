import time
from typing import NamedTuple
from urllib.parse import parse_qs, urlparse

import yt_university.config as config
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from yt_university.config import MAX_JOB_AGE_SECS
from yt_university.crud.video import get_all_videos, get_video, upsert_video
from yt_university.services.process import process
from yt_university.services.summarize import generate_summary
from yt_university.stub import in_progress

logger = config.get_logger(__name__)

web_app = FastAPI()

web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InProgressJob(NamedTuple):
    call_id: str
    start_time: int
    status: str


@web_app.post("/api/process")
async def process_workflow(url: str = Body(..., embed=True)):
    from yt_university.database import get_db_session

    # defensive programming
    parsed = urlparse(url)
    id = parse_qs(parsed.query)["v"][0]

    ## assume only youtube videos
    sanitized_url = "https://www.youtube.com/watch?v=" + id

    now = int(time.time())
    try:
        inprogress_job = in_progress[sanitized_url]
        if (
            isinstance(inprogress_job, InProgressJob)
            and (now - inprogress_job.start_time) < MAX_JOB_AGE_SECS
        ):
            existing_call_id = inprogress_job.call_id
            logger.info(
                f"Found existing, unexpired call ID {existing_call_id} for video {sanitized_url}"
            )
            return {"call_id": existing_call_id}
    except KeyError:
        pass

    async with get_db_session() as session:
        video = await get_video(session, id)

    if video and video.transcription is not None:
        raise HTTPException(status_code=400, detail="Video already processed")
    call = process.spawn(sanitized_url)

    in_progress[sanitized_url] = InProgressJob(
        call_id=call.object_id, start_time=now, status="init"
    )

    logger.info(f"Started new call ID {call.object_id}")
    return {"call_id": call.object_id}


@web_app.post("/api/summarize")
async def invoke_transcription(id: str = Body(..., embed=True)):
    from yt_university.database import get_db_session

    async with get_db_session() as session:
        video = await get_video(session, id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if not video.transcription:
        raise HTTPException(
            status_code=404, detail="Transcription not available for this video"
        )

    summary = generate_summary.spawn(video.title, video.transcription).get()
    async with get_db_session() as session:
        video_data = await upsert_video(session, video.id, {"summary": summary})

    return {id: video_data.id, "summary": video_data.summary}


@web_app.get("/api/status/{call_id}")
async def poll_status(call_id: str):
    from modal.call_graph import InputInfo, InputStatus
    from modal.functions import FunctionCall

    function_call = FunctionCall.from_id(call_id)
    graph: list[InputInfo] = function_call.get_call_graph()

    try:
        function_call.get(timeout=0.1)
    except TimeoutError:
        pass
    except Exception as exc:
        if exc.args:
            inner_exc = exc.args[0]
            if "HTTPError 403" in inner_exc:
                return dict(error="permission denied on video download")
        return dict(error="unknown job processing error")

    try:
        main_stub = graph[0].children[0]
        map_root = main_stub.children[0]
    except IndexError:
        return dict(stage="init", status="in_progress")

    status = dict(
        stage=map_root.function_name,
        status=InputStatus(map_root.status).name,
    )

    if map_root.function_name == "transcribe":
        leaves = map_root.children
        tasks = len({leaf.task_id for leaf in leaves})
        done_segments = len(
            [leaf for leaf in leaves if leaf.status == InputStatus.SUCCESS]
        )
        total_segments = len(leaves)

        status["total_segments"] = total_segments
        status["tasks"] = tasks
        status["done_segments"] = done_segments
    elif (
        map_root.function_name == "summarize" and map_root.status == InputStatus.SUCCESS
    ) or main_stub.status == InputStatus.SUCCESS:
        status["stage"] = "end"
        status["status"] = "DONE"

    return status


@web_app.get("/api/videos")
async def get_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
):
    from yt_university.database import get_db_session

    async with get_db_session() as session:
        video = await get_all_videos(session, page, page_size)

    return video


@web_app.get("/api/video")
async def get_individual_video(
    id: str = Query(
        ..., description="The ID of the video"
    ),  # Use ellipsis to make it a required field
):
    """
    Fetch a video by its ID.
    """
    from yt_university.database import get_db_session

    async with get_db_session() as session:
        video = await get_video(session, id)

    # Check if the video was found
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return video
