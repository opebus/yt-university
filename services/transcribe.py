from pathlib import Path
from typing import Iterator, Tuple

from modal import Function, Image, Volume, enter, method

from yt_university.config import DATA_DIR, MODEL_DIR, get_logger
from yt_university.stub import stub

logger = get_logger(__name__)

BASE_MODEL = "openai/whisper-large-v3"
volume = Volume.from_name("yt-university-cache", create_if_missing=True)


def download_model_to_folder():
    from huggingface_hub import snapshot_download

    snapshot_download(
        BASE_MODEL,
        local_dir=MODEL_DIR,
        ignore_patterns=["*.pt", "*.bin"],  # Using safetensors
    )


image = (
    Image.from_registry("nvidia/cuda:12.1.1-devel-ubuntu22.04", add_python="3.11")
    .apt_install("git", "ffmpeg")
    .pip_install(
        "transformers",
        "huggingface-hub",
        "hf-transfer",
        "torch",
        "yt-dlp",
        "ffmpeg-python",
        "wheel",
        "packaging",
        "ninja",
    )
    .run_commands("python -m pip install flash-attn --no-build-isolation", gpu="A10G")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_function(download_model_to_folder, timeout=60 * 20)
)


@stub.cls(
    timeout=60 * 10,
    container_idle_timeout=60,
    allow_concurrent_inputs=2,
    gpu="A10G",
    image=image,
    volumes={DATA_DIR: volume},
)
class Whisper:
    """
    Whisper model class for transcribing audio on a per-segment basis.
    """

    @enter()
    def setup(self):
        """Set up the Whisper model for transcription."""
        import time

        import torch
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

        logger.info("🥶 Cold starting inference")
        start = time.monotonic_ns()

        device = "cuda" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            MODEL_DIR,
            torch_dtype=torch_dtype,
            use_safetensors=True,
            attn_implementation="flash_attention_2",
        ).to(device)

        processor = AutoProcessor.from_pretrained(MODEL_DIR)

        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            max_new_tokens=128,
            torch_dtype=torch_dtype,
            device=device,
            chunk_length_s=30,
            batch_size=16,
            return_timestamps=True,
            model_kwargs={"attn_implementation": "flash_attention_2"},
        )

        duration_s = (time.monotonic_ns() - start) / 1e9
        logger.info(f"🏎️ Engine started in {duration_s:.0f}s")

    @method()
    def transcribe_segment(self, start: float, end: float, audio_filepath: Path):
        """Transcribe a specific segment of an audio file."""
        import tempfile
        import time

        import ffmpeg

        t0 = time.time()
        with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
            (
                ffmpeg.input(str(audio_filepath))
                .filter("atrim", start=start, end=end)
                .output(f.name)
                .overwrite_output()
                .run(quiet=True)
            )
            # Transcribe the processed audio segment
            result = self.pipe(f.name)
            logger.info(
                f"Transcribed segment from {start:.2f} to {end:.2f} in {time.time() - t0:.2f} seconds."
            )

            # Adjust timestamps to original audio timeline
            for segment in result["chunks"]:
                restored_timestamp = (
                    segment["timestamp"][0] + start,
                    segment["timestamp"][1] + start,
                )
                segment["timestamp"] = restored_timestamp

            return result


@stub.function(
    image=image,
    volumes={DATA_DIR: volume},
    timeout=900,
)
def transcribe(
    audio_filepath: Path,
    result_path: Path,
):
    import json

    segment_gen = split_silences(str(audio_filepath))
    output_text = ""
    output_segments = []

    f = Function.lookup("yt-university", "Whisper.transcribe_segment")
    for result in f.starmap(segment_gen, kwargs=dict(audio_filepath=audio_filepath)):
        output_text += result["text"]
        for chunk in result["chunks"]:
            output_segments.append(chunk["timestamp"])

    result = {
        "text": output_text,
        "segments": output_segments,
        "language": "en",
    }

    logger.info(f"Writing whisper transcription to {result_path}")
    with open(DATA_DIR + result_path, "w") as f:
        json.dump(result, f, indent=4)
    volume.commit()


def split_silences(
    path: str, min_segment_length: float = 30.0, min_silence_length: float = 1.0
) -> Iterator[Tuple[float, float]]:
    """
    Split audio file into contiguous chunks using the ffmpeg `silencedetect` filter.
    Yields tuples (start, end) of each chunk in seconds.
    """

    import re

    import ffmpeg

    silence_end_re = re.compile(
        r" silence_end: (?P<end>[0-9]+(\.?[0-9]*)) \| silence_duration: (?P<dur>[0-9]+(\.?[0-9]*))"
    )
    metadata = ffmpeg.probe(path)
    duration = float(metadata["format"]["duration"])

    try:
        reader = (
            ffmpeg.input(str(path))
            .filter("silencedetect", n="-10dB", d=min_silence_length)
            .output("pipe:", format="null")
            .run_async(pipe_stderr=True)
        )
    except Exception as e:
        logger.error(f"FFmpeg error: {e.stderr}")

    cur_start = 0.0
    num_segments = 0

    while True:
        line = reader.stderr.readline().decode("utf-8")
        if not line:
            break
        match = silence_end_re.search(line)
        if match:
            silence_end, silence_dur = match.group("end"), match.group("dur")
            split_at = float(silence_end) - (float(silence_dur) / 2)

            if (split_at - cur_start) < min_segment_length:
                continue

            yield cur_start, split_at
            cur_start = split_at
            num_segments += 1

    # silencedetect can place the silence end *after* the end of the full audio segment.
    # Such segments definitions are negative length and invalid.
    if duration > cur_start:
        yield cur_start, duration
        num_segments += 1
    logger.info(f"Split {path} into {num_segments} segments")
