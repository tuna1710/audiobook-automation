import re

PRESET_VOICES = [
    "Thiền Tâm Đức",
    "Thanh Long",
    "Bảo Ngọc",
    "Thảo Vy",
    "Mai Phương",
    "Hùng Dũng",
    "Quỳnh Như",
    "Minh Hoàng",
    "Hoài An",
    "Gia Huy"
]

def clean_voice_name(voice_str: str) -> str:
    """
    Làm sạch tên giọng VieNeu từ giao diện Gradio, loại bỏ phần chú thích trong ngoặc đơn,
    và tự động khớp chính xác với _preset_voices của VieNeu để tuyệt đối không bị ValueError.
    """
    if not voice_str:
        return "Thiền Tâm Đức"
    
    clean = re.sub(r'\(.*?\)', '', str(voice_str)).strip()
    for preset in PRESET_VOICES:
        if preset.lower() == clean.lower():
            return preset
        if preset.lower() in clean.lower() or clean.lower() in preset.lower():
            return preset
    return clean if clean else "Thiền Tâm Đức"

def extract_script_components(script_text: str):
    """
    Phân tích kịch bản đầu vào:
    - Bóc tách tiêu đề video.
    - Bóc tách ý tưởng visual concept.
    - Bóc tách nội dung giọng đọc thuần túy (loại bỏ mô tả, header).
    - Bóc tách mô tả video có sẵn.
    - Bóc tách thời gian hẹn giờ.
    """
    if not script_text or not script_text.strip():
        return "", "", "", "", ""

    text = script_text.strip()
    
    # 1. Trích xuất thời gian đăng
    sched_match = re.search(r'\[NGÀY ĐĂNG\]:\s*([^\r\n]+)', text, re.IGNORECASE)
    sched_time_str = sched_match.group(1).strip() if sched_match else ""

    # 2. Trích xuất Tiêu đề gợi ý
    title_match = re.search(r'\[TIÊU ĐỀ GỢI Ý\]:\s*(?:-\s*(?:Option 1:?)?\s*)?([^\r\n]+)', text, re.IGNORECASE)
    auto_title = title_match.group(1).strip() if title_match else ""
    if not auto_title:
        title_alt = re.search(r'-\s*Tiêu đề YouTube.*?:\s*([^\r\n]+)', text, re.IGNORECASE)
        auto_title = title_alt.group(1).strip() if title_alt else ""

    # 3. Trích xuất Ý tưởng Thumbnail / Visual
    visual_match = re.search(r'\[Ý TƯỞNG THUMBNAIL\]:?\s*(?:-\s*Visual:?\s*|\s*)([^\r\n]+(?:\n[^\r\n-]+)*)', text, re.IGNORECASE)
    visual_concept = visual_match.group(1).strip() if visual_match else ""

    # 4. Trích xuất Mô tả video
    desc_match = re.search(r'(?:\[MÔ TẢ VIDEO\]:?)(.*?)(?=(?:---\s*\[|\Z))', text, re.DOTALL | re.IGNORECASE)
    custom_desc = desc_match.group(1).strip() if desc_match else ""

    # 5. Trích xuất Văn bản đọc thuần túy cho TTS
    split_marker = "--- [VĂN BẢN ĐỌC CHO VIENEU-TTS-V3-TURBO] ---"
    if split_marker in text:
        speech_text = text.split(split_marker, 1)[1].strip()
    else:
        # Nếu không có split marker, loại bỏ các block meta
        clean_text = re.sub(r'\[(?:NGÀY ĐĂNG|TIÊU ĐỀ GỢI Ý|THÔNG TIN TÁC PHẨM|Ý TƯỞNG THUMBNAIL|MÔ TẢ VIDEO)\].*?(?=\n\n|\n\[|\Z)', '', text, flags=re.DOTALL | re.IGNORECASE)
        speech_text = clean_text.strip()

    # Loại bỏ các tag biểu cảm cho TTS
    speech_text = re.sub(r'\[(?:thở dài|hắng giọng|cười|ngắt nghỉ|im lặng|hơi thở)[^\]]*\]', '', speech_text, flags=re.IGNORECASE).strip()

    return auto_title, visual_concept, speech_text, custom_desc, sched_time_str
