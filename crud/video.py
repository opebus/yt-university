import logging

from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def add_video(session, video_data):
    try:
        session.add(video_data)
        await session.commit()
        await session.refresh(video_data)
        return video_data
    except Exception as e:
        logger.error(f"Failed to add video: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to add video to database")


async def upsert_video(session, video_id: str, update_data: dict):
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.future import select

    from yt_university.models.video import Video

    try:
        # Try to fetch the existing video
        result = await session.execute(select(Video).where(Video.id == video_id))
        video = result.scalars().first()

        if video:
            # Video exists, update its fields
            for key, value in update_data.items():
                if hasattr(video, key):
                    setattr(video, key, value)
                else:
                    logger.warning(
                        f"Attempted to update non-existent field '{key}' on Video model."
                    )
        else:
            # Video does not exist, create a new instance
            video = Video(**update_data)
            session.add(video)

        # Commit changes and refresh the instance
        await session.commit()
        await session.refresh(video)

        return video

    except HTTPException as e:
        # Re-throw HTTP exceptions to be handled by FastAPI
        raise e
    except SQLAlchemyError as e:
        # Log and handle database-related errors
        logger.error(f"Database error during upsert operation: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500, detail="Internal server error during video upsert"
        )
    except Exception as e:
        # Log and handle unexpected errors
        logger.error(f"Failed to upsert video: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500, detail="Internal server error during video upsert"
        )


async def get_video(session, video_id):
    from sqlalchemy.future import select

    from yt_university.models.video import Video

    stmt = select(Video).filter(Video.id == video_id)
    result = await session.execute(stmt)
    video = result.scalars().first()

    return video


async def get_all_videos(session, category=None, page=1, page_size=10):
    from sqlalchemy.future import select

    from yt_university.models.video import Video

    offset = (page - 1) * page_size
    query = select(Video)

    if category:
        query = query.where(Video.category == category)

    query = query.offset(offset).limit(page_size)
    result = await session.execute(query)
    videos = result.scalars().all()

    return videos
