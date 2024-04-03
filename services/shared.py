from modal import Function, functions

from yt_university.services.transcribe import transcribe
from yt_university.stub import stub


@stub.function()
def process(video_url):
    f = Function.lookup("yt-university", "Downloader.run")
    call = f.spawn(video_url)
    audio_path = functions.gather(call)
    print("this is the audio path", audio_path)

    call = transcribe.spawn(audio_path[0], "transcription.json")
    res = functions.gather(call)
    return res
