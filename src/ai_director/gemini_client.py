import os
import re
import time
import json
import urllib.parse
from typing import List, Optional, Dict, Any

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
    "đèn": "streetlamp",
    "đồng hồ": "antique clock",
    "cửa sổ": "rainy window",
    "bức thư": "old handwritten letter",
    "căn phòng": "dimly lit study room",
    "bước chân": "mysterious footsteps in fog",
    "mặt nạ": "Venetian porcelain mask",
    "bóng tối": "shadowy silhouette",
    "ngọn lửa": "flickering candle flame"
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


def transliterate_fallback_vietnamese(text: str, cut_part: int = 0) -> str:
    """
    Dịch nhanh các danh từ thị giác tiếng Việt sang tiếng Anh khi phải dùng fallback prompt.
    Hỗ trợ biến đổi góc máy nếu là Part 2 (Góc máy phụ).
    """
    lowered = text.lower()
    found_keywords = []
    for vi_w, en_w in VI_TO_EN_MAP.items():
        if vi_w in lowered:
            found_keywords.append(en_w)
    core = ", ".join(found_keywords[:3]) if found_keywords else "a dramatic moody mystery scene"

    if cut_part == 2:
        part2_prefixes = [
            f"dramatic low-angle view of {core}",
            f"extreme close-up macro detail of {core}",
            f"atmospheric over-the-shoulder POV shot of {core}",
            f"wide aerial bird-eye perspective of {core}"
        ]
        import random
        return random.choice(part2_prefixes)

    return f"a scene featuring {core}"


def parse_gemini_json_response(raw_text: str) -> Dict[int, str]:
    """
    Bộ giải mã JSON siêu cấp 3 tầng, có khả năng tự động hàn gắn chuỗi JSON bị cắt cụt (Unterminated string).
    Tuyệt đối không quăng ngoại lệ làm gián đoạn pipeline.
    """
    if not raw_text or not raw_text.strip():
        return {}

    clean = raw_text.strip()
    clean = re.sub(r"^```json\s*", "", clean, flags=re.MULTILINE)
    clean = re.sub(r"^```\s*", "", clean, flags=re.MULTILINE).strip()

    # Cách 1: Parse JSON chuẩn
    try:
        data = json.loads(clean)
        if isinstance(data, list):
            res = {}
            for item in data:
                if isinstance(item, dict) and "index" in item and "prompt" in item:
                    res[int(item["index"])] = str(item["prompt"]).strip()
            if res:
                return res
        elif isinstance(data, dict):
            res = {}
            for k, v in data.items():
                if isinstance(v, str):
                    digits = re.findall(r"\d+", str(k))
                    if digits:
                        res[int(digits[0])] = v.strip()
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict) and "index" in item and "prompt" in item:
                            res[int(item["index"])] = str(item["prompt"]).strip()
            if res:
                return res
    except Exception:
        pass

    # Cách 2: Tự động đóng mảng JSON tại vị trí đối tượng hoàn chỉnh gần nhất (sửa lỗi đứt đuôi chuỗi)
    last_brace = clean.rfind("}")
    if last_brace != -1:
        truncated_valid = clean[:last_brace + 1].strip()
        if not truncated_valid.startswith("["):
            truncated_valid = "[" + truncated_valid
        truncated_valid = truncated_valid.rstrip().rstrip(",") + "]"
        try:
            data = json.loads(truncated_valid)
            if isinstance(data, list):
                res = {}
                for item in data:
                    if isinstance(item, dict) and "index" in item and "prompt" in item:
                        res[int(item["index"])] = str(item["prompt"]).strip()
                if res:
                    return res
        except Exception:
            pass

    # Cách 3: Regex quét toàn bộ các cặp {"index": X, "prompt": "..."} hoàn chỉnh
    res = {}
    p1 = r'\{\s*"index"\s*:\s*(\d+)\s*,\s*"prompt"\s*:\s*"(.*?)(?<!\\)"'
    for m in re.finditer(p1, clean, re.DOTALL):
        idx = int(m.group(1))
        p = m.group(2).replace('\"', '"').replace('\n', ' ').strip()
        res[idx] = p

    p2 = r'\{\s*"prompt"\s*:\s*"(.*?)(?<!\\)"\s*,\s*"index"\s*:\s*(\d+)'
    for m in re.finditer(p2, clean, re.DOTALL):
        idx = int(m.group(2))
        p = m.group(1).replace('\"', '"').replace('\n', ' ').strip()
        if idx not in res:
            res[idx] = p

    return res


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
        return None


class GeminiKeyPool:
    """
    Quản lý cụm Gemini API Keys xoay tua (Round-robin) và theo dõi trạng thái Cooldown khi gặp lỗi 429 Quota Exceeded.
    """
    _instance = None

    def __init__(self):
        self.cooldowns = {}
        self.key_usage_count = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = GeminiKeyPool()
        return cls._instance

    def parse_keys(self, raw_input: str) -> List[str]:
        if not raw_input:
            env_key = os.environ.get("GEMINI_API_KEY", "")
            if not env_key:
                try:
                    from google.colab import userdata
                    env_key = userdata.get("GEMINI_API_KEY") or ""
                except Exception:
                    pass
            if env_key:
                return [env_key.strip()]
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
        for k in keys:
            if self.cooldowns.get(k, 0) <= now:
                return k
        best_key = min(keys, key=lambda k: self.cooldowns.get(k, 0))
        return best_key


def _call_gemini_rest_api(prompt_instruction: str, api_key: str, model_name: str = "gemini-2.5-flash") -> Optional[str]:
    """
    Gọi trực tiếp Google Gemini REST API v1beta với chế độ responseMimeType: application/json.
    Không phụ thuộc vào thư viện bên ngoài và tốc độ phản hồi cực nhanh.
    """
    import requests
    clean_key = api_key.strip().strip('"').strip("'")
    clean_mod = model_name.replace("models/", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_mod}:generateContent?key={clean_key}"

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": clean_key
    }
    payload = {
        "contents": [{"parts": [{"text": prompt_instruction}]}],
        "generationConfig": {
            "temperature": 0.75,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json"
        }
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=40)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        elif resp.status_code == 429:
            return "ERROR_429"
    except Exception:
        pass
    return None


def generate_micro_batch_visual_prompts(
    cuts_text_list: Optional[List[str]] = None,
    visual_concept: str = "",
    api_key: str = "",
    model_name: str = "gemini-2.5-flash",
    art_style: str = "cinematic",
    batch_size: int = 25,
    scenes: Optional[List[str]] = None,
    cuts: Optional[List[dict]] = None
) -> List[str]:
    """
    AI ĐẠO DIỄN HÌNH ẢNH MẺ LỚN (BATCH 20-25 CẢNH BẰNG JSON API):
    - Đột phá hiệu năng: 50-100 cảnh chỉ tốn đúng 2-4 lượt gọi API (Tiết kiệm 85% requests, miễn nhiễm 429).
    - Giữ trọn vẹn mạch cảm xúc (Narrative Continuity) xuyên suốt toàn bộ phân đoạn thoại.
    - Bộ giải mã JSON 3 tầng tự động hàn gắn chuỗi đứt đuôi nếu LLM bị ngắt kết nối.
    - Tự động nhận diện phân cảnh Part 2 [Góc máy phụ] để tạo góc quay điện ảnh tương phản.
    """
    if cuts is not None and len(cuts) > 0:
        total_cuts = len(cuts)
        cuts_data = cuts
    else:
        raw_list = cuts_text_list if cuts_text_list is not None else (scenes or [])
        total_cuts = len(raw_list)
        cuts_data = [{"index": i + 1, "text": t, "part": 0} for i, t in enumerate(raw_list)]

    if total_cuts == 0:
        return []

    tmpl = get_style_template(art_style)
    clean_concept = visual_concept.strip() if visual_concept else ""
    final_prompts = ["" for _ in range(total_cuts)]

    for idx, c in enumerate(cuts_data):
        c_txt = c.get("text", "")
        c_part = c.get("part", 0)
        core = transliterate_fallback_vietnamese(clean_concept if clean_concept else c_txt, cut_part=c_part)
        final_prompts[idx] = f"{tmpl['prefix']} {core}{tmpl['suffix']}"

    pool = GeminiKeyPool.get_instance()
    all_keys = pool.parse_keys(api_key)
    if not all_keys:
        return final_prompts

    models_to_try = []
    base_model = str(model_name).lower()
    if "pro" in base_model:
        models_to_try = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
    elif "lite" in base_model:
        models_to_try = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"]
    else:
        models_to_try = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]

    bs = max(5, min(batch_size, 30))
    chunks = [cuts_data[i:i + bs] for i in range(0, total_cuts, bs)]

    print(f"🎬 [AI Director JSON Engine] Đang đạo diễn kịch bản {total_cuts} cảnh qua {len(chunks)} mẻ (mỗi mẻ tối đa {bs} cảnh)...")

    for chunk_idx, chunk_cuts in enumerate(chunks):
        chunk_indices = [c.get("index", i + 1) for i, c in enumerate(chunk_cuts)]
        cuts_summary = []
        for c in chunk_cuts:
            c_idx = c.get("index", 1)
            part_info = " [Góc máy phụ - Part 2]" if c.get("part") == 2 else ""
            cuts_summary.append(f'Cảnh {c_idx}{part_info}: "{c.get("text", "")}"')

        formatted_scenes = "\n".join(cuts_summary)

        system_instruction = (
            f"You are an award-winning Hollywood cinematography director designing a sequential visual storyboard for: {tmpl['director_instruction']}\n\n"
            f"Story Overall Concept: {clean_concept if clean_concept else 'Cinematic mystery storytelling'}\n\n"
            f"Sequential Scenes to direct ({len(chunk_cuts)} scenes):\n{formatted_scenes}\n\n"
            "DIRECTOR MANDATORY INSTRUCTIONS:\n"
            "1. Shot Variation & Flow:\n"
            "   - Establish scenes with atmospheric wide or medium shots.\n"
            "   - For any scene marked '[Góc máy phụ - Part 2]', create an alternate cinematic angle of that concept (dramatic low-angle, extreme macro close-up, over-the-shoulder POV, or wide bird-eye view).\n"
            "2. Visual Metaphor & Atmosphere:\n"
            "   - Describe specific physical actions, objects, lighting, and expressions reflecting the narrative.\n"
            "   - Focus on ONE single subject per scene. Never use plural nouns (no 'cars', 'people'). Avoid fingers/hands.\n"
            "   - Anti-repetition: Vary focal points so consecutive scenes do not show the exact same object.\n"
            "3. Length constraint: 12 to 20 English words per scene. Do not include style words like 'sketch' or 'photo'.\n"
            "4. OUTPUT FORMAT: Return STRICTLY a valid JSON array of objects (no markdown, no conversational text):\n"
            "[\n"
            f'  {{"index": {chunk_indices[0]}, "prompt": "a shadowy detective holding a brass lantern in foggy cobblestone alley"}},\n'
            f'  {{"index": {chunk_indices[-1]}, "prompt": "extreme close-up of an intricate antique pocket watch ticking on mahogany desk"}}\n'
            "]"
        )

        chunk_success = False

        for key_idx, current_key in enumerate(all_keys):
            if chunk_success:
                break
            if pool.cooldowns.get(current_key, 0) > time.time() and len(all_keys) > 1:
                continue

            for cand_model in models_to_try:
                raw_json_text = _call_gemini_rest_api(system_instruction, current_key, cand_model)
                if raw_json_text == "ERROR_429":
                    pool.mark_cooldown(current_key, 40.0)
                    break

                if raw_json_text and len(raw_json_text) > 10:
                    parsed_dict = parse_gemini_json_response(raw_json_text)
                    if parsed_dict and len(parsed_dict) > 0:
                        for offset, cut_item in enumerate(chunk_cuts):
                            global_idx = chunk_idx * bs + offset
                            c_num = cut_item.get("index", global_idx + 1)

                            prompt_val = parsed_dict.get(c_num)
                            if not prompt_val:
                                prompt_val = parsed_dict.get(offset + 1)

                            if prompt_val:
                                clean_p = re.sub(r'["*]', '', prompt_val).strip()
                                words = clean_p.split()
                                if len(words) > 22:
                                    clean_p = " ".join(words[:22])
                                final_prompts[global_idx] = f"{tmpl['prefix']} {clean_p}{tmpl['suffix']}"

                        chunk_success = True
                        break

            if chunk_success:
                break

        if chunk_idx < len(chunks) - 1:
            time.sleep(0.3)

    print(f"🎉 [AI Director] Hoàn tất lên kịch bản hình ảnh cho {total_cuts} phân cảnh!")
    return final_prompts


def enhance_visual_prompt_gemini(
    scene_text: str,
    visual_concept: str,
    api_key: str,
    model_name: str = "gemini-2.5-flash",
    art_style: str = "cinematic"
) -> str:
    """
    Hàm wrapper tương thích ngược: Sinh prompt cho 1 phân cảnh đơn lẻ.
    """
    results = generate_micro_batch_visual_prompts(
        cuts_text_list=[scene_text],
        visual_concept=visual_concept,
        api_key=api_key,
        model_name=model_name,
        art_style=art_style,
        batch_size=1
    )
    return results[0] if results else f"35mm film photograph of {scene_text[:50]}, cinematic lighting, 8k"
