# 🎙️ Audiobook Automation AI Studio (V19.7)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/PyTorch-2.0%2B-ee4c2c.svg" alt="PyTorch">
  <img src="https://img.shields.io/badge/Gradio-Web%20UI-orange.svg" alt="Gradio">
  <img src="https://img.shields.io/badge/FFmpeg-Cinematic%20Engine-green.svg" alt="FFmpeg">
  <img src="https://img.shields.io/badge/License-MIT-purple.svg" alt="License MIT">
</p>

> **Hệ thống tự động hóa toàn diện từ Kịch bản văn bản (Text) thành Video Essay & Audiobook điện ảnh chuẩn phát hành YouTube, TikTok, Facebook Reels.**  
> Tích hợp trí tuệ nhân tạo: **VieNeu-TTS 48kHz**, **SDXL-Turbo Photorealistic**, **Whisper Subtitles (Dynamic Script Alignment)**, **YouTube Auto-Upload & Chapters**, và **Động cơ tạo Thumbnail High-CTR Booster**.

---

## 🌟 Tính Năng Cốt Lõi (Key Features)

| Phân hệ | Tính năng nổi bật |
| :--- | :--- |
| 🎙️ **Giọng đọc (TTS)** | Tích hợp **VieNeu-TTS-v3-Turbo 48kHz**, giọng truyền cảm tự nhiên (Thiền Tâm Đức, Thanh Long, Bảo Ngọc...), tự động làm sạch thẻ biểu cảm `[thở dài]`, `[cười]`. |
| 📱 **Đa tỉ lệ (Multi-Ratio)** | **16:9 Ngang** (1920x1080) cho YouTube Video Essay chuẩn & **9:16 Dọc** (1080x1920) chuẩn gốc cho TikTok, YouTube Shorts, Reels. |
| 📝 **Phụ đề (Subtitles)** | **Dynamic Word Alignment (difflib)**: Khớp 100% kịch bản gốc vào mốc thời gian Whisper trong < 0.5s. Khống chế nghiêm ngặt tối đa 2 dòng sub, không phân mảnh cắt cảnh video. |
| 🛡️ **Safe Zone Subtitle (V19.7)** | Chuẩn hóa toạ độ hiển thị video dọc: Phụ đề nằm gọn ở 1/3 dưới màn hình, cách xa Tiêu đề **> 900 pixel**, tuyệt đối không bị đè chữ trên mọi thiết bị di động. |
| ⏱️ **YouTube Chapters** | Tự động quét các hồi/chương trong kịch bản, đối soát mốc thời gian thực tế từ giọng đọc, tạo danh sách Timestamps hợp lệ (`00:00 - ...`) và ghi đè vào mô tả video. |
| 🖼️ **Thumbnail CTR Booster** | Tự động bóc tách text gợi ý giật gân, trích xuất khung hình cao trào, chèn chữ vàng viền đen 3D độ tương phản cao ở Safe Zone trái (tránh bị nhãn thời lượng YouTube che). |
| 🚀 **YouTube Auto-Upload** | Upload video trực tiếp lên kênh YouTube, tự động đặt metadata, hẹn giờ công khai, tự động gán Thumbnail đẹp mắt và ghi nhận tiến độ vào CSV. |
| 📦 **Sản xuất hàng loạt (Batch)** | Nhận diện cả thư mục kịch bản `.txt`, tự động xếp hàng sản xuất hàng chục video liên tục không cần giám sát. |

---

## 📂 Cấu Trúc Mã Nguồn (Modular Architecture)

Dự án được cấu trúc theo dạng module tiêu chuẩn công nghiệp:

```text
audiobook-automation/
├── configs/
│   └── app_config.yaml         # Thông số mặc định (Font: 60/18, tỷ lệ, màu sắc, safe zone)
├── fonts/
│   └── BeVietnamPro-Bold.ttf   # Font chữ tiếng Việt chuẩn điện ảnh không lỗi dấu
├── src/
│   ├── tts/                    # 🎙️ VieNeu-TTS Engine & Bộ làm sạch kịch bản
│   ├── subtitles/              # 📝 Whisper Aligner, 2-line Formatter, YouTube Chapters
│   ├── ai_director/            # 🧠 Gemini AI Prompt Enhancer, Pexels Rotator, SDXL Engine
│   ├── video/                  # 🎬 BGM Mixer, Waveform Visualizer, Thumbnail, Compositor
│   ├── youtube/                # 🚀 OAuth2 Auth, Resumable Uploader, CSV Progress Logger
│   ├── pipeline/               # 🔄 Bộ điều phối quy trình (Orchestrator: Single & Batch)
│   └── ui/                     # 🖥️ Giao diện Gradio Web Studio (Tab 1 & Tab 2)
├── notebooks/
│   └── Colab_Launcher.ipynb    # Launcher 3 ô lệnh siêu gọn trên Google Colab
├── .env.example                # File mẫu cấu hình API Keys (An toàn cho Git)
├── .gitignore                  # Bảo vệ tuyệt đối API Keys, Token và Output
├── requirements.txt            # Danh sách thư viện Python chuẩn hóa
├── Dockerfile                  # Container hóa triển khai máy chủ độc lập
├── main.py                     # Điểm khởi chạy chính: Web UI & Chế độ dòng lệnh CLI
└── README.md                   # Tài liệu hướng dẫn sử dụng chi tiết
```

---

## 🚀 Hướng Dẫn Cài Đặt & Sử Dụng

### 1. Chạy Trên Google Colab (Nhanh Nhất & Miễn Phí GPU T4/L4/A100)

Bạn không cần cấu hình phức tạp trên máy tính, chỉ cần mở file `notebooks/Colab_Launcher.ipynb` trên Google Colab và chạy lần lượt 3 ô lệnh:

*   **Ô 1: Kết nối Drive & Tải mã nguồn**:
    ```bash
    !git clone https://github.com/<your-username>/audiobook-automation.git
    %cd /content/audiobook-automation
    ```
*   **Ô 2: Cài đặt thư viện**:
    ```bash
    !pip install -q -r requirements.txt
    ```
*   **Ô 3: Khởi chạy Web Studio**:
    ```bash
    !python main.py --share
    ```
    -> Gradio sẽ cung cấp một đường link công khai (dạng `https://xxxx.gradio.live`) để bạn sử dụng ngay trên trình duyệt.

---

### 2. Chạy Trên Máy Tính Cá Nhân (Local PC Windows có GPU NVIDIA)

#### Bước 1: Cài đặt công cụ nền tảng
*   Cài đặt **Python 3.10** hoặc **3.11** (tích chọn *Add Python to PATH* khi cài đặt).
*   Cài đặt **FFmpeg** và thêm vào biến môi trường hệ thống (`PATH`).
*   Cài đặt **Git**.

#### Bước 2: Tải dự án và tạo môi trường ảo
Mở Command Prompt (cmd) hoặc PowerShell:
```bash
# Clone repository
git clone https://github.com/<your-username>/audiobook-automation.git
cd audiobook-automation

# Tạo môi trường ảo cách ly
python -m venv venv
venv\Scripts\activate

# Cài đặt thư viện
pip install -r requirements.txt
```

#### Bước 3: Cấu hình khóa API
```bash
# Sao chép file mẫu
copy .env.example .env
```
Mở file `.env` bằng Notepad và điền các khóa API của bạn:
```env
GEMINI_API_KEY=AIzaSy...
PEXELS_API_KEYS=key1,key2
DEVICE=cuda
```

#### Bước 4: Khởi chạy
```bash
python main.py
```
Mở trình duyệt truy cập: `http://localhost:7860`.

---

### 3. Chạy Trên Máy Chủ VPS Linux / Cloud GPU (RunPod, Vast.ai, Ubuntu 22.04)

```bash
# 1. Cài đặt các gói hệ thống
sudo apt update && sudo apt install -y python3-pip python3-venv ffmpeg git

# 2. Clone repo & thiết lập môi trường
git clone https://github.com/<your-username>/audiobook-automation.git
cd audiobook-automation
python3 -m venv venv
source venv/bin/activate

# 3. Cài đặt thư viện
pip install --upgrade pip
pip install -r requirements.txt

# 4. Cấu hình .env
cp .env.example .env
nano .env

# 5. Khởi chạy server
python main.py --host 0.0.0.0 --port 7860
```

---

### 4. Chạy Tự Động Bằng Dòng Lệnh (Headless CLI / Tự Động Hóa 24/7)

Nếu bạn muốn hẹn giờ cronjob chạy đêm tự động render kịch bản không cần mở Web:
```bash
python main.py --cli --script ./sample_script.txt --aspect-ratio 16:9 --voice "Thiền Tâm Đức"
```

---

### 5. Triển Khai Bằng Docker

```bash
# Build Docker image
docker build -t audiobook-automation .

# Khởi chạy container với GPU NVIDIA
docker run --gpus all -p 7860:7860 --env-file .env audiobook-automation
```

---

## 🔒 Hướng Dẫn Bảo Mật Khi Đẩy Code Lên GitHub

Hệ thống đã được thiết lập sẵn file `.gitignore` phòng vệ nhiều lớp:
1. **Khóa API & File môi trường**: Mọi file `.env`, `.env.local` đều bị chặn tự động, không bao giờ vô tình bị đẩy lên GitHub.
2. **File xác thực YouTube**: File `client_secrets.json` và `youtube_token.json` được loại trừ 100%. Bạn chỉ lưu các file này trên máy cá nhân hoặc nạp qua Colab Secrets.
3. **Thành phẩm video**: Thư mục `outputs/`, `temp_work/` và tất cả các file video `.mp4`, audio `.wav` dung lượng nặng đều được tự động bỏ qua để giữ kho lưu trữ Git luôn nhẹ và sạch.

---

## 📜 Giấy Phép (License)
Dự án được phân phối dưới giấy phép **MIT License**. Bạn toàn quyền sử dụng, tùy biến và phát triển thương mại.
