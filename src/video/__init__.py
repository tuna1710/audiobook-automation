"""
Video Module: Audio Mixing, Waveforms, Thumbnails & FFmpeg Compositor
"""
from .audio_mixer import handle_background_music
from .waveform import build_waveform_filter
from .thumbnail import extract_thumbnail_metadata, generate_ctr_booster_thumbnail, find_system_font
from .compositor import (
    render_ultimate_video,
    render_ultimate_video_v19,
    render_ultimate_video_v18,
    escape_ffmpeg_filter_path,
    get_best_video_encoder
)

__all__ = [
    "handle_background_music",
    "build_waveform_filter",
    "extract_thumbnail_metadata",
    "generate_ctr_booster_thumbnail",
    "find_system_font",
    "render_ultimate_video",
    "render_ultimate_video_v19",
    "render_ultimate_video_v18",
    "escape_ffmpeg_filter_path",
    "get_best_video_encoder"
]
