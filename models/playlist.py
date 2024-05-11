from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import AlchemyBase

playlist_video = Table(
    "playlist_video",
    AlchemyBase.metadata,
    Column("playlist_id", ForeignKey("playlist.id"), primary_key=True),
    Column("video_id", ForeignKey("video.id"), primary_key=True),
    Column("created_at", DateTime, server_default=func.now()),
)


class Playlist(AlchemyBase):
    __tablename__ = "playlist"

    id: Mapped[UUID] = mapped_column(default=uuid4, primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)

    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"))

    user = relationship("User", back_populates="playlists")
    videos = relationship("Video", secondary=playlist_video, back_populates="playlists")
