import os
import time
import uuid
import json
import shutil
import subprocess
from datetime import datetime, timezone, timedelta

from ..tts import extract_script_components, clean_voice_name, get_tts_engine
from ..subtitles import extract_whisper_segments_and_srt, recalculate_and_inject_youtube_chapters
from ..ai_director import (
    enhance_visual_prompt_gemini,
    generate_micro_batch_visual_prompts,
    PexelsRotator,
    generate_sdxl_metaphor_image
)
from ..video import handle_background_music, generate_ctr_booster_thumbnail, render_ultimate_video
from ..youtube import upload_to_youtube

def build_retention_cuts(segments, total_dur: float, auto_sync_mode: bool = True, max_scenes_manual: int = 15, enable_retention: bool = True):
    """
    Xây dựng các mốc chuyển cảnh (Cuts) đồng bộ theo câu nói hoặc chia đều kịch bản.
    """
    cuts = []
    if auto_sync_mode and segments:
        for seg in segments:
            st = float(seg["start"])
            et = float(seg["end"])
            cuts.append({
                "start": st,
                "end": et,
                "duration": max(0.5, et - st),
                "text": seg.get("text", "")
            })
    else:
        num_scenes = max(1, int(max_scenes_manual))
        dur_step = total_dur / num_scenes
        for i in range(num_scenes):
            st = i * dur_step
            et = min(total_dur, (i + 1) * dur_step)
            cuts.append({
                "start": st,
                "end": et,
                "duration": max(0.5, et - st),
                "text": f"Phân cảnh {i+1}"
            })
    return cuts

def generate_scenes_for_cuts(cuts, visual_mode: str, session_id: str, aspect_ratio: str, pexels_keys: str, gemini_api_key: str, gemini_model: str, visual_concept: str, temp_dir: str = "temp_work", art_style: str = "cinematic"):
    """
    Chuẩn bị tài nguyên hình ảnh/video cho từng phân cảnh.
    Sử dụng Micro-Batch Storyboard (3 cảnh / 1 request) để:
    - Giảm số lượt gọi Gemini từ 15-20 xuống chỉ còn 3-5 requests (< 10 requests).
    - Duy trì liên kết thị giác & đạo diễn điện ảnh (Wide -> Medium -> Close-up).
    - Ngăn ngừa lỗi 429 Quota Exceeded và tối ưu hóa thời gian sinh ảnh.
    """
    os.makedirs(temp_dir, exist_ok=True)
    is_vertical = "9:16" in aspect_ratio
    rotator = PexelsRotator(pexels_keys)
    assets = []
    thumbs = []

    # Tiền xử lý kịch bản phân cảnh Micro-Batch nếu dùng SDXL hoặc chế độ AI
    prompts = []
    if "Pexels" not in visual_mode or not pexels_keys:
        cut_texts = [cut.get("text", "") for cut in cuts]
        print(f"[AI Director] Bắt đầu Micro-Batch Storyboard ({len(cut_texts)} cảnh, Style: {art_style})...")
        prompts = generate_micro_batch_visual_prompts(
            scenes=cut_texts,
            visual_concept=visual_concept,
            api_key=gemini_api_key,
            model_name=gemini_model,
            art_style=art_style,
            batch_size=3
        )

    for i, cut in enumerate(cuts):
        asset_path = os.path.join(temp_dir, f"asset_{session_id}_{i}.jpg")
        if "Pexels" in visual_mode and pexels_keys:
            video_asset = os.path.join(temp_dir, f"asset_{session_id}_{i}.mp4")
            orientation = "portrait" if is_vertical else "landscape"
            kw = cut.get("text", "").split()[:3]
            query = " ".join(kw) if kw else "mystery cinematic"
            res = rotator.search_and_download_video(query, video_asset, orientation=orientation)
            if res:
                assets.append(video_asset)
                continue

        # Lấy prompt đã được tối ưu từ Micro-Batch hoặc fallback
        if i < len(prompts) and prompts[i]:
            prompt = prompts[i]
        else:
            prompt = enhance_visual_prompt_gemini(cut.get("text", ""), visual_concept, gemini_api_key, gemini_model, art_style=art_style)

        img_out = generate_sdxl_metaphor_image(prompt, aspect_ratio, asset_path, scene_idx=i)
        assets.append(img_out)
        if len(thumbs) < 4:
            thumbs.append(img_out)

    return assets, thumbs

def process_full_pipeline(
    script_input: str,
    aspect_ratio: str = "16:9",
    visual_mode: str = "SDXL (AI Hình Ảnh Ẩn Dụ)",
    sync_mode_choice: str = "Tự động (Theo phụ đề Whisper)",
    num_scenes_slider: int = 15,
    pexels_key_input: str = "",
    gemini_api_key_input: str = "",
    gemini_model_input: str = "gemini-2.5-flash",
    allow_reuse_input: bool = False,
    voice_selected: str = "Thiền Tâm Đức",
    topic_title_custom: str = "",
    title_font_size: int = 60,
    title_style: str = "✨ Điện Ảnh Sang Trọng (Chữ Trắng Đổ Bóng - Không Hộp Đen)",
    bgm_file = None,
    bgm_gdrive_url: str = "",
    bgm_volume: float = 0.15,
    add_subtitles: bool = True,
    sub_color: str = "Vàng viền đen (Nổi bật - Khuyên dùng)",
    waveform_style: str = "Tắt",
    retention_cuts_enabled: bool = True,
    sub_font_size: int = 18,
    art_style: str = "📷 Điện Ảnh Đời Thực (35mm Photorealistic - Mặc định)",
    auto_upload_yt: bool = False,
    yt_privacy: str = "private",
    editor_email: str = "",
    shared_drive_folder: str = "",
    progress = None,
    outputs_dir: str = "outputs",
    temp_dir: str = "temp_work",
    fonts_dir: str = "fonts"
):
    """
    LUỒNG XỬ LÝ TOÀN DIỆN CHO 1 KỊCH BẢN (END-TO-END PIPELINE).
    """
    if not script_input or not script_input.strip():
        return None, None, None, [], "❌ Lỗi: Vui lòng dán nội dung kịch bản!", "", ""

    vn_tz = timezone(timedelta(hours=7))
    session_id = datetime.now(vn_tz).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:4]
    t_start = time.time()

    os.makedirs(outputs_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    if progress: progress(0.05, desc="Đang phân tích kịch bản...")
    auto_title, visual_concept, speech_text, custom_desc, sched_time_str = extract_script_components(script_input)
    final_title = topic_title_custom.strip() if topic_title_custom.strip() else auto_title

    # 1. TTS
    if progress: progress(0.20, desc=f"Đang sinh giọng đọc {voice_selected}...")
    actual_voice = clean_voice_name(voice_selected)
    voice_audio_path = os.path.join(temp_dir, f"voice_{session_id}.wav")
    tts_engine = get_tts_engine()
    tts_engine.synthesize(text=speech_text, voice=actual_voice, output_path=voice_audio_path)

    # 2. BGM
    if progress: progress(0.35, desc="Đang hòa âm nhạc nền...")
    final_audio_path = handle_background_music(bgm_file, bgm_gdrive_url, voice_audio_path, session_id, bgm_volume, temp_dir=temp_dir)

    # 3. Subtitles (Whisper-first & difflib alignment)
    if progress: progress(0.50, desc="Đang quét phụ đề Whisper...")
    srt_path = os.path.join(outputs_dir, f"subtitles_{session_id}.srt")
    segments, srt_path = extract_whisper_segments_and_srt(voice_audio_path, speech_text, srt_path, gemini_api_key=gemini_api_key_input, gemini_model=gemini_model_input)

    cmd_dur = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', final_audio_path]
    total_dur = float(subprocess.check_output(cmd_dur).decode().strip())

    is_auto_sync = "Tự động" in sync_mode_choice
    cuts = build_retention_cuts(segments, total_dur, auto_sync_mode=is_auto_sync, max_scenes_manual=num_scenes_slider, enable_retention=retention_cuts_enabled)

    # 4. Phân cảnh hình ảnh
    if progress: progress(0.65, desc=f"Đang chuẩn bị {len(cuts)} phân cảnh...")
    scene_assets, gallery_thumbs = generate_scenes_for_cuts(cuts, visual_mode, session_id, aspect_ratio, pexels_key_input, gemini_api_key_input, gemini_model_input, visual_concept, temp_dir=temp_dir, art_style=art_style)

    # 5. Dựng video MP4 hoàn thiện
    if progress: progress(0.85, desc="Đang render video MP4...")
    video_path = os.path.join(outputs_dir, f"video_{session_id}.mp4")
    render_ultimate_video(
        scene_assets, cuts, final_audio_path, srt_path, final_title,
        title_font_size=title_font_size, add_subtitles=add_subtitles,
        sub_color_choice=sub_color, waveform_style=waveform_style,
        output_video_path=video_path, aspect_ratio=aspect_ratio,
        title_style=title_style, sub_font_size=sub_font_size,
        temp_dir=temp_dir, fonts_dir=fonts_dir
    )

    # 6. Tự động tạo Thumbnail CTR Booster (1280x720)
    try:
        thumb_path = generate_ctr_booster_thumbnail(
            video_path=video_path,
            raw_script=script_input,
            fallback_title=final_title,
            session_id=session_id,
            outputs_dir=outputs_dir,
            fonts_dir=fonts_dir
        )
        if thumb_path and os.path.exists(thumb_path):
            gallery_thumbs.insert(0, thumb_path)
    except Exception as e_tb:
        print(f"⚠️ Cảnh báo Thumbnail: {e_tb}")

    # 7. Tính toán & ghi đè YouTube Chapters
    is_vert = "9:16" in aspect_ratio
    if custom_desc and len(custom_desc.strip()) > 5:
        yt_description = custom_desc.strip()
    else:
        extra_tags = "#shorts #tiktok #reels #videoessay" if is_vert else "#videoessay #tamlyhoc #triethoc"
        yt_description = f"{final_title}\n\nNội dung video essay tâm lý học và triết học ứng dụng.\nGiọng đọc: {voice_selected} (VieNeu-TTS).\n\n#tamlyhoc #triethoc #khacky {extra_tags} #vieneu"

    try:
        yt_description = recalculate_and_inject_youtube_chapters(
            description=yt_description,
            raw_script=script_input,
            segments_data=segments,
            total_dur=total_dur,
            gemini_api_key=gemini_api_key_input,
            gemini_model=gemini_model_input
        )
    except Exception as e_ch:
        print(f"⚠️ Cảnh báo Chapters: {e_ch}")

    # Copy audio vào outputs/
    delivered_audio_path = os.path.join(outputs_dir, f"audio_{session_id}.wav")
    try:
        shutil.copyfile(final_audio_path, delivered_audio_path)
    except Exception:
        delivered_audio_path = final_audio_path

    if progress: progress(1.0, desc="Hoàn tất!")

    total_time = time.time() - t_start
    status_msg = f"🎉 XUẤT BẢN THÀNH CÔNG TRONG {total_time:.1f} GIÂY!\n- Video: {video_path}\n- Thời lượng: {total_dur:.1f}s\n- Tiêu đề: {final_title}\n- Phân cảnh: {len(cuts)} cảnh"

    # Tự động Upload nếu bật
    yt_tags = "#tamlyhoc, #triethoc, #audiobook"
    if auto_upload_yt:
        upload_res = upload_to_youtube(
            video_file_path=video_path,
            title=final_title,
            description=yt_description,
            tags=yt_tags,
            is_schedule=bool(sched_time_str),
            custom_schedule_time=sched_time_str,
            privacy_status=yt_privacy,
            editor_email=editor_email,
            shared_drive_folder=shared_drive_folder,
            outputs_dir=outputs_dir
        )
        status_msg += f"\n\n{upload_res}"

    return video_path, delivered_audio_path, srt_path, gallery_thumbs, status_msg, final_title, yt_description

def process_batch_pipeline(
    batch_files, batch_folder_path: str, aspect_ratio: str, visual_mode: str,
    sync_mode_choice: str, num_scenes_slider: int, pexels_key_input: str,
    allow_reuse_input: bool, voice_selected: str, title_font_size: int = 60,
    title_style: str = "✨ Điện Ảnh Sang Trọng (Chữ Trắng Đổ Bóng - Không Hộp Đen)",
    bgm_file = None, bgm_gdrive_url: str = "", bgm_volume: float = 0.15,
    add_subtitles: bool = True, sub_color: str = "Vàng viền đen (Nổi bật - Khuyên dùng)",
    waveform_style: str = "Tắt", retention_cuts_enabled: bool = True,
    tab1_gemini_key: str = "", editor_email: str = "", shared_drive_folder: str = "",
    sub_font_size: int = 18, b_gemini_key: str = "", b_gemini_model: str = "gemini-2.5-flash",
    art_style: str = "📷 Điện Ảnh Đời Thực (35mm Photorealistic - Mặc định)",
    auto_upload_batch: bool = True, b_yt_privacy: str = "private", progress = None
):
    """
    XỬ LÝ MẺ HÀNG LOẠT (BATCH PROCESSING) TỪ DANH SÁCH FILE HOẶC THƯ MỤC.
    """
    # Gom danh sách kịch bản
    all_scripts = []
    if batch_files:
        for f in batch_files:
            p = f if isinstance(f, str) else getattr(f, "name", str(f))
            if os.path.exists(p) and p.endswith(".txt"):
                try:
                    with open(p, "r", encoding="utf-8") as rf:
                        all_scripts.append((os.path.basename(p), rf.read()))
                except Exception:
                    pass

    if batch_folder_path and os.path.exists(batch_folder_path.strip()):
        for root, _, files in os.walk(batch_folder_path.strip()):
            for fn in files:
                if fn.endswith(".txt") and not fn.startswith("."):
                    fp = os.path.join(root, fn)
                    try:
                        with open(fp, "r", encoding="utf-8") as rf:
                            all_scripts.append((fn, rf.read()))
                    except Exception:
                        pass

    if not all_scripts:
        return None, None, None, [], "❌ Lỗi: Không tìm thấy file kịch bản .txt nào!", "", ""

    effective_key = b_gemini_key.strip() if b_gemini_key else tab1_gemini_key.strip()
    created_videos = []
    last_audio = None
    last_srt = None
    all_thumbs = []
    last_title = ""
    last_desc = ""
    batch_logs = []

    for idx, (fname, content) in enumerate(all_scripts, 1):
        if progress: progress(idx / len(all_scripts), desc=f"Đang làm mẻ: Tập {idx}/{len(all_scripts)} ({fname})...")
        v_p, a_p, s_p, thumbs, p_status, tit, desc = process_full_pipeline(
            script_input=content,
            aspect_ratio=aspect_ratio,
            visual_mode=visual_mode,
            sync_mode_choice=sync_mode_choice,
            num_scenes_slider=num_scenes_slider,
            pexels_key_input=pexels_key_input,
            gemini_api_key_input=effective_key,
            gemini_model_input=b_gemini_model,
            allow_reuse_input=allow_reuse_input,
            voice_selected=voice_selected,
            topic_title_custom="",
            title_font_size=title_font_size,
            title_style=title_style,
            bgm_file=bgm_file,
            bgm_gdrive_url=bgm_gdrive_url,
            bgm_volume=bgm_volume,
            add_subtitles=add_subtitles,
            sub_color=sub_color,
            waveform_style=waveform_style,
            retention_cuts_enabled=retention_cuts_enabled,
            sub_font_size=sub_font_size,
            art_style=art_style,
            auto_upload_yt=auto_upload_batch,
            yt_privacy=b_yt_privacy,
            editor_email=editor_email,
            shared_drive_folder=shared_drive_folder
        )
        if v_p:
            created_videos.append(v_p)
            last_audio = a_p
            last_srt = s_p
            last_title = tit
            last_desc = desc
            if thumbs:
                all_thumbs.extend(thumbs[:2])
            
            yt_info = ""
            if auto_upload_batch and p_status:
                for line in p_status.splitlines():
                    if any(k in line for k in ["YOUTUBE", "youtu.be", "Video ID", "LÊN LỊCH", "Lỗi", "Thumbnail"]):
                        yt_info += "\n   " + line.strip()
            batch_logs.append(f"✅ [{idx}/{len(all_scripts)}] '{fname}' -> {os.path.basename(v_p)}{yt_info}")
        else:
            batch_logs.append(f"❌ [{idx}/{len(all_scripts)}] '{fname}': Thất bại!")

    mode_desc = " (ĐÃ TỰ ĐỘNG ĐĂNG YOUTUBE CHO CẢ MẺ)" if auto_upload_batch else " (Chỉ Tạo Video)"
    delimiter = "\n\n"
    summary = f"🎉 HOÀN THÀNH MẺ BATCH: {len(created_videos)}/{len(all_scripts)} video thành công!{mode_desc}\n\n" + delimiter.join(batch_logs)
    last_v = created_videos[-1] if created_videos else None
    return last_v, last_audio, last_srt, all_thumbs, summary, last_title, last_desc
