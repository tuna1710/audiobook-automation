"""
Video Module: Audio Mixing, Waveforms, Thumbnails & FFmpeg Compositor
"""
from .audio_mixer import handle_background_music
from .waveform import build_waveform_filter
from .thumbnail import extract_thumbnail_metadata, generate_ctr_booster_thumbnail
from .compositor import render_ultimate_video

__all__ = [
    "handle_background_music",
    "build_waveform_filter",
    "extract_thumbnail_metadata",
    "generate_ctr_booster_thumbnail",
    "render_ultimate_video"
]
