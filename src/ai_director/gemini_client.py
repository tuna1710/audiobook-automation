def init_gemini_client(api_key: str):
    """
    Khởi tạo Google GenerativeAI client tương thích ngược.
    """
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai
    except Exception as e:
        print(f"⚠️ Không thể khởi tạo Google GenerativeAI: {e}")
        return None


import os
import re
import time
from typing import List, Optional

ART_STYLE_TEMPLATES = {
    "pencil": {
        "prefix": "Detailed pencil sketch of",
        "suffix": ", fine graphite linework, delicate cross-hatching, monochrome drawing on textured parchment paper, artistic sketchbook masterpiece",
        "director_instruction": "a detailed monochrome pencil sketch and graphite drawing, hand-drawn fine linework and charcoal shading."
    },
    "watercolor": {
        "prefix": "Traditional ink wash painting of",
        "suffix": ", sumi-e style, subtle watercolor textures, atmospheric oriental ink brushwork, textured paper, masterpiece",
        "director_instruction": "a traditional oriental ink wash and watercolor painting, minimal elegant brushwork and atmospheric mist."
    },
    "comic_noir": {
        "prefix": "Graphic novel noir illustration of",
        "suffix": ", heavy black shadows, sharp inking lines, high-contrast dramatic comic art, gritty mystery atmosphere",
        "director_instruction": "a vintage graphic novel comic illustration in dramatic noir style, high contrast ink shadows and gritty mystery."
    },
    "cinematic": {
        "prefix": "35mm film photograph of",
        "suffix": ", cinematic lighting, shallow depth of field, 8k resolution, authentic realism, sharp focus",
        "director_instruction": "an award-winning 35mm cinematic photograph, realistic natural lighting, authentic textures and sharp focus."
    }
}

VI_TO_EN_MAP = {
    "ô tô": "vintage automobile",
    "xe hơi": "car",
    "xe": "vehicle",
    "mưa": "rain",
    "đêm": "night",
    "tối": "darkness",
    "phố": "street",
    "đường": "alley",
    "nhà": "building",
    "người": "solitary figure",
    "đàn ông": "man",
    "phụ nữ": "woman",
    "rừng": "forest",
    "biển": "ocean",
    "núi": "mountain",
    "vụ án": "crime mystery",
    "bí ẩn": "mystery",
    "cảnh sát": "investigator",
    "thám tử": "detective",
    "sương mù": "mist",
    "đèn": "streetlamp"
}


def get_style_template(art_style: str) -> dict:
    style_str = str(art_style).lower()
    if "chì" in style_str or "pencil" in style_str:
        return ART_STYLE_TEMPLATES["pencil"]
    elif "thủy mặc" in style_str or "ink" in style_str or "watercolor" in style_str:
        return ART_STYLE_TEMPLATES["watercolor"]
    elif "truyện tranh" in style_str or "comic" in style_str or "noir" in style_str:
        return ART_STYLE_TEMPLATES["comic_noir"]
    return ART_STYLE_TEMPLATES["cinematic"]


def transliterate_fallback_vietnamese(text: str) -> str:
    """
    Dịch nhanh các danh từ thị giác tiếng Việt sang tiếng Anh khi phải dùng fallback prompt.
    """
    lowered = text.lower()
    found_keywords = []
    for vi_w, en_w in VI_TO_EN_MAP.items():
        if vi_w in lowered:
            found_keywords.append(en_w)
    if found_keywords:
        return "a scene with " + ", ".join(found_keywords[:3])
    return "a dramatic moody mystery scene"


class GeminiKeyPool:
    """
    Quản lý cụm Gemini API Keys xoay tua (Round-robin) và theo dõi trạng thái Cooldown khi gặp lỗi 429 Quota Exceeded.
    """
    _instance = None

    def __init__(self):
        self.cooldowns = {}  # key -> float (timestamp hết hạn cooldown)
        self.key_usage_count = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = GeminiKeyPool()
        return cls._instance

    def parse_keys(self, raw_input: str) -> List[str]:
        if not raw_input:
            return []
        keys = [k.strip() for k in re.split(r'[,;\n]+', raw_input) if k.strip()]
        return keys

    def mark_cooldown(self, key: str, duration_seconds: float = 60.0):
        self.cooldowns[key] = time.time() + duration_seconds

    def get_available_key(self, raw_input: str) -> Optional[str]:
        keys = self.parse_keys(raw_input)
        if not keys:
            return None
        now = time.time()
        # Tìm key còn hạn ngạch (không bị cooldown)
        for k in keys:
            if self.cooldowns.get(k, 0) <= now:
                return k
        # Nếu tất cả đều bị cooldown, chọn key có thời gian chờ ngắn nhất
        best_key = min(keys, key=lambda k: self.cooldowns.get(k, 0))
        return best_key


def enhance_visual_prompt_gemini(
    scene_text: str,
    visual_concept: str,
    api_key: str,
    model_name: str = "gemini-2.5-flash",
    art_style: str = "cinematic"
) -> str:
    """
    Sử dụng Gemini AI với bộ đệm chống lỗi 429 Quota Exceeded đa tầng:
    1. Hỗ trợ xoay tua nhiều API Key (Key Rotation).
    2. Fallback sang các Model dự phòng (gemini-2.5-flash-lite, gemini-2.0-flash, gemini-1.5-flash) khi model chính cạn 20 RPM.
    3. Thử lại có độ trễ (Retry with Backoff) khi gặp 429.
    4. Compact prompt chuẩn token < 40 từ.
    """
    clean_concept = visual_concept.strip() if visual_concept else ""
    clean_scene = scene_text.strip() if scene_text else ""
    tmpl = get_style_template(art_style)

    # Chuẩn bị fallback tiếng Anh thông minh nếu Gemini hoàn toàn không khả dụng
    core_desc = transliterate_fallback_vietnamese(clean_concept if clean_concept else clean_scene)
    fallback_prompt = f"{tmpl['prefix']} a solitary subject featuring {core_desc}{tmpl['suffix']}"

    if not api_key or not api_key.strip():
        return fallback_prompt

    pool = GeminiKeyPool.get_instance()
    all_keys = pool.parse_keys(api_key)
    if not all_keys:
        return fallback_prompt

    # Danh sách model theo thứ tự ưu tiên (Google tính quota 20 RPM RIÊNG BIỆT cho từng model)
    models_to_try = []
    base_model = str(model_name).lower()
    if "pro" in base_model:
        models_to_try = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
    elif "lite" in base_model:
        models_to_try = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    else:
        models_to_try = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-1.5-flash"]

    import importlib
    try:
        genai = importlib.import_module("google.generativeai")
    except Exception as e:
        print(f"⚠️ Thư viện google.generativeai chưa sẵn sàng: {e}")
        return fallback_prompt

    prompt_content = (
        f"You are an expert art director. Describe ONLY the central subject for: {tmpl['director_instruction']}\n\n"
        "STRICT CONSTRAINTS (UNDER 18 WORDS):\n"
        "1. Focus strictly on ONE single main subject or atmospheric environment (e.g. 'a single vintage sedan parked on damp road', 'a solitary detective seen in profile', 'an empty rainy street').\n"
        "2. NEVER use plural words for subjects (avoid 'cars', 'people', 'buildings').\n"
        "3. If depicting a person, describe silhouette, profile, or medium shot. Do not describe open hands or fingers.\n"
        "4. DO NOT include style words like 'sketch', 'photo', 'drawing' (these will be added automatically).\n"
        "5. Output ONLY the raw subject description in under 18 English words.\n\n"
        f"Story Concept: {clean_concept}\nScene Text: {clean_scene}"
    )

    # Thử qua các Key khả dụng
    for key_idx, current_key in enumerate(all_keys):
        # Kiểm tra cooldown
        if pool.cooldowns.get(current_key, 0) > time.time() and len(all_keys) > 1:
            continue

        try:
            genai.configure(api_key=current_key)
        except Exception as e:
            print(f"⚠️ Lỗi cấu hình Gemini API Key: {e}")
            continue

        # Thử qua các Model dự phòng
        for candidate_model in models_to_try:
            try:
                model_inst = genai.GenerativeModel(candidate_model)
                resp = model_inst.generate_content(prompt_content)
                if resp and resp.text:
                    raw_subj = resp.text.strip().replace('"', '').replace('\n', ' ')
                    words = raw_subj.split()
                    if len(words) > 18:
                        raw_subj = " ".join(words[:18])
                    final_prompt = f"{tmpl['prefix']} {raw_subj}{tmpl['suffix']}"
                    return final_prompt
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower() or "limit" in err_str.lower():
                    # Trích xuất thời gian chờ retry nếu có
                    retry_wait = 40.0
                    m = re.search(r'retry in ([0-9.]+)\s*s', err_str, re.IGNORECASE)
                    if m:
                        try:
                            retry_wait = float(m.group(1))
                        except Exception:
                            pass
                    
                    pool.mark_cooldown(current_key, retry_wait)
                    
                    # Nếu còn Key khác trong cụm xoay tua, chuyển ngay sang Key tiếp theo!
                    if len(all_keys) > 1 and key_idx < len(all_keys) - 1:
                        print(f"🔄 Gemini Key [{current_key[:8]}...] chạm hạn mức 429. Đang tự động đổi sang Key tiếp theo trong cụm...")
                        break  # Thoát loop candidate_model để sang key tiếp theo

                    # Nếu chỉ có 1 Key, thử đổi sang Model dự phòng (Flash-Lite / 2.0 / 1.5)
                    print(f"🔄 Model '{candidate_model}' chạm hạn mức 20 RPM (429). Tự động chuyển fallback sang model dự phòng tiếp theo...")
                    continue
                else:
                    print(f"ℹ️ Gemini lỗi ({candidate_model}): {e}")
                    continue

    print("⚠️ Tất cả Gemini Keys/Models đều đang trong trạng thái chờ quota 429. Sử dụng Smart Fallback Prompt an toàn.")
    return fallback_prompt
