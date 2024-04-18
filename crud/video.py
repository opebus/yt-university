import logging

from fastapi import HTTPException
from sqlalchemy.future import select
from yt_university.helper import sanitize_youtube_url
from yt_university.models.video import Video

logger = logging.getLogger(__name__)


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


async def update_video(session, video_id: str, update_data: dict) -> Video:
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


async def get_video_by_url(session, video_url):
    try:
        sanitized_url = sanitize_youtube_url(video_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    stmt = select(Video).filter(Video.url == sanitized_url).first()
    result = await session.execute(stmt)
    video = result.scalars()

    return video


async def get_video(session, video_id):
    stmt = select(Video).filter(Video.id == video_id).first()
    result = await session.execute(stmt)
    video = result.scalars()

    return video


async def get_all_videos(session, page, page_size):
    offset = (page - 1) * page_size

    stmt = select(Video).offset(offset).limit(page_size)
    result = await session.execute(stmt)
    videos = result.scalars().all()

    return videos
