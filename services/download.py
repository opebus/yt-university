import logging

from modal import Image, Volume, method

from yt_university.config import DATA_DIR
from yt_university.stub import stub

downloader_image = (
    Image.debian_slim(python_version="3.10").apt_install("ffmpeg").pip_install("yt-dlp")
)

volume = Volume.from_name("yt-university-cache", create_if_missing=True)

logger = logging.getLogger(__name__)


@stub.cls(
    container_idle_timeout=5,
    image=downloader_image,
    timeout=60 * 10,
    volumes={DATA_DIR: volume},
)
class Downloader:
    @method()
    def run(self, url):
        video_path, thumbnail_path, meta_dict = self.get_youtube(url)
        wav_path = self.convert_to_wav(video_path)
        return wav_path, thumbnail_path, meta_dict

    def get_youtube(self, video_url):
        """
        Downloads the audio from a YouTube video and saves metadata to a .info.json file.
        """
        import yt_dlp

        ydl_opts = {
            "format": "bestaudio[ext=m4a]",
            "writethumbnail": True,
            "outtmpl": f"{DATA_DIR}%(id)s.%(ext)s",
        }

        meta_dict = {}
        metadata_keys = [
            "id",
            "title",
            "description",
            "channel",
            "channel_id",
            "date",
            "duration",
            "language",
            "upload_date",
            "thumbnail",
        ]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            meta_dict = {key: info.get(key, "") for key in metadata_keys}
            logger.info(meta_dict)
            ydl.process_info(info)

        video_path = f"{DATA_DIR}{meta_dict['id']}.{info['ext']}"
        thumbnail_path = f"{DATA_DIR}{meta_dict['id']}.webp"

        logger.info(f"Successfully downloaded {video_url} to {video_path}")
        volume.commit()

        return video_path, thumbnail_path, meta_dict

    def convert_to_wav(self, video_file_path, offset=0):
        """
        Converts an m4a audio file to WAV format using ffmpeg.
        """
        import os

        if not os.path.exists(video_file_path):
            raise FileNotFoundError("m4a file not found.")

        out_path = video_file_path.replace("m4a", "wav")
        if os.path.exists(out_path):
            logger.info(f"WAV file already exists: {out_path}")
            return out_path

        offset_args = f"-ss {offset}" if offset > 0 else ""
        conversion_command = f'ffmpeg -hide_banner -v warning -stats {offset_args} -i "{video_file_path}" -ar 16000 -ac 1 -c:a pcm_s16le "{out_path}"'
        if os.system(conversion_command) != 0:
            raise RuntimeError("Error converting file to WAV.")

        logger.info(f"Conversion to WAV ready: {out_path}")
        volume.commit()

        return out_path
