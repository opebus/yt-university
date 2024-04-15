import logging

from modal import Image, Secret, Volume

from yt_university.config import DATA_DIR
from yt_university.services.download import Downloader
from yt_university.services.transcribe import transcribe
from yt_university.stub import stub

image = (
    Image.debian_slim(python_version="3.11")
    .apt_install("libpq-dev")
    .pip_install("python-dotenv", "psycopg2", "asyncpg", "sqlalchemy", "supabase")
)

volume = Volume.from_name("yt-university-cache", create_if_missing=True)

logger = logging.getLogger(__name__)


@stub.function(
    container_idle_timeout=60,
    image=image,
    timeout=600,
    secrets=[Secret.from_name("supabase")],
    volumes={DATA_DIR: volume},
)
async def process(video_url):
    import os
    import uuid

    from supabase import Client, create_client
    from yt_university.database import get_db_session
    from yt_university.models import Video

    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    id = uuid.uuid4()

    downloader = Downloader()

    download_call = downloader.run.spawn(video_url, id)
    result = download_call.get()
    audio_path, thumbnail_path, metadata = result

    volume.reload()

    with open(audio_path, "rb") as f:
        supabase.storage.from_("audio").upload(file=f, path=audio_path.split("/")[-1])

    with open(thumbnail_path, "rb") as f:
        supabase.storage.from_("thumbnail").upload(
            file=f, path=thumbnail_path.split("/")[-1]
        )

    session = await anext(get_db_session())
    video = Video(
        id=id,
        url=video_url,
        title=metadata["title"],
        description=metadata["description"],
        duration=metadata["duration"],
        language=metadata["language"],
    )
    await add_video(session, video)

    transcribe_call = transcribe.spawn(audio_path)
    transcription = transcribe_call.get()
    await update_transcription(session, id, transcription)


async def add_video(db_session, video_data: any) -> any:
    db_session.add(video_data)
    await db_session.commit()
    await db_session.refresh(video_data)

    return video_data


async def update_transcription(
    db_session, video_id: int, new_transcription: str
) -> any:
    from sqlalchemy.future import select
    from fastapi import HTTPException
    from yt_university.models import Video

    video = (
        await db_session.scalars(select(Video).where(Video.id == video_id))
    ).first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    video.transcription = new_transcription

    await db_session.commit()
    await db_session.refresh(video)

    return video
