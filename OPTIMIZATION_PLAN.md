# Kế Hoạch Tối Ưu Hóa Dự Án `audiobook-automation`

> **Trạng thái:** Đã khảo sát mã nguồn, chưa chỉnh sửa code.  
> **Mục tiêu:** Tăng tốc độ pipeline (TTS, Subtitle, FFmpeg Render) và sửa triệt để lỗi kéo dãn khung hình dọc `9:16` bằng bố cục ảnh vuông `1:1` chuẩn tự nhiên.

---

## Phần 1: Tối Ưu Tốc Độ & Hiệu Năng (TTS, Subtitle, AI Director & FFmpeg)

Qua khảo sát các file `src/pipeline/orchestrator.py`, `src/tts/engine.py`, `src/subtitles/whisper_aligner.py`, `src/ai_director/sdxl_engine.py`, và `src/video/compositor.py`, các điểm nghẽn (bottleneck) chính và phương án tối ưu gồm:

### 1.1. Xử lý song song Pipeline (TTS / BGM / Whisper / AI Director)
- **Hiện trạng (`src/pipeline/orchestrator.py`):**
  - Toàn bộ pipeline chạy tuần tự từng bước: `TTS` $\rightarrow$ `Hòa âm BGM` $\rightarrow$ `Whisper` $\rightarrow$ `Gemini AI Director` $\rightarrow$ `Sinh ảnh SDXL` $\rightarrow$ `Render FFmpeg`.
- **Phương án tối ưu:**
  1. **Song song hóa sau bước TTS:** Ngay khi có `voice_audio_path`, chạy song song `handle_background_music` (CPU/FFmpeg) và `extract_whisper_segments_and_srt` (GPU/Whisper) bằng `ThreadPoolExecutor`.
  2. **Tối ưu TTS theo đoạn (Chunked TTS + Cache):**
     - Chia nhỏ văn bản dài theo đoạn/câu hợp lý thay vì dồn 1 lần, bọc trong `torch.inference_mode()` để giảm VRAM và tránh nghẽn bộ nhớ.
     - Hỗ trợ lưu cache file audio tạm theo hash nội dung + giọng đọc để khi chạy lại/sửa tiêu đề không phải tổng hợp lại từ đầu.
  3. **Tăng tốc Whisper Subtitle:**
     - Nâng cấp tùy chọn sang `faster-whisper` (CTranslate2, `int8`/`float16`) giúp nhận diện mốc thời gian nhanh hơn **4x–6x** so với `openai-whisper` gốc và nhẹ VRAM hơn, giữ nguyên thuật toán `align_script_with_whisper_segments` để khớp 100% chính tả kịch bản.

### 1.2. Tối ưu Render Video FFmpeg (`src/video/compositor.py`)
- **Hiện trạng:**
  - `zoompan` chạy trên CPU cho từng clip ở độ phân giải đầy đủ (`1080x1920` hoặc `1920x1080`), sau đó encode từng clip $\rightarrow$ concat $\rightarrow$ **re-encode lại toàn bộ video** ở bước cuối để chèn Title, Subtitle, Waveform.
  - Trên Colab (thường chỉ có 2 vCPU), chạy 4 worker `zoompan` cùng lúc dễ gây quá tải CPU (CPU thrashing).
- **Phương án tối ưu:**
  1. **Giảm tải `zoompan`:**
     - Với định dạng `9:16` dùng ảnh vuông `1080x1080`, `zoompan` chỉ phải tính toán trên `1080x1080` (giảm ~44% số điểm ảnh so với `1080x1920`), giúp tăng tốc render clip gần gấp đôi.
     - Tự động điều chỉnh `num_workers` theo số nhân CPU thực tế (`os.cpu_count()`) để tránh nghẽn RAM/CPU.
  2. **Tối ưu tham số Encode 2 bước:**
     - Bước 1 (render clip lẻ): Dùng preset nhanh nhất (`ultrafast` cho CPU hoặc `p1`/`fast` cho `h264_nvenc`) vì bước cuối vẫn encode lại khi burn subtitle/title.
     - Bước 3 (render hoàn thiện): Tối ưu cờ `h264_nvenc` (thêm `-rc vbr`, `-spatial-aq 1`, `-movflags +faststart`) hoặc `libx264` (`-preset veryfast -threads 0 -movflags +faststart`).
  3. **Tùy chọn "Tắt hiệu ứng Zoompan (Static Fade)"** (tùy chọn cấu hình): Nếu người dùng cần render siêu tốc cho audiobook dài 30–60 phút, có thể dùng filter `scale` + `pad` + `fade` thuần (không `zoompan`), tốc độ render sẽ tăng **5x–10x**.

---

## Phần 2: Sửa Định Dạng Dọc `9:16` — Giữ Nguyên Khung Hình Vuông `1:1` (Không Kéo Dãn Người)

### 2.1. Nguyên nhân gây "kéo dài người, không thật" hiện tại
1. **Ở khâu sinh ảnh (`src/ai_director/sdxl_engine.py`, dòng 103):**
   - Hiện tại đang ép SDXL/SD-Turbo sinh ảnh ở tỷ lệ `640x1152` (dọc cực đoan) rồi resize lên `1080x1920`. Các model SD-Turbo/SDXL được huấn luyện tối ưu nhất ở tỷ lệ vuông `1:1` (`512x512` hoặc `768x768`/`1024x1024`). Khi ép sinh `640x1152`, AI rất dễ vẽ người bị kéo dài, dị dạng hoặc chồng đầu.
2. **Ở khâu ghép video (`src/video/compositor.py`, dòng 68):**
   - Lệnh filter hiện tại dùng `scale={vid_w}:{vid_h}` (tức `scale=1080:1920`) **không có `force_original_aspect_ratio`**. Nếu ảnh đầu vào là hình vuông `1:1` hoặc `16:9`, FFmpeg sẽ kéo giãn chiều dọc lên `1080x1920`, làm nhân vật bị biến dạng.

### 2.2. Giải pháp thiết kế khung hình `9:16` mới (Chuẩn Vuông Trong Khung Dọc)
Thay vì kéo dãn ảnh ra full `1080x1920`, ta giữ nguyên khung hình vuông **`1080x1080` (tỷ lệ 1:1)** đặt gọn trên nền canvas dọc **`1080x1920`**:

1. **Khâu sinh ảnh (`sdxl_engine.py`):**
   - Khi chọn `9:16`, sinh ảnh ở tỷ lệ vuông **`1:1`** (ví dụ `768x768` hoặc `1024x1024`, sau đó resize chuẩn `1080x1080` bằng `LANCZOS`).
   - Kết quả: Tỷ lệ cơ thể nhân vật tự nhiên 100%, chi tiết sắc nét hơn và sinh ảnh cũng nhanh hơn.

2. **Khâu dựng video (`compositor.py`):**
   - Video xuất ra vẫn giữ chuẩn **`1080x1920` (9:16)** để đăng TikTok / YouTube Shorts / Reels bình thường.
   - Ảnh/Video phân cảnh được scale giữ nguyên tỷ lệ gốc (`force_original_aspect_ratio=decrease`) để vừa khít khung vuông `1080x1080` ở giữa (hoặc hơi lệch trên một chút, tùy chỉnh được).
   - **Phần nền trên & dưới (420px trên + 420px dưới) — Đã chốt: Nền đen thuần (`#000000`):**
     - Sử dụng nền đen thuần (`pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black`) — cực nhẹ, không tốn thêm chi phí xử lý làm mờ của FFmpeg, render nhanh tối đa và giúp chữ Tiêu đề + Phụ đề nổi bật, dễ đọc nhất.
   - **Tối ưu Safe Zone cho chữ:**
     - **Vùng trên (0 – 420px):** Đặt **Tiêu đề truyện** (`y ≈ 140–200`), hoàn toàn tách biệt, không che mặt nhân vật trong ảnh.
     - **Vùng giữa (420 – 1500px):** Khung hình vuông `1080x1080` hiển thị trọn vẹn cảnh truyện, không bị chữ đè lên.
     - **Vùng dưới (1500 – 1920px):** Đặt **Phụ đề (Subtitle)** và **Sóng âm (Waveform)** rất dễ đọc, không bị dính vào giao diện nút bấm của TikTok/YouTube Shorts.

3. **Cấu hình linh hoạt (`configs/app_config.yaml`):**
   - Thêm tùy chọn `vertical_layout_mode: "square_in_9_16"` (Vuông trong khung 9:16 - Mặc định) hoặc `"full_crop"` (Cắt vừa khung, không kéo dãn) để người dùng chủ động chọn mà không làm hỏng khả năng tương thích ngược.

---

## Thứ Tự Triển Khai Đề Xuất (Khi Bắt Đầu Code)
- [x] **Bước 1:** Cập nhật `configs/app_config.yaml` thêm cấu hình `vertical_layout_mode: "square_in_9_16"`, `vertical_bg_color: "black"`, `enable_zoompan`, và mục `performance` (`parallel_post_tts`, `whisper_backend`, `tts_chunk_cache`). *(Đã xong)*
- [x] **Bước 2:** Sửa `src/ai_director/sdxl_engine.py` để sinh ảnh `1:1` (`768x768` -> `1080x1080`) khi dùng chế độ vuông trong `9:16`, kèm `torch.inference_mode()`. *(Đã xong)*
- [x] **Bước 3:** Sửa `src/video/compositor.py` để ghép khung vuông `1080x1080` vào canvas `1080x1920` nền đen thuần (`setsar=1`, không kéo dãn), `zoompan` chỉ chạy trên `1080x1080`, hỗ trợ `enable_zoompan: false` và tối ưu `num_workers` + `-movflags +faststart`. *(Đã xong & đã test render FFmpeg 1080x1920 thành công)*
- [x] **Bước 4:** Tối ưu `src/pipeline/orchestrator.py`, `src/tts/engine.py` và `src/subtitles/whisper_aligner.py` (chạy song song BGM + Whisper, hỗ trợ `faster-whisper`, cache TTS theo hash + `torch.inference_mode()`). *(Đã xong)*
- [x] **Bước 5:** Kiểm tra thực tế bằng mẫu ngắn (2 cảnh, 3s, 9:16 + phụ đề + tiêu đề): biên dịch toàn bộ `src/` & `main.py` thành công, render `1080x1920` (`SAR 1:1 DAR 9:16`) trong `2.10s`, xác nhận điểm ảnh vùng trên/dưới là đen thuần `(0, 0, 0)` và ảnh vuông giữa khung nguyên vẹn. *(Đã xong)*
