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


def generate_micro_batch_visual_prompts(
    cuts_text_list: Optional[List[str]] = None,
    visual_concept: str = "",
    api_key: str = "",
    model_name: str = "gemini-2.5-flash",
    art_style: str = "cinematic",
    batch_size: int = 3,
    scenes: Optional[List[str]] = None
) -> List[str]:
    if cuts_text_list is None:
        cuts_text_list = scenes or []
    """
    MICRO-BATCH DIRECTOR (3-4 CẢNH / REQUEST):
    - Đạt chuẩn chất lượng điện ảnh Hollywood cao nhất: AI có góc nhìn chuỗi phân cảnh (Shot Sequence),
      phân bổ nhịp nhàng (Wide shot -> Medium action -> Close-up detail).
    - Giữ trọn tính nhất quán (Visual Continuity) về màu sắc, phương tiện, nhân vật.
    - Cắt giảm 75% - 80% số request API: 12-16 cảnh chỉ tốn đúng 3 - 4 requests (Hoàn toàn < 10, miễn nhiễm lỗi 429).
    """
    total_cuts = len(cuts_text_list)
    if total_cuts == 0:
        return []

    tmpl = get_style_template(art_style)
    clean_concept = visual_concept.strip() if visual_concept else ""
    final_prompts = ["" for _ in range(total_cuts)]

    # Chuẩn bị danh sách fallback sẵn sàng
    for idx, txt in enumerate(cuts_text_list):
        core = transliterate_fallback_vietnamese(clean_concept if clean_concept else txt)
        final_prompts[idx] = f"{tmpl['prefix']} a solitary subject featuring {core}{tmpl['suffix']}"

    if not api_key or not api_key.strip():
        return final_prompts

    pool = GeminiKeyPool.get_instance()
    all_keys = pool.parse_keys(api_key)
    if not all_keys:
        return final_prompts

    import importlib
    try:
        genai = importlib.import_module("google.generativeai")
    except Exception as e:
        print(f"⚠️ Thư viện google.generativeai chưa sẵn sàng: {e}")
        return final_prompts

    # Danh sách model dự phòng
    models_to_try = []
    base_model = str(model_name).lower()
    if "pro" in base_model:
        models_to_try = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
    elif "lite" in base_model:
        models_to_try = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    else:
        models_to_try = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-1.5-flash"]

    # Chia nhỏ danh sách cảnh thành từng cụm mini (Micro-Batches: 3-4 cảnh)
    bs = max(1, min(batch_size, 4))
    chunks = [list(range(i, min(i + bs, total_cuts))) for i in range(0, total_cuts, bs)]

    print(f"🎬 [Micro-Batch Director] Tối ưu {total_cuts} cảnh thành {len(chunks)} cụm mini ({bs} cảnh/request) để đạt độ chân thực tối đa!")

    for chunk_idx, indices in enumerate(chunks):
        chunk_texts = [cuts_text_list[idx] for idx in indices]
        
        # Xây dựng prompt đạo diễn chuyên sâu cho cụm mini
        formatted_scenes = "\n".join([f"Scene {n+1}: {chunk_texts[n]}" for n in range(len(chunk_texts))])
        
        prompt_instruction = (
            f"You are a master Hollywood cinematography director designing a sequential visual storyboard for: {tmpl['director_instruction']}\n\n"
            f"Story Overall Concept: {clean_concept}\n\n"
            f"Sequential Scenes to direct:\n{formatted_scenes}\n\n"
            "DIRECTOR INSTRUCTIONS FOR MAXIMUM CINEMATIC REALISM:\n"
            "1. Create cinematic shot variation across the sequence:\n"
            "   - First scene in sequence: Wide atmospheric establishing shot.\n"
            "   - Middle scene(s): Focused medium shot on primary action or subject.\n"
            "   - Final scene in sequence: Dramatic close-up detail, evocative texture, or chiaroscuro shadow.\n"
            "2. Maintain strict visual continuity (coherent vehicle, character silhouette, color tone, lighting).\n"
            "3. Focus on ONE single subject per scene. Never use plural nouns (no 'cars', 'people'). Avoid fingers/hands.\n"
            f"4. Under 18 English words per scene. Do not include style words like 'sketch' or 'photo'.\n"
            f"5. Return EXACTLY {len(indices)} lines numbered 1 to {len(indices)}, formatted like:\n"
            "1. <raw subject description for scene 1>\n"
            "2. <raw subject description for scene 2>\n"
            f"... up to {len(indices)}."
        )

        chunk_success = False

        # Thử qua các Key khả dụng
        for key_idx, current_key in enumerate(all_keys):
            if chunk_success:
                break
            if pool.cooldowns.get(current_key, 0) > time.time() and len(all_keys) > 1:
                continue

            try:
                genai.configure(api_key=current_key)
            except Exception:
                continue

            for cand_model in models_to_try:
                try:
                    model_inst = genai.GenerativeModel(cand_model)
                    resp = model_inst.generate_content(prompt_instruction)
                    if resp and resp.text:
                        raw_lines = resp.text.strip().split("\n")
                        extracted_descriptions = []
                        for line in raw_lines:
                            clean_line = re.sub(r'^\s*(\d+[\.\:\)\-]|Scene\s*\d+[\:\.\-]?)\s*', '', line, flags=re.IGNORECASE).strip()
                            clean_line = clean_line.replace('"', '').replace('*', '')
                            if clean_line:
                                words = clean_line.split()
                                if len(words) > 18:
                                    clean_line = " ".join(words[:18])
                                extracted_descriptions.append(clean_line)

                        # Gán mô tả vào từng cảnh tương ứng
                        for offset, global_idx in enumerate(indices):
                            if offset < len(extracted_descriptions) and extracted_descriptions[offset]:
                                subj_desc = extracted_descriptions[offset]
                                final_prompts[global_idx] = f"{tmpl['prefix']} {subj_desc}{tmpl['suffix']}"

                        chunk_success = True
                        break
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "quota" in err_str.lower():
                        pool.mark_cooldown(current_key, 40.0)
                        if len(all_keys) > 1 and key_idx < len(all_keys) - 1:
                            print(f"🔄 Đổi sang Key tiếp theo cho cụm {chunk_idx + 1}...")
                            break
                        continue
                    else:
                        continue

        # Thêm độ trễ rất nhẹ 0.5s giữa các cụm để kết nối mạng mượt mà
        if chunk_idx < len(chunks) - 1:
            time.sleep(0.5)

    return final_prompts


def enhance_visual_prompt_gemini(
    scene_text: str,
    visual_concept: str,
    api_key: str,
    model_name: str = "gemini-2.5-flash",
    art_style: str = "cinematic"
) -> str:
    """
    Hàm wrapper tương thích ngược: Sinh prompt cho 1 phân cảnh đơn lẻ qua Micro-Batch.
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
