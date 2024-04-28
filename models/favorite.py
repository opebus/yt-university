from sqlalchemy import ForeignKey, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yt_university.models.video import Video

# Importing for more specific types
from . import AlchemyBase, MetadataMixin


class Favorite(AlchemyBase, MetadataMixin):
    __tablename__ = "favorite"

    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), primary_key=True)
    video_id: Mapped[str] = mapped_column(ForeignKey("video.id"), primary_key=True)

    user = relationship("User", back_populates="videos")
    video = relationship("Video", back_populates="users")

    @staticmethod
    def after_insert(mapper, connection, target):
        video_table = Video.__table__
        connection.execute(
            video_table.update()
            .where(video_table.c.id == target.video_id)
            .values(favorite_count=video_table.c.favorite_count + 1)
        )

    @staticmethod
    def after_delete(mapper, connection, target):
        video_table = Video.__table__
        connection.execute(
            video_table.update()
            .where(video_table.c.id == target.video_id)
            .values(favorite_count=video_table.c.favorite_count - 1)
        )


# Event listeners that trigger after inserting or deleting a favorite
event.listen(Favorite, "after_insert", Favorite.after_insert)
event.listen(Favorite, "after_delete", Favorite.after_delete)
