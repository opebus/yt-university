import logging

from modal import Image, Secret, Volume

from yt_university.config import DATA_DIR
from yt_university.services.download import Downloader
from yt_university.services.transcribe import transcribe
from yt_university.stub import stub

image = Image.debian_slim(python_version="3.11").pip_install("supabase")

volume = Volume.from_name("yt-university-cache", create_if_missing=True)

logger = logging.getLogger(__name__)


@stub.function(
    container_idle_timeout=60,
    image=image,
    timeout=600,
    secrets=[Secret.from_name("supabase")],
    volumes={DATA_DIR: volume},
)
def process(video_url):
    import os
    import uuid

    from supabase import Client, create_client

    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
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

    # supabase.table("videos").upsert(metadata, ["id"])

    transcribe_call = transcribe.spawn(audio_path)
    transcription = transcribe_call.get()

    # supabase.table("videos").upsert(transcription, ["id"])
