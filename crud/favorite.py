import logging

from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def add_favorite(session, user_id: str, video_id: str):
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.future import select

    from yt_university.models import favorite

    try:
        existing_favorite = await session.execute(
            select(favorite).where(
                favorite.c.user_id == user_id,
                favorite.c.video_id == video_id,
            )
        )
        favorite_instance = existing_favorite.first()

        if favorite_instance:
            raise HTTPException(status_code=400, detail="Favorite already exists")

        await session.execute(
            favorite.insert().values(user_id=user_id, video_id=video_id)
        )
        await session.commit()
        return {"status": "success", "message": "Favorite added successfully"}
    except HTTPException as e:
        raise e
    except SQLAlchemyError as e:
        logger.error(f"Failed to add favorite: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to add favorite in database"
        )


async def remove_favorite(session, user_id: str, video_id: str):
    from sqlalchemy.future import select

    from yt_university.models import favorite

    try:
        result = await session.execute(
            select(favorite).where(
                favorite.c.user_id == user_id, favorite.c.video_id == video_id
            )
        )
        favorite_instance = result.first()
        if not favorite_instance:
            raise HTTPException(status_code=404, detail="Favorite not found")

        await session.execute(
            favorite.delete().where(
                favorite.c.user_id == user_id, favorite.c.video_id == video_id
            )
        )
        await session.commit()
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to remove favorite: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to remove favorite")


async def get_user_favorites(session, user_id: str):
    from sqlalchemy.future import select

    from yt_university.models import Video, favorite

    try:
        result = await session.execute(
            select(Video)
            .join(favorite)
            .where(
                favorite.c.user_id == user_id,
            )
        )
        videos = result.scalars().all()
        return videos
    except Exception as e:
        logger.error(f"Failed to fetch favorites: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch favorites")
