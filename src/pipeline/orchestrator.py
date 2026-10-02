import os
import time
import uuid
import glob
import json
import shutil
import subprocess
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional, Any

from .channel_profiles import get_channel_profile, get_channel_token_file, DEFAULT_TAGS
from ..tts import extract_script_components, clean_voice_name, get_tts_engine
from ..subtitles import (
    extract_whisper_segments_and_srt,
    build_subtitle_retention_cuts,
    recalculate_and_inject_youtube_chapters
)
from ..ai_director import (
    call_gemini_all_in_one_director,
    analyze_sentence_to_detective_prompt,
    generate_sdxl_metaphor_image,
    parse_key_pool,
    download_unique_stock_video
)
from ..video import (
    handle_background_music,
    generate_ctr_booster_thumbnail,
    render_ultimate_video
)
from ..youtube import upload_to_youtube, check_script_already_published, record_successful_publish

# Alias tương thích ngược
build_retention_cuts = build_subtitle_retention_cuts


def generate_v20_scenes_for_cuts(
    cuts: list,
    visual_mode: str,
    session_id: str,
    aspect_ratio: str,
    raw_keys_input: str,
    gemini_api_key: str = "",
    gemini_model_choice: str = "gemini-3.5-flash-lite",
    topic_title: str = "",
    visual_concept: str = "",
    allow_reuse: bool = False,
    precomputed_prompts: dict = None,
    channel_profile: str = "🕯️ Trinh Thám & Kinh Dị Gothic (Kênh Nỗi Sợ AudioBook)",
    temp_dir: str = "temp_work",
    outputs_dir: str = "outputs"
) -> Tuple[List[str], List[str]]:
    """
    QUẢN LÝ PHÂN CẢNH V20 (SUBTITLE-LOCKED UNIQUE VISUALS):
    - 100% hình đi cùng sub: Khóa chặt theo từng câu phụ đề.
    - Ưu tiên prompts từ All-in-One Gemini Director -> Fallback Gothic Detective Rule Engine.
    - Xuất toàn bộ kịch bản prompt chi tiết ra outputs/prompts_{session_id}.txt & .json.
    """
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(outputs_dir, exist_ok=True)

    key_pool = parse_key_pool(raw_keys_input)
    is_stock_mode = "video stock" in visual_mode.lower()

    scene_assets = []
    gallery_thumbs = []
    asset_pool = []
    recent_concepts_buffer = []
    saved_prompts_info = []

    ai_director_prompts = precomputed_prompts
    if ai_director_prompts is None and not is_stock_mode and gemini_api_key and gemini_api_key.strip():
        ai_director_prompts, _ = call_gemini_all_in_one_director(
            cuts, "", topic_title, visual_concept, gemini_api_key,
            selected_model=gemini_model_choice, channel_profile=channel_profile
        )

    stock_queries = [
        "night rain city street contemplation", "lonely pensive person sitting cafe",
        "misty forest path morning sunbeams", "calm ocean waves sunset reflection",
        "hands writing journal candle desk", "clouds rolling over high mountains",
        "empty park bench autumn leaves rain", "person looking rainy window night",
        "vintage clock time passing slow motion", "zen water ripples reflection nature",
        "dramatic foggy mountain peak sunrise", "ancient library old books candle flame"
    ]

    for i, cut in enumerate(cuts):
        should_reuse = allow_reuse and (not cut.get("is_early", False)) and (len(asset_pool) >= 15) and (i % 2 == 1)
        if should_reuse:
            chosen_asset = asset_pool[i % len(asset_pool)]
            scene_assets.append(chosen_asset)
            continue

        if not is_stock_mode:
            # CHẾ ĐỘ 1: ẢNH NGHỆ THUẬT AI (SDXL)
            c_idx = cut["index"]
            if ai_director_prompts and c_idx in ai_director_prompts:
                prompt = ai_director_prompts[c_idx]
                prompt_src = f"Gemini AI Director ({gemini_model_choice})"
            else:
                prompt = analyze_sentence_to_detective_prompt(
                    cut.get("text", ""), cut.get("part", 0), i,
                    topic_title=topic_title,
                    visual_concept=visual_concept,
                    recent_concepts=recent_concepts_buffer,
                    channel_profile=channel_profile
                )
                prompt_src = "Gothic Detective Rule Engine (100% Khớp Sub)"

            saved_prompts_info.append({
                "scene_index": cut["index"],
                "part": cut.get("part", 0),
                "duration": cut.get("duration", 0.0),
                "voice_text": cut.get("text", ""),
                "prompt": prompt,
                "source": prompt_src
            })

            out_img = os.path.join(temp_dir, f"scene_{session_id}_{i+1}.jpg")
            img_res = generate_sdxl_metaphor_image(prompt, aspect_ratio, out_img, i)
            scene_assets.append(img_res)
            gallery_thumbs.append(img_res)
            asset_pool.append(img_res)
        else:
            # CHẾ ĐỘ 2: VIDEO STOCK FOOTAGE
            stock_q = stock_queries[i % len(stock_queries)]
            out_vid = os.path.join(temp_dir, f"raw_stock_{session_id}_{i+1}.mp4")
            vid_res = download_unique_stock_video(stock_q, aspect_ratio, key_pool, out_vid)

            if vid_res and os.path.exists(vid_res):
                scene_assets.append(vid_res)
                asset_pool.append(vid_res)
                thumb_path = os.path.join(temp_dir, f"thumb_{session_id}_{i+1}.jpg")
                try:
                    subprocess.run(
                        ['ffmpeg', '-y', '-ss', '00:00:01', '-i', vid_res, '-vframes', '1', '-q:v', '3', thumb_path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    gallery_thumbs.append(thumb_path)
                except Exception:
                    pass
            else:
                out_img = os.path.join(temp_dir, f"scene_{session_id}_{i+1}.jpg")
                img_res = generate_sdxl_metaphor_image("atmospheric 35mm film still, candle light, moody introspection", aspect_ratio, out_img, i)
                scene_assets.append(img_res)
                gallery_thumbs.append(img_res)
                asset_pool.append(img_res)

    # Tự động lưu toàn bộ Prompts vào outputs/
    if saved_prompts_info:
        try:
            prompts_json_path = os.path.join(outputs_dir, f"prompts_{session_id}.json")
            prompts_txt_path = os.path.join(outputs_dir, f"prompts_{session_id}.txt")
            with open(prompts_json_path, "w", encoding="utf-8") as pf:
                json.dump(saved_prompts_info, pf, ensure_ascii=False, indent=2)
            with open(prompts_txt_path, "w", encoding="utf-8") as tf:
                tf.write("====================================================\n")
                tf.write("KỊCH BẢN PROMPT HÌNH ẢNH (AI ĐẠO DIỄN V20)\n")
                tf.write(f"Tiêu đề: {topic_title}\n")
                tf.write(f"Session ID: {session_id}\n")
                tf.write(f"Tổng số phân cảnh: {len(saved_prompts_info)}\n")
                tf.write("====================================================\n\n")
                for item in saved_prompts_info:
                    p_label = f" (Góc máy phụ Part {item['part']})" if item.get('part', 0) > 0 else ""
                    tf.write(f"[Cảnh {item['scene_index']}{p_label}] (Thời lượng: {item['duration']:.2f}s)\n")
                    tf.write(f"- Lời thoại: \"{item['voice_text']}\"\n")
                    tf.write(f"- Nguồn tạo: {item['source']}\n")
                    tf.write(f"- SDXL Prompt:\n{item['prompt']}\n")
                    tf.write("----------------------------------------------------\n\n")
            print(f"📝 Đã lưu toàn bộ {len(saved_prompts_info)} prompt cảnh vào: {prompts_txt_path}")
        except Exception as e:
            print(f"⚠️ Lỗi lưu file prompts: {e}")

    return scene_assets, gallery_thumbs


# Alias tương thích ngược
generate_scenes_for_cuts = generate_v20_scenes_for_cuts
generate_v18_scenes_for_cuts = generate_v20_scenes_for_cuts


def process_full_pipeline(
    script_input: str,
    aspect_ratio: str = "16:9",
    visual_mode: str = "🎨 100% Ảnh Nghệ Thuật AI (SDXL Photorealism)",
    sync_mode_choice: str = "⚡ Tự động theo từng câu Subtitle (Whisper Sync)",
    num_scenes_slider: int = 12,
    pexels_key_input: str = "",
    gemini_api_key_input: str = "",
    gemini_model_input: str = "gemini-3.5-flash-lite",
    allow_reuse_input: bool = False,
    voice_selected: str = "Thiền Tâm Đức",
    topic_title_custom: str = "",
    title_font_size: int = 60,
    title_style: str = "✨ Điện Ảnh Sang Trọng (Chữ Trắng Đổ Bóng - Không Hộp Đen)",
    bgm_file: Any = None,
    bgm_gdrive_url: str = "",
    bgm_volume: float = 0.15,
    add_subtitles: bool = True,
    sub_color: str = "Vàng viền đen (Nổi bật - Khuyên dùng)",
    waveform_style: str = "Tắt",
    retention_cuts_enabled: bool = True,
    sub_font_size: int = 18,
    auto_upload_yt: bool = False,
    yt_privacy: str = "Riêng tư / Hẹn giờ (private)",
    editor_email: str = "",
    shared_drive_folder: str = "",
    channel_profile: str = "🕯️ Trinh Thám & Kinh Dị Gothic (Kênh Nỗi Sợ AudioBook)",
    custom_visual_concept: str = "",
    custom_yt_tags: str = "",
    custom_yt_desc: str = "",
    temp_dir: str = "temp_work",
    outputs_dir: str = "outputs",
    progress=None,
    **kwargs
):
    """
    QUY TRÌNH SẢN XUẤT AUDIOBOOK ĐIỆN ẢNH TOÀN DIỆN V20.0
    """
    if not script_input or not script_input.strip():
        return None, None, None, [], "❌ Lỗi: Vui lòng dán kịch bản vào ô text!", "", ""

    if "title_size_slider" in kwargs:
        title_font_size = kwargs["title_size_slider"]
    if "title_style_dropdown" in kwargs:
        title_style = kwargs["title_style_dropdown"]

    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(outputs_dir, exist_ok=True)

    actual_gemini_key = str(gemini_api_key_input).strip() if (gemini_api_key_input and str(gemini_api_key_input).strip()) else os.environ.get("GEMINI_API_KEY", "")

    vn_tz = timezone(timedelta(hours=7))
    session_id = datetime.now(vn_tz).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:4]
    t_start = time.time()

    if progress is not None:
        progress(0.05, desc="Đang phân tích kịch bản & trích xuất tiêu đề...")

    prof = get_channel_profile(channel_profile)
    auto_title, visual_concept_extracted, speech_text, custom_desc_extracted, sched_time_str = extract_script_components(
        script_input, channel_profile=channel_profile, default_concept=custom_visual_concept or prof.get("visual_concept", "")
    )
    final_title = topic_title_custom.strip() if topic_title_custom.strip() else auto_title

    # 1. Sinh âm thanh VieNeu-TTS
    actual_voice = clean_voice_name(voice_selected if voice_selected else prof.get("voice", "Thiền Tâm Đức"))
    if progress is not None:
        progress(0.20, desc=f"Đang đọc văn bản bằng giọng {actual_voice}...")

    voice_audio_path = os.path.join(temp_dir, f"voice_{session_id}.wav")
    tts_engine = get_tts_engine()
    tts_engine.synthesize(speech_text, actual_voice, voice_audio_path)

    # 2. Xử lý nhạc nền BGM
    if progress is not None:
        progress(0.35, desc=f"Đang hòa âm nhạc nền ({int(bgm_volume*100)}%)...")
    final_audio_path = handle_background_music(bgm_file, bgm_gdrive_url, voice_audio_path, session_id, bgm_volume, temp_dir=temp_dir)

    # 3. QUÉT SUBTITLE TRƯỚC (WHISPER-FIRST)
    if progress is not None:
        progress(0.50, desc="Đang quét phụ đề Whisper để lấy mốc cắt cảnh theo từng câu...")
    srt_path = os.path.join(outputs_dir, f"subtitles_{session_id}.srt")
    segments, srt_path = extract_whisper_segments_and_srt(
        voice_audio_path, speech_text, srt_path,
        gemini_api_key=actual_gemini_key, gemini_model=gemini_model_input
    )

    cmd_dur = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', final_audio_path]
    total_dur = float(subprocess.check_output(cmd_dur).decode().strip())

    is_auto_sync = "tự động" in sync_mode_choice.lower()
    cuts = build_subtitle_retention_cuts(
        segments, total_dur, auto_sync_mode=is_auto_sync,
        max_scenes_manual=num_scenes_slider, enable_retention=retention_cuts_enabled
    )

    # 4. ĐẠO DIỄN TOÀN DIỆN (ALL-IN-ONE SINGLE API CALL)
    ai_prompts, ai_chapters = {}, []
    if ("ảnh nghệ thuật" in visual_mode.lower() or "sdxl" in visual_mode.lower()) and actual_gemini_key and actual_gemini_key.strip():
        if progress is not None:
            progress(0.60, desc="Đang gọi AI Đạo Diễn (Gemini All-in-One) sinh Prompt bám sát Sub & Chapters...")
        ai_prompts, ai_chapters = call_gemini_all_in_one_director(
            cuts=cuts,
            full_speech=speech_text,
            topic_title=final_title,
            visual_concept=custom_visual_concept or visual_concept_extracted or prof.get("visual_concept", ""),
            gemini_key=actual_gemini_key,
            selected_model=gemini_model_input,
            channel_profile=channel_profile
        )

    # 5. Tạo phân cảnh hình ảnh V20
    if progress is not None:
        progress(0.68, desc=f"Đang chuẩn bị {len(cuts)} phân cảnh ({visual_mode})...")
    scene_assets, gallery_thumbs = generate_v20_scenes_for_cuts(
        cuts=cuts,
        visual_mode=visual_mode,
        session_id=session_id,
        aspect_ratio=aspect_ratio,
        raw_keys_input=pexels_key_input,
        gemini_api_key=actual_gemini_key,
        gemini_model_choice=gemini_model_input,
        topic_title=final_title,
        visual_concept=custom_visual_concept or visual_concept_extracted or prof.get("visual_concept", ""),
        allow_reuse=allow_reuse_input,
        precomputed_prompts=ai_prompts,
        channel_profile=channel_profile,
        temp_dir=temp_dir,
        outputs_dir=outputs_dir
    )

    # 6. Dựng video MP4 hoàn thiện
    if progress is not None:
        progress(0.85, desc=f"Đang render video MP4 ({aspect_ratio} - Native Full Frame)...")
    video_path = os.path.join(outputs_dir, f"video_{session_id}.mp4")
    render_ultimate_video(
        scene_assets=scene_assets,
        cuts=cuts,
        audio_path=final_audio_path,
        srt_path=srt_path,
        topic_title=final_title,
        title_font_size=title_font_size,
        add_subtitles=add_subtitles,
        sub_color_choice=sub_color,
        waveform_style=waveform_style,
        output_video_path=video_path,
        aspect_ratio=aspect_ratio,
        title_style=title_style,
        sub_font_size=sub_font_size,
        temp_dir=temp_dir
    )

    # 7. TỰ ĐỘNG TẠO THUMBNAIL YOUTUBE CTR BOOSTER (1280x720 HD)
    try:
        thumb_path = generate_ctr_booster_thumbnail(
            video_path=video_path,
            raw_script=script_input,
            fallback_title=final_title,
            session_id=session_id,
            visual_mode=visual_mode,
            gemini_api_key=actual_gemini_key,
            gemini_model=gemini_model_input,
            outputs_dir=outputs_dir
        )
        if thumb_path and os.path.exists(thumb_path):
            if gallery_thumbs is None:
                gallery_thumbs = []
            gallery_thumbs.insert(0, thumb_path)
            print(f"🖼️ Đã tạo xong Thumbnail YouTube CTR Booster: {thumb_path}")
    except Exception as e_tb:
        print(f"⚠️ Cảnh báo tạo Thumbnail: {e_tb}")

    # Sao chép file âm thanh chính thức vào outputs/
    delivered_audio_path = os.path.join(outputs_dir, f"audio_{session_id}.wav")
    try:
        shutil.copyfile(final_audio_path, delivered_audio_path)
    except Exception:
        delivered_audio_path = final_audio_path

    if progress is not None:
        progress(1.0, desc="Hoàn tất!")

    total_time = time.time() - t_start
    is_vert = "9:16" in aspect_ratio
    status_msg = (
        f"🎉 XUẤT BẢN THÀNH CÔNG TRONG {total_time:.1f} GIÂY!\n"
        f"- Hồ Sơ Kênh: {channel_profile}\n"
        f"- Định dạng khung hình: {aspect_ratio} {'(Native 1080x1920 Dọc Gốc)' if is_vert else '(1920x1080 Ngang Chuẩn)'}\n"
        f"- Cơ chế cắt cảnh: {'⚡ Tự động theo từng câu Subtitle' if is_auto_sync else f'Thủ công ({num_scenes_slider} cảnh)'}\n"
        f"- Tổng số phân cảnh: {len(cuts)} cảnh (Ăn khớp 100% từng câu nói)\n"
        f"- File Video: {video_path}\n"
        f"- Giọng đọc: {actual_voice}\n"
        f"- Tiêu đề: {final_title}\n"
        f"- Phụ đề: Đã chèn trực tiếp (Safe Zone) + Xuất file {srt_path}"
    )
    if sched_time_str:
        status_msg += f"\n- 📅 Ngày hẹn giờ đăng: {sched_time_str} (Giờ VN)"

    if custom_yt_desc and len(custom_yt_desc.strip()) > 5:
        yt_description = custom_yt_desc.strip()
    elif custom_desc_extracted and len(custom_desc_extracted.strip()) > 5:
        yt_description = custom_desc_extracted.strip()
    else:
        extra_tags = "#shorts #tiktok #reels #videoessay" if is_vert else "#videoessay #audiobook #podcast"
        yt_description = (
            f"{final_title}\n\n"
            f"{prof.get('desc_template', 'Nội dung sản xuất tự động bằng AI.')}\n\n"
            f"Giọng đọc: {actual_voice} (VieNeu-TTS).\n\n"
            f"{extra_tags}"
        )

    # CHUẨN HÓA & GHI ĐÈ TIMESTAMPS / YOUTUBE CHAPTERS
    try:
        print("⏱️ Đang tự động đối chiếu mốc thời gian thực tế để tạo YouTube Chapters...")
        yt_description = recalculate_and_inject_youtube_chapters(
            description=yt_description,
            raw_script=script_input,
            segments_data=segments,
            total_dur=total_dur,
            gemini_api_key=actual_gemini_key,
            gemini_model=gemini_model_input,
            precomputed_chapters=ai_chapters
        )
        print("✨ Đã chuẩn hóa và cập nhật mục Timestamps chuẩn xác 100% vào mô tả YouTube!")
    except Exception as e_ch:
        print(f"⚠️ Cảnh báo tạo Chapters: {e_ch}")

    # Lưu metadata json
    meta_path = os.path.join(outputs_dir, f"meta_{session_id}.json")
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "session_id": session_id,
                "title": final_title,
                "channel_profile": channel_profile,
                "description": yt_description,
                "video_path": video_path,
                "audio_path": delivered_audio_path,
                "schedule_time": sched_time_str if sched_time_str else "",
                "prompts_txt": os.path.join(outputs_dir, f"prompts_{session_id}.txt"),
                "prompts_json": os.path.join(outputs_dir, f"prompts_{session_id}.json"),
                "created_at": datetime.now(timezone(timedelta(hours=7))).isoformat()
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Lưu meta: {e}")

    # 1-CLICK TỰ ĐỘNG ĐĂNG YOUTUBE
    if auto_upload_yt:
        if progress is not None:
            progress(0.95, desc="🚀 Đang tự động kết nối YouTube & Đăng video (1-Click Auto Upload)...")
        try:
            yt_res = upload_to_youtube(
                "outputs", video_path, video_path, None,
                final_title, yt_description,
                custom_yt_tags if custom_yt_tags else prof.get("tags", DEFAULT_TAGS),
                bool(sched_time_str), sched_time_str, yt_privacy,
                editor_email, shared_drive_folder,
                outputs_dir=outputs_dir, channel_profile=channel_profile
            )
            status_msg += f"\n\n============================================================\n🚀 KẾT QUẢ ĐĂNG YOUTUBE TỰ ĐỘNG:\n{yt_res}\n============================================================"
        except Exception as yt_err:
            status_msg += f"\n\n⚠️ Lỗi khi tự động đăng YouTube: {yt_err}"

    return video_path, delivered_audio_path, srt_path, gallery_thumbs, status_msg, final_title, yt_description


def process_batch_pipeline(
    uploaded_files: Any,
    folder_path: str,
    aspect_ratio: str,
    visual_mode: str,
    sync_mode_choice: str,
    num_scenes_slider: int,
    pexels_key_input: str,
    gemini_api_key_input: str,
    gemini_model_input: str,
    allow_reuse_input: bool,
    voice_selected: str,
    title_font_size: int = 40,
    title_style: str = "✨ Điện Ảnh Sang Trọng (Chữ Trắng Đổ Bóng - Không Hộp Đen)",
    bgm_file: Any = None,
    bgm_gdrive_url: str = "",
    bgm_volume: float = 0.15,
    add_subtitles: bool = True,
    sub_color: str = "Vàng viền đen (Nổi bật - Khuyên dùng)",
    waveform_style: str = "Tắt",
    retention_cuts_enabled: bool = True,
    sub_font_size: int = 18,
    auto_upload_yt: bool = True,
    yt_privacy: str = "Riêng tư / Hẹn giờ (private)",
    editor_email: str = "",
    shared_drive_folder: str = "",
    channel_profile: str = "🕯️ Trinh Thám & Kinh Dị Gothic (Kênh Nỗi Sợ AudioBook)",
    custom_visual_concept: str = "",
    custom_yt_tags: str = "",
    custom_yt_desc: str = "",
    check_published_first: bool = True,
    temp_dir: str = "temp_work",
    outputs_dir: str = "outputs",
    progress=None
) -> str:
    """
    HỆ THỐNG XỬ LÝ HÀNG LOẠT NHIỀU KỊCH BẢN (BATCH PROCESSING) V20:
    - Hỗ trợ tải lên nhiều file .txt hoặc quét folder kịch bản.
    - Tự động kiểm tra file quan_ly_san_xuat.csv để bỏ qua kịch bản đã đăng (chống trùng lặp).
    - Sản xuất nối tiếp từng video và xuất báo cáo tổng kết.
    """
    script_paths = []
    if uploaded_files:
        if isinstance(uploaded_files, list):
            for uf in uploaded_files:
                p = uf.name if hasattr(uf, "name") else str(uf)
                if os.path.exists(p) and p.endswith(".txt"):
                    script_paths.append(p)
        else:
            p = uploaded_files.name if hasattr(uploaded_files, "name") else str(uploaded_files)
            if os.path.exists(p) and p.endswith(".txt"):
                script_paths.append(p)

    if folder_path and os.path.exists(folder_path.strip()):
        txt_files = sorted(glob.glob(os.path.join(folder_path.strip(), "*.txt")))
        for tf in txt_files:
            if tf not in script_paths:
                script_paths.append(tf)

    if not script_paths:
        return "❌ Lỗi: Không tìm thấy file kịch bản (.txt) nào từ upload hoặc thư mục chỉ định!"

    total_files = len(script_paths)
    print(f"📦 Bắt đầu xử lý hàng loạt {total_files} kịch bản...")

    results_log = []
    skipped_count = 0
    success_count = 0

    for i, sp in enumerate(script_paths, 1):
        file_name = os.path.basename(sp)
        print(f"\n[{i}/{total_files}] Đang xử lý file: {file_name}")

        # Kiểm tra kịch bản đã đăng hay chưa
        if check_published_first:
            already, row_info = check_script_already_published(sp, shared_drive_folder)
            if already:
                msg = f"⏭️ Bỏ qua {file_name}: Kịch bản đã được xuất bản trước đó (Link: {row_info.get('Link_Video', '')})."
                print(msg)
                results_log.append(msg)
                skipped_count += 1
                continue

        try:
            with open(sp, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                continue

            v_path, _, _, _, s_msg, f_title, _ = process_full_pipeline(
                script_input=content,
                aspect_ratio=aspect_ratio,
                visual_mode=visual_mode,
                sync_mode_choice=sync_mode_choice,
                num_scenes_slider=num_scenes_slider,
                pexels_key_input=pexels_key_input,
                gemini_api_key_input=gemini_api_key_input,
                gemini_model_input=gemini_model_input,
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
                auto_upload_yt=auto_upload_yt,
                yt_privacy=yt_privacy,
                editor_email=editor_email,
                shared_drive_folder=shared_drive_folder,
                channel_profile=channel_profile,
                custom_visual_concept=custom_visual_concept,
                custom_yt_tags=custom_yt_tags,
                custom_yt_desc=custom_yt_desc,
                temp_dir=temp_dir,
                outputs_dir=outputs_dir,
                progress=progress
            )
            success_count += 1
            results_log.append(f"✅ [{i}/{total_files}] Hoàn tất: {file_name} -> {os.path.basename(v_path)}")
        except Exception as e_batch:
            err = f"❌ [{i}/{total_files}] Thất bại {file_name}: {e_batch}"
            print(err)
            results_log.append(err)

    summary_header = f"🎉 KẾT QUẢ XỬ LÝ HÀNG LOẠT:\n- Tổng số file: {total_files}\n- Thành công: {success_count}\n- Bỏ qua (đã đăng): {skipped_count}\n\n"
    return summary_header + "\n".join(results_log)
