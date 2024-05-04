from uuid import uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AlchemyBase, MetadataMixin


class Playlist(AlchemyBase, MetadataMixin):
    __tablename__ = "playlist"

    id: Mapped[str] = mapped_column(default=uuid4, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)

    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"))

    user = relationship("User", back_populates="playlists")
    videos = relationship("PlaylistVideo", back_populates="playlist")
