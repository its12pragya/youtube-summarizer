"""Helpers for URL parsing, transcript fetching, and formatting."""
import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


def extract_video_id(url: str) -> str:
    """Pull the 11-character video ID out of any YouTube URL format."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"shorts\/([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract a video ID from: {url}")


def seconds_to_timestamp(seconds: float) -> str:
    """Convert 135.2 seconds into '02:15'. Handles hour-long videos."""
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def fetch_transcript(video_id: str, lang: str = "en") -> str:
    """Fetch the transcript and return it as one string with timestamps inline."""
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=[lang, "en"])
    except TranscriptsDisabled:
        raise RuntimeError("This video has transcripts disabled.")
    except NoTranscriptFound:
        raise RuntimeError(f"No transcript found for language '{lang}'.")

    lines = []
    for snippet in fetched:
        ts = seconds_to_timestamp(snippet.start)
        text = snippet.text.replace("\n", " ").strip()
        lines.append(f"[{ts}] {text}")
    return "\n".join(lines)


def truncate_transcript(transcript: str, max_chars: int = 25000) -> tuple[str, bool]:
    """Keep transcripts under the model's context window. Returns (text, was_truncated)."""
    if len(transcript) <= max_chars:
        return transcript, False
    return transcript[:max_chars], True
