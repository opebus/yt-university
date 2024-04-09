import uuid

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID  # Adjust based on your database
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.functions import current_timestamp

from . import Base


class Video(Base):
    __tablename__ = "video_transcription"

    # Use the UUID type for the id column. Adjust the import and type according to your database.
    id: Mapped[UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    youtube_url: Mapped[str] = mapped_column(index=True, unique=True)
    title: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()
    transcription: Mapped[str] = mapped_column()
    transcription_status: Mapped[str] = mapped_column(
        default="pending"
    )  # e.g., pending, in_progress, completed, failed
    uploaded_by: Mapped[str] = mapped_column(index=True)  # username of the uploader
    upload_date: Mapped[str] = Column(
        default=current_timestamp()
    )  # Adjusted to use a datetime type
    is_processed: Mapped[bool] = mapped_column(
        default=False
    )  # flag to indicate if video has been processed

    # Add additional fields as necessary...
