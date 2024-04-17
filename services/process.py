import logging
from http.client import HTTPException

from modal import Secret, Volume

from yt_university.config import DATA_DIR
from yt_university.models.video import Video
from yt_university.services.download import Downloader
from yt_university.services.transcribe import transcribe
from yt_university.stub import shared_webapp_image, stub

logger = logging.getLogger(__name__)

volume = Volume.from_name("yt-university-cache", create_if_missing=True)


@stub.function(
    container_idle_timeout=60,
    image=shared_webapp_image,
    timeout=600,
    secrets=[Secret.from_name("supabase")],
    volumes={DATA_DIR: volume},
)
async def process(video_url):
    import os

    from supabase import Client, create_client

    from yt_university.database import get_db_session
    from yt_university.models import Video

    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    downloader = Downloader()

    download_call = downloader.run.spawn(video_url)
    result = download_call.get()
    audio_path, thumbnail_path, metadata = result

    volume.reload()

    session = await anext(get_db_session())
    video = Video(
        url=video_url,
        title=metadata["title"],
        description=metadata["description"],
        duration=metadata["duration"],
        language=metadata["language"],
    )
    video = await add_video(session, video)

    with open(audio_path, "rb") as f:
        supabase.storage.from_("audio").upload(file=f, path=audio_path.split("/")[-1])
    os.remove(audio_path)

    with open(thumbnail_path, "rb") as f:
        supabase.storage.from_("thumbnail").upload(
            file=f, path=thumbnail_path.split("/")[-1]
        )
    os.remove(thumbnail_path)

    transcribe_call = transcribe.spawn(audio_path)
    transcription = transcribe_call.get()
    video_data = await update_video(session, video.id, {"transcription": transcription})

    return video_data


async def add_video(session, video_data: Video) -> Video:
    try:
        session.add(video_data)
        await session.commit()
        await session.refresh(video_data)
        return video_data
    except Exception as e:
        logger.error(f"Failed to add video: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to add video to database")


# async def update_transcription(
#     session, video_id: int, new_transcription: str
# ) -> any:
#     from fastapi import HTTPException
#     from sqlalchemy.future import select

#     from yt_university.models import Video

#     video = (
#         await session.scalars(select(Video).where(Video.id == video_id))
#     ).first()

#     if not video:
#         raise HTTPException(status_code=404, detail="Video not found")

#     video.transcription = new_transcription

#     await session.commit()
#     await session.refresh(video)

#     return video


async def update_video(session, video_id: str, update_data: dict) -> Video:
    from fastapi import HTTPException
    from sqlalchemy.future import select

    try:
        result = await session.execute(select(Video).where(Video.id == video_id))
        video = result.scalars().first()

        # If video does not exist, raise an HTTPException
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        # Update the video fields based on provided update_data dictionary
        for key, value in update_data.items():
            if hasattr(video, key):
                setattr(video, key, value)
            else:
                logger.warning(
                    f"Attempted to update non-existent field '{key}' on Video model."
                )

        # Commit changes and refresh the instance
        await session.commit()
        await session.refresh(video)

        return video
    except HTTPException:
        raise  # Re-throw the HTTPException for handling by FastAPI
    except Exception as e:
        logger.error(f"Failed to update video: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500, detail="Internal server error during video update"
        )
