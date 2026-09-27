import os
import re
import shutil
import subprocess

def extract_thumbnail_metadata(raw_script: str, fallback_title: str):
    """
    BÓC TÁCH DỮ LIỆU THUMBNAIL TỪ KỊCH BẢN:
    - Tìm text gợi ý ngắn gọn (3 - 5 chữ).
    - Tìm visual prompt cho thumbnail nếu có.
    """
    thumb_text = ""
    text_patterns = [
        r'(?:-\s*Chữ lớn trên ảnh\s*(?:\(tối đa \d+ chữ\))?\s*:\s*)([^\r\n]+)',
        r'(?:-\s*Text gợi ý hiển thị trên Thumbnail.*?:\s*)([^\r\n]+)',
        r'(?:Text gợi ý trên Thumbnail.*?:\s*)([^\r\n]+)',
        r'(?:Text Thumbnail.*?:\s*)([^\r\n]+)'
    ]
    for pat in text_patterns:
        m = re.search(pat, raw_script, re.IGNORECASE)
        if m:
            cand = m.group(1).strip().replace('"', '').replace("'", "")
            if 2 <= len(cand) <= 35:
                thumb_text = cand
                break

    if not thumb_text:
        words = fallback_title.split(':')
        first_part = words[0].strip()
        first_part = re.sub(r'^(?:kỳ án|vụ án|thảm án|hồ sơ)\s*', '', first_part, flags=re.IGNORECASE)
        thumb_text = ' '.join(first_part.split()[:4]).upper()

    visual_patterns = [
        r'(?:\[Ý TƯỞNG THUMBNAIL\]:?\s*(?:-\s*Visual:?\s*|\s*))([^\r\n]+(?:\n[^\r\n-]+)*)',
        r'(?:-\s*Visual:?\s*)([^\r\n]+)'
    ]
    thumb_visual = ""
    for pat in visual_patterns:
        m = re.search(pat, raw_script, re.IGNORECASE)
        if m:
            cand = m.group(1).strip()
            if len(cand) > 15:
                thumb_visual = cand
                break

    return thumb_text.strip().upper(), thumb_visual.strip()

def generate_ctr_booster_thumbnail(
    video_path: str,
    raw_script: str,
    fallback_title: str,
    session_id: str,
    outputs_dir: str = "outputs",
    fonts_dir: str = "fonts"
) -> str:
    """
    TỰ ĐỘNG TẠO THUMBNAIL YOUTUBE CTR BOOSTER (1280x720 HD):
    - Bóc tách Text giật gân từ kịch bản (ví dụ: "THƯỢC DƯỢC ĐEN").
    - Tạo ảnh nền 1280x720 từ video cao trào hoặc Gothic Noir background.
    - Chèn chữ Vàng viền đen khối 3D, đổ bóng sâu, đặt ở Safe Zone (Center-Left) tránh đè mốc thời lượng YouTube.
    """
    thumb_text, _ = extract_thumbnail_metadata(raw_script, fallback_title)
    if not thumb_text:
        thumb_text = "HỒ SƠ KỲ ÁN"

    os.makedirs(outputs_dir, exist_ok=True)
    out_thumb_path = os.path.join(outputs_dir, f"thumbnail_{session_id}.jpg")
    latest_thumb_path = os.path.join(outputs_dir, "thumbnail_latest.jpg")
    raw_base_path = os.path.join(outputs_dir, f"raw_base_{session_id}.jpg")

    base_ready = False

    # 1. Trích xuất khung hình đắt giá từ video (giây 15 - 30)
    if video_path and os.path.exists(video_path) and os.path.getsize(video_path) > 10000:
        for ss_time in ["00:00:20", "00:00:15", "00:00:30", "00:00:05"]:
            try:
                cmd_ext = [
                    'ffmpeg', '-y',
                    '-ss', ss_time,
                    '-i', video_path,
                    '-vframes', '1',
                    '-vf', 'scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720',
                    '-q:v', '2',
                    raw_base_path
                ]
                subprocess.run(cmd_ext, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if os.path.exists(raw_base_path) and os.path.getsize(raw_base_path) > 5000:
                    base_ready = True
                    break
            except Exception:
                pass

    # 2. Nếu chưa có nền từ video, tạo nền Gothic Noir điện ảnh siêu thực
    if not base_ready:
        try:
            cmd_bg = [
                'ffmpeg', '-y',
                '-f', 'lavfi', '-i', 'color=c=0x0a0c10:s=1280x720:d=1',
                '-vf', 'drawbox=x=0:y=0:w=1280:h=720:color=0x181016@0.6:t=fill',
                '-vframes', '1',
                '-q:v', '2',
                raw_base_path
            ]
            subprocess.run(cmd_bg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            base_ready = True
        except Exception:
            pass

    # Áp dụng Typography CTR Booster với Be Vietnam Pro
    font_path = os.path.join(fonts_dir, "BeVietnamPro-Bold.ttf")
    if not os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    escaped_font = str(font_path).replace(':', r'\:')
    escaped_text = thumb_text.replace("'", "'\\''").replace(':', r'\:')

    # Tính toán kích thước chữ tự động
    if len(thumb_text) <= 12:
        font_sz = 94
    elif len(thumb_text) <= 20:
        font_sz = 78
    else:
        font_sz = 62

    try:
        cmd_draw = [
            'ffmpeg', '-y',
            '-i', raw_base_path,
            '-vf', (
                'scale=1280:720,'
                'drawbox=x=0:y=0:w=720:h=720:color=black@0.45:t=fill,'
                f"drawtext=text='{escaped_text}':fontfile='{escaped_font}':fontsize={font_sz}:"
                f"fontcolor=0xFFE600:bordercolor=black:borderw=9:"
                f"shadowcolor=black@0.9:shadowx=6:shadowy=6:"
                f"x=75:y=(h-text_h)/2"
            ),
            '-vframes', '1',
            '-q:v', '2',
            out_thumb_path
        ]
        subprocess.run(cmd_draw, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        if os.path.exists(out_thumb_path):
            try:
                shutil.copyfile(out_thumb_path, latest_thumb_path)
            except Exception:
                pass
    except Exception as e_draw:
        print(f"⚠️ Lỗi render chữ Thumbnail: {e_draw}")

    if os.path.exists(raw_base_path):
        try: os.remove(raw_base_path)
        except Exception: pass

    return out_thumb_path if os.path.exists(out_thumb_path) else latest_thumb_path
