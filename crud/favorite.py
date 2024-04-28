import logging

from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def add_favorite(session, user_id: str, video_id: str):
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.future import select

    from yt_university.models import Favorite

    try:
        # Fetch any existing favorite, including soft-deleted ones
        existing_favorite = await session.execute(
            select(Favorite).where(
                Favorite.user_id == user_id, Favorite.video_id == video_id
            )
        )
        favorite_instance = existing_favorite.scalars().first()

        if favorite_instance:
            if favorite_instance.deleted_at:
                # If the favorite is soft-deleted, restore it
                favorite_instance.undelete()
                message = "Favorite restored successfully."
            else:
                # If the favorite already exists and is not deleted, return an error
                raise HTTPException(status_code=400, detail="Favorite already exists")
        else:
            # If no favorite exists, create a new one
            new_favorite = Favorite(user_id=user_id, video_id=video_id)
            session.add(new_favorite)
            message = "Favorite added successfully."

        # Commit changes and refresh the instance
        await session.commit()
        if favorite_instance:
            await session.refresh(favorite_instance)
        else:
            await session.refresh(new_favorite)

        return {"status": "success", "message": message}
    except HTTPException as e:
        raise e
    except SQLAlchemyError as e:
        logger.error(f"Failed to add/restore favorite: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to add/restore favorite in database"
        )


async def remove_favorite(session, user_id: str, video_id: str):
    from sqlalchemy.future import select

    from yt_university.models.favorite import Favorite

    try:
        favorite = await session.execute(
            select(Favorite).where(
                Favorite.user_id == user_id, Favorite.video_id == video_id
            )
        )
        favorite_instance = favorite.scalars().first()
        if not favorite_instance:
            raise HTTPException(status_code=404, detail="Favorite not found")

        favorite_instance.delete()
        await session.commit()
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to remove favorite: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to remove favorite")


async def get_user_favorites(session, user_id: str):
    from sqlalchemy.future import select

    from yt_university.models.favorite import Favorite
    from yt_university.models.video import Video

    try:
        result = await session.execute(
            select(Video).join(Favorite).where(Favorite.user_id == user_id)
        )
        videos = result.scalars().all()
        return videos
    except Exception as e:
        logger.error(f"Failed to fetch favorites: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch favorites")
