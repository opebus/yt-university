from modal import Function, functions

from yt_university.services.transcribe import transcribe
from yt_university.stub import stub


@stub.function()
def process(video_url):
    import uuid

    id = uuid.uuid4()

    f = Function.lookup("yt-university", "Downloader.run")
    call = f.spawn(video_url, id)
    results = functions.gather(call)
    audio_path, thumbnail_path, metadata = results[0]

    # with open(audio_path, 'rb') as f:
    #     supabase.storage.from_("audio").upload(file=f, path=audio_path.split("/")[-1])

    # with open(thumbnail_path, 'rb') as f:
    #     supabase.storage.from_("thumbnails").upload(file=f, path=thumbnail_path.split("/")[-1])

    # supabase.table("videos").upsert(metadata, ["id"])

    call = transcribe.spawn(audio_path)
    results = functions.gather(call)
    transcription = results[0]

    # supabase.table("videos").upsert(transcription, ["id"])
