import os
import glob
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any
import gradio as gr

from ..pipeline import process_full_pipeline, process_batch_pipeline
from ..tts import PRESET_VOICES, extract_script_components
from ..youtube import (
    upload_to_youtube,
    get_youtube_auth_url,
    verify_oauth_code_and_save_token,
    find_token_file,
    resolve_file_path
)

TITLE_STYLES = [
    "✨ Điện Ảnh Sang Trọng (Chữ Trắng Đổ Bóng - Không Hộp Đen)",
    "🎬 Hộp Nền Đen Mờ Sang Trọng (Điện Ảnh Netflix)",
    "🚫 Tắt Tiêu Đề Trên Video (Chỉ hiển thị phụ đề & hình ảnh)"
]

SUB_COLORS = [
    "Vàng viền đen (Nổi bật - Khuyên dùng)",
    "Trắng viền đen (Thanh lịch)"
]

WAVEFORM_STYLES = [
    "Tắt (Khuyên dùng cho Phim Tài Liệu)",
    "Equalizer Hiện Đại (Cột sóng Cyan/Gold)",
    "Sóng Âm Mềm Mại (Đường line uốn lượn Trắng)",
    "Vàng Kim Huyền Bí (Cột sóng Gold)",
    "Dải Màu Gradient (Sóng neon Cyan/Tím)"
]

ART_STYLE_CHOICES = [
    "📷 Điện Ảnh Đời Thực (35mm Photorealistic - Mặc định)",
    "✏️ Phác Thảo Bút Chì Đen Trắng (Pencil & Charcoal Sketch)",
    "📜 Tranh Thủy Mặc Cổ Trang (Ink Wash & Watercolor)",
    "🕵️ Truyện Tranh Noir Cổ Điển (Vintage Graphic Novel Noir)"
]


def get_available_rendered_videos(outputs_dir: str = "outputs") -> List[str]:
    """
    Quét danh sách các file video đã render hoàn chỉnh trong thư mục outputs.
    """
    if not os.path.exists(outputs_dir):
        return ["(Chưa có video nào trong outputs)"]
    vids = sorted(glob.glob(os.path.join(outputs_dir, "video_*.mp4")), key=os.path.getmtime, reverse=True)
    names = [os.path.basename(v) for v in vids]
    return names if names else ["(Chưa có video nào trong outputs)"]


def get_sample_tomorrow_time() -> str:
    """
    Tạo mốc thời gian 19:30 tối ngày mai theo giờ Việt Nam (UTC+7).
    """
    vn_tz = timezone(timedelta(hours=7))
    tomorrow_vn = datetime.now(vn_tz) + timedelta(days=1)
    return tomorrow_vn.strftime("%Y-%m-%d 19:30")


def create_gradio_app(default_gemini_key: str = "", default_pexels_key: str = ""):
    """
    Xây dựng giao diện Web Gradio V19.7 đa nền tảng với đầy đủ 3 Tab chuyên nghiệp:
    - Tab 1: Sản xuất đơn lẻ với bộ chọn Phong Cách Nghệ Thuật (Art Style)
    - Tab 2: Sản xuất hàng loạt tích hợp cài đặt API Key & Phong cách riêng cho cả mẻ
    - Tab 3: Trung tâm phân phối YouTube Studio OAuth2
    """
    sample_time_vn = get_sample_tomorrow_time()

    with gr.Blocks(title="Audiobook Automation AI Studio V19.7") as demo:
        gr.Markdown(
            "# 🎙️ AUDIOBOOK AUTOMATION STUDIO V19.7\n"
            "### 🎬 Sản Xuất Video Essay & Audiobook Tự Động: VieNeu-TTS 48kHz | SDXL Multi-Art Styles | Whisper | 1-Click YouTube Auto Publish"
        )

        with gr.Tabs():
            # ==========================================================
            # TAB 1: SẢN XUẤT ĐƠN LẺ
            # ==========================================================
            with gr.TabItem("🎬 TAB 1: SẢN XUẤT VIDEO ĐƠN LẺ"):
                with gr.Row():
                    with gr.Column(scale=5):
                        script_box = gr.Textbox(
                            label="📜 Dán Nội Dung Kịch Bản Vào Đây:",
                            lines=12,
                            placeholder="Dán toàn bộ kịch bản (Bao gồm [TIÊU ĐỀ GỢI Ý], [Ý TƯỞNG THUMBNAIL], [MÔ TẢ VIDEO]...)"
                        )

                        aspect_ratio_radio = gr.Radio(
                            choices=[
                                "16:9 Ngang (YouTube Video Essay Chuẩn - 1920x1080)",
                                "9:16 Dọc (TikTok / YouTube Shorts / Facebook Reels - 1080x1920)"
                            ],
                            value="16:9 Ngang (YouTube Video Essay Chuẩn - 1920x1080)",
                            label="📱 Định Dạng Khung Hình:"
                        )

                        with gr.Row():
                            visual_mode_dropdown = gr.Dropdown(
                                choices=["SDXL (AI Hình Ảnh Ẩn Dụ)", "Pexels (Video Stock Chuyển Động)", "Pexels Ưu Tiên (Thiếu sẽ bù SDXL)"],
                                value="SDXL (AI Hình Ảnh Ẩn Dụ)",
                                label="🎨 Nguồn Tư Liệu Thị Giác:",
                                scale=2
                            )
                            art_style_dropdown = gr.Dropdown(
                                choices=ART_STYLE_CHOICES,
                                value=ART_STYLE_CHOICES[0],
                                label="🖌️ Phong Cách Nghệ Thuật (Art Style):",
                                scale=3
                            )

                        with gr.Row():
                            sync_mode_dropdown = gr.Dropdown(
                                choices=["Tự động (Theo phụ đề Whisper)", "Thủ công (Chia đều kịch bản)"],
                                value="Tự động (Theo phụ đề Whisper)",
                                label="⚡ Cơ Chế Cắt Cảnh:"
                            )
                            num_scenes_slider = gr.Slider(minimum=5, maximum=40, value=15, step=1, label="Số Cảnh (Khi chọn thủ công):")

                        with gr.Accordion("⚙️ CÀI ĐẶT NÂNG CAO (AI & API KEYS)", open=False):
                            with gr.Row():
                                gemini_key_box = gr.Textbox(label="Gemini API Keys (Hỗ trợ nhiều key cách bằng dấu phẩy để nhân bội Quota):", placeholder="AIzaSy..., AIzaSy... (Tự động xoay tua chống lỗi 429)", value=default_gemini_key, type="password")
                                gemini_model_dropdown = gr.Dropdown(
                                    choices=["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"],
                                    value="gemini-2.5-flash",
                                    label="Gemini Model:"
                                )
                            with gr.Row():
                                pexels_key_box = gr.Textbox(label="Pexels API Keys (Xoay tua nhiều key cách bằng dấu phẩy):", value=default_pexels_key)
                                allow_reuse_box = gr.Checkbox(label="Cho phép dùng lại hình ảnh đẹp", value=False)

                        with gr.Row():
                            voice_dropdown = gr.Dropdown(choices=PRESET_VOICES, value="Thiền Tâm Đức", label="🎙️ Giọng Đọc (VieNeu-TTS):")
                            topic_title_box = gr.Textbox(label="🏷️ Tiêu Đề Tùy Biến (Để trống sẽ tự lấy từ kịch bản):")

                        with gr.Row():
                            title_style_dropdown = gr.Dropdown(choices=TITLE_STYLES, value=TITLE_STYLES[0], label="✨ Phong Cách Tiêu Đề:", scale=3)
                            title_size_slider = gr.Slider(minimum=20, maximum=100, value=60, step=2, label="🔠 Cỡ chữ Tiêu đề (Mặc định 60):", scale=2)

                        with gr.Accordion("🎵 NHẠC NỀN (BGM) & HIỆU ỨNG ÂM THANH", open=False):
                            with gr.Row():
                                bgm_upload = gr.Audio(label="Tải file nhạc nền (mp3/wav):", type="filepath")
                                bgm_gdrive_box = gr.Textbox(label="Hoặc dán Link Google Drive BGM:")
                                bgm_vol_slider = gr.Slider(minimum=0.05, maximum=0.5, value=0.15, step=0.01, label="Âm lượng BGM (Mặc định 15%):")

                        with gr.Accordion("📝 CÀI ĐẶT PHỤ ĐỀ & SÓNG ÂM (SAFE ZONE FIX V19.7)", open=True):
                            with gr.Row():
                                add_sub_cb = gr.Checkbox(label="Bật phụ đề (Subtitles)", value=True)
                                sub_color_dropdown = gr.Dropdown(choices=SUB_COLORS, value=SUB_COLORS[0], label="Màu chữ phụ đề:")
                                waveform_dropdown = gr.Dropdown(choices=WAVEFORM_STYLES, value=WAVEFORM_STYLES[0], label="Hiệu ứng sóng âm:")
                                sub_size_slider = gr.Slider(minimum=14, maximum=40, value=18, step=1, label="🔤 Cỡ chữ Phụ đề (Mặc định 18):")

                        with gr.Accordion("🚀 CẤU HÌNH YOUTUBE & BÁO CÁO (KHI BẤM NÚT ĐĂNG YOUTUBE)", open=False):
                            with gr.Row():
                                yt_privacy_dropdown = gr.Dropdown(choices=["private", "unlisted", "public"], value="private", label="Chế độ riêng tư:")
                                editor_email_box = gr.Textbox(label="Email người làm:")
                                shared_drive_box = gr.Textbox(label="Thư mục báo cáo CSV (Google Drive / Local):", value="outputs")

                        with gr.Row():
                            generate_only_btn = gr.Button("🔥 BẮT ĐẦU SẢN XUẤT (CHỈ TẠO VIDEO)", variant="secondary", size="lg", scale=1)
                            generate_and_upload_btn = gr.Button("🚀 1-CLICK: TẠO VIDEO & TỰ ĐỘNG ĐĂNG YOUTUBE LUÔN", variant="primary", size="lg", scale=1)

                    with gr.Column(scale=5):
                        video_output = gr.Video(label="🎬 Video MP4 Thành Phẩm:")
                        with gr.Row():
                            audio_output = gr.Audio(label="🔊 File Âm Thanh Chính Thức:")
                            srt_output = gr.File(label="📄 File Phụ Đề Chuẩn SRT:")
                        gallery_output = gr.Gallery(label="🖼️ Thumbnail YouTube (CTR Booster) & Phân Cảnh:", columns=2, height="auto")
                        status_output = gr.Textbox(label="📊 Nhật Ký & Tiến Độ Xuất Bản:", lines=6)
                        with gr.Accordion("📋 TIÊU ĐỀ & MÔ TẢ ĐÃ TÍNH TIMESTAMPS YOUTUBE", open=False):
                            display_title = gr.Textbox(label="Tiêu đề chuẩn SEO:")
                            display_desc = gr.Textbox(label="Mô tả hoàn chỉnh (Đã chèn Chapters):", lines=8)

            # ==========================================================
            # TAB 2: SẢN XUẤT HÀNG LOẠT (BATCH PROCESSING)
            # ==========================================================
            with gr.TabItem("📦 TAB 2: SẢN XUẤT HÀNG LOẠT (BATCH PROCESSING)"):
                with gr.Row():
                    with gr.Column(scale=5):
                        batch_files_box = gr.File(label="📂 Chọn nhiều file kịch bản (.txt):", file_count="multiple", file_types=[".txt"])
                        batch_folder_box = gr.Textbox(label="Hoặc nhập đường dẫn thư mục kịch bản (Local / Drive):")

                        b_aspect_ratio = gr.Radio(
                            choices=[
                                "16:9 Ngang (YouTube Video Essay Chuẩn - 1920x1080)",
                                "9:16 Dọc (TikTok / YouTube Shorts / Facebook Reels - 1080x1920)"
                            ],
                            value="16:9 Ngang (YouTube Video Essay Chuẩn - 1920x1080)",
                            label="📱 Định Dạng Cho Cả Mẻ:"
                        )

                        with gr.Row():
                            b_voice_dropdown = gr.Dropdown(choices=PRESET_VOICES, value="Thiền Tâm Đức", label="Giọng Đọc Cho Cả Mẻ:", scale=2)
                            b_art_style = gr.Dropdown(choices=ART_STYLE_CHOICES, value=ART_STYLE_CHOICES[0], label="🖌️ Phong Cách Cho Cả Mẻ:", scale=3)
                            b_sub_size = gr.Slider(minimum=14, maximum=40, value=18, step=1, label="🔤 Cỡ chữ Phụ đề Batch:", scale=2)

                        with gr.Accordion("⚙️ CÀI ĐẶT API KEYS CHO MẺ BATCH (Tự động lấy từ Tab 1 nếu để trống)", open=False):
                            with gr.Row():
                                b_gemini_key_box = gr.Textbox(
                                    label="Gemini API Keys (Batch - Hỗ trợ xoay tua nhiều key):",
                                    value=default_gemini_key,
                                    placeholder="AIzaSy..., AIzaSy... (Để trống sẽ tự động lấy từ Tab 1)",
                                    type="password"
                                )
                                b_gemini_model_dropdown = gr.Dropdown(
                                    choices=["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"],
                                    value="gemini-2.5-flash",
                                    label="Gemini Model:"
                                )
                            with gr.Row():
                                b_pexels_key_box = gr.Textbox(
                                    label="Pexels API Keys (Batch):",
                                    value=default_pexels_key,
                                    placeholder="Để trống sẽ tự động lấy từ Tab 1..."
                                )

                        with gr.Accordion("🚀 CẤU HÌNH YOUTUBE CHO CẢ MẺ (1-CLICK BATCH UPLOAD)", open=True):
                            with gr.Row():
                                b_yt_privacy = gr.Dropdown(
                                    choices=["private", "unlisted", "public"],
                                    value="private",
                                    label="Chế độ riêng tư YouTube khi Upload Batch:",
                                    scale=1
                                )
                                b_editor_email = gr.Textbox(
                                    label="📧 Email Người Phụ Trách:",
                                    placeholder="ví dụ: admin@gmail.com",
                                    scale=1
                                )
                                b_shared_drive = gr.Textbox(
                                    label="📂 Thư mục báo cáo CSV (Local / Google Drive):",
                                    value="outputs",
                                    scale=1
                                )

                        with gr.Row():
                            batch_run_only_btn = gr.Button("📦 BẮT ĐẦU CHẠY MẺ BATCH (CHỈ TẠO VIDEO)", variant="secondary", size="lg", scale=1)
                            batch_run_and_upload_btn = gr.Button("🚀 1-CLICK BATCH: TẠO XONG 1 VIDEO LÀ UPLOAD YOUTUBE LUÔN", variant="primary", size="lg", scale=1)

                    with gr.Column(scale=5):
                        b_video_out = gr.Video(label="🎬 Video MP4 hoàn tất gần nhất:")
                        b_status_out = gr.Textbox(label="📊 Tiến độ toàn bộ mẻ & Kết quả Đăng YouTube:", lines=12)

            # ==========================================================
            # TAB 3: ĐĂNG & LÊN LỊCH PHÁT HÀNH YOUTUBE (OAUTH2 STUDIO)
            # ==========================================================
            with gr.TabItem("🚀 TAB 3: ĐĂNG & LÊN LỊCH PHÁT HÀNH YOUTUBE"):
                gr.Markdown("### 🎯 1. CHỌN NGUỒN VIDEO ĐĂNG LÊN YOUTUBE:")
                video_source_mode = gr.Radio(
                    choices=[
                        "🎬 Video vừa tạo ở Tab 1 (Mặc định)",
                        "📁 Chọn từ danh sách các video đã tạo (outputs/)",
                        "💻 Tải lên file video từ máy tính"
                    ],
                    value="🎬 Video vừa tạo ở Tab 1 (Mặc định)",
                    label="Nguồn video cần đăng:"
                )

                with gr.Row():
                    history_vids_dropdown = gr.Dropdown(
                        label="📁 Chọn video trong thư mục outputs/ (Chỉ hiển thị video hoàn thiện):",
                        choices=get_available_rendered_videos(),
                        value=get_available_rendered_videos()[0] if get_available_rendered_videos() else None,
                        scale=3
                    )
                    refresh_vids_btn = gr.Button("🔄 Làm mới danh sách outputs/", scale=1)

                custom_video_file = gr.File(label="💻 Hoặc tải file video MP4 bất kỳ từ máy tính của bạn:")

                gr.Markdown(
                    "### ⏰ 2. TÍNH NĂNG HẸN GIỜ LÊN LỊCH ĐĂNG (SCHEDULE PUBLISH):\n"
                    "*(Hệ thống hỗ trợ đặt giờ phát hành tự động theo định dạng `YYYY-MM-DD HH:MM` — Múi giờ Việt Nam GMT+7)*"
                )
                schedule_cb = gr.Checkbox(label="⏰ Bật Hẹn Giờ Lên Lịch Đăng Tự Động (Tự động công khai đúng giờ)", value=False)
                with gr.Row():
                    custom_sched_time_box = gr.Textbox(
                        label="Ngày giờ phát hành YouTube (Định dạng: YYYY-MM-DD HH:MM):",
                        placeholder=f"VD: {sample_time_vn}",
                        value="",
                        lines=1,
                        scale=3
                    )
                    btn_fill_sample = gr.Button(f"📋 Dán nhanh mốc 19:30 ngày mai", variant="secondary", scale=1)

                gr.Markdown("### 📝 3. THÔNG TIN VIDEO YOUTUBE (TỰ ĐỘNG ĐỒNG BỘ HOẶC TÙY BIẾN):")
                yt_title_box = gr.Textbox(label="Tiêu đề Video YouTube:", lines=1)
                yt_desc_box = gr.Textbox(label="Mô tả Video (SEO Description & Chapters):", lines=5)
                yt_tags_box = gr.Textbox(
                    label="Thẻ Tags YouTube (Mặc định chuẩn SEO):",
                    value="Audiobook, truyện trinh thám, kinh dị gothic, sách nói kinh dị, video essay",
                    lines=1
                )
                yt_privacy_tab3 = gr.Dropdown(
                    label="Chế độ đăng (Khi không hẹn giờ):",
                    choices=["private", "unlisted", "public"],
                    value="private"
                )

                gr.Markdown("### 🔑 4. XÁC THỰC TÀI KHOẢN YOUTUBE (OAUTH 2.0 CHUẨN https://localhost):")
                with gr.Row():
                    secrets_file_box = gr.File(label="Tải file client_secret.json lên đây (hoặc để sẵn ở thư mục gốc / configs):")
                    redirect_uri_box = gr.Textbox(
                        label="Redirect URI (Mặc định https://localhost):",
                        value="https://localhost"
                    )

                with gr.Row():
                    get_url_btn = gr.Button("🔗 BƯỚC 1: LẤY LINK ĐĂNG NHẬP GOOGLE", variant="secondary")
                oauth_url_display = gr.Textbox(label="Link & Hướng dẫn ủy quyền chi tiết:", interactive=False, lines=5)

                with gr.Row():
                    auth_code_box = gr.Textbox(
                        label="Dán TOÀN BỘ URL localhost vào đây (bắt đầu bằng https://localhost/?state=...):",
                        placeholder="https://localhost/?state=...&code=...",
                        scale=3
                    )
                    save_token_btn = gr.Button("💾 BƯỚC 2: XÁC THỰC & LƯU TOKEN", variant="primary", scale=2)
                token_status_box = gr.Textbox(label="Trạng thái Token:", interactive=False, lines=2)

                gr.Markdown("### 👥 5. QUẢN LÝ TIẾN ĐỘ & BÁO CÁO DÙNG CHUNG:")
                with gr.Row():
                    tab3_editor_email = gr.Textbox(label="📧 Email Người Phụ Trách:", placeholder="ví dụ: admin@gmail.com", scale=2)
                    tab3_shared_folder = gr.Textbox(label="📂 Thư mục báo cáo CSV (Local / Google Drive):", value="outputs", scale=2)

                upload_yt_btn = gr.Button("📤 ĐĂNG / LÊN LỊCH VIDEO LÊN YOUTUBE NGAY", variant="primary", size="lg")
                yt_status_box = gr.Textbox(label="Kết quả đăng / hẹn giờ YouTube:", interactive=False, lines=5)

        # ==========================================================
        # EVENT BINDINGS (KẾT NỐI SỰ KIỆN TƯƠNG TÁC)
        # ==========================================================
        # 1. TAB 1: SẢN XUẤT ĐƠN LẺ
        def handle_tab1(
            script, ratio, visual_mode, art_style, sync_mode, num_scenes,
            pexels_key, gemini_key, gemini_model, allow_reuse, voice,
            topic_title, title_size, title_style, bgm_up, bgm_gd,
            bgm_vol, add_sub, sub_color, waveform, sub_size,
            privacy, email, shared_folder, auto_up
        ):
            return process_full_pipeline(
                script_input=script,
                aspect_ratio=ratio,
                visual_mode=visual_mode,
                sync_mode_choice=sync_mode,
                num_scenes_slider=num_scenes,
                pexels_key_input=pexels_key,
                gemini_api_key_input=gemini_key,
                gemini_model_input=gemini_model,
                allow_reuse_input=allow_reuse,
                voice_selected=voice,
                topic_title_custom=topic_title,
                title_font_size=title_size,
                title_style=title_style,
                bgm_file=bgm_up,
                bgm_gdrive_url=bgm_gd,
                bgm_volume=bgm_vol,
                add_subtitles=add_sub,
                sub_color=sub_color,
                waveform_style=waveform,
                retention_cuts_enabled=True,
                sub_font_size=sub_size,
                art_style=art_style,
                auto_upload_yt=auto_up,
                yt_privacy=privacy,
                editor_email=email,
                shared_drive_folder=shared_folder
            )

        tab1_inputs_list = [
            script_box, aspect_ratio_radio, visual_mode_dropdown, art_style_dropdown, sync_mode_dropdown,
            num_scenes_slider, pexels_key_box, gemini_key_box, gemini_model_dropdown,
            allow_reuse_box, voice_dropdown, topic_title_box, title_size_slider,
            title_style_dropdown, bgm_upload, bgm_gdrive_box, bgm_vol_slider,
            add_sub_cb, sub_color_dropdown, waveform_dropdown, sub_size_slider,
            yt_privacy_dropdown, editor_email_box, shared_drive_box
        ]

        # Nút 1: Chỉ tạo video
        generate_only_btn.click(
            fn=lambda *args: handle_tab1(*args, False),
            inputs=tab1_inputs_list,
            outputs=[
                video_output, audio_output, srt_output, gallery_output,
                status_output, display_title, display_desc
            ]
        )

        # Nút 2: 1-Click tạo & tự đăng YouTube luôn
        generate_and_upload_btn.click(
            fn=lambda *args: handle_tab1(*args, True),
            inputs=tab1_inputs_list,
            outputs=[
                video_output, audio_output, srt_output, gallery_output,
                status_output, display_title, display_desc
            ]
        )

        # 2. TAB 2: SẢN XUẤT HÀNG LOẠT
        def handle_tab2(
            batch_files, batch_folder, ratio, voice, art_style, sub_size,
            privacy, email, shared_folder,
            b_gemini_key, b_gemini_model, b_pexels_key,
            tab1_gemini_key, tab1_gemini_model, tab1_pexels_key,
            title_size, title_style, bgm_up, bgm_gd, bgm_vol,
            add_sub, sub_color, waveform,
            auto_up
        ):
            # Tự động kế thừa API key từ Tab 1 nếu Tab 2 để trống
            effective_gemini_key = b_gemini_key.strip() if b_gemini_key and b_gemini_key.strip() else tab1_gemini_key.strip()
            effective_gemini_model = b_gemini_model if b_gemini_model else tab1_gemini_model
            effective_pexels_key = b_pexels_key.strip() if b_pexels_key and b_pexels_key.strip() else tab1_pexels_key.strip()

            return process_batch_pipeline(
                batch_files=batch_files,
                batch_folder_path=batch_folder,
                aspect_ratio=ratio,
                visual_mode="SDXL (AI Hình Ảnh Ẩn Dụ)",
                sync_mode_choice="Tự động (Theo phụ đề Whisper)",
                num_scenes_slider=15,
                pexels_key_input=effective_pexels_key,
                allow_reuse_input=False,
                voice_selected=voice,
                title_font_size=title_size,
                title_style=title_style,
                bgm_file=bgm_up,
                bgm_gdrive_url=bgm_gd,
                bgm_volume=bgm_vol,
                add_subtitles=add_sub,
                sub_color=sub_color,
                waveform_style=waveform,
                retention_cuts_enabled=True,
                tab1_gemini_key=effective_gemini_key,
                editor_email=email,
                shared_drive_folder=shared_folder,
                sub_font_size=sub_size,
                b_gemini_key=effective_gemini_key,
                b_gemini_model=effective_gemini_model,
                art_style=art_style,
                auto_upload_batch=auto_up,
                b_yt_privacy=privacy
            )

        tab2_inputs_list = [
            batch_files_box, batch_folder_box, b_aspect_ratio, b_voice_dropdown, b_art_style, b_sub_size,
            b_yt_privacy, b_editor_email, b_shared_drive,
            b_gemini_key_box, b_gemini_model_dropdown, b_pexels_key_box,
            gemini_key_box, gemini_model_dropdown, pexels_key_box,
            title_size_slider, title_style_dropdown, bgm_upload, bgm_gdrive_box, bgm_vol_slider,
            add_sub_cb, sub_color_dropdown, waveform_dropdown
        ]

        # Nút 1: Chạy mẻ chỉ tạo video
        batch_run_only_btn.click(
            fn=lambda *args: handle_tab2(*args, False),
            inputs=tab2_inputs_list,
            outputs=[
                b_video_out, b_status_out
            ]
        )

        # Nút 2: 1-Click BATCH: Tạo xong 1 video là upload YouTube luôn!
        batch_run_and_upload_btn.click(
            fn=lambda *args: handle_tab2(*args, True),
            inputs=tab2_inputs_list,
            outputs=[
                b_video_out, b_status_out
            ]
        )

        # 3. TAB 3: Các nút tiện ích
        btn_fill_sample.click(
            fn=get_sample_tomorrow_time,
            outputs=[custom_sched_time_box]
        )

        refresh_vids_btn.click(
            fn=lambda: gr.update(choices=get_available_rendered_videos(), value=get_available_rendered_videos()[0] if get_available_rendered_videos() else None),
            outputs=[history_vids_dropdown]
        )

        get_url_btn.click(
            fn=get_youtube_auth_url,
            inputs=[secrets_file_box, redirect_uri_box],
            outputs=[oauth_url_display, redirect_uri_box]
        )

        save_token_btn.click(
            fn=verify_oauth_code_and_save_token,
            inputs=[auth_code_box, redirect_uri_box],
            outputs=[token_status_box]
        )

        # 4. TAB 3: Logic xử lý tải lên YouTube
        def handle_tab3_manual_upload(
            source_mode: str,
            tab1_video: Any,
            history_video_name: str,
            uploaded_file: Any,
            title: str,
            description: str,
            tags: str,
            is_sched: bool,
            sched_time: str,
            privacy: str,
            email: str,
            shared_folder: str
        ) -> str:
            resolved_tab1 = resolve_file_path(tab1_video)
            resolved_custom = resolve_file_path(uploaded_file)
            resolved_hist = None

            if history_video_name and not str(history_video_name).startswith("("):
                cand = os.path.join("outputs", history_video_name)
                if os.path.exists(cand):
                    resolved_hist = cand

            target_path = None
            if "máy tính" in str(source_mode).lower():
                target_path = resolved_custom
            elif "outputs" in str(source_mode).lower():
                target_path = resolved_hist
            else:
                target_path = resolved_tab1 or resolved_hist or resolved_custom

            if not target_path or not os.path.exists(target_path):
                return f"❌ Lỗi: Không tìm thấy file video hợp lệ để tải lên! (Nguồn đang chọn: {source_mode})"

            return upload_to_youtube(
                video_file_path=target_path,
                title=title,
                description=description,
                tags=tags,
                is_schedule=is_sched,
                custom_schedule_time=sched_time,
                privacy_status=privacy,
                editor_email=email,
                shared_drive_folder=shared_folder,
                outputs_dir="outputs"
            )

        upload_yt_btn.click(
            fn=handle_tab3_manual_upload,
            inputs=[
                video_source_mode, video_output, history_vids_dropdown, custom_video_file,
                yt_title_box, yt_desc_box, yt_tags_box, schedule_cb, custom_sched_time_box,
                yt_privacy_tab3, tab3_editor_email, tab3_shared_folder
            ],
            outputs=[yt_status_box]
        )

    return demo
