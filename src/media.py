from __future__ import annotations

import os
import subprocess
from pathlib import Path

import imageio_ffmpeg


def ffmpeg_executable() -> str:
    """Return the app-local FFmpeg executable installed with imageio-ffmpeg."""
    return imageio_ffmpeg.get_ffmpeg_exe()


def ffmpeg_version() -> str:
    executable = ffmpeg_executable()
    completed = subprocess.run(
        [executable, "-version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    return completed.stdout.splitlines()[0]


def extract_audio(source: Path, destination: Path) -> Path:
    """Convert an audio/video file to Whisper-friendly mono 16 kHz WAV."""
    command = [
        ffmpeg_executable(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    subprocess.run(
        command,
        check=True,
        capture_output=True,
        timeout=None,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    return destination

