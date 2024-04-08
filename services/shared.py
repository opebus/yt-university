from modal import Function, functions

from yt_university.services.transcribe import transcribe
from yt_university.stub import stub


@stub.function()
def process(video_url):
    import uuid

    id = uuid.uuid4()

    f = Function.lookup("yt-university", "Downloader.run")
    call = f.spawn(video_url, f"{id}/")
    audio_path = functions.gather(call)

    call = transcribe.spawn(audio_path[0], f"{id}/transcription.json")
    res = functions.gather(call)
    return res
