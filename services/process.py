import logging

from modal import Secret, Volume

from yt_university.config import DATA_DIR
from yt_university.crud.video import upsert_video
from yt_university.services.download import Downloader
from yt_university.services.summarize import summarize
from yt_university.services.transcribe import transcribe
from yt_university.stub import shared_webapp_image, stub

logger = logging.getLogger(__name__)

volume = Volume.from_name("yt-university-cache", create_if_missing=True)


@stub.function(
    container_idle_timeout=5,
    image=shared_webapp_image,
    timeout=600,
    secrets=[Secret.from_name("university")],
    volumes={DATA_DIR: volume},
)
async def process(video_url):
    # import os

    # from supabase import Client, create_client

    from yt_university.database import get_db_session
    from yt_university.models import Video

    # url: str = os.getenv("SUPABASE_URL")
    # key: str = os.getenv("SUPABASE_KEY")

    # supabase: Client = create_client(url, key)

    downloader = Downloader()

    download_call = downloader.run.spawn(video_url)
    result = download_call.get()
    audio_path, thumbnail_path, metadata = result

    volume.reload()

    video = Video(
        id=metadata["id"],
        url=video_url,
        title=metadata["title"],
        description=metadata["description"],
        duration=metadata["duration"],
        language=metadata["language"],
        channel=metadata["channel"],
        channel_id=metadata["channel_id"],
        uploaded_at=metadata["upload_date"],
        thumbnail=metadata["thumbnail"],
    )

    # with open(audio_path, "rb") as f:
    #     try:
    #         supabase.storage.from_("audio").upload(
    #             file=f, path=audio_path.split("/")[-1]
    #         )
    #     except Exception as e:
    #         if "The resource already exists" in str(e):
    #             supabase.storage.from_("audio").update(
    #                 file=f, path=audio_path.split("/")[-1]
    #             )
    #         else:
    #             raise e
    # os.remove(audio_path)

    # with open(thumbnail_path, "rb") as f:
    #     try:
    #         supabase.storage.from_("thumbnail").upload(
    #             file=f, path=thumbnail_path.split("/")[-1]
    #         )
    #     except Exception as e:
    #         if "The resource already exists" in str(e):
    #             supabase.storage.from_("thumbnail").update(
    #                 file=f, path=thumbnail_path.split("/")[-1]
    #             )
    #         else:
    #             raise e
    # os.remove(thumbnail_path)
    async with get_db_session() as session:
        video = await upsert_video(session, video.id, video.to_dict())

        transcription = transcribe.spawn(audio_path).get()
        video_data = await upsert_video(
            session, video.id, {"transcription": transcription}
        )

        summary = summarize.spawn(transcription).get()
        video_data = await upsert_video(session, video.id, {"summary": summary})

    return video_data
