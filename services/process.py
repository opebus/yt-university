import logging

from modal import Secret, Volume

from yt_university.config import DATA_DIR
from yt_university.crud.video import upsert_video
from yt_university.services.download import Downloader
from yt_university.services.summarize import categorize_text, generate_summary
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
    keep_warm=1,
)
async def process(video_url: str, user_id: str):
    from yt_university.database import get_db_session
    from yt_university.models import Video

    downloader = Downloader()

    download_call = downloader.run.spawn(video_url)
    result = download_call.get()
    audio_path, _, metadata = result

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
        user_id=user_id,
        favorite_count=0,
    )

    async with get_db_session() as session:
        video = await upsert_video(session, video.id, video.to_dict())

        transcription = transcribe.spawn(audio_path).get()
        video_data = await upsert_video(
            session, video.id, {"transcription": transcription}
        )

        summary = generate_summary.spawn(video.title, transcription).get()
        video_data = await upsert_video(session, video.id, {"summary": summary})

        category = categorize_text.spawn(video.title, summary).get()
        video_data = await upsert_video(session, video.id, {"category": category})

        # related = get_related_content.spawn(video.url).get()
        # print(related)
        # video_data = await upsert_video(session, video.id, {"related_content": related})

    return video_data
