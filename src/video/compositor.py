import os
import uuid
import textwrap
import subprocess
from .waveform import build_waveform_filter

def escape_ffmpeg_filter_path(p: str) -> str:
    """Escape các ký tự đặc biệt cho FFmpeg filter graph."""
    if not p:
        return ""
    p_abs = os.path.abspath(p)
    return p_abs.replace('\\', '/').replace(':', r'\:').replace("'", r"\'")

def render_ultimate_video(
    scene_assets, cuts, audio_path: str, srt_path: str, topic_title: str,
    title_font_size: int = 60, add_subtitles: bool = True,
    sub_color_choice: str = "Vàng viền đen", waveform_style: str = "Tắt",
    output_video_path: str = "outputs/final_video.mp4", aspect_ratio: str = "16:9",
    title_style: str = "✨ Điện Ảnh Sang Trọng (Chữ Trắng Đổ Bóng - Không Hộp Đen)",
    sub_font_size: int = 18, temp_dir: str = "temp_work", fonts_dir: str = "fonts"
) -> str:
    """
    ĐỘNG CƠ DỰNG PHIM ĐIỆN ẢNH V19.7:
    - Hỗ trợ Native Full Frame: 16:9 (1920x1080) và 9:16 (1080x1920).
    - Chuẩn hóa Safe Zone 9:16: sub_margin_v = 38 (không wave) / 52 (có wave), cách xa Tiêu đề > 900px, 100% không đè chữ.
    - Cỡ chữ mặc định: Tiêu đề 60, Phụ đề 18.
    """
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(os.path.dirname(output_video_path) or ".", exist_ok=True)

    fps = 24
    is_vertical = "9:16" in aspect_ratio
    vid_w, vid_h = (1080, 1920) if is_vertical else (1920, 1080)

    font_path = os.path.join(fonts_dir, "BeVietnamPro-Bold.ttf")
    if not os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    escaped_font_path = escape_ffmpeg_filter_path(font_path)

    camera_moves = [
        "zoompan=z='min(zoom+0.0008,1.20)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frame_count}:s={vid_w}x{vid_h}:fps={fps}",
        "zoompan=z='if(lte(zoom,1.0),1.20,max(1.001,zoom-0.0008))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frame_count}:s={vid_w}x{vid_h}:fps={fps}",
        "zoompan=z='1.12':x='if(lte(on,1),0,x+0.35)':y='ih/2-(ih/zoom/2)':d={frame_count}:s={vid_w}x{vid_h}:fps={fps}",
        "zoompan=z='1.12':x='if(lte(on,1),(iw-iw/zoom)/2,x-0.35)':y='ih/2-(ih/zoom/2)':d={frame_count}:s={vid_w}x{vid_h}:fps={fps}",
        "zoompan=z='min(zoom+0.0006,1.18)':x='iw/3-(iw/zoom/3)':y='ih/3-(ih/zoom/3)':d={frame_count}:s={vid_w}x{vid_h}:fps={fps}",
        "zoompan=z='min(zoom+0.0006,1.18)':x='iw/2-(iw/zoom/2)':y='if(lte(on,1),0,y+0.25)':d={frame_count}:s={vid_w}x{vid_h}:fps={fps}"
    ]

    temp_clips = []
    for i, (asset, cut) in enumerate(zip(scene_assets, cuts)):
        scene_dur = cut["duration"]
        fade_dur = min(0.30, max(0.08, scene_dur / 4))
        st_out = max(0.05, scene_dur - fade_dur)
        frame_count = max(25, int(scene_dur * fps))

        clip_path = os.path.join(temp_dir, f"temp_clip_{i}.mp4")
        if asset.endswith(('.mp4', '.mov', '.webm', '.mkv')):
            vf_vid = f"scale={vid_w}:{vid_h}:force_original_aspect_ratio=increase,crop={vid_w}:{vid_h},fps={fps},fade=t=in:st=0:d={fade_dur:.2f},fade=t=out:st={st_out:.2f}:d={fade_dur:.2f}"
            cmd = [
                'ffmpeg', '-y', '-stream_loop', '-1', '-i', asset,
                '-vf', vf_vid, '-t', f"{scene_dur:.3f}", '-an',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', clip_path
            ]
        else:
            move_template = camera_moves[i % len(camera_moves)]
            move_interpolated = move_template.format(frame_count=frame_count, vid_w=vid_w, vid_h=vid_h, fps=fps)
            vf_img = f"scale={vid_w}:{vid_h},{move_interpolated},fade=t=in:st=0:d={fade_dur:.2f},fade=t=out:st={st_out:.2f}:d={fade_dur:.2f}"
            cmd = [
                'ffmpeg', '-y', '-loop', '1', '-i', asset,
                '-vf', vf_img, '-t', f"{scene_dur:.3f}",
                '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', clip_path
            ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            cmd_fallback = [
                'ffmpeg', '-y', '-loop', '1', '-i', asset,
                '-vf', f"scale={vid_w}:{vid_h},fps={fps},fade=t=in:st=0:d={fade_dur:.2f},fade=t=out:st={st_out:.2f}:d={fade_dur:.2f}",
                '-t', f"{scene_dur:.3f}", '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', clip_path
            ]
            subprocess.run(cmd_fallback, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        temp_clips.append(clip_path)

    concat_txt = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_txt, 'w', encoding='utf-8') as f:
        for c in temp_clips:
            f.write(f"file '{os.path.abspath(c)}'\n")

    temp_concat_video = os.path.join(temp_dir, "temp_concat.mp4")
    cmd_concat = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_txt, '-c:v', 'copy', temp_concat_video]
    subprocess.run(cmd_concat, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    wave_filter = build_waveform_filter(waveform_style, is_vertical)

    extra_filters = []
    is_title_disabled = (not topic_title) or (len(str(topic_title).strip()) <= 2) or ("Tắt" in str(title_style))

    if not is_title_disabled:
        wrap_width = 24 if is_vertical else 46
        clean_raw_title = str(topic_title).strip().replace('"', '').replace("'", "")
        if "|" in clean_raw_title and len(clean_raw_title) > 42:
            parts = [p.strip() for p in clean_raw_title.split("|") if p.strip()]
            if parts:
                clean_raw_title = parts[0]

        wrapped_lines = textwrap.wrap(clean_raw_title, width=wrap_width)
        wrapped_title_text = "\n".join(wrapped_lines)

        title_text_file = os.path.join(temp_dir, f"title_{uuid.uuid4().hex[:6]}.txt")
        with open(title_text_file, "w", encoding="utf-8") as tf:
            tf.write(wrapped_title_text)

        title_y = 140 if is_vertical else 50
        effective_title_size = int(title_font_size) if title_font_size else 60
        line_spacing_px = 8 if is_vertical else 6
        escaped_title_file = escape_ffmpeg_filter_path(title_text_file)

        if "Hộp Nền" in str(title_style):
            box_padding = max(8, int(effective_title_size * 0.35))
            extra_filters.append(f"drawtext=fontfile='{escaped_font_path}':textfile='{escaped_title_file}':reload=0:x=(w-text_w)/2:y={title_y}:fontsize={effective_title_size}:fontcolor=white:box=1:boxcolor=black@0.45:boxborderw={box_padding}:line_spacing={line_spacing_px}")
        else:
            extra_filters.append(f"drawtext=fontfile='{escaped_font_path}':textfile='{escaped_title_file}':reload=0:x=(w-text_w)/2:y={title_y}:fontsize={effective_title_size}:fontcolor=white:borderw=2.5:bordercolor=black@0.85:shadowcolor=black@0.90:shadowx=2:shadowy=3:line_spacing={line_spacing_px}")

    if add_subtitles and os.path.exists(srt_path):
        font_color = "&H0000FFFF" if "Vàng" in sub_color_choice else "&H00FFFFFF"
        base_sub_size = int(sub_font_size) if sub_font_size else 18
        
        # 🔥 V19.7 SAFE ZONE FIX
        if is_vertical:
            effective_sub_size = int(base_sub_size * 1.25)
            sub_margin_v = 52 if wave_filter else 38
            outline_val = 3.0
        else:
            effective_sub_size = base_sub_size
            sub_margin_v = 34 if wave_filter else 24
            outline_val = 2.2

        escaped_srt = escape_ffmpeg_filter_path(srt_path)
        sub_font_name = "Be Vietnam Pro"
        fontsdir_opt = ""
        fonts_dir_path = os.path.abspath(fonts_dir)
        if os.path.exists(fonts_dir_path):
            escaped_fontsdir = escape_ffmpeg_filter_path(fonts_dir_path)
            fontsdir_opt = f":fontsdir='{escaped_fontsdir}'"

        extra_filters.append(f"subtitles='{escaped_srt}'{fontsdir_opt}:force_style='FontName={sub_font_name},Bold=1,FontSize={effective_sub_size},PrimaryColour={font_color},OutlineColour=&H00000000,BorderStyle=1,Outline={outline_val},Shadow=1.2,Alignment=2,MarginV={sub_margin_v}'")

    if wave_filter:
        if extra_filters:
            combined_complex = f"{wave_filter},{','.join(extra_filters)}[vout]"
        else:
            combined_complex = f"{wave_filter}[vout]"
        cmd_final = [
            'ffmpeg', '-y',
            '-i', temp_concat_video,
            '-i', audio_path,
            '-filter_complex', combined_complex,
            '-map', '[vout]',
            '-map', '1:a',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
            '-c:a', 'aac', '-b:a', '192k',
            '-shortest',
            output_video_path
        ]
    else:
        cmd_final = [
            'ffmpeg', '-y',
            '-i', temp_concat_video,
            '-i', audio_path
        ]
        if extra_filters:
            cmd_final.extend(['-vf', ','.join(extra_filters)])
        cmd_final.extend([
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
            '-c:a', 'aac', '-b:a', '192k',
            '-shortest',
            output_video_path
        ])

    subprocess.run(cmd_final, check=True)
    return output_video_path
