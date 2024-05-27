import time
from typing import NamedTuple
from urllib.parse import parse_qs, urlparse

import yt_university.config as config
from fastapi import Body, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from yt_university.config import MAX_JOB_AGE_SECS
from yt_university.crud.playlist import (
    add_playlist,
    add_videos_to_playlist,
    delete_playlist,
    get_all_playlists,
    get_playlist,
    remove_videos_from_playlist,
)
from yt_university.crud.video import (
    get_all_videos,
    get_video,
    upsert_video,
)
from yt_university.services.process import process
from yt_university.services.summarize import categorize_text, generate_summary
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


class Favorite(BaseModel):
    user_id: str
    video_id: str


class InProgressJob(NamedTuple):
    call_id: str
    start_time: int
    status: str


class WorkflowRequest(BaseModel):
    url: str
    user_id: str
    force: bool = False


@web_app.post("/api/process")
async def process_workflow(request: WorkflowRequest):
    from yt_university.database import get_db_session
    from yt_university.models import Video

    url = request.url
    user_id = request.user_id
    force = request.force

    # Parse the URL to handle different YouTube URL formats
    parsed = urlparse(url)
    if "youtu.be" in parsed.netloc:
        # Handling the shortened YouTube URL format
        video_id = parsed.path[1:]  # Skip the first '/' in the path to get the ID
    else:
        # Handling the standard YouTube URL format
        query_params = parse_qs(parsed.query)
        video_id = query_params.get("v", [None])[
            0
        ]  # Get 'v' parameter or default to None if not present

    # Ensure video_id is not None before proceeding
    if video_id is None:
        raise ValueError("Invalid YouTube URL provided.")

    # Reconstruct a sanitized YouTube URL
    sanitized_url = f"https://www.youtube.com/watch?v={video_id}"

    now = int(time.time())
    if not force:
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
        video = await get_video(session, id, load_columns=[Video.transcription])
        if video and video.transcription is not None:
            raise HTTPException(status_code=400, detail="Video already processed")

    call = process.spawn(sanitized_url, user_id)

    in_progress[sanitized_url] = InProgressJob(
        call_id=call.object_id, start_time=now, status="init"
    )

    logger.info(f"Started new call ID {call.object_id}")
    return {"call_id": call.object_id}


@web_app.post("/api/summarize")
async def invoke_transcription(id: str = Body(..., embed=True)):
    from yt_university.database import get_db_session
    from yt_university.models import Video

    async with get_db_session() as session:
        video = await get_video(session, id, load_columns=[Video.transcription])

        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        if not video.transcription:
            raise HTTPException(
                status_code=404, detail="Transcription not available for this video"
            )

        summary = generate_summary.spawn(video.title, video.transcription).get()
        category = categorize_text.spawn(video.title, summary).get()
        video_data = await upsert_video(
            session, video.id, {"summary": summary, "category": category}
        )

    return {
        id: video_data.id,
        "summary": video_data.summary,
        "category": video_data.category,
    }


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
async def all_videos(
    user_id: str = Query(None, description="The user ID to fetch favorites for"),
    category: str = Query(None, description="The category of the videos to fetch"),
    is_user: bool = Query(False, description="Whether to filter by user ID"),
    page: int = Query(1, description="Page number of the results"),
    page_size: int = Query(10, description="Number of results per page"),
):
    """
    Fetch videos optionally filtered by category with pagination.
    """
    from yt_university.database import get_db_session

    async with get_db_session() as session:
        videos = await get_all_videos(
            session, user_id, category, is_user, page, page_size
        )

    if not videos:
        raise HTTPException(status_code=404, detail="No videos found")

    return videos


@web_app.get("/api/videos/{id}")
async def get_individual_video(id: str):
    """
    Fetch a video by its ID.
    """
    from yt_university.database import get_db_session

    async with get_db_session() as session:
        video = await get_video(session, id, load_columns="all")

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return video


@web_app.get("/api/categories")
async def get_video_categories():
    from yt_university.services.summarize import CATEGORIES

    categories = CATEGORIES

    if not categories:
        raise HTTPException(status_code=404, detail="No categories found")

    return categories


@web_app.post("/api/users/{user_id}/favorites/{video_id}")
async def add_to_favorites(video_id: str, user_id: str):
    from yt_university.crud.favorite import add_favorite
    from yt_university.database import get_db_session

    try:
        async with get_db_session() as session:
            favorite_data = await add_favorite(session, user_id, video_id)
            return favorite_data
    except HTTPException as e:
        raise e


@web_app.delete("/api/users/{user_id}/favorites/{video_id}")
async def delete_favorite(video_id: str, user_id: str):
    from yt_university.crud.favorite import remove_favorite
    from yt_university.database import get_db_session

    try:
        async with get_db_session() as session:
            await remove_favorite(session, user_id, video_id)
            return {"status": "success", "message": "Favorite has been removed"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@web_app.get("/api/users/{user_id}/favorites")
async def list_favorites(user_id: str):
    from yt_university.crud.favorite import get_user_favorites
    from yt_university.database import get_db_session

    try:
        async with get_db_session() as session:
            favorites = await get_user_favorites(session, user_id)
            return favorites
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


class CreatePlaylist(BaseModel):
    name: str
    description: str
    user_id: str
    video_ids: list[str] = []


@web_app.post("/api/playlists")
async def create_playlist(playlist_data: CreatePlaylist):
    from yt_university.database import get_db_session

    try:
        async with get_db_session() as session:
            new_playlist = await add_playlist(session, playlist_data)
            return new_playlist
    except Exception as e:
        logger.error(f"Failed to create a new playlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@web_app.delete("/api/playlists/{playlist_id}")
async def delete_existing_playlist(playlist_id: str):
    from yt_university.database import get_db_session

    try:
        async with get_db_session() as session:
            await delete_playlist(session, playlist_id)
            return {"status": "success", "message": "Playlist has been deleted"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to delete playlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@web_app.post("/api/playlists/{playlist_id}/videos")
async def add_video_existing_playlist(
    playlist_id: str, video_ids: list[str] = Body(..., embed=True)
):
    from yt_university.database import get_db_session

    try:
        async with get_db_session() as session:
            updated_playlist = await add_videos_to_playlist(
                session, playlist_id, video_ids
            )
            return updated_playlist
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to update playlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@web_app.delete("/api/playlists/{playlist_id}/videos")
async def delete_video_existing_playlist(
    playlist_id: str, video_ids: list[str] = Body(..., embed=True)
):
    from yt_university.database import get_db_session

    try:
        async with get_db_session() as session:
            updated_playlist = await remove_videos_from_playlist(
                session, playlist_id, video_ids
            )
            return updated_playlist
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to update playlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@web_app.get("/api/playlists")
async def list_playlists_for_user(
    user_id: str = Query(None, description="The user ID to fetch playlists for"),
):
    from yt_university.database import get_db_session

    try:
        async with get_db_session() as session:
            playlists = await get_all_playlists(session, user_id=user_id)
            return playlists
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to list playlists for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@web_app.get("/api/playlists/{playlist_id}")
async def get_playlist_details(playlist_id: str):
    from yt_university.database import get_db_session

    try:
        async with get_db_session() as session:
            playlist = await get_playlist(session, playlist_id)
            return playlist
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to retrieve playlist with ID {playlist_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


class ClerkWebhook(BaseModel):
    data: dict
    object: str
    type: str


@web_app.post("/api/user")
async def user_webhook(request: Request):
    import json
    import os

    from svix.webhooks import Webhook, WebhookVerificationError
    from yt_university.crud.user import add_user, delete_user, update_user
    from yt_university.database import get_db_session

    headers = request.headers
    payload = await request.body()
    secret = os.environ["CLERK_SIGNING_SECRET"]

    try:
        wh = Webhook(secret)
        wh.verify(payload, headers)
    except WebhookVerificationError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Invalid signature"},
        )

    webhook_data = json.loads(payload.decode())
    webhook = ClerkWebhook(**webhook_data)

    user_data = webhook.data
    if webhook.type != "user.deleted":
        user_data = {
            "id": webhook.data["id"],
            "username": webhook.data["username"],
            "first_name": webhook.data["first_name"],
            "last_name": webhook.data["last_name"],
            "primary_email_address_id": webhook.data["primary_email_address_id"],
            "email_addresses": webhook.data["email_addresses"],
        }

    async with get_db_session() as session:
        if webhook.type == "user.created":
            user_created = await add_user(session, user_data)
            return JSONResponse(
                content={"message": "User created successfully", "user": user_created},
                status_code=status.HTTP_201_CREATED,
            )
        elif webhook.type == "user.updated":
            user_updated = await update_user(session, user_data)
            return JSONResponse(
                content={"message": "User updated successfully", "user": user_updated},
                status_code=status.HTTP_200_OK,
            )
        elif webhook.type == "user.deleted":
            await delete_user(session, user_data)
            return JSONResponse(
                content={"message": "User deleted successfully"},
                status_code=status.HTTP_204_NO_CONTENT,
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported event type")
