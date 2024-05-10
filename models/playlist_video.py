from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Importing for more specific types
from .base import AlchemyBase, MetadataMixin


class PlaylistVideo(AlchemyBase, MetadataMixin):
    __tablename__ = "playlist_video"

    playlist_id: Mapped[UUID] = mapped_column(
        ForeignKey("playlist.id"), nullable=False, primary_key=True, index=True
    )
    video_id: Mapped[str] = mapped_column(
        ForeignKey("video.id"), nullable=False, primary_key=True, index=True
    )

    playlist = relationship("Playlist", back_populates="videos")
    video = relationship("Video", back_populates="playlists")
