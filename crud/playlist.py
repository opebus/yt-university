import logging

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select

logger = logging.getLogger(__name__)


async def add_playlist(session, playlist_data):
    from yt_university.models import Playlist

    try:
        playlist = Playlist(**playlist_data)
        session.add(playlist)
        await session.commit()
        await session.refresh(playlist)
        return playlist
    except Exception as e:
        logger.error(f"Failed to add playlist: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to add playlist to database"
        )


async def update_playlist(session, playlist_id: str, update_data: dict):
    from yt_university.models import Playlist

    try:
        result = await session.execute(
            select(Playlist).where(Playlist.id == playlist_id)
        )
        playlist = result.scalars().first()

        if playlist:
            for key, value in update_data.items():
                if hasattr(playlist, key):
                    setattr(playlist, key, value)
                else:
                    logger.warning(
                        f"Attempted to update non-existent field '{key}' on Playlist model."
                    )
        else:
            raise HTTPException(status_code=404, detail="Playlist not found")

        await session.commit()
        await session.refresh(playlist)
        return playlist

    except HTTPException as e:
        raise e
    except SQLAlchemyError as e:
        logger.error(f"Database error during update operation: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500, detail="Internal server error during playlist update"
        )
    except Exception as e:
        logger.error(f"Failed to update playlist: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500, detail="Internal server error during playlist update"
        )


async def delete_playlist(session, playlist_id):
    from yt_university.models import Playlist

    try:
        result = await session.execute(
            select(Playlist).where(Playlist.id == playlist_id)
        )
        playlist = result.scalars().first()

        if playlist:
            await session.delete(playlist)
            await session.commit()
        else:
            raise HTTPException(status_code=404, detail="Playlist not found")

    except HTTPException as e:
        raise e
    except SQLAlchemyError as e:
        logger.error(f"Database error during delete operation: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500, detail="Internal server error during playlist deletion"
        )
    except Exception as e:
        logger.error(f"Failed to delete playlist: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500, detail="Internal server error during playlist deletion"
        )


async def get_all_playlists(session, user_id=None):
    from sqlalchemy.future import select
    from sqlalchemy.orm import joinedload

    from yt_university.models import Playlist

    try:
        # Start with a basic query to select all playlists
        query = select(Playlist).order_by(Playlist.name)

        # If a user_id is provided, modify the query to filter playlists by this user
        if user_id:
            query = query.where(Playlist.user_id == user_id).options(
                joinedload(Playlist.user)
            )

        result = await session.execute(query)
        playlists = result.scalars().all()

        return playlists
    except Exception as e:
        logger.error(f"Database error during fetching playlists: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during fetching playlists"
        )


async def get_playlist(session, playlist_id):
    from fastapi import HTTPException
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.future import select
    from sqlalchemy.orm import joinedload

    from yt_university.models import Playlist

    try:
        stmt = (
            select(Playlist)
            .options(joinedload(Playlist.videos))
            .where(Playlist.id == playlist_id)
        )
        result = await session.execute(stmt)
        playlist = result.scalars().first()

        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")

        return playlist
    except SQLAlchemyError as e:
        logger.error(f"Database error during fetch operation: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during playlist fetch"
        )
