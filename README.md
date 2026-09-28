# 🎙️ Audiobook Automation AI Studio (V19.7)

<p align="center">
  <a href="https://colab.research.google.com/github/tuna1710/audiobook-automation/blob/main/notebooks/Colab_Launcher.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"></a>
  <a href="https://github.com/"><img src="https://img.shields.io/badge/Awesome-Audiobook-green?logo=github" alt="Awesome Audiobook"></a>
  <a href="https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo"><img src="https://img.shields.io/badge/%F0%9F%A4%97%20VieNeu--TTS-v3--Turbo-red" alt="VieNeu-TTS v3 Turbo"></a>
  <a href="https://pytorch.org/"><img src="https://img.shields.io/badge/PyTorch-2.0%2B-ee4c2c?logo=pytorch&logoColor=white" alt="PyTorch"></a>
  <a href="https://gradio.app/"><img src="https://img.shields.io/badge/Gradio-Web%20Studio-orange?logo=gradio&logoColor=white" alt="Gradio"></a>
  <a href="https://ffmpeg.org/"><img src="https://img.shields.io/badge/FFmpeg-Cinematic%20Engine-007808?logo=ffmpeg&logoColor=white" alt="FFmpeg"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License MIT"></a>
  <a href="#donation"><img src="https://img.shields.io/badge/Donate-VietinBank%20QR-blue?logo=cashapp&logoColor=white" alt="Donate VietinBank"></a>
</p>

<p align="center">
  <b>Hệ thống tự động hóa toàn diện từ Kịch bản (Text) thành Video Essay & Audiobook điện ảnh chuẩn phát hành YouTube, TikTok, Facebook Reels.</b><br>
  <i>Tích hợp: <b>VieNeu-TTS 48kHz</b>, <b>SDXL-Turbo Photorealistic</b>, <b>Whisper Subtitles (Dynamic Script Alignment)</b>, <b>YouTube Auto-Upload & Chapters</b>, và <b>Động cơ tạo Thumbnail High-CTR Booster</b>.</i>
</p>

---

> [!IMPORTANT]
> **🚀 Phiên Bản V19.7 Chính Thức: Module Hóa Đa Nền Tảng & Safe Zone Video Dọc**
> - **Chuẩn hóa Safe Zone 9:16**: Khắc phục triệt để lỗi toạ độ ảo `libass`, đưa phụ đề về đúng vùng 1/3 dưới màn hình (`Y: 1150 - 1630`), cách xa Tiêu đề **> 900 pixel**, tuyệt đối không bị đè chữ trên TikTok, Shorts và Reels.
> - **Cỡ chữ điện ảnh mặc định**: Tiêu đề **60**, Phụ đề **18** (chữ Be Vietnam Pro Bold sắc nét).
> - **Tự động hóa YouTube Chapters**: Tính toán chuẩn xác mốc thời gian thực tế từ âm thanh Whisper và ghi đè vào mô tả video.
> - **Thumbnail High-CTR Booster**: Tự động render ảnh bìa 1280x720 với chữ vàng viền đen 3D giật gân, an toàn tránh nhãn thời lượng YouTube.

> [!TIP]
> **Khởi chạy siêu tốc:** Dự án có thể chạy trực tiếp trên **Google Colab miễn phí** chỉ với 3 ô lệnh qua `notebooks/Colab_Launcher.ipynb`, hoặc chạy ổn định 24/7 trên **Máy tính cá nhân (GPU NVIDIA)**, **VPS đám mây (RunPod, Vast.ai)** và **Docker**.

---

### 🎬 Tính Năng Trực Quan (Feature Showcase)

<table>
  <tr>
    <td align="center" width="33%">
      <b>🎞️ 16:9 YouTube Video Essay</b><br><br>
      <i>Khung hình 1920x1080 chuẩn phim tài liệu, chuyển động máy quay Slow Push/Pan, phụ đề Be Vietnam Pro 2 dòng tinh tế.</i>
    </td>
    <td align="center" width="33%">
      <b>📱 9:16 Shorts / TikTok Safe Zone</b><br><br>
      <i>Khung hình 1080x1920 dọc gốc, Tiêu đề đỉnh trên, Phụ đề 1/3 dưới, giải phóng >900px không gian điện ảnh trung tâm.</i>
    </td>
    <td align="center" width="34%">
      <b>🖼️ High-CTR Booster Thumbnail</b><br><br>
      <i>Ảnh bìa 1280x720 HD tự động trích từ video cao trào, Typography Vàng viền đen khối 3D thu hút lượt click vượt trội.</i>
    </td>
  </tr>
</table>

---

## 📌 Mục Lục Điều Hướng (Table of Contents)

1. [🌟 Tính Năng Nổi Bật](#tinh-nang)
2. [📊 Hiệu Năng & Đo Lường Phần Cứng (Benchmarks)](#benchmarks)
3. [📂 Cấu Trúc Mã Nguồn (Modular Architecture)](#cau-truc)
4. [🚀 Hướng Dẫn Cài Đặt (Quick Start)](#cai-dat)
   - [Cách 1: Google Colab (Launcher 3 ô lệnh)](#colab)
   - [Cách 2: Windows PC (NVIDIA GPU)](#windows)
   - [Cách 3: Linux / Cloud GPU](#linux)
   - [Cách 4: Docker Container](#docker)
5. [🎛️ Hướng Dẫn Sử Dụng Studio](#huong-dan)
   - [Tab 1: Sản Xuất Video Đơn Lẻ](#tab1)
   - [Tab 2: Sản Xuất Hàng Loạt (Batch)](#tab2)
   - [Tab 3: Đăng & Lên Lịch Phát Hành YouTube (OAuth2 Studio)](#tab3)
   - [Chế Độ Dòng Lệnh (CLI)](#cli)
6. [🔑 Hướng Dẫn Cấu Hình YouTube Data API & OAuth 2.0](#youtube-setup)
   - [Bước 1: Bật YouTube Data API v3](#step1-yt)
   - [Bước 2: Cấu hình OAuth Consent Screen & Test Users](#step2-yt)
   - [Bước 3: Tạo OAuth 2.0 Client ID (Desktop App)](#step3-yt)
   - [Bước 4: Quy Trình Xác Thực 2 Bước Trực Quan Trên WebUI](#step4-yt)
   - [Những Lưu Ý Quan Trọng Về Quota & Kỹ Thuật](#notes-yt)
7. [🔒 Tiêu Chuẩn Bảo Mật (Zero-Leak Security)](#bao-mat)
8. [🗺️ Lộ Trình Phát Triển (Roadmap)](#roadmap)
9. [☕ Ủng Hộ Phát Triển (Support & Donation)](#donation)
10. [📑 Bản Quyền & Tri Ân (Credits & License)](#license)

---

## 🌟 1. Tính Năng Nổi Bật <a name="tinh-nang"></a>

| Phân hệ | Công nghệ tích hợp | Mô tả trải nghiệm |
| :--- | :--- | :--- |
| 🎙️ **Giọng đọc (TTS)** | **VieNeu-TTS-v3-Turbo 48kHz** | Giọng đọc truyền cảm tự nhiên (Thiền Tâm Đức, Thanh Long, Bảo Ngọc...), tự động làm sạch thẻ biểu cảm `[thở dài]`, `[cười]`. |
| 📱 **Đa tỉ lệ (Multi-Ratio)** | **Native 16:9 & 9:16** | Không dùng dải mờ hai bên, khung hình dọc được render thực tế 1080x1920 cho TikTok/Shorts. |
| 📝 **Phụ đề (Subtitles)** | **Dynamic Script Aligner** | Sử dụng thuật toán `difflib.SequenceMatcher` đối soát khớp 100% kịch bản gốc vào nhịp đọc Whisper trong < 0.5s. Khống chế tối đa 2 dòng sub. |
| 🛡️ **Safe Zone V19.7** | **libass Coordinate Fix** | Toạ độ phụ đề video dọc được chuẩn hóa với `sub_margin_v = 38/52`, tạo khoảng cách an toàn >900px, 100% không đè Tiêu đề. |
| ⏱️ **YouTube Chapters** | **Auto-Timestamps Engine** | Tự động bóc tách các Hồi/Chương, tính toán mốc phát thực tế và cập nhật vào mô tả YouTube (`00:00 - Hồi 1...`). |
| 🖼️ **Thumbnail CTR Booster** | **Automated 3D Typography** | Tự động phát hiện từ khóa giật gân, xuất ảnh bìa 1280x720, chèn chữ Vàng kim viền đen khối 3D ở lề trái an toàn. |
| 🚀 **YouTube Auto-Upload** | **Google YouTube Data API** | Tự động tải video, gán metadata, hẹn giờ công khai, gắn thumbnail và ghi log tiến độ nhóm vào Google Sheets / CSV. |
| 📦 **Sản xuất hàng loạt** | **Batch Pipeline Queue** | Thả một thư mục chứa hàng chục file kịch bản `.txt`, hệ thống tự động sản xuất liên tục xuyên đêm. |

---

## 📊 2. Hiệu Năng & Đo Lường Phần Cứng <a name="benchmarks"></a>

| Phần cứng | Tốc độ Giọng đọc (TTS RTF) | Tốc độ Render Phim (10 phút 1080p) | Mức tiêu thụ VRAM |
| :--- | :---: | :---: | :---: |
| ☁️ **Google Colab (Tesla T4 15GB)** | **~0.03** (~33× real-time) | **~2 phút 30 giây** | ~6.8 GB |
| ⚡ **PC / VPS (RTX 3060 12GB)** | **~0.02** (~50× real-time) | **~1 phút 45 giây** | ~6.5 GB |
| 🚀 **PC / Cloud (RTX 4090 24GB)** | **~0.008** (~120× real-time) | **~45 giây** | ~7.2 GB |
| 💻 **CPU i5 12th Gen (Không GPU)** | **~0.50** (2× real-time) | **~8 phút 10 giây** | ~3.5 GB RAM |

---

## 📂 3. Cấu Trúc Mã Nguồn (Modular Architecture) <a name="cau-truc"></a>

```text
audiobook-automation/
├── configs/
│   └── app_config.yaml         # Cấu hình tĩnh: cỡ chữ (60/18), màu sắc, safe zone, preset
├── fonts/
│   └── BeVietnamPro-Bold.ttf   # Font chữ điện ảnh tiếng Việt chính thức
├── src/
│   ├── tts/                    # 🎙️ VieNeu-TTS Engine & Bộ làm sạch kịch bản
│   │   ├── engine.py           # Khởi tạo model VieNeu-TTS Turbo, quản lý cache GPU
│   │   └── text_cleaner.py     # Bóc tách kịch bản, làm sạch biểu cảm [thở dài], [cười]
│   ├── subtitles/              # 📝 Whisper Aligner, Formatter khống chế 2 dòng sub, Chapters
│   │   ├── whisper_aligner.py  # Thuật toán Hybrid Alignment (difflib) chống lệch sub
│   │   ├── formatter.py        # Khống chế subtitle tối đa 2 dòng, ngắt câu thông minh
│   │   └── chapters.py         # Tự động tính toán & ghi đè YouTube Timestamps
│   ├── ai_director/            # 🧠 Gemini AI Prompt Enhancer, Pexels Rotator, SDXL Engine
│   │   ├── gemini_client.py    # Kết nối Gemini Flash/Pro tối ưu câu lệnh thị giác
│   │   ├── pexels_rotator.py   # Cụm xoay tua đa khóa Pexels API tải video stock
│   │   └── sdxl_engine.py      # Sinh ảnh ẩn dụ AI bằng SDXL / SD-Turbo 16:9 & 9:16
│   ├── video/                  # 🎬 Động cơ Dựng phim (FFmpeg Video Engine)
│   │   ├── audio_mixer.py      # Hòa âm nhạc nền BGM, cân bằng âm lượng tự động
│   │   ├── waveform.py         # Bộ sinh sóng âm Visualizer (Equalizer, Gradient, Line)
│   │   ├── thumbnail.py        # Tạo ảnh bìa YouTube CTR Booster (1280x720 chữ 3D Vàng kim)
│   │   └── compositor.py       # Render video hoàn chỉnh, chuẩn hóa Safe Zone 9:16 & 16:9
│   ├── youtube/                # 🚀 Xuất bản & Tự động hóa YouTube
│   │   ├── oauth_auth.py       # Quản lý OAuth2 Token an toàn
│   │   ├── uploader.py         # Upload video, hẹn giờ công khai, gán thumbnail tự động
│   │   └── gdrive_logger.py    # Ghi nhận tiến độ công việc nhóm vào file CSV
│   ├── pipeline/               # 🔄 Bộ điều phối quy trình (Orchestrator: Single & Batch)
│   │   └── orchestrator.py
│   └── ui/                     # 🖥️ Giao diện Gradio Web Studio (Tab 1 & Tab 2)
│       └── gradio_app.py
├── notebooks/
│   └── Colab_Launcher.ipynb    # File chạy 3 cell siêu ngắn trên Google Colab
├── .env.example                # File mẫu cấu hình API Keys
├── .gitignore                  # Bảo vệ tuyệt đối khóa API và dữ liệu cá nhân
├── requirements.txt            # Danh sách thư viện Python
├── Dockerfile                  # Container hóa triển khai máy chủ
├── main.py                     # Entry point: Web UI & CLI
└── README.md                   # Tài liệu hướng dẫn sử dụng chi tiết
```

---

## 🚀 4. Hướng Dẫn Cài Đặt (Quick Start) <a name="cai-dat"></a>

### Cách 1: Chạy Trên Google Colab (Khuyên Dùng) <a name="colab"></a>

> [!TIP]
> Google Colab cung cấp GPU T4 miễn phí, xử lý video 30 phút trong vài phút mà không tốn tài nguyên máy tính cá nhân.

1. Tải file [`notebooks/Colab_Launcher.ipynb`](notebooks/Colab_Launcher.ipynb) về máy và mở trên [Google Colab](https://colab.research.google.com/).
2. Bấm chạy lần lượt **3 ô lệnh**:
   * **Ô 1: Tải mã nguồn**:
     ```bash
     !git clone https://github.com/tuna1710/audiobook-automation.git
     %cd /content/audiobook-automation
     ```
   * **Ô 2: Cài đặt thư viện**:
     ```bash
     !pip install -q -r requirements.txt
     ```
   * **Ô 3: Khởi chạy Studio**:
     ```bash
     !python main.py --share
     ```
3. Nhấp vào đường link **`https://xxxx.gradio.live`** hiển thị ở cuối để bắt đầu làm video!

---

### Cách 2: Chạy Trên Máy Tính Windows (NVIDIA GPU) <a name="windows"></a>

Mở **PowerShell** hoặc **Command Prompt**:

```powershell
# 1. Clone repository
git clone https://github.com/tuna1710/audiobook-automation.git
cd audiobook-automation

# 2. Tạo môi trường ảo
python -m venv venv
venv\Scripts\activate

# 3. Cài đặt thư viện
pip install -r requirements.txt

# 4. Thiết lập file cấu hình bí mật .env
copy .env.example .env
# Mở file .env và điền GEMINI_API_KEY, PEXELS_API_KEYS của bạn

# 5. Khởi chạy Web Studio
python main.py
```
Truy cập tại: `http://localhost:7860`.

---

### Cách 3: Chạy Trên Máy Chủ Linux / Cloud GPU (RunPod, Vast.ai, Ubuntu) <a name="linux"></a>

```bash
# 1. Cài đặt các gói hệ thống
sudo apt update && sudo apt install -y python3-pip python3-venv ffmpeg git

# 2. Clone repo & thiết lập môi trường
git clone https://github.com/tuna1710/audiobook-automation.git
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

### Cách 4: Triển Khai Bằng Docker <a name="docker"></a>

```bash
# Build Docker image
docker build -t audiobook-automation .

# Khởi chạy container với GPU NVIDIA
docker run --gpus all -p 7860:7860 --env-file .env audiobook-automation
```

---

## 🎛️ 5. Hướng Dẫn Sử Dụng Studio <a name="huong-dan"></a>

### Tab 1: Sản Xuất Video Đơn Lẻ <a name="tab1"></a>
1. **Dán kịch bản**: Dán toàn bộ nội dung kịch bản vào ô văn bản lớn (bao gồm cả `[TIÊU ĐỀ GỢI Ý]`, `[Ý TƯỞNG THUMBNAIL]`, `[MÔ TẢ VIDEO]`).
2. **Chọn định dạng**:
   - `16:9 Ngang`: Cho video dài phát hành YouTube.
   - `9:16 Dọc`: Cho TikTok, Reels, YouTube Shorts.
3. **Chọn giọng đọc**: Chọn giọng VieNeu-TTS (Ví dụ: *Thiền Tâm Đức* cho truyện trinh thám/tâm lý, *Thanh Long* cho bản tin phóng sự).
4. **Nhạc nền BGM**: Tải file nhạc nền hoặc dán link Google Drive (hệ thống tự cân bằng âm lượng 15%).
5. **Bấm "BẮT ĐẦU SẢN XUẤT"**: Hệ thống sẽ tự tạo âm thanh, phụ đề khớp 100%, render video, tạo ảnh bìa Thumbnail CTR Booster và xuất file thành phẩm vào thư mục `outputs/`.

### Tab 2: Sản Xuất Hàng Loạt (Batch Processing) <a name="tab2"></a>
1. Chọn nhiều file kịch bản `.txt` hoặc nhập đường dẫn thư mục kịch bản.
2. Chọn tỷ lệ khung hình chung và giọng đọc mong muốn.
3. Bấm **"BẮT ĐẦU CHẠY CẢ MẺ HÀNG LOẠT"**: Hệ thống sẽ tự động xử lý tuần tự từng tập phim và lưu toàn bộ kết quả vào `outputs/`.

### Tab 3: Đăng & Lên Lịch Phát Hành YouTube (OAuth2 Studio) <a name="tab3"></a>
Tự động hóa hoàn toàn việc đưa sản phẩm lên YouTube với đầy đủ tính năng:
1. **Lựa chọn nguồn video**:
   - Chọn ngay *Video vừa tạo ở Tab 1*.
   - Hoặc chọn từ danh sách dropdown các file video đã render trong thư mục `outputs/`.
   - Hoặc tải trực tiếp file `.mp4` từ máy tính lên.
2. **Hẹn giờ công khai tự động (Schedule Publish)**:
   - Nhập thời gian phát hành theo định dạng `YYYY-MM-DD HH:MM` (múi giờ GMT+7 Việt Nam).
   - Có nút bấm nhanh **"📋 Dán nhanh mốc 19:30 ngày mai"** (khung giờ vàng người xem).
   - Video sẽ được YouTube giữ ở chế độ `private` và tự động công khai đúng thời điểm.
3. **SEO & Metadata**:
   - Tự động đồng bộ Tiêu đề, Thẻ Tags và Mô tả hoàn chỉnh (đã kèm mốc thời gian YouTube Chapters).
4. **Xác thực an toàn 2 bước**:
   - Bấm **BƯỚC 1: Lấy link đăng nhập Google** > Cho phép cấp quyền > Copy toàn bộ URL `https://localhost/?state=...&code=...` dán vào **BƯỚC 2** > Bấm **Xác thực & Lưu Token**.
   - Token được lưu vĩnh viễn và tự động làm mới (auto-refresh) khi hết hạn.
5. **Đăng video**: Bấm **"📤 ĐĂNG / LÊN LỊCH VIDEO LÊN YOUTUBE NGAY"**, hệ thống sẽ chia nhỏ video 5MB và truyền tải an toàn với cơ chế tự động thử lại khi gián đoạn mạng.

### Chế Độ Dòng Lệnh Không Cần Giao Diện (Headless CLI) <a name="cli"></a>
Thích hợp để lập lịch cronjob tự động chạy xuyên đêm:
```bash
python main.py --cli --script ./sample_script.txt --aspect-ratio 16:9 --voice "Thiền Tâm Đức"
```

---

## 🔑 6. Hướng Dẫn Cấu Hình YouTube Data API & OAuth 2.0 <a name="youtube-setup"></a>

Để sử dụng tính năng Đăng & Lên lịch tự động lên YouTube, bạn chỉ cần thực hiện 4 bước thiết lập một lần duy nhất trên Google Cloud:

### Bước 1: Tạo Project & Bật YouTube Data API v3 <a name="step1-yt"></a>
1. Truy cập [Google Cloud Console](https://console.cloud.google.com/).
2. Tạo một Project mới (ví dụ: `Audiobook-AI-Publisher`).
3. Vào menu **APIs & Services** > **Library**.
4. Tìm kiếm từ khóa **YouTube Data API v3** và bấm nút **ENABLE (Bật)**.

### Bước 2: Cấu hình Màn hình đồng ý OAuth (OAuth Consent Screen) <a name="step2-yt"></a>
1. Vào **APIs & Services** > **OAuth consent screen**.
2. Chọn loại người dùng: **External** (Bên ngoài) > Bấm **Create**.
3. Điền tên ứng dụng (ví dụ: `Audiobook Studio`) và email hỗ trợ của bạn.
4. Ở bước **Scopes**, thêm các phạm vi:
   - `https://www.googleapis.com/auth/youtube.upload`
   - `https://www.googleapis.com/auth/youtube`
5. Ở bước **Test Users (Người dùng thử nghiệm)**: **RẤT QUAN TRỌNG!**
   - Thêm địa chỉ Gmail mà bạn sẽ dùng để đăng nhập và đăng video. *(Nếu không thêm, Google sẽ chặn đăng nhập với lỗi 403 Access Denied)*.
   - *(Tùy chọn: Bạn có thể bấm **Publish App** để đưa ứng dụng sang trạng thái Production giúp Refresh Token không bị hết hạn sau 7 ngày).*

### Bước 3: Tạo OAuth Client ID & Tải file `client_secret.json` <a name="step3-yt"></a>
1. Vào **APIs & Services** > **Credentials** > Bấm **+ CREATE CREDENTIALS** > Chọn **OAuth client ID**.
2. Tại mục Application type: Chọn **Desktop app** (Ứng dụng cho máy tính).
3. Đặt tên và bấm **Create**.
4. Bấm **DOWNLOAD JSON** để tải file bí mật về máy.
5. Đổi tên file thành `client_secret.json` và đặt vào thư mục gốc của dự án `audiobook-automation/` (hoặc upload trực tiếp trên TAB 3 của WebUI).

### Bước 4: Quy Trình Xác Thực 2 Bước Trực Quan Trên WebUI <a name="step4-yt"></a>
1. Khởi chạy WebUI và chuyển sang **TAB 3: ĐĂNG & LÊN LỊCH PHÁT HÀNH YOUTUBE**.
2. Bấm **🔗 BƯỚC 1: LẤY LINK ĐĂNG NHẬP GOOGLE**.
3. Mở đường link hiển thị trên trình duyệt > Chọn tài khoản Google sở hữu kênh YouTube > Bấm **Tiếp tục** > Bấm **Cho phép**.
4. Trình duyệt chuyển sang trang `https://localhost/?state=...&code=4/0A...` (báo không thể kết nối - điều này là bình thường).
5. **Copy TOÀN BỘ đường link** trên thanh địa chỉ, dán vào ô **BƯỚC 2** và bấm **💾 BƯỚC 2: XÁC THỰC & LƯU TOKEN**.
6. Hệ thống báo `🎉 XÁC THỰC THÀNH CÔNG!` và tự động tạo file `token.json`. Từ nay bạn có thể đăng video mọi lúc mà không cần xác thực lại.

### ⚠️ Những Lưu Ý Quan Trọng Về Quota & Kỹ Thuật <a name="notes-yt"></a>
* 📊 **Hạn Mức Quota Hàng Ngày**: Google cấp mặc định 10.000 units/ngày cho mỗi project. Mỗi video upload tốn 1.600 units, thumbnail tốn 50 units (tối đa ~6 video/ngày). Quota tự động reset vào **14:00 giờ Việt Nam** hàng ngày.
* 🛡️ **Tuyệt Đối Không Xóa `MediaFileUpload`**: Lớp này chịu trách nhiệm cắt nhỏ video thành từng khối 5MB để truyền tải an toàn. Hệ thống đã được tích hợp thuật toán **Exponential Backoff Retry** tự động thử lại 5 lần nếu kết nối mạng Colab hoặc server bị chập chờn.
* 📱 **Xác Minh Kênh Bằng Số Điện Thoại**: Kênh YouTube cần bật tính năng tiêu chuẩn (Standard/Intermediate features) trong YouTube Studio để được phép upload custom thumbnail và video dài hơn 15 phút.

---


## 🔒 7. Tiêu Chuẩn Bảo Mật (Zero-Leak Security) <a name="bao-mat"></a>

Dự án tuân thủ nghiêm ngặt tiêu chuẩn an ninh mã nguồn:
* 🛡️ **Tự động chặn bằng `.gitignore`**: Toàn bộ file `.env`, `client_secrets.json`, `youtube_token.json` bị chặn tự động, không bao giờ vô tình bị đẩy lên GitHub.
* 📦 **Loại trừ thành phẩm video nặng**: Thư mục `outputs/`, `temp_work/` và các định dạng media `.mp4`, `.wav`, `.srt` không bị commit, giúp repo luôn siêu nhẹ (< 1MB) và tải cực nhanh.
* 🔑 **Bảo vệ khóa API**: Chỉ sử dụng `.env.example` chứa chuỗi mẫu an toàn.

---

## 🗺️ 8. Lộ Trình Phát Triển (Roadmap) <a name="roadmap"></a>

- [x] Tích hợp VieNeu-TTS-v3-Turbo 48kHz (Eager loop mode).
- [x] Khống chế phụ đề tối đa 2 dòng điện ảnh.
- [x] Tự động tính toán & ghi đè YouTube Chapters.
- [x] Động cơ tạo Thumbnail High-CTR Booster 1280x720.
- [x] Chuẩn hóa Safe Zone phụ đề video dọc 9:16 (V19.7).
- [x] Tách cấu trúc dự án dạng module chuẩn Git/GitHub.
- [ ] Tích hợp clone giọng nói từ file mẫu (Instant Voice Cloning) qua Web UI.
- [ ] Bổ sung hiệu ứng chuyển cảnh điện ảnh nâng cao (Cinematic Transitions / Motion Blur).
- [ ] Hỗ trợ đồng bộ tự động phụ đề đa ngôn ngữ (Việt - Anh song ngữ).

---

## ☕ 9. Ủng Hộ Phát Triển (Support & Donation) <a name="donation"></a>

> [!NOTE]
> Dự án **Audiobook Automation AI Studio** được phát triển và duy trì hoàn toàn phi lợi nhuận vì cộng đồng sáng tạo nội dung.  
> Nếu công cụ này giúp ích cho công việc sản xuất nội dung của bạn, giúp tiết kiệm thời gian dựng phim mỗi ngày hoặc giúp kênh của bạn phát triển, bạn có thể **mời tác giả một ly cà phê ☕** hoặc đóng góp một phần chi phí duy trì máy chủ GPU để cùng nhau hoàn thiện dự án ngày càng xịn xò hơn!

<div align=center>

| Chuyển Khoản Nhanh VietQR (Việt Nam) | Thông Tin Tài Khoản Ngân Hàng |
| :---: | :--- |
| <img src="assets/vietqr_donation.png" width="240" alt="VietQR Donation"> | 🏦 **Ngân hàng**: **VietinBank** (TMCP Công thương Việt Nam)<br><br>💳 **Số tài khoản**: <code>109810171095</code><br><br>👤 **Chủ tài khoản**: **NGUYỄN TUẤN ANH**<br><br>💬 **Nội dung gợi ý**: <code>Ung ho Audiobook AI</code> |

</div>

---

## 📑 10. Bản Quyền & Tri Ân (Credits & License) <a name="license"></a>

Dự án này kế thừa và sử dụng các công nghệ mã nguồn mở tuyệt vời:
* [VieNeu-TTS](https://github.com/pnnbao97/VieNeu-TTS) bởi **Phạm Nguyễn Ngọc Bảo** (`pnnbao97`).
* [OpenAI Whisper](https://github.com/openai/whisper) cho nhận diện âm thanh và trích xuất mốc thời gian.
* [Stability AI SDXL-Turbo](https://huggingface.co/stabilityai/sdxl-turbo) cho hình ảnh ẩn dụ nghệ thuật.
* [FFmpeg](https://ffmpeg.org/) cho động cơ kết xuất video điện ảnh đa luồng.
* [Gradio](https://gradio.app/) cho giao diện Web Studio tương tác trực quan.

Phát hành theo giấy phép **[MIT License](LICENSE)**. Bạn được tự do sử dụng, chỉnh sửa và ứng dụng cho mục đích cá nhân lẫn thương mại.
