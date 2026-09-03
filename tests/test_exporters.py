from src.exporters import TranscriptSegment, as_srt, as_text, as_vtt


SEGMENTS = [
    TranscriptSegment(0.0, 1.234, " こんにちは "),
    TranscriptSegment(61.5, 62.75, "世界"),
]


def test_text_export() -> None:
    assert as_text(SEGMENTS) == "こんにちは\n世界\n"


def test_srt_export() -> None:
    output = as_srt(SEGMENTS)
    assert "00:00:00,000 --> 00:00:01,234" in output
    assert "00:01:01,500 --> 00:01:02,750" in output


def test_vtt_export() -> None:
    output = as_vtt(SEGMENTS)
    assert output.startswith("WEBVTT\n\n")
    assert "00:00:00.000 --> 00:00:01.234" in output

