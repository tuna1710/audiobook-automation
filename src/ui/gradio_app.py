import os
import gradio as gr
from ..pipeline import process_full_pipeline, process_batch_pipeline
from ..tts import PRESET_VOICES

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

def create_gradio_app(default_gemini_key: str = "", default_pexels_key: str = ""):
    """
    Xây dựng giao diện Web Gradio V19.7 đa nền tảng.
    """
    with gr.Blocks(title="Audiobook Automation AI Studio V19.7", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            "# 🎙️ AUDIOBOOK AUTOMATION STUDIO V19.7\n"
            "### 🎬 Sản Xuất Video Essay & Audiobook Tự Động: VieNeu-TTS 48kHz | SDXL Photorealism | Whisper | CTR Booster Thumbnail"
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
                                label="🎨 Chế Độ Thị Giác:"
                            )
                            sync_mode_dropdown = gr.Dropdown(
                                choices=["Tự động (Theo phụ đề Whisper)", "Thủ công (Chia đều kịch bản)"],
                                value="Tự động (Theo phụ đề Whisper)",
                                label="⚡ Cơ Chế Cắt Cảnh:"
                            )
                            num_scenes_slider = gr.Slider(minimum=5, maximum=40, value=15, step=1, label="Số Cảnh (Khi chọn thủ công):")

                        with gr.Accordion("⚙️ CÀI ĐẶT NÂNG CAO (AI & API KEYS)", open=False):
                            with gr.Row():
                                gemini_key_box = gr.Textbox(label="Gemini API Key:", value=default_gemini_key, type="password")
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

                        with gr.Accordion("🚀 TỰ ĐỘNG ĐĂNG YOUTUBE & BÁO CÁO NHÓM", open=False):
                            auto_upload_cb = gr.Checkbox(label="Tự động Upload lên YouTube sau khi render", value=False)
                            with gr.Row():
                                yt_privacy_dropdown = gr.Dropdown(choices=["private", "unlisted", "public"], value="private", label="Chế độ riêng tư:")
                                editor_email_box = gr.Textbox(label="Email người làm:")
                                shared_drive_box = gr.Textbox(label="Thư mục báo cáo CSV (Google Drive / Local):")

                        generate_btn = gr.Button("🔥 BẮT ĐẦU SẢN XUẤT VIDEO HOÀN THIỆN", variant="primary", size="lg")

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

                generate_btn.click(
                    fn=process_full_pipeline,
                    inputs=[
                        script_box, aspect_ratio_radio, visual_mode_dropdown, sync_mode_dropdown,
                        num_scenes_slider, pexels_key_box, gemini_key_box, gemini_model_dropdown,
                        allow_reuse_box, voice_dropdown, topic_title_box, title_size_slider,
                        title_style_dropdown, bgm_upload, bgm_gdrive_box, bgm_vol_slider,
                        add_sub_cb, sub_color_dropdown, waveform_dropdown, gr.State(True),
                        sub_size_slider, auto_upload_cb, yt_privacy_dropdown, editor_email_box,
                        shared_drive_box
                    ],
                    outputs=[
                        video_output, audio_output, srt_output, gallery_output,
                        status_output, display_title, display_desc
                    ]
                )

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

                        b_voice_dropdown = gr.Dropdown(choices=PRESET_VOICES, value="Thiền Tâm Đức", label="Giọng Đọc Cho Cả Mẻ:")
                        b_sub_size = gr.Slider(minimum=14, maximum=40, value=18, step=1, label="🔤 Cỡ chữ Phụ đề Batch (Mặc định 18):")

                        batch_btn = gr.Button("🚀 BẮT ĐẦU CHẠY CẢ MẺ HÀNG LOẠT", variant="primary", size="lg")

                    with gr.Column(scale=5):
                        b_video_out = gr.Video(label="🎬 Video MP4 hoàn tất gần nhất:")
                        b_status_out = gr.Textbox(label="📊 Tiến độ toàn bộ mẻ:", lines=8)

                batch_btn.click(
                    fn=process_batch_pipeline,
                    inputs=[
                        batch_files_box, batch_folder_box, b_aspect_ratio,
                        gr.State("SDXL (AI Hình Ảnh Ẩn Dụ)"), gr.State("Tự động (Theo phụ đề Whisper)"),
                        gr.State(15), pexels_key_box, gr.State(False), b_voice_dropdown,
                        title_size_slider, title_style_dropdown, bgm_upload, bgm_gdrive_box,
                        bgm_vol_slider, add_sub_cb, sub_color_dropdown, waveform_dropdown,
                        gr.State(True), gemini_key_box, editor_email_box, shared_drive_box,
                        b_sub_size, gemini_key_box, gemini_model_dropdown, auto_upload_cb,
                        yt_privacy_dropdown
                    ],
                    outputs=[
                        b_video_out, audio_output, srt_output, gallery_output,
                        b_status_out, display_title, display_desc
                    ]
                )

    return demo
