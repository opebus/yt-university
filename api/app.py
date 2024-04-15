import time

import yt_university.config as config
from fastapi import FastAPI, Query
from yt_university.services.shared import process
from contextlib import asynccontextmanager

logger = config.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Function that handles startup and shutdown events.
    To understand more, read https://fastapi.tiangolo.com/advanced/events/
    """
    from yt_university.database import sessionmanager

    yield
    if sessionmanager._engine is not None:
        # Close the DB connection
        await sessionmanager.close()


web_app = FastAPI(lifespan=lifespan)

# A transcription taking > 10 minutes should be exceedingly rare.
MAX_JOB_AGE_SECS = 10 * 60


@web_app.post("/api/transcribe")
async def transcribe_job(
    video_url: str = Query(..., description="The URL of the video to transcribe"),
):
    now = int(time.time())
    try:
        # query database to get job
        job = {"start_time": now}
        if now - job.start_time < MAX_JOB_AGE_SECS:
            logger.info(
                f"Found existing, unexpired call ID {job.call_id} already in progress."
            )
        return {"call_id": job.call_id, "status": "in_progress"}
    except Exception:
        pass
    # f = Function.lookup("yt-university", "Downloader.run")
    # call = f.spawn(video_url)
    # audio_path = functions.gather(call)
    # print('this is the audio path', audio_path)

    # call = transcribe.spawn(audio_path[0], "transcription.json")
    # res = functions.gather(call)

    call = process.spawn(video_url)

    logger.info(f"Started new call ID {call.object_id}")
    return {"call_id": call.object_id, "status": "in_progress"}
