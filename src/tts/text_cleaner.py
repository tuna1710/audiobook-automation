import re
from datetime import datetime

# 25 giọng đọc chuẩn 100% có sẵn trong VieNeu-TTS Turbo
PRESET_VOICES = [
    "Thiền Tâm Đức",
    "Minh Đức",
    "Mai Anh",
    "Ngọc Huyền",
    "Ngọc Linh",
    "Thanh Bình",
    "Thùy Dung",
    "Mỹ Duyên",
    "Quỳnh Anh",
    "Đoan Trang",
    "Thục Đoan",
    "Kim Thanh",
    "Ngọc Trân",
    "Trúc Ly",
    "Hải Đăng",
    "Thiện Minh",
    "Minh Triết",
    "Đức Trí",
    "Quốc Tuấn",
    "Quang Sơn",
    "Phạm Tuyên",
    "Thái Sơn",
    "Xuân Vĩnh",
    "Adam",
    "Adam bựa"
]

VOICE_FALLBACK_MAP = {
    "bảo ngọc": "Mai Anh",
    "thảo vy": "Thùy Dung",
    "thanh long": "Thanh Bình",
    "mai phương": "Mai Anh",
    "minh hoàng": "Minh Triết",
    "hùng dũng": "Hải Đăng",
    "quỳnh như": "Quỳnh Anh",
    "hoài an": "Mỹ Duyên",
    "gia huy": "Đức Trí",
    "minh quân": "Minh Đức",
    "minh quân pro": "Minh Đức"
}


def clean_voice_name(voice_str: str) -> str:
    """
    Làm sạch tên giọng VieNeu từ giao diện Gradio, loại bỏ phần chú thích trong ngoặc đơn,
    và tự động khớp chính xác với 25 giọng có sẵn trong VieNeu-TTS để tuyệt đối không bị ValueError.
    """
    if not voice_str:
        return "Thiền Tâm Đức"

    clean = re.sub(r'\(.*?\)', '', str(voice_str)).strip()

    # 1. Khớp chính xác với 25 giọng của VieNeu
    for preset in PRESET_VOICES:
        if preset.lower() == clean.lower():
            return preset

    # 2. Khớp với bảng ánh xạ giọng cũ / alias
    clean_lower = clean.lower()
    if clean_lower in VOICE_FALLBACK_MAP:
        return VOICE_FALLBACK_MAP[clean_lower]

    for old_v, target_v in VOICE_FALLBACK_MAP.items():
        if old_v in clean_lower:
            return target_v

    # 3. Khớp chuỗi con
    for preset in PRESET_VOICES:
        if preset.lower() in clean_lower or clean_lower in preset.lower():
            return preset

    # 4. Fallback an toàn tuyệt đối
    return "Thiền Tâm Đức"


def extract_schedule_from_text(raw_text: str) -> str:
    """
    Trích xuất mốc ngày giờ hẹn đăng định dạng YYYY-MM-DD HH:MM
    Ví dụ: 2026-09-24 19:30, Ngày đăng: 2026-09-24 19:30, [LỊCH ĐĂNG]: 2026-09-24 19:30
    """
    sched_patterns = [
        r'(?i)(?:ngày đăng|lịch đăng|thời gian đăng|hẹn giờ|schedule|publish\s*at)\s*[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2})',
        r'(?i)\[\s*(?:lịch đăng|ngày đăng|schedule)\s*\]\s*[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2})',
        r'\b(20\d{2}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2})\b'
    ]
    for pat in sched_patterns:
        m = re.search(pat, raw_text)
        if m:
            raw_s = m.group(1).replace('/', '-')
            try:
                datetime.strptime(raw_s, "%Y-%m-%d %H:%M")
                return raw_s
            except Exception:
                pass
    return ""


def extract_script_components(raw_text: str, channel_profile: str = "", default_concept: str = ""):
    """
    Bóc tách kịch bản đầu vào:
    - Bóc tách tiêu đề video (YouTube title, option 1, header markdown #).
    - Bóc tách visual prompt/concept theo hồ sơ kênh hoặc override.
    - Bóc tách mô tả SEO & Hashtags.
    - Bóc tách ngày giờ hẹn đăng (Schedule time).
    - Bóc tách văn bản đọc thuần túy cho TTS (lọc bỏ tags biểu cảm [thở dài], [cười]).
    """
    if not raw_text or not raw_text.strip():
        return "", "", "", "", ""

    from ..pipeline.channel_profiles import get_channel_profile
    prof = get_channel_profile(channel_profile) if channel_profile else {}
    default_title = f"AUDIOBOOK {prof.get('channel_name', 'HỆ THỐNG').upper()}" if prof else "TRINH THÁM & KINH DỊ GOTHIC KINH ĐIỂN"
    topic_title = default_title

    # 1. Trích xuất tiêu đề
    for line in raw_text.splitlines():
        line_s = line.strip()
        line_lower = line_s.lower()
        if line_lower.startswith("tiêu đề youtube") or line_lower.startswith("tieu de youtube"):
            parts = line_s.split(":", 1)
            if len(parts) > 1 and len(parts[1].strip()) > 3:
                topic_title = parts[1].strip().replace('"', '').replace("'", "")
                break
        elif line_lower.startswith("- option 1:"):
            parts = line_s.split(":", 1)
            if len(parts) > 1 and len(parts[1].strip()) > 3:
                topic_title = parts[1].strip().replace('"', '').replace("'", "")
                break
        elif line_lower.startswith("tiêu đề:") or line_lower.startswith("tieu de:"):
            parts = line_s.split(":", 1)
            if len(parts) > 1 and len(parts[1].strip()) > 3:
                topic_title = parts[1].strip().replace('"', '').replace("'", "")
                break
        elif line_s.startswith("# "):
            cand = line_s[2:].strip().replace('"', '').replace("'", "")
            if len(cand) > 3:
                topic_title = cand
                break

    # 2. Trích xuất ý tưởng Visual Concept
    visual_prompt = default_concept or (prof.get("visual_concept") if prof else "") or "19th century Victorian Gothic atmosphere, dark moody chiaroscuro lighting, detective mystery, cinematic suspense"
    for line in raw_text.splitlines():
        line_s = line.strip()
        line_lower = line_s.lower()
        if line_lower.startswith("- visual:") or line_lower.startswith("visual:"):
            parts = line_s.split(":", 1)
            if len(parts) > 1 and len(parts[1].strip()) > 10:
                visual_prompt = parts[1].strip()
                break

    # 3. Trích xuất Mô tả Video (SEO Description)
    custom_description = None
    desc_patterns = [
        r'(?:\[\s*(?:MÔ TẢ VIDEO|MO TA VIDEO|MÔ TẢ YOUTUBE|MO TA YOUTUBE|MÔ TẢ|MO TA|SEO DESCRIPTION)\s*\]:?|(?:MÔ TẢ VIDEO|MO TA VIDEO|MÔ TẢ YOUTUBE|MO TA YOUTUBE|SEO DESCRIPTION)\s*:)(.*?)(?=(?:[\r\n]+\s*---|---\s*\[|[\r\n]+\s*\[|[\r\n]+\s*#{1,6}\s+[^\r\n#]|\Z))',
        r'(?:^|\n)\s*-\s*(?:Mô tả ngắn & Hashtags|Mô tả & Hashtags|Mô tả ngắn|Mô tả|Description)\s*:(.*?)(?=(?:[\r\n]+\s*[-#\[]|\n\s*---|---\s*\[|\Z))'
    ]
    for pat in desc_patterns:
        desc_match = re.search(pat, raw_text, re.IGNORECASE | re.DOTALL)
        if desc_match:
            cand_desc = desc_match.group(1).strip()
            if len(cand_desc) > 5:
                custom_description = cand_desc
                break

    # 4. Trích xuất Ngày đăng từ kịch bản
    extracted_schedule_str = extract_schedule_from_text(raw_text)

    # 5. Trích xuất Văn bản đọc cho VieNeu-TTS
    split_marker = "--- [VĂN BẢN ĐỌC CHO VIENEU-TTS-V3-TURBO] ---"
    if split_marker in raw_text:
        speech_text = raw_text.split(split_marker, 1)[1].strip()
    else:
        cleaned = raw_text
        for pat in desc_patterns:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        valid_lines = []
        for line in cleaned.splitlines():
            ls = line.strip().lower()
            clean_l = ls.lstrip('[-*# \t')
            if any(clean_l.startswith(p) for p in ["tiêu đề", "tieu de", "visual", "option", "ngày đăng", "ngay dang", "lịch đăng", "lich dang", "hẹn giờ", "schedule", "publish"]):
                continue
            if re.search(r'\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}\b', line) and len(line.strip()) < 50:
                continue
            valid_lines.append(line)
        speech_text = "\n".join(valid_lines).strip()

    # Làm sạch các thẻ biểu cảm
    speech_text = re.sub(
        r'\[(?:thở dài|hắng giọng|cười|ngắt nghỉ|im lặng|hơi thở|thì thầm|tiếng thở|tiếng cười|tiếng động)[^\]]*\]',
        '',
        speech_text,
        flags=re.IGNORECASE
    ).strip()

    return topic_title, visual_prompt, speech_text, custom_description or "", extracted_schedule_str
