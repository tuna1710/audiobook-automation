# Kế Hoạch Cập Nhật Dự Án `audiobook-automation`

> **Nguyên tắc thực hiện:** Chia thành từng mục nhỏ độc lập để chỉnh sửa và kiểm tra nhanh, tránh timeout.

---

## Phần A: Cập Nhật Gemini Models (Chỉ Dùng Free Tier)

> **Lưu ý:** Không sử dụng các model chỉ có Paid Tier (`gemini-4-neon`, `gemini-4-carbon`, `gemini-4-argon`). Loại bỏ các model đã deprecated (`gemini-3.7-flash`, `gemini-3.5-flash`, `gemini-2.5-flash`, `gemini-3-flash-preview`).

### [x] Mục A1: Cập nhật `src/ai_director/gemini_client.py`
- **Vị trí:** Hàm `clean_gemini_model_name()` (dòng 74–103), `call_gemini_all_in_one_director()` (dòng 306, 321, 386–389), và các alias cuối file (dòng 481, 487, 497).
- **Chi tiết sửa:**
  1. Đổi `default_model` sang `"gemini-4-hydrogen"`.
  2. Bổ sung nhận diện `4-hydrogen` / `hydrogen` $\rightarrow$ `"gemini-4-hydrogen"` trong `clean_gemini_model_name()`.
  3. Ánh xạ an toàn các model cũ nếu người dùng nhập tay:
     - `3.7` $\rightarrow$ `"gemini-3.8-flash"`
     - `3.5-flash` (không có `lite`) $\rightarrow$ `"gemini-3.6-flash"`
     - `2.5-flash` $\rightarrow$ `"gemini-3.5-flash-lite"`
  4. Cập nhật danh sách fallback `target_models` (chỉ gồm các model có Free Tier):
     ```python
     ["gemini-4-hydrogen", "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.1-flash-lite"]
     ```

### [x] Mục A2: Cập nhật danh sách model trên UI `src/ui/gradio_app.py`
- **Vị trí:** `GEMINI_MODELS` (dòng 61–67) và nhãn dropdown (dòng 311).
- **Chi tiết sửa:**
  - Cập nhật `GEMINI_MODELS` chỉ gồm các model Free Tier Active:
    1. `"🚀 gemini-4-hydrogen (Mới nhất - Khuyên dùng, Free Tier)"`
    2. `"⚡ gemini-3.5-flash-lite (Siêu nhanh & Tiết kiệm Quota Free Tier)"`
    3. `"🌟 gemini-3.8-flash (Ổn định dòng 3.x - Chất lượng đạo diễn cao)"`
    4. `"⚖️ gemini-3.6-flash (Cân bằng tốc độ & Độ chi tiết)"`
    5. `"🛡️ gemini-3.1-flash-lite (Dự phòng dòng Lite)"`

### [x] Mục A3: Cập nhật cấu hình `configs/app_config.yaml`
- **Vị trí:** `app.engine` (dòng 4) và `ai_director` (dòng 18–27).
- **Chi tiết sửa:**
  - Đổi `default_model: "gemini-4-hydrogen"`.
  - Cập nhật `supported_models` khớp với danh sách Free Tier ở Mục A1.

### [x] Mục A4: Đồng bộ `default_model` ở các module phụ & `README.md`
- **Chi tiết sửa:**
  - `src/pipeline/orchestrator.py` (dòng 42, 188): đổi default thành `"gemini-4-hydrogen"`.
  - `src/subtitles/chapters.py` (dòng 10): đổi default thành `"gemini-4-hydrogen"`.
  - `src/subtitles/whisper_aligner.py` (dòng 222): đổi default thành `"gemini-4-hydrogen"`.
  - `src/video/thumbnail.py` (dòng 76): đổi default thành `"gemini-4-hydrogen"`.
  - `README.md` (dòng 22, 33): cập nhật mô tả model mới.

---

## Phần B: Thêm Chủ Đề Bán Sách & Cảnh Sách Thực Tế (Nằm Trên Bàn Cafe, Bàn Trà...)

> **Kiến trúc thiết kế (Book-in-Scene Mockup Engine):**
> Thay vì dán ảnh bìa 2D phẳng lên góc video hoặc dùng AI vẽ lại làm méo chữ tiếng Việt trên bìa, hệ thống sẽ:
> 1. Dùng **SDXL-Turbo / Pexels** tạo các bối cảnh bàn thật có chiều sâu (bàn gỗ quán cafe cạnh tách latte, bàn trà ấm áp, bàn đọc sách bên cửa sổ nắng, kệ sách...).
> 2. Dùng **Pillow + NumPy** biến đổi ảnh bìa gốc thành **cuốn sách 3D** (thêm độ dày gáy/trang giấy, biến đổi phối cảnh `PERSPECTIVE` nằm nghiêng tự nhiên trên mặt bàn, đổ bóng mềm `GaussianBlur` và cân bằng ánh sáng ấm).
> 3. Đưa các ảnh **"Sách nằm trong bối cảnh"** này trực tiếp vào chuỗi phân cảnh video (`scene_assets`) kết hợp hiệu ứng chuyển động camera Ken Burns mượt mà.

### [x] Mục B1: Thêm Hồ Sơ Kênh Bán Sách trong `src/pipeline/channel_profiles.py`
- **Vị trí:** Dictionary `CHANNEL_PROFILES_PRESET`.
- **Chi tiết sửa:**
  - Thêm preset mới: `"📚 Review Sách & Bán Sách (BookTok / Affiliate)"`.
  - Cấu hình `genre_role`, `visual_concept`, `style_suffix`, `voice` (`"Mai Anh"`), `tags`, `desc_template` (có sẵn chỗ gắn link đặt mua sách / Affiliate / CTA), và `fallback_keywords` chuyên về không gian đọc sách, bàn cafe, bàn trà.

### [x] Mục B2: Tạo module `src/video/book_mockup.py` (Động cơ đặt sách vào bối cảnh thực tế)
- **File mới:** `src/video/book_mockup.py` (chỉ dùng `Pillow` & `numpy` có sẵn, không tốn thêm VRAM GPU).
- **Chức năng chính:**
  - `create_3d_book_layer(cover_path)`: Tạo độ dày cạnh sách/trang giấy + hiệu ứng ánh sáng nhẹ lên bìa.
  - `compose_book_on_scene(cover_path, bg_image_path, preset_layout)`: Biến đổi phối cảnh (`PERSPECTIVE`) cho cuốn sách nằm nghiêng tự nhiên trên mặt bàn (hỗ trợ nhiều góc đặt khác nhau: nằm ngang góc phải, nằm chéo giữa bàn, dựng nhẹ cạnh tách trà...), tạo bóng đổ mềm (`drop shadow`) và hòa trộn ánh sáng với ảnh nền.
  - Danh sách prompt nền bàn chuyên dụng (`BOOK_SCENE_BACKGROUNDS`):
    1. Bàn gỗ quán cafe ấm áp với tách cà phê latte bên cạnh, ánh nắng sáng dịu.
    2. Bàn trà gỗ tối giản với ấm trà gốm, ánh sáng chiều thư giãn.
    3. Bàn đọc sách cạnh cửa sổ nắng, chậu cây nhỏ, bokeh ấm áp.
    4. Bàn làm việc gỗ sồi cổ điển với đèn bàn vàng ấm.

### [x] Mục B3: Thêm tùy chọn Ảnh Bìa & Bối Cảnh Sách trên UI `src/ui/gradio_app.py`
- **Vị trí:** Tab 1 (`TẠO VIDEO ESSAY`).
- **Chi tiết sửa:**
  - Thêm `book_cover_input = gr.Image(type="filepath", label="📕 Ảnh Bìa Cuốn Sách (Tùy chọn - Dùng cho Video Bán Sách)")`.
  - Thêm `book_cover_mode = gr.Dropdown(...)` với các chế độ:
    - `"☕ Xen kẽ cảnh Sách trên bàn Cafe/Trà + Cảnh minh họa nội dung"` (Khuyên dùng: Intro & các cảnh chuyển ý là sách nằm trên bàn cafe/trà, giữa là cảnh minh họa nội dung sách).
    - `"📖 100% Cảnh Sách trên nhiều bàn Cafe / Bàn Trà / Bàn Đọc Sách"` (Toàn bộ video là các góc quay cuốn sách thật ở nhiều không gian khác nhau).
    - `"📌 Chỉ dùng cho Intro/Outro & Thumbnail"`
  - Truyền `book_cover_input` và `book_cover_mode` vào luồng xử lý Tab 1 (giữ mặc định rỗng cho Tab Batch).

### [x] Mục B5: Nối luồng dữ liệu trong `src/pipeline/orchestrator.py`
- **Vị trí:** Hàm điều phối tạo `scene_assets` trong `orchestrator.py`.
- **Chi tiết sửa:**
  - Khi người dùng có tải lên `book_cover_path`:
    - Sinh/lấy 3–4 ảnh nền bàn cafe, bàn trà, bàn đọc sách (qua SDXL hoặc Pexels tùy `visual_mode`).
    - Gọi `book_mockup.py` để tạo 3–4 ảnh **"Cuốn sách nằm trên bàn"** độ phân giải chuẩn (`1920x1080` hoặc `1080x1920`).
    - Chèn các ảnh này vào `scene_assets` theo `book_cover_mode` đã chọn trước khi gọi `render_ultimate_video()`.

### [x] Mục B6: Nâng cấp Thumbnail Bán Sách trong `src/video/thumbnail.py`
- **Vị trí:** Hàm `generate_ctr_booster_thumbnail()`.
- **Chi tiết sửa:**
  - Thêm tham số tùy chọn `book_cover_path: str = ""` (hoặc dùng trực tiếp 1 ảnh Book-in-Scene đã dựng ở Mục B4).
  - Nếu có `book_cover_path`, đặt cuốn sách nổi bật ở phần bên phải/nền ấm áp và chừa vùng Safe Zone bên trái cho chữ tiêu đề CTR lớn.

---

## Phần C: Thêm Chỉnh Tốc Độ Đọc (TTS Speed Control)

> **Nguyên lý đồng bộ:** Áp dụng chỉnh tốc độ (`FFmpeg atempo`, giữ nguyên cao độ giọng nói) ngay tại bước xuất file `voice_{session_id}.wav` **trước** khi chạy Whisper và hòa âm BGM, đảm bảo phụ đề, cắt cảnh và nhạc nền khớp 100%.

### [x] Mục C1: Hỗ trợ `speed` trong `src/tts/engine.py`
- **Vị trí:** `TTSEngine.synthesize()` (dòng 35–48) và `preview_voice_sample()` (dòng 57–72).
- **Chi tiết sửa:**
  - Thêm tham số `speed: float = 1.0` (giới hạn an toàn `0.75` – `1.50`).
  - Nếu `abs(speed - 1.0) >= 0.02`: chạy FFmpeg filter `atempo={speed:.2f}` (giữ nguyên sample rate & cao độ giọng đọc) ghi đè lại file WAV đầu ra.
  - Cập nhật `preview_voice_sample(voice_selected, speed=1.0)` để nút **"🎧 Nghe thử giọng này"** phản ánh đúng tốc độ đã chọn.

### [x] Mục C2: Thêm thanh trượt tốc độ đọc trên UI `src/ui/gradio_app.py`
- **Vị trí:** Tab 1 (cạnh `voice_dropdown` và `btn_preview_voice`, dòng 344–357) và Tab Batch.
- **Chi tiết sửa:**
  - Thêm `voice_speed_slider = gr.Slider(minimum=0.75, maximum=1.50, value=1.0, step=0.05, label="⏱️ Tốc độ đọc (1.0x = Chuẩn)")`.
  - Truyền `voice_speed_slider` vào `btn_preview_voice.click(...)`, Tab 1 render, và Tab Batch render.

### [x] Mục C3: Nối tham số `voice_speed` trong `src/pipeline/orchestrator.py` & `main.py`
- **Vị trí:** `orchestrator.py` (dòng 249–252 và chữ ký hàm Tab 1 / Batch) và `main.py` (tùy chọn `--speed`).
- **Chi tiết sửa:**
  - Thêm `voice_speed: float = 1.0` vào pipeline và truyền vào `tts_engine.synthesize(..., speed=voice_speed)`.

---

## Phần D: Kiểm Tra Sau Khi Sửa

### [x] Mục D1: Kiểm tra cú pháp & import toàn bộ module
- Chạy `python3 -m py_compile` cho các file đã sửa.
- Kiểm tra `clean_gemini_model_name()` với các chuỗi đầu vào cũ và mới.
- Kiểm tra `CHANNEL_PROFILES_PRESET` load đúng profile bán sách.
- Kiểm tra `book_mockup.py` ghép ảnh bìa giả lập lên ảnh nền không lỗi.
- Kiểm tra `FFmpeg atempo` xử lý file WAV khi `speed != 1.0`.
