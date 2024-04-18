import logging
import pathlib


def get_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(levelname)s: %(asctime)s: %(name)s  %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger


DATA_DIR = "/data/"
MODEL_DIR = "/model/"  # Location of modal checkpoint.

RAW_AUDIO_DIR = pathlib.Path(DATA_DIR, "raw_audio")
# Stores metadata of individual podcast episodes as JSON.
PODCAST_METADATA_DIR = pathlib.Path(DATA_DIR, "podcast_metadata")
# Completed episode transcriptions. Stored as flat files with
# files structured as '{guid_hash}-{model_slug}.json'.
TRANSCRIPTIONS_DIR = pathlib.Path(DATA_DIR, "transcriptions")
# Searching indexing files, refreshed by scheduled functions.
SEARCH_DIR = pathlib.Path(DATA_DIR, "search")

MAX_JOB_AGE_SECS = 2 * 60
