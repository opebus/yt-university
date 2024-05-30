from collections.abc import Iterator
from pathlib import Path

from modal import Image, Volume, enter, gpu, method

from yt_university.config import DATA_DIR, MODEL_DIR, get_logger
from yt_university.stub import stub

logger = get_logger(__name__)

BASE_MODEL = "openai/whisper-large-v3"
volume = Volume.from_name("yt-university-cache", create_if_missing=True)


def download_model_to_folder():
    from huggingface_hub import snapshot_download
    from transformers.utils.hub import move_cache

    snapshot_download(
        BASE_MODEL,
        local_dir=MODEL_DIR,
        ignore_patterns=["*.pt", "*.bin"],  # Using safetensors
    )

    move_cache()


image = (
    Image.from_registry("nvidia/cuda:12.1.1-devel-ubuntu20.04", add_python="3.12")
    .apt_install("git", "ffmpeg")
    .pip_install(
        "transformers==4.39.3",
        "torch",
        "optimum",
        "accelerate",
        "huggingface-hub",
        "hf-transfer",
        "yt-dlp",
        "ffmpeg-python",
        "wheel",
        "packaging",
        "ninja",
    )
    .run_commands(
        "python -m pip install flash-attn --no-build-isolation", gpu=gpu.A10G()
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_function(download_model_to_folder)
)


@stub.cls(
    timeout=60 * 10,
    container_idle_timeout=5,
    allow_concurrent_inputs=1,
    # using gpu throw index out of bound error from CUDA - unresolved yet
    # on a 2h50m video, T4 cost $0.16 versus A10G at $0.20
    # since processing is asynchronous, ok to use T4
    gpu=gpu.A10G(),
    # cpu=2,
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
        from transformers import (
            AutoModelForSpeechSeq2Seq,
            AutoProcessor,
            pipeline,
            utils,
        )

        logger.info("🥶 Cold starting inference")
        start = time.monotonic_ns()

        device = "cuda" if torch.cuda.is_available() else "cpu"
        device_int = 0 if device == "cuda" else -1
        logger.info(f"Running on {device}")
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            MODEL_DIR,
            torch_dtype=torch_dtype,
            use_safetensors=True,
            attn_implementation="flash_attention_2"
            if utils.is_flash_attn_2_available() == "cuda"
            else "sdpa",
        ).to(device)

        processor = AutoProcessor.from_pretrained(MODEL_DIR)

        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            max_new_tokens=128,
            torch_dtype=torch_dtype,
            chunk_length_s=30,
            batch_size=24,
            return_timestamps=True,
            model_kwargs={"attn_implementation": "flash_attention_2"},
            device=device_int,
        )

        duration_s = (time.monotonic_ns() - start) / 1e9
        logger.info(f"🏎️ Engine started in {duration_s:.0f}s")

    @method()
    def transcribe_segment(self, start: float, end: float, audio_filepath: Path):
        """Transcribe a specific segment of an audio file."""

        import gc
        import tempfile
        import time

        import ffmpeg
        import torch

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
            result = self.pipe(
                f.name, generate_kwargs={"language": "<|en|>", "task": "transcribe"}
            )
            logger.info(
                f"Transcribed segment from {start:.2f} to {end:.2f} in {time.time() - t0:.2f} seconds."
            )

            # Adjust timestamps to original audio timeline
            for segment in result["chunks"]:
                restored_timestamp = (
                    segment["timestamp"][0] + start
                    if segment["timestamp"][0] is not None
                    else None,
                    # Fix for error faced
                    # Whisper did not predict an ending timestamp, which can happen if audio is cut off in the middle of a word. Also make sure WhisperTimeStampLogitsProcessor was used during generation.
                    segment["timestamp"][1] + start
                    if segment["timestamp"][1] is not None
                    else None,
                )
                segment["timestamp"] = restored_timestamp

        gc.collect()
        with torch.no_grad():
            torch.cuda.empty_cache()
        return result


@stub.function(image=image, volumes={DATA_DIR: volume}, timeout=900, keep_warm=1)
def transcribe(
    audio_filepath: Path,
):
    segment_gen = split_silences(str(audio_filepath))
    output_segments = []

    whisper = Whisper()
    for result in whisper.transcribe_segment.starmap(
        segment_gen, kwargs=dict(audio_filepath=audio_filepath)
    ):
        output_segments.extend(result["chunks"])

    return {
        "chunks": output_segments,
        "language": "en",
    }


def split_silences(
    path: str, min_segment_length: float = 480.0, min_silence_length: float = 1.0
) -> Iterator[tuple[float, float]]:
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
