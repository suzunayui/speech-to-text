from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str


def _timestamp(seconds: float, separator: str) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{milliseconds:03d}"


def as_text(segments: list[TranscriptSegment]) -> str:
    return "\n".join(segment.text.strip() for segment in segments).strip() + "\n"


def as_srt(segments: list[TranscriptSegment]) -> str:
    blocks = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(
            f"{index}\n{_timestamp(segment.start, ',')} --> "
            f"{_timestamp(segment.end, ',')}\n{segment.text.strip()}"
        )
    return "\n\n".join(blocks) + "\n"


def as_vtt(segments: list[TranscriptSegment]) -> str:
    blocks = ["WEBVTT"]
    for segment in segments:
        blocks.append(
            f"{_timestamp(segment.start, '.')} --> "
            f"{_timestamp(segment.end, '.')}\n{segment.text.strip()}"
        )
    return "\n\n".join(blocks) + "\n"

