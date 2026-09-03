from __future__ import annotations

import platform
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from faster_whisper import WhisperModel

from .exporters import TranscriptSegment


class TranscriptionCancelled(Exception):
    pass


def cuda_available() -> bool:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return False
    try:
        result = subprocess.run([executable, "--query-gpu=name", "--format=csv,noheader"],
                                check=False, capture_output=True, text=True, timeout=5)
        return result.returncode == 0 and bool(result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


def best_device() -> str:
    return "cuda" if cuda_available() else "cpu"


def recommended_compute_type(device: str) -> str:
    if device == "cuda":
        return "float16"
    if platform.machine().lower() == "arm64":
        return "int8"
    return "int8"


def create_model(model_size: str, device: str = "cpu") -> WhisperModel:
    return WhisperModel(
        model_size,
        device=device,
        compute_type=recommended_compute_type(device),
    )


def transcribe(
    model: WhisperModel,
    audio_path: Path,
    language: str | None,
    progress: Callable[[float], None] | None = None,
) -> tuple[list[TranscriptSegment], str, float]:
    raw_segments, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
        vad_filter=True,
    )
    duration = max(float(info.duration), 0.001)
    segments: list[TranscriptSegment] = []
    for segment in raw_segments:
        segments.append(
            TranscriptSegment(
                start=float(segment.start),
                end=float(segment.end),
                text=segment.text,
            )
        )
        if progress:
            progress(min(float(segment.end) / duration, 1.0))
    if progress:
        progress(1.0)
    return segments, info.language, float(info.language_probability)
