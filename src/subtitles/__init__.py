"""
Subtitles Module: Alignment, Formatting & YouTube Chapters
"""
from .formatter import format_timestamp_srt, format_srt_max_two_lines
from .whisper_aligner import align_script_with_whisper_segments, extract_whisper_segments_and_srt
from .chapters import recalculate_and_inject_youtube_chapters

__all__ = [
    "format_timestamp_srt",
    "format_srt_max_two_lines",
    "align_script_with_whisper_segments",
    "extract_whisper_segments_and_srt",
    "recalculate_and_inject_youtube_chapters"
]
