import os
import sys
import argparse
from dotenv import load_dotenv

# Tải cấu hình môi trường từ .env nếu có
load_dotenv()

# Thêm thư mục hiện tại vào sys.path để import các module nội bộ
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.ui import create_gradio_app
from src.pipeline import process_full_pipeline, process_batch_pipeline


def parse_args():
    parser = argparse.ArgumentParser(description="Audiobook Automation AI Studio V20.0 (Cinema Gothic V20)")
    parser.add_argument("--share", action="store_true", help="Tạo link công khai Gradio Share (Bắt buộc cho Google Colab)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Địa chỉ IP host (Mặc định: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=7860, help="Cổng chạy Web UI (Mặc định: 7860)")
    parser.add_argument("--cli", action="store_true", help="Chạy dạng dòng lệnh không cần giao diện đồ họa")
    parser.add_argument("--script", type=str, default="", help="Đường dẫn file kịch bản khi chạy --cli")
    parser.add_argument("--aspect-ratio", type=str, default="16:9", choices=["16:9", "9:16"], help="Định dạng video (16:9 hoặc 9:16)")
    parser.add_argument("--voice", type=str, default="Thiền Tâm Đức", help="Tên giọng đọc VieNeu-TTS")
    return parser.parse_args()


def print_hardware_banner():
    """
    Kiểm tra và hiển thị trạng thái phần cứng (Mặc định GPU T4 trên Google Colab).
    """
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"🚀 PHẦN CỨNG: GPU {device_name} ({vram_gb:.1f} GB VRAM) - FP16 Kích Hoạt Tối Ưu")
        else:
            print("⚠️ CẢNH BÁO PHẦN CỨNG: Đang chạy trên CPU! Khuyên dùng GPU Tesla T4 trên Colab để đạt tốc độ tối đa.")
    except Exception:
        pass


def main():
    args = parse_args()

    # Kiểm tra biến môi trường & Colab Secrets (Chìa khóa 🔑)
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        try:
            from google.colab import userdata
            val = userdata.get("GEMINI_API_KEY")
            if val:
                gemini_key = str(val).strip()
                os.environ["GEMINI_API_KEY"] = gemini_key
                print("🔑 Đã tự động nạp GEMINI_API_KEY từ Colab Secrets (Chìa khóa 🔑)!")
        except Exception:
            pass

    pexels_keys = os.environ.get("PEXELS_API_KEYS", "").strip()

    # Chế độ dòng lệnh thuần túy (CLI Headless)
    if args.cli:
        print("🚀 Khởi động chế độ dòng lệnh (Headless CLI)...")
        print_hardware_banner()
        if not args.script or not os.path.exists(args.script):
            print(f"❌ Lỗi: Vui lòng cung cấp đường dẫn file kịch bản hợp lệ qua --script")
            sys.exit(1)

        with open(args.script, "r", encoding="utf-8") as f:
            script_content = f.read()

        ratio_label = "9:16 Dọc (TikTok / YouTube Shorts / Facebook Reels - 1080x1920)" if args.aspect_ratio == "9:16" else "16:9 Ngang (YouTube Video Essay Chuẩn - 1920x1080)"

        print(f"📄 Đang xử lý: {args.script} ({args.aspect_ratio})")
        res = process_full_pipeline(
            script_input=script_content,
            aspect_ratio=ratio_label,
            voice_selected=args.voice,
            gemini_api_key_input=gemini_key,
            pexels_key_input=pexels_keys
        )
        print(res[4])  # In status message
        sys.exit(0)

    # Chế độ Web UI (Gradio)
    print("=" * 60)
    print("🎙️ AUDIOBOOK AUTOMATION STUDIO V20.0 (Cinema Gothic V20)")
    print(f"🌐 Server: http://localhost:{args.port}")
    if args.share:
        print("🔗 Chế độ chia sẻ trực tuyến (--share): BẬT (Thích hợp cho Google Colab)")
    print_hardware_banner()
    print("=" * 60)

    app = create_gradio_app(default_gemini_key=gemini_key, default_pexels_key=pexels_keys)
    app.queue(default_concurrency_limit=2).launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        debug=False
    )


if __name__ == "__main__":
    main()
