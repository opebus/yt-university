import logging

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger(__name__)


async def add_playlist(session, playlist_data):
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.future import select

    from yt_university.models import Playlist, User, Video

    try:
        data = jsonable_encoder(playlist_data)

        video_ids = data.pop("video_ids", None)
        user_id = data.pop("user_id", None)

        playlist = Playlist(**data)

        user = await session.execute(select(User).where(User.id == user_id))
        playlist.user = user.scalars().first()

        if video_ids:
            videos = await session.execute(select(Video).where(Video.id.in_(video_ids)))
            playlist.videos.extend(videos.scalars().all())

        session.add(playlist)
        await session.commit()
        await session.refresh(playlist)
        return playlist
    except SQLAlchemyError as e:
        logger.error(f"Failed to add playlist: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to add playlist to database"
        )


async def update_playlist(session, playlist_id: str, new_data: dict):
    from fastapi import HTTPException
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.future import select

    from yt_university.models import Playlist

    try:
        result = await session.execute(
            select(Playlist).where(Playlist.id == playlist_id)
        )
        playlist = result.scalars().first()

        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")

        for key, value in new_data.items():
            if value is not None and hasattr(playlist, key):
                setattr(playlist, key, value)

        await session.commit()
        await session.refresh(playlist)
        return playlist
    except SQLAlchemyError as e:
        logger.error(f"Failed to edit playlist: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500, detail="Internal server error during playlist edit"
        )


async def add_videos_to_playlist(session, playlist_id: str, video_ids: list):
    from sqlalchemy.future import select
    from sqlalchemy.orm import joinedload

    from yt_university.models import Playlist, Video

    try:
        playlist_result = await session.execute(
            select(Playlist)
            .options(joinedload(Playlist.videos))
            .where(Playlist.id == playlist_id)
        )
        playlist = playlist_result.scalars().first()

        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")

        videos_result = await session.execute(
            select(Video).where(Video.id.in_(video_ids))
        )
        videos = videos_result.scalars().all()

        if not videos:
            raise HTTPException(status_code=404, detail="No videos found")
        for video in videos:
            if video not in playlist.videos:
                playlist.videos.append(video)

        await session.commit()
        return playlist

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to add videos to playlist: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Internal server error during adding videos to playlist",
        )


async def remove_videos_from_playlist(session, playlist_id: str, video_ids: list):
    from sqlalchemy.future import select
    from sqlalchemy.orm import joinedload

    from yt_university.models import Playlist, Video

    try:
        playlist_result = await session.execute(
            select(Playlist)
            .options(joinedload(Playlist.videos))
            .where(Playlist.id == playlist_id)
        )
        playlist = playlist_result.scalars().first()

        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")

        videos_result = await session.execute(
            select(Video).where(Video.id.in_(video_ids))
        )
        videos = videos_result.scalars().all()

        if not videos:
            raise HTTPException(status_code=404, detail="No videos found")

        for video in videos:
            if video in playlist.videos:
                playlist.videos.remove(video)

        await session.commit()

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to remove videos from playlist: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Internal server error during removing videos from playlist",
        )


async def delete_playlist(session, playlist_id: str):
    from sqlalchemy.future import select

    from yt_university.models import Playlist

    try:
        result = await session.execute(
            select(Playlist).where(Playlist.id == playlist_id)
        )
        playlist = result.scalars().first()

        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")

        await session.delete(playlist)
        await session.commit()

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to delete playlist: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500, detail="Internal server error during playlist deletion"
        )


async def get_all_playlists(session, user_id=None):
    from sqlalchemy.future import select

    from yt_university.models import Playlist

    try:
        query = select(Playlist).order_by(Playlist.name)

        if user_id:
            query = query.where(Playlist.user_id == user_id)

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
