from urllib.parse import parse_qs, urlparse


def sanitize_youtube_url(url):
    # Parse the URL
    parsed_url = urlparse(url)

    # Validate that it is a YouTube URL
    if "youtube.com" not in parsed_url.netloc and "youtu.be" not in parsed_url.netloc:
        raise ValueError("Invalid YouTube URL")

    # Extract query parameters
    query_params = parse_qs(parsed_url.query)
    video_id = query_params.get("v")

    # Check if video ID is present
    if video_id is None:
        raise ValueError("YouTube URL does not contain a valid video ID")

    # Construct a clean YouTube URL with only the video ID
    safe_url = f"https://www.youtube.com/watch?v={video_id[0]}"
    return safe_url
