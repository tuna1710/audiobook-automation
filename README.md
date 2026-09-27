# 🎙️ Audiobook Automation AI Studio (V19.7)

> **Hệ thống tự động hóa sản xuất Video Essay & Audiobook điện ảnh chuyên sâu**  
> Tích hợp: **VieNeu-TTS 48kHz**, **SDXL-Turbo Photorealistic**, **Whisper Subtitles (Dynamic Script Alignment)**, **YouTube Auto-Upload & Chapters**, **High-CTR Booster Thumbnail**.

---

## 🌟 Tính Năng Nổi Bật

1. **🎙️ VieNeu-TTS 48kHz**: Giọng đọc truyền cảm tự nhiên, làm sạch thẻ biểu cảm tự động, hỗ trợ 10+ preset giọng chuẩn.
2. **📱 Native Full Frame Multi-Ratio**:
   - **16:9 Ngang** (1920x1080) cho YouTube Video Essay chuẩn.
   - **9:16 Dọc** (1080x1920) cho TikTok, YouTube Shorts, Facebook Reels.
3. **🛡️ Safe Zone Subtitle Fix (V19.7)**: Tự động căn chỉnh toạ độ phụ đề cách xa Tiêu đề > 900px, khống chế tối đa 2 dòng sub, tuyệt đối không bị đè chữ.
4. **⏱️ Auto YouTube Chapters**: Tự động bóc tách hồi/chương và khớp mốc thời gian thực tế từ âm thanh, ghi đè chuẩn xác vào mô tả video.
5. **🖼️ CTR Booster Thumbnail Generator**: Tự động tạo ảnh bìa HD 1280x720, chèn chữ vàng viền đen 3D giật gân, đưa lên đầu gallery và gán trực tiếp vào video YouTube qua API.
6. **📦 Batch Processing**: Xử lý hàng chục tập phim cùng lúc từ thư mục kịch bản.

---

## 📂 Cấu Trúc Mã Nguồn (Modular Architecture)

```text
audiobook-automation/
├── configs/
│   └── app_config.yaml         # Cấu hình tĩnh (font size, màu sắc, safe zone, preset)
├── fonts/
│   └── BeVietnamPro-Bold.ttf   # Font chữ tiếng Việt chuẩn điện ảnh
├── src/
│   ├── tts/                    # 🎙️ VieNeu-TTS Engine & Bộ làm sạch kịch bản
│   ├── subtitles/              # 📝 Whisper Aligner (difflib), 2-line Sub Formatter, Chapters
│   ├── ai_director/            # 🧠 Gemini AI Prompt Enhancer, Pexels Rotator, SDXL Engine
│   ├── video/                  # 🎬 BGM Mixer, Waveform Visualizer, Thumbnail, FFmpeg Compositor
│   ├── youtube/                # 🚀 OAuth2 Auth, Resumable Uploader, Google Sheets Logger
│   ├── pipeline/               # 🔄 Bộ điều phối quy trình (Orchestrator: Single & Batch)
│   └── ui/                     # 🖥️ Giao diện Gradio Web Studio (Tab 1 & Tab 2)
├── notebooks/
│   └── Colab_Launcher.ipynb    # File chạy 3 cell siêu gọn trên Google Colab
├── .env.example                # File mẫu cấu hình API Keys
├── requirements.txt            # Danh sách thư viện Python
├── Dockerfile                  # Container hóa triển khai máy chủ
├── main.py                     # Entry point: Web UI & CLI
└── README.md                   # Hướng dẫn chi tiết
```

---

## 🚀 Hướng Dẫn Cài Đặt & Sử Dụng

### 1. Chạy Trên Google Colab
Chỉ cần mở file `notebooks/Colab_Launcher.ipynb` trên Google Colab, sau đó bấm chạy lần lượt 3 ô lệnh:
* Ô 1: Tải mã nguồn từ GitHub.
* Ô 2: Cài đặt thư viện `pip install -r requirements.txt`.
* Ô 3: Khởi chạy Web UI `python main.py --share`.

---

### 2. Chạy Trên Máy Tính Cá Nhân (Local PC có GPU NVIDIA) hoặc VPS (Ubuntu)
```bash
# 1. Clone repository
git clone https://github.com/your-username/audiobook-automation.git
cd audiobook-automation

# 2. Tạo môi trường ảo
python3 -m venv venv
source venv/bin/activate  # Trên Windows: venv\Scripts\activate

# 3. Cài đặt thư viện
pip install -r requirements.txt

# 4. Cấu hình file .env
cp .env.example .env
# Mở file .env và điền GEMINI_API_KEY, PEXELS_API_KEYS

# 5. Khởi chạy Web UI
python main.py
```
Truy cập giao diện tại: `http://localhost:7860`.

---

### 3. Chạy Không Cần Giao Diện (Headless CLI / Tự Động Hóa)
```bash
python main.py --cli --script ./sample_script.txt --aspect-ratio 16:9 --voice "Thiền Tâm Đức"
```

---

### 4. Chạy Bằng Docker
```bash
# Build Docker image
docker build -t audiobook-automation .

# Khởi chạy container với GPU NVIDIA
docker run --gpus all -p 7860:7860 --env-file .env audiobook-automation
```

---

## 📄 License
Phát hành theo giấy phép MIT.
