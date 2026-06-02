"""Audio format handling and conversion utilities."""

import subprocess
from pathlib import Path

ALLOWED_EXTENSIONS = {".webm", ".mp3", ".wav", ".m4a", ".mp4", ".mov"}


def validate_audio_format(filename: str) -> bool:
    """Check file extension against allowed list."""
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def detect_no_audio_track(input_path: str) -> bool:
    """Check if a media file has no audio stream using ffprobe.

    Returns True if the file has no audio track, False otherwise.
    On ffprobe errors, returns False (let ffmpeg fail later with a descriptive message).
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "csv=p=0",
                input_path,
            ],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() == ""
    except Exception:
        return False


def convert_to_wav(input_path: str, output_path: str) -> str:
    """Convert audio to 16kHz mono WAV using ffmpeg.

    Args:
        input_path: Path to input audio file.
        output_path: Path for output WAV file.

    Returns:
        The output_path on success.

    Raises:
        subprocess.CalledProcessError: If ffmpeg fails.
    """
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            output_path,
        ],
        check=True,
        capture_output=True,
    )
    return output_path

