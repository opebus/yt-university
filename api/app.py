import time
from contextlib import asynccontextmanager
from typing import NamedTuple

import yt_university.config as config
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from yt_university.database import get_db_session
from yt_university.models.video import Video
from yt_university.services.process import process
from yt_university.stub import in_progress

logger = config.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Function that handles startup and shutdown events.
    To understand more, read https://fastapi.tiangolo.com/advanced/events/
    """
    from yt_university.database import sessionmanager

    yield
    if sessionmanager._engine is not None:
        # Close the DB connection
        await sessionmanager.close()


web_app = FastAPI(lifespan=lifespan)

web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_JOB_AGE_SECS = 2 * 60


class InProgressJob(NamedTuple):
    call_id: str
    start_time: int


@web_app.post("/api/transcribe")
async def transcribe_job(
    video_url: str = Query(..., description="The URL of the video to transcribe"),
):
    now = int(time.time())
    try:
        inprogress_job = in_progress[video_url]
        if (
            isinstance(inprogress_job, InProgressJob)
            and (now - inprogress_job.start_time) < MAX_JOB_AGE_SECS
        ):
            existing_call_id = inprogress_job.call_id
            logger.info(
                f"Found existing, unexpired call ID {existing_call_id} for video {video_url}"
            )
            return {"call_id": existing_call_id}
    except KeyError:
        pass
    call = process.spawn(video_url)

    in_progress[video_url] = InProgressJob(call_id=call.object_id, start_time=now)

    logger.info(f"Started new call ID {call.object_id}")
    return {"call_id": call.object_id}


@web_app.get("/api/status/{call_id}")
async def poll_status(call_id: str):
    from modal.call_graph import InputInfo, InputStatus
    from modal.functions import FunctionCall

    function_call = FunctionCall.from_id(call_id)
    graph: List[InputInfo] = function_call.get_call_graph()

    try:
        function_call.get(timeout=0.1)
    except TimeoutError:
        pass
    except Exception as exc:
        print(exc)
        if exc.args:
            inner_exc = exc.args[0]
            if "HTTPError 403" in inner_exc:
                return dict(error="permission denied on video download")
        return dict(error="unknown job processing error")

    downloaded = False
    try:
        download_root = graph[0].children[0].children[1]
        downloaded = download_root.status

        map_root = graph[0].children[0].children[0]
    except IndexError:
        return dict(finished=False, downloaded=downloaded)

    assert map_root.function_name == "transcribe"

    leaves = map_root.children
    tasks = len({leaf.task_id for leaf in leaves})
    done_segments = len([leaf for leaf in leaves if leaf.status == InputStatus.SUCCESS])
    total_segments = len(leaves)
    finished = map_root.status == InputStatus.SUCCESS

    return dict(
        finished=finished,
        total_segments=total_segments,
        tasks=tasks,
        done_segments=done_segments,
        downloaded=downloaded,
    )


@web_app.get("/api/videos/")
async def get_videos(
    session=Depends(get_db_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
):
    from sqlalchemy.future import select

    # Calculate offset
    offset = (page - 1) * page_size

    # Apply offset and limit to the query
    stmt = select(Video).offset(offset).limit(page_size)
    result = await session.execute(stmt)
    videos = result.scalars().all()
    return videos


@web_app.get("/api/videos/{video_id}")
async def read_video(video_id, session=Depends(get_db_session)):
    from sqlalchemy.future import select

    video = await session.scalars(select(Video).filter(Video.id == video_id).first())
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video
