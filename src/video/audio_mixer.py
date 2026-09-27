import os
import subprocess

def handle_background_music(bgm_file, bgm_gdrive_url: str, voice_audio_path: str, session_id: str, bgm_volume: float = 0.15, temp_dir: str = "temp_work") -> str:
    """
    Hòa âm nhạc nền BGM với giọng đọc voice theo tỷ lệ âm lượng bgm_volume (mặc định 15%).
    Nếu không có BGM, trả về file giọng đọc gốc.
    """
    if not bgm_file and not bgm_gdrive_url:
        return voice_audio_path

    os.makedirs(temp_dir, exist_ok=True)
    raw_bgm_path = None

    if bgm_file:
        raw_bgm_path = bgm_file if isinstance(bgm_file, str) else getattr(bgm_file, "name", str(bgm_file))
    elif bgm_gdrive_url:
        try:
            import gdown
            raw_bgm_path = os.path.join(temp_dir, f"bgm_download_{session_id}.mp3")
            gdown.download(bgm_gdrive_url, raw_bgm_path, quiet=True, fuzzy=True)
        except Exception as e:
            print(f"⚠️ Lỗi tải BGM Google Drive: {e}")
            raw_bgm_path = None

    if not raw_bgm_path or not os.path.exists(raw_bgm_path):
        return voice_audio_path

    final_audio_path = os.path.join(temp_dir, f"mixed_audio_{session_id}.wav")
    vol_str = f"{max(0.01, min(1.0, float(bgm_volume))):.2f}"

    cmd = [
        'ffmpeg', '-y',
        '-i', voice_audio_path,
        '-stream_loop', '-1',
        '-i', raw_bgm_path,
        '-filter_complex', f"[1:a]volume={vol_str}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        '-map', '[aout]',
        '-c:a', 'pcm_s16le',
        final_audio_path
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(final_audio_path) and os.path.getsize(final_audio_path) > 1000:
            return final_audio_path
    except Exception as e:
        print(f"⚠️ Lỗi hòa âm BGM: {e}")

    return voice_audio_path
