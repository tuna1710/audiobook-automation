import re
import json
import os
import glob
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any
import gradio as gr

from ..pipeline import (
    process_full_pipeline,
    process_batch_pipeline,
    CHANNEL_PROFILES_PRESET,
    get_channel_profile,
    get_channel_token_file,
    DEFAULT_TAGS
)
from ..tts import (
    PRESET_VOICES,
    clean_voice_name,
    extract_script_components,
    preview_voice_sample
)
from ..ai_director import DEFAULT_PEXELS_KEYS
from ..youtube import (
    upload_to_youtube,
    get_youtube_auth_url,
    verify_oauth_code_and_save_token,
    find_token_file,
    resolve_file_path
)

TITLE_STYLES = [
    "✨ Điện Ảnh Sang Trọng (Chữ Trắng Đổ Bóng - Không Hộp Đen)",
    "📦 Hộp Nền Đen Mờ (Tăng độ tương phản)",
    "🚫 Tắt Tiêu Đề (Khung hình sạch 100%)"
]

SUB_COLORS = [
    "Vàng viền đen (Nổi bật - Khuyên dùng)",
    "Trắng viền đen (Cổ điển)"
]

WAVEFORM_CHOICES = [
    "Tắt (Không dùng sóng nhạc)",
    "📊 Equalizer Cổ Điển (Cyan & Gold)",
    "〰️ Mềm Mại Tối Giản (White Line)",
    "✨ Vàng Ánh Kim (Gold Bar)",
    "🌈 Gradient Hiện Đại (Cyan & Purple)"
]

VISUAL_MODES_V20 = [
    "🎨 100% Ảnh Nghệ Thuật AI (SDXL Photorealism)",
    "🎬 100% Video Stock (Pexels / Coverr / Mixkit)"
]

SYNC_MODES = [
    "⚡ Tự động theo từng câu Subtitle (Whisper Sync)",
    "🎛️ Cắt đều theo số lượng cảnh thủ công"
]

GEMINI_MODELS = [
    "⚡ gemini-3.5-flash-lite (Khuyên dùng Free Tier - Siêu nhanh & Tiết kiệm Quota)",
    "🌟 gemini-3.8-flash (Chất lượng đạo diễn cao nhất - Chuẩn All-in-One)",
    "⚖️ gemini-3.5-flash (Cân bằng tốc độ & Độ chi tiết)",
    "🛡️ gemini-3.1-flash-lite (Dự phòng ổn định dòng Lite)",
    "🎯 gemini-3.7-flash (Tư duy & Đạo diễn phân cảnh nâng cao)"
]

VOICE_OPTIONS = [
    "Thiền Tâm Đức (Nam - Trầm ấm, chiêm nghiệm, Gothic & Phật pháp - Mặc định)",
    "Minh Đức (Nam - Kịch tính, trinh thám, podcast)",
    "Mai Anh (Nữ - Ấm áp, truyền cảm, tự nhiên)",
    "Ngọc Huyền (Nữ - Dịu dàng, thanh thoát, khoa học & cổ tích)",
    "Thanh Bình (Nam - Truyền cảm, bài học cuộc sống)",
    "Thùy Dung (Nữ - Nhẹ nhàng, cảm xúc)",
    "Minh Triết (Nam - Hào hùng, lịch sử & sử thi)",
    "Hải Đăng (Nam - Mạnh mẽ, dứt khoát)",
    "Mỹ Duyên (Nữ - Ngọt ngào, tự sự)",
    "Quỳnh Anh (Nữ - Trong sáng, biểu cảm)",
    "Đoan Trang (Nữ - Trang nhã, thanh lịch)",
    "Đức Trí (Nam - Hiện đại, tự nhiên)",
    "Quốc Tuấn (Nam - Trầm, dứt khoát)"
]

DEFAULT_KEYS_TEXT = "\n".join(DEFAULT_PEXELS_KEYS)


def get_available_rendered_videos(outputs_dir: str = "outputs") -> List[str]:
    """Quét danh sách tất cả các file video đã render hoặc lưu trong thư mục outputs."""
    if not os.path.exists(outputs_dir):
        return ["(Chưa có video nào trong thư mục outputs)"]
    extensions = ("*.mp4", "*.mov", "*.mkv", "*.webm", "*.avi")
    vids = []
    for ext in extensions:
        vids.extend(glob.glob(os.path.join(outputs_dir, ext)))
        vids.extend(glob.glob(os.path.join(outputs_dir, "*", ext)))
    if not vids:
        return ["(Chưa có video nào trong thư mục outputs)"]
    unique_vids = list(set(vids))
    unique_vids.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    res = [os.path.relpath(v, outputs_dir) for v in unique_vids]
    return res if res else ["(Chưa có video nào trong thư mục outputs)"]


def load_video_metadata_for_ui(selected_vid: str, outputs_dir: str = "outputs", sample_tomorrow_vn: str = "") -> dict:
    """Đọc metadata (tiêu đề, mô tả, lên lịch, tags, thumbnail, channel) theo video được chọn."""
    default_channel = "🕯️ Trinh Thám & Kinh Dị Gothic (Kênh Nỗi Sợ AudioBook)"
    default_res = {
        "video_path": None,
        "thumbnail_path": None,
        "title": "",
        "description": "",
        "tags": DEFAULT_TAGS,
        "channel_profile": default_channel,
        "is_schedule": True,
        "schedule_time": sample_tomorrow_vn
    }
    if not selected_vid or str(selected_vid).startswith("("):
        return default_res

    vid_path = selected_vid if os.path.isabs(selected_vid) else os.path.join(outputs_dir, selected_vid)
    if not os.path.exists(vid_path):
        return default_res

    default_res["video_path"] = vid_path
    base_name = os.path.splitext(os.path.basename(vid_path))[0]
    session_id = base_name
    for prefix in ["video_", "final_video_", "rendered_"]:
        if base_name.startswith(prefix):
            session_id = base_name[len(prefix):]
            break

    # 1. Tìm file metadata JSON
    meta_candidates = [
        os.path.join(outputs_dir, f"meta_{session_id}.json"),
        os.path.join(outputs_dir, f"meta_{base_name}.json"),
        os.path.join(outputs_dir, f"{base_name}.json"),
        os.path.join(outputs_dir, f"{session_id}.json")
    ]
    meta_data = {}
    for cand in meta_candidates:
        if os.path.exists(cand):
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                break
            except Exception:
                pass

    if not meta_data and os.path.exists(outputs_dir):
        for m_file in glob.glob(os.path.join(outputs_dir, "meta_*.json")):
            try:
                with open(m_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if d.get("session_id") == session_id or os.path.basename(d.get("video_path", "")) == os.path.basename(vid_path):
                        meta_data = d
                        break
            except Exception:
                continue

    # 2. Tìm thumbnail
    thumb_path = None
    if meta_data.get("thumbnail_path") and os.path.exists(meta_data.get("thumbnail_path")):
        thumb_path = meta_data.get("thumbnail_path")
    else:
        thumb_candidates = [
            os.path.join(outputs_dir, f"thumbnail_{session_id}.jpg"),
            os.path.join(outputs_dir, f"thumbnail_{session_id}.png"),
            os.path.join(outputs_dir, f"thumbnail_{base_name}.jpg"),
            os.path.join(outputs_dir, f"thumbnail_{base_name}.png"),
            os.path.join(outputs_dir, f"{base_name}.jpg"),
            os.path.join(outputs_dir, f"{base_name}.png"),
            os.path.join(outputs_dir, "thumbnail_latest.jpg")
        ]
        for t_cand in thumb_candidates:
            if os.path.exists(t_cand):
                thumb_path = t_cand
                break
    default_res["thumbnail_path"] = thumb_path

    # 3. Trích xuất Title
    if meta_data.get("title"):
        default_res["title"] = str(meta_data.get("title")).strip()
    else:
        clean_title = re.sub(r'^(video_|final_video_)', '', base_name).replace('_', ' ').strip().title()
        default_res["title"] = clean_title

    # 4. Trích xuất Channel Profile & Tags
    channel_name = meta_data.get("channel_profile", "")
    if channel_name and channel_name in CHANNEL_PROFILES_PRESET:
        default_res["channel_profile"] = channel_name

    prof = CHANNEL_PROFILES_PRESET.get(default_res["channel_profile"], {})
    if meta_data.get("tags"):
        default_res["tags"] = meta_data.get("tags")
    else:
        default_res["tags"] = prof.get("tags", DEFAULT_TAGS)

    # 5. Trích xuất Description
    if meta_data.get("description"):
        default_res["description"] = meta_data.get("description")
    else:
        desc_tmpl = prof.get("desc_template", "")
        default_res["description"] = default_res["title"] + chr(10) + chr(10) + desc_tmpl + chr(10) + chr(10) + "#Audiobook #VideoEssay"

    # 6. Trích xuất Lên lịch
    if meta_data.get("schedule_time"):
        default_res["schedule_time"] = meta_data.get("schedule_time")
        default_res["is_schedule"] = meta_data.get("is_schedule", True)
    elif "is_schedule" in meta_data:
        default_res["is_schedule"] = meta_data.get("is_schedule")

    return default_res


def create_gradio_app(outputs_dir: str = "outputs", temp_dir: str = "temp_work", default_gemini_key: str = "", default_pexels_key: str = ""):
    """Khởi tạo giao diện Gradio V20.0."""
    vn_tz = timezone(timedelta(hours=7))
    sample_tomorrow_vn = (datetime.now(vn_tz) + timedelta(days=1)).strftime("%Y-%m-%d 19:30")

    sample_script = f"""Tiêu đề: BÍ MẬT DƯỚI TẦNG HẦM CỦA DINH THỰ GOTHIC
- Visual: 19th century Victorian Gothic manor in heavy dense midnight fog, flickering gas lamps, dark moody chiaroscuro lighting, detective mystery
[LỊCH ĐĂNG]: {sample_tomorrow_vn}
[MÔ TẢ VIDEO]: Audiobook kinh dị gothic và trinh thám tâm lý kinh điển - Kênh Nỗi Sợ AudioBook. Cùng khám phá những bí ẩn rùng rợn bị chôn giấu qua năm tháng.
#NoiSoAudioBook #TruyenTrinhTham #KinhDiGothic #EdgarAllanPoe #SherlockHolmes #SachNoiKinhDi

--- [VĂN BẢN ĐỌC CHO VIENEU-TTS-V3-TURBO] ---
Đêm hôm đó, một cơn mưa lạnh buốt bao trùm khắp thị trấn cổ kính.
Ánh đèn dầu lập lòe hắt những cái bóng kỳ dị lên bức tường đá ẩm mốc.
Từ sâu dưới tầng hầm dinh thự cổ, một tiếng gõ cửa bí ẩn vang lên đều đặn.
Ai đang ẩn nấp sau cánh cửa gỗ sồi đã bị khóa chặt suốt trăm năm qua?
Một bí mật kinh hoàng sắp sửa được phơi bày trong bóng tối mịt mù."""

    colab_gemini_key = default_gemini_key.strip() if default_gemini_key and default_gemini_key.strip() else os.environ.get("GEMINI_API_KEY", "")
    active_pexels_text = default_pexels_key.strip() if default_pexels_key and default_pexels_key.strip() else DEFAULT_KEYS_TEXT

    with gr.Blocks(title="NỖI SỢ AUDIOBOOK - HỆ THỐNG DỰNG VIDEO TRINH THÁM & KINH DỊ GOTHIC V20.0") as demo:
        gr.Markdown("# 🎙️🎬 NỖI SỢ AUDIOBOOK: TRÌNH TẠO VIDEO TRINH THÁM & KINH DỊ GOTHIC ĐIỆN ẢNH V20.0")
        gr.Markdown("📱 **Video Dọc 9:16 Gốc (Không Cắt Xén)** | 📁 **Tách Sạch outputs/ & temp_work/** | ⚡ **Đồng Bộ Từng Câu Subtitle** | 🤖 **AI Đạo Diễn All-in-One** | 🔑 **Pexels / Coverr / Mixkit**")

        with gr.Tabs():
            # =================================================================
            # TAB 1: TẠO VIDEO ESSAY
            # =================================================================
            with gr.Tab("🎬 TAB 1: TẠO VIDEO ESSAY"):
                with gr.Row():
                    with gr.Column(scale=6):
                        with gr.Row():
                            channel_profile_dropdown = gr.Dropdown(
                                label="📺 Chọn Hồ Sơ Kênh (Preset 1-Click Tự Động Hóa):",
                                choices=list(CHANNEL_PROFILES_PRESET.keys()),
                                value="🕯️ Trinh Thám & Kinh Dị Gothic (Kênh Nỗi Sợ AudioBook)",
                                scale=5
                            )
                            visual_concept_box = gr.Textbox(
                                label="🎨 Không Gian Mỹ Thuật / Concept Hình Ảnh (Tự động theo Kênh):",
                                value=CHANNEL_PROFILES_PRESET["🕯️ Trinh Thám & Kinh Dị Gothic (Kênh Nỗi Sợ AudioBook)"]["visual_concept"],
                                lines=1,
                                scale=7
                            )

                        with gr.Row():
                            aspect_ratio_radio = gr.Radio(
                                label="📱 Định dạng Khung Hình Video (Aspect Ratio):",
                                choices=[
                                    "16:9 Ngang (YouTube Video Essay Chuẩn - 1920x1080)",
                                    "9:16 Dọc (TikTok / YouTube Shorts / Facebook Reels - 1080x1920)"
                                ],
                                value="16:9 Ngang (YouTube Video Essay Chuẩn - 1920x1080)",
                                scale=3
                            )
                            visual_mode_dropdown = gr.Dropdown(
                                label="🎯 Chọn Phương Pháp Hình Ảnh/Video:",
                                choices=VISUAL_MODES_V20,
                                value=VISUAL_MODES_V20[0],
                                scale=4
                            )

                        with gr.Row():
                            sync_mode_dropdown = gr.Dropdown(
                                label="⚡ Cơ chế Đồng Bộ Phân Cảnh (Subtitle Sync):",
                                choices=SYNC_MODES,
                                value=SYNC_MODES[0],
                                scale=4
                            )
                            retention_cuts_cb = gr.Checkbox(
                                label="🎯 Quy tắc 2 phút giữ chân người xem (Retention Cuts)",
                                value=True,
                                info="Tự động khóa chặt nhịp cắt cảnh 2.4s - 6.8s chống trôi lệch hình.",
                                scale=3
                            )
                            num_scenes_slider = gr.Slider(
                                minimum=4,
                                maximum=120,
                                value=12,
                                step=1,
                                label="🎛️ Số lượng cảnh (Khi chọn Thủ công):",
                                scale=3
                            )

                        with gr.Accordion("🤖 CẤU HÌNH AI ĐẠO DIỄN V20 (HÌNH ĐI CÙNG SUB 100% & 1 REQUEST ALL-IN-ONE)", open=True):
                            with gr.Row():
                                gemini_key_box = gr.Textbox(
                                    label="🔑 Google Gemini API Key (Miễn phí tại aistudio.google.com):",
                                    placeholder="Dán Gemini API Key vào đây...",
                                    value=colab_gemini_key,
                                    type="password",
                                    scale=4
                                )
                                gemini_model_dropdown = gr.Dropdown(
                                    label="🧠 Chọn Model AI Đạo Diễn (Google AI Studio 2026):",
                                    choices=GEMINI_MODELS,
                                    value=GEMINI_MODELS[0],
                                    scale=3
                                )
                                allow_reuse_cb = gr.Checkbox(
                                    label="♻️ Tiết kiệm GPU (Tái sử dụng ảnh)",
                                    value=False,
                                    info="Mặc định TẮT: 100% phân cảnh đều có ảnh độc bản.",
                                    scale=2
                                )

                        with gr.Accordion("🔑 CỤM PEXELS & STOCK API KEYS (COVERR / MIXKIT / PEXELS)", open=False):
                            pexels_key_box = gr.Textbox(
                                label="Danh sách Pexels API Key (Tự động xoay tua khi chạm rate limit):",
                                value=active_pexels_text,
                                lines=2
                            )

                        with gr.Row():
                            script_file_upload = gr.File(
                                label="📂 Tải lên 1 File Kịch Bản (.txt, .md):",
                                file_types=[".txt", ".md"],
                                scale=3
                            )
                            btn_clear_script = gr.Button("🗑️ Xóa trắng kịch bản", scale=1)

                        script_box = gr.Textbox(
                            label="📄 Nội dung Kịch bản (Bao gồm tiêu đề, visual concept, mốc thời gian và văn bản đọc):",
                            lines=10,
                            value=sample_script
                        )

                        with gr.Row():
                            voice_dropdown = gr.Dropdown(
                                label="🔊 Giọng đọc VieNeu-TTS (48kHz):",
                                choices=VOICE_OPTIONS,
                                value=VOICE_OPTIONS[0],
                                scale=3
                            )
                            btn_preview_voice = gr.Button("🎧 Nghe thử giọng này", variant="secondary", scale=1)
                            title_top_box = gr.Textbox(
                                label="🏷️ Tiêu đề hiển thị trên video:",
                                placeholder="Để trống hệ thống tự bóc tách...",
                                lines=1,
                                scale=3
                            )

                        with gr.Row():
                            title_style_dropdown = gr.Dropdown(
                                label="🎨 Kiểu dáng Tiêu đề trên video:",
                                choices=TITLE_STYLES,
                                value=TITLE_STYLES[0],
                                scale=3
                            )
                            title_size_slider = gr.Slider(minimum=20, maximum=100, value=60, step=2, label="🔠 Cỡ chữ Tiêu đề:", scale=2)

                        preview_voice_audio = gr.Audio(
                            label="🔊 Âm thanh nghe thử giọng đọc:",
                            type="filepath",
                            interactive=False
                        )

                        with gr.Accordion("🌊 CÀI ĐẶT SÓNG NHẠC (VISUALIZER), NHẠC NỀN BGM & PHỤ ĐỀ", open=False):
                            with gr.Row():
                                waveform_dropdown = gr.Dropdown(
                                    label="🌊 Kiểu Sóng Nhạc:",
                                    choices=WAVEFORM_CHOICES,
                                    value=WAVEFORM_CHOICES[0],
                                    scale=3
                                )
                                bgm_vol_slider = gr.Slider(minimum=0.02, maximum=0.35, value=0.10, step=0.01, label="Âm lượng BGM:", scale=2)

                            with gr.Row():
                                bgm_upload = gr.Audio(label="Tải lên file nhạc BGM (MP3/WAV):", type="filepath", scale=2)
                                bgm_gdrive_box = gr.Textbox(
                                    label="Hoặc dán Link Nhạc từ Google Drive:",
                                    placeholder="https://drive.google.com/file/d/.../view?usp=sharing",
                                    lines=1,
                                    scale=2
                                )

                            with gr.Row():
                                add_subtitles_cb = gr.Checkbox(label="📝 Bật Phụ đề tự động (Whisper Safe Zone)", value=True, scale=2)
                                sub_color_dropdown = gr.Dropdown(
                                    label="Màu sắc phụ đề:",
                                    choices=SUB_COLORS,
                                    value=SUB_COLORS[0],
                                    scale=2
                                )
                                sub_size_slider = gr.Slider(
                                    minimum=14,
                                    maximum=40,
                                    value=18,
                                    step=1,
                                    label="🔤 Cỡ chữ Phụ đề (Mặc định 18):",
                                    scale=2
                                )

                        with gr.Accordion("🚀 TỰ ĐỘNG ĐĂNG YOUTUBE NGAY SAU KHI RENDER (1-CLICK AUTO UPLOAD)", open=True):
                            with gr.Row():
                                yt_privacy_t1 = gr.Dropdown(
                                    label="Chế độ riêng tư YouTube:",
                                    choices=["Riêng tư / Hẹn giờ (private)", "Công khai (public)", "Không công khai (unlisted)"],
                                    value="Riêng tư / Hẹn giờ (private)",
                                    scale=2
                                )
                            with gr.Row():
                                editor_email_t1 = gr.Textbox(
                                    label="Email người phụ trách (Ghi log CSV nhóm):",
                                    placeholder="VD: editor@gmail.com",
                                    scale=3
                                )
                                shared_drive_folder_t1 = gr.Textbox(
                                    label="Thư mục Google Drive dùng chung (Lưu quan_ly_san_xuat.csv):",
                                    value="/content/drive/MyDrive/BAO CAO CONG VIEC",
                                    scale=3
                                )

                        with gr.Row():
                            generate_btn = gr.Button("🚀 BẮT ĐẦU TẠO VIDEO ESSAY NGAY (CHỈ TẠO)", variant="secondary", size="lg", scale=1)
                            generate_and_upload_btn = gr.Button("🎬 TẠO VIDEO & TỰ ĐỘNG ĐĂNG YOUTUBE", variant="primary", size="lg", scale=1)

                    with gr.Column(scale=5):
                        status_display = gr.Textbox(label="Trạng thái tiến trình xử lý:", interactive=False, lines=6)
                        video_output = gr.Video(label="🎬 Video MP4 Thành Phẩm (Native 9:16 Full Frame + Khớp Subtitle):")
                        with gr.Row():
                            audio_output = gr.Audio(label="🎙️ Audio Lời Bình Đã Hòa Âm (WAV):", type="filepath", scale=2)
                            srt_output = gr.File(label="📄 Tải file phụ đề (.SRT):", scale=2)
                        gallery_output = gr.Gallery(label="🖼️ Phân cảnh hình ảnh & Thumbnail CTR Booster:", columns=4, height=180)

            # =================================================================
            # TAB 2: TẠO HÀNG LOẠT (BATCH PROCESSING)
            # =================================================================
            with gr.Tab("📦 TAB 2: TẠO VIDEO HÀNG LOẠT (BATCH PROCESSING)"):
                with gr.Row():
                    with gr.Column(scale=6):
                        b_channel_profile = gr.Dropdown(
                            label="📺 Chọn Hồ Sơ Kênh cho Đợt Batch này:",
                            choices=list(CHANNEL_PROFILES_PRESET.keys()),
                            value="🕯️ Trinh Thám & Kinh Dị Gothic (Kênh Nỗi Sợ AudioBook)"
                        )
                        b_visual_concept_box = gr.Textbox(
                            label="🎨 Mỹ thuật / Concept cho loạt kịch bản:",
                            value=CHANNEL_PROFILES_PRESET["🕯️ Trinh Thám & Kinh Dị Gothic (Kênh Nỗi Sợ AudioBook)"]["visual_concept"],
                            lines=1
                        )
                        with gr.Row():
                            batch_files_upload = gr.File(
                                label="📂 Tải lên nhiều file .txt:",
                                file_count="multiple",
                                file_types=[".txt"],
                                scale=3
                            )
                            batch_folder_input = gr.Textbox(
                                label="📁 Hoặc đường dẫn thư mục kịch bản:",
                                placeholder="/content/drive/MyDrive/KichBan",
                                scale=3
                            )

                        with gr.Row():
                            b_aspect_ratio = gr.Radio(
                                label="Định dạng khung hình:",
                                choices=["16:9 Ngang (1920x1080)", "9:16 Dọc (1080x1920)"],
                                value="16:9 Ngang (1920x1080)",
                                scale=3
                            )
                            b_visual_mode = gr.Dropdown(
                                label="Phương pháp hình ảnh:",
                                choices=VISUAL_MODES_V20,
                                value=VISUAL_MODES_V20[0],
                                scale=3
                            )

                        with gr.Row():
                            b_voice = gr.Dropdown(
                                label="Giọng đọc VieNeu:",
                                choices=VOICE_OPTIONS,
                                value=VOICE_OPTIONS[0],
                                scale=3
                            )
                            b_btn_preview_voice = gr.Button("🎧 Nghe thử giọng", scale=1)
                            b_check_published = gr.Checkbox(
                                label="🛡️ Bỏ qua kịch bản đã đăng (Kiểm tra quan_ly_san_xuat.csv)",
                                value=True,
                                scale=2
                            )

                        b_preview_voice_audio = gr.Audio(label="Nghe thử giọng (Batch):", type="filepath", interactive=False)

                        with gr.Row():
                            b_editor_email = gr.Textbox(label="Email người làm (Báo cáo CSV):", scale=3)
                            b_shared_drive = gr.Textbox(label="Thư mục Drive dùng chung:", value="/content/drive/MyDrive/BAO CAO CONG VIEC", scale=3)

                        with gr.Row():
                            batch_run_btn = gr.Button("🚀 BẮT ĐẦU CHẠY BATCH (CHỈ TẠO)", variant="secondary", size="lg")
                            batch_run_and_upload_btn = gr.Button("🎬 CHẠY BATCH & TỰ ĐỘNG ĐĂNG YOUTUBE", variant="primary", size="lg")

                    with gr.Column(scale=6):
                        batch_status_box = gr.Textbox(label="Nhật ký xử lý hàng loạt:", lines=18, interactive=False)

            # =================================================================
            # TAB 3: ĐĂNG & LÊN LỊCH PHÁT HÀNH YOUTUBE
            # =================================================================
            with gr.Tab("🚀 TAB 3: ĐĂNG & LÊN LỊCH PHÁT HÀNH YOUTUBE"):
                with gr.Row():
                    with gr.Column(scale=6):
                        yt_channel_dropdown = gr.Dropdown(
                            label="📺 Chọn Hồ Sơ Kênh cần đăng (Tự động tải đúng token tương ứng):",
                            choices=list(CHANNEL_PROFILES_PRESET.keys()),
                            value="🕯️ Trinh Thám & Kinh Dị Gothic (Kênh Nỗi Sợ AudioBook)"
                        )
                        yt_video_source = gr.Radio(
                            label="Nguồn Video:",
                            choices=[
                                "🎬 Video vừa tạo ở Tab 1 (Mặc định)",
                                "📁 Chọn từ danh sách thư mục outputs/",
                                "💻 Tải file video tùy chọn từ máy tính"
                            ],
                            value="🎬 Video vừa tạo ở Tab 1 (Mặc định)"
                        )
                        with gr.Row():
                            history_vids_dropdown = gr.Dropdown(
                                label="Danh sách video trong thư mục outputs/: ",
                                choices=get_available_rendered_videos(outputs_dir),
                                value=get_available_rendered_videos(outputs_dir)[0] if get_available_rendered_videos(outputs_dir) else None,
                                scale=4
                            )
                            btn_refresh_vids = gr.Button("🔄 Làm mới danh sách", scale=2, variant="secondary")

                        with gr.Row():
                            history_vid_preview = gr.Video(
                                label="👁️ Video đã chọn từ thư mục outputs/: ",
                                interactive=False,
                                height=240,
                                scale=1
                            )
                            yt_thumbnail_image = gr.Image(
                                label="🖼️ Thumbnail tự động liên kết (hoặc tải ảnh mới):",
                                type="filepath",
                                height=240,
                                scale=1
                            )
                        custom_vid_upload = gr.File(label="Tải video từ máy:", file_types=[".mp4", ".mov", ".mkv"])

                        yt_title_box = gr.Textbox(label="Tiêu đề YouTube (Tối đa 100 ký tự):", lines=1)
                        yt_desc_box = gr.Textbox(label="Mô tả YouTube (Đã kèm Timestamps & Hashtags):", lines=6)
                        yt_tags_box = gr.Textbox(label="Thẻ Tags (Cách nhau bằng dấu phẩy):", value=DEFAULT_TAGS, lines=2)

                        with gr.Row():
                            schedule_cb = gr.Checkbox(label="⏰ Lên lịch phát hành tự động", value=True, scale=1)
                            custom_sched_time_box = gr.Textbox(
                                label="Thời gian hẹn giờ (YYYY-MM-DD HH:MM):",
                                value=sample_tomorrow_vn,
                                scale=2
                            )
                            yt_privacy_status = gr.Dropdown(
                                label="Trạng thái nếu không hẹn giờ:",
                                choices=["private", "public", "unlisted"],
                                value="private",
                                scale=1
                            )

                        yt_upload_btn = gr.Button("🚀 XÁC NHẬN TẢI LÊN YOUTUBE NGAY", variant="primary", size="lg")

                    with gr.Column(scale=6):
                        yt_result_box = gr.Textbox(label="Kết quả tải lên YouTube:", lines=10, interactive=False)

                        with gr.Accordion("🔑 XÁC THỰC OAUTH2 YOUTUBE (NẾU CHƯA CÓ TOKEN)", open=False):
                            secrets_file_upload = gr.File(label="Tải lên client_secret.json:", file_types=[".json"])
                            redirect_uri_box = gr.Textbox(label="Redirect URI:", value="https://localhost")
                            btn_get_auth_url = gr.Button("👉 Bước 1: Lấy link đăng nhập Google")
                            auth_instruction_box = gr.Textbox(label="Hướng dẫn xác thực & Link đăng nhập:", lines=5, interactive=False)
                            auth_code_box = gr.Textbox(label="👉 Bước 2: Dán mã code hoặc toàn bộ URL chuyển hướng vào đây:")
                            btn_verify_code = gr.Button("✅ Bước 3: Xác thực & Lưu Token vĩnh viễn")
                            token_verify_status = gr.Textbox(label="Trạng thái xác thực:", interactive=False)

        # =====================================================================
        # SỰ KIỆN GIAO DIỆN (EVENT HANDLERS)
        # =====================================================================

        # Cập nhật thông tin khi đổi Hồ sơ Kênh
        def on_channel_profile_change(prof_name):
            prof = get_channel_profile(prof_name)
            return prof["visual_concept"], prof["voice"], prof["tags"], prof["desc_template"]

        channel_profile_dropdown.change(
            fn=on_channel_profile_change,
            inputs=[channel_profile_dropdown],
            outputs=[visual_concept_box, voice_dropdown, yt_tags_box, yt_desc_box]
        )

        b_channel_profile.change(
            fn=lambda p: (get_channel_profile(p)["visual_concept"], get_channel_profile(p)["voice"]),
            inputs=[b_channel_profile],
            outputs=[b_visual_concept_box, b_voice]
        )

        # Nghe thử giọng VieNeu
        btn_preview_voice.click(
            fn=lambda v: preview_voice_sample(v, temp_dir=temp_dir),
            inputs=[voice_dropdown],
            outputs=[preview_voice_audio]
        )
        b_btn_preview_voice.click(
            fn=lambda v: preview_voice_sample(v, temp_dir=temp_dir),
            inputs=[b_voice],
            outputs=[b_preview_voice_audio]
        )

        # Bóc tách kịch bản khi rời ô text
        def on_script_blur(raw_text, current_profile):
            t, v, _, d, s = extract_script_components(raw_text, channel_profile=current_profile)
            prof = get_channel_profile(current_profile)
            return t, t, d if d else prof.get("desc_template", ""), bool(s), s if s else sample_tomorrow_vn

        script_box.blur(
            fn=on_script_blur,
            inputs=[script_box, channel_profile_dropdown],
            outputs=[title_top_box, yt_title_box, yt_desc_box, schedule_cb, custom_sched_time_box]
        )

        btn_clear_script.click(fn=lambda: "", outputs=[script_box])

        # Đọc file kịch bản tải lên
        def load_script_file(f):
            if not f:
                return ""
            p = f.name if hasattr(f, "name") else str(f)
            try:
                with open(p, "r", encoding="utf-8") as fl:
                    return fl.read()
            except Exception:
                return ""

        script_file_upload.change(fn=load_script_file, inputs=[script_file_upload], outputs=[script_box])

        # Tab 1: Tạo video chỉ render
        def handle_tab1_generate(*args):
            return process_full_pipeline(
                script_input=args[0],
                aspect_ratio=args[1],
                visual_mode=args[2],
                sync_mode_choice=args[3],
                num_scenes_slider=args[4],
                pexels_key_input=args[5],
                gemini_api_key_input=args[6],
                gemini_model_input=args[7],
                allow_reuse_input=args[8],
                voice_selected=args[9],
                topic_title_custom=args[10],
                title_font_size=args[11],
                title_style=args[12],
                bgm_file=args[13],
                bgm_gdrive_url=args[14],
                bgm_volume=args[15],
                add_subtitles=args[16],
                sub_color=args[17],
                waveform_style=args[18],
                retention_cuts_enabled=args[19],
                sub_font_size=args[20],
                auto_upload_yt=False,
                yt_privacy=args[21],
                editor_email=args[22],
                shared_drive_folder=args[23],
                channel_profile=args[24],
                custom_visual_concept=args[25],
                custom_yt_tags="",
                custom_yt_desc="",
                temp_dir=temp_dir,
                outputs_dir=outputs_dir
            )

        # Tab 1: Tạo video và tự động đăng YouTube
        def handle_tab1_generate_and_upload(*args):
            return process_full_pipeline(
                script_input=args[0],
                aspect_ratio=args[1],
                visual_mode=args[2],
                sync_mode_choice=args[3],
                num_scenes_slider=args[4],
                pexels_key_input=args[5],
                gemini_api_key_input=args[6],
                gemini_model_input=args[7],
                allow_reuse_input=args[8],
                voice_selected=args[9],
                topic_title_custom=args[10],
                title_font_size=args[11],
                title_style=args[12],
                bgm_file=args[13],
                bgm_gdrive_url=args[14],
                bgm_volume=args[15],
                add_subtitles=args[16],
                sub_color=args[17],
                waveform_style=args[18],
                retention_cuts_enabled=args[19],
                sub_font_size=args[20],
                auto_upload_yt=True,
                yt_privacy=args[21],
                editor_email=args[22],
                shared_drive_folder=args[23],
                channel_profile=args[24],
                custom_visual_concept=args[25],
                custom_yt_tags="",
                custom_yt_desc="",
                temp_dir=temp_dir,
                outputs_dir=outputs_dir
            )

        tab1_inputs = [
            script_box, aspect_ratio_radio, visual_mode_dropdown, sync_mode_dropdown,
            num_scenes_slider, pexels_key_box, gemini_key_box, gemini_model_dropdown, allow_reuse_cb,
            voice_dropdown, title_top_box, title_size_slider, title_style_dropdown,
            bgm_upload, bgm_gdrive_box, bgm_vol_slider, add_subtitles_cb, sub_color_dropdown,
            waveform_dropdown, retention_cuts_cb, sub_size_slider, yt_privacy_t1,
            editor_email_t1, shared_drive_folder_t1, channel_profile_dropdown, visual_concept_box
        ]

        generate_btn.click(
            fn=handle_tab1_generate,
            inputs=tab1_inputs,
            outputs=[video_output, audio_output, srt_output, gallery_output, status_display, yt_title_box, yt_desc_box]
        )

        generate_and_upload_btn.click(
            fn=handle_tab1_generate_and_upload,
            inputs=tab1_inputs,
            outputs=[video_output, audio_output, srt_output, gallery_output, status_display, yt_title_box, yt_desc_box]
        )

        # Tab 2: Batch processing
        def handle_tab2_batch(*args):
            return process_batch_pipeline(
                uploaded_files=args[0],
                folder_path=args[1],
                aspect_ratio=args[2],
                visual_mode=args[3],
                sync_mode_choice=args[4],
                num_scenes_slider=12,
                pexels_key_input=args[5],
                gemini_api_key_input=args[6],
                gemini_model_input=args[7],
                allow_reuse_input=False,
                voice_selected=args[8],
                editor_email=args[9],
                shared_drive_folder=args[10],
                channel_profile=args[11],
                custom_visual_concept=args[12],
                check_published_first=args[13],
                auto_upload_yt=args[14],
                temp_dir=temp_dir,
                outputs_dir=outputs_dir
            )

        batch_run_btn.click(
            fn=lambda *a: handle_tab2_batch(*a, False),
            inputs=[
                batch_files_upload, batch_folder_input, b_aspect_ratio, b_visual_mode, sync_mode_dropdown,
                pexels_key_box, gemini_key_box, gemini_model_dropdown, b_voice,
                b_editor_email, b_shared_drive, b_channel_profile, b_visual_concept_box, b_check_published
            ],
            outputs=[batch_status_box]
        )

        batch_run_and_upload_btn.click(
            fn=lambda *a: handle_tab2_batch(*a, True),
            inputs=[
                batch_files_upload, batch_folder_input, b_aspect_ratio, b_visual_mode, sync_mode_dropdown,
                pexels_key_box, gemini_key_box, gemini_model_dropdown, b_voice,
                b_editor_email, b_shared_drive, b_channel_profile, b_visual_concept_box, b_check_published
            ],
            outputs=[batch_status_box]
        )

        # Tab 3: Video selection, metadata linking & refresh handlers
        def on_history_video_change(selected_vid):
            meta = load_video_metadata_for_ui(selected_vid, outputs_dir, sample_tomorrow_vn)
            return (
                meta["channel_profile"],
                meta["video_path"],
                meta["thumbnail_path"],
                meta["title"],
                meta["description"],
                meta["tags"],
                meta["is_schedule"],
                meta["schedule_time"]
            )

        def refresh_history_videos():
            vids = get_available_rendered_videos(outputs_dir)
            val = vids[0] if vids and not vids[0].startswith("(") else None
            meta = load_video_metadata_for_ui(val, outputs_dir, sample_tomorrow_vn)
            return (
                gr.update(choices=vids, value=val),
                meta["channel_profile"],
                meta["video_path"],
                meta["thumbnail_path"],
                meta["title"],
                meta["description"],
                meta["tags"],
                meta["is_schedule"],
                meta["schedule_time"]
            )

        def on_video_source_change(source, gen_video):
            if "outputs" in str(source).lower():
                vids = get_available_rendered_videos(outputs_dir)
                val = vids[0] if vids and not vids[0].startswith("(") else None
                meta = load_video_metadata_for_ui(val, outputs_dir, sample_tomorrow_vn)
                return (
                    gr.update(choices=vids, value=val),
                    meta["channel_profile"],
                    meta["video_path"],
                    meta["thumbnail_path"],
                    meta["title"],
                    meta["description"],
                    meta["tags"],
                    meta["is_schedule"],
                    meta["schedule_time"]
                )
            elif "máy tính" in str(source).lower():
                return gr.update(), gr.update(), None, None, gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
            else:
                meta = load_video_metadata_for_ui(gen_video, outputs_dir, sample_tomorrow_vn)
                return (
                    gr.update(),
                    meta["channel_profile"] if meta["channel_profile"] else gr.update(),
                    gen_video,
                    meta["thumbnail_path"],
                    meta["title"] if meta["title"] else gr.update(),
                    meta["description"] if meta["description"] else gr.update(),
                    meta["tags"] if meta["tags"] else gr.update(),
                    meta["is_schedule"],
                    meta["schedule_time"] if meta["schedule_time"] else gr.update()
                )

        def on_yt_channel_profile_change(prof_name):
            prof = get_channel_profile(prof_name)
            return prof.get("tags", DEFAULT_TAGS)

        btn_refresh_vids.click(
            fn=refresh_history_videos,
            outputs=[
                history_vids_dropdown,
                yt_channel_dropdown,
                history_vid_preview,
                yt_thumbnail_image,
                yt_title_box,
                yt_desc_box,
                yt_tags_box,
                schedule_cb,
                custom_sched_time_box
            ]
        )

        history_vids_dropdown.change(
            fn=on_history_video_change,
            inputs=[history_vids_dropdown],
            outputs=[
                yt_channel_dropdown,
                history_vid_preview,
                yt_thumbnail_image,
                yt_title_box,
                yt_desc_box,
                yt_tags_box,
                schedule_cb,
                custom_sched_time_box
            ]
        )

        yt_video_source.change(
            fn=on_video_source_change,
            inputs=[yt_video_source, video_output],
            outputs=[
                history_vids_dropdown,
                yt_channel_dropdown,
                history_vid_preview,
                yt_thumbnail_image,
                yt_title_box,
                yt_desc_box,
                yt_tags_box,
                schedule_cb,
                custom_sched_time_box
            ]
        )

        yt_channel_dropdown.change(
            fn=on_yt_channel_profile_change,
            inputs=[yt_channel_dropdown],
            outputs=[yt_tags_box]
        )

        # Tab 3: Upload YouTube
        yt_upload_btn.click(
            fn=upload_to_youtube,
            inputs=[
                yt_video_source, video_output, history_vids_dropdown, custom_vid_upload,
                yt_title_box, yt_desc_box, yt_tags_box, schedule_cb, custom_sched_time_box,
                yt_privacy_status, editor_email_t1, shared_drive_folder_t1,
                yt_thumbnail_image, yt_channel_dropdown
            ],
            outputs=[yt_result_box]
        )

        # OAuth helpers
        btn_get_auth_url.click(
            fn=get_youtube_auth_url,
            inputs=[secrets_file_upload, redirect_uri_box],
            outputs=[auth_instruction_box, redirect_uri_box]
        )

        btn_verify_code.click(
            fn=verify_oauth_code_and_save_token,
            inputs=[auth_code_box, redirect_uri_box],
            outputs=[token_verify_status]
        )

    return demo
