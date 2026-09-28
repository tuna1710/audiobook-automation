import re

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


def get_style_template(art_style: str) -> dict:
    style_str = str(art_style).lower()
    if "chì" in style_str or "pencil" in style_str:
        return ART_STYLE_TEMPLATES["pencil"]
    elif "thủy mặc" in style_str or "ink" in style_str or "watercolor" in style_str:
        return ART_STYLE_TEMPLATES["watercolor"]
    elif "truyện tranh" in style_str or "comic" in style_str or "noir" in style_str:
        return ART_STYLE_TEMPLATES["comic_noir"]
    return ART_STYLE_TEMPLATES["cinematic"]


def init_gemini_client(api_key: str):
    """
    Khởi tạo Gemini API client.
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


def enhance_visual_prompt_gemini(
    scene_text: str,
    visual_concept: str,
    api_key: str,
    model_name: str = "gemini-2.5-flash",
    art_style: str = "cinematic"
) -> str:
    """
    Sử dụng Gemini AI để tối ưu hóa mô tả phân cảnh thành English Prompt điện ảnh chuẩn SDXL:
    - Kỹ thuật Compact Template & Front-loading: Đưa phong cách lên đầu câu, giới hạn ngữ cảnh < 45 từ để triệt tiêu lỗi CLIP 77 tokens.
    - Hỗ trợ đa dạng phong cách: Bút chì (Pencil sketch), Thủy mặc, Comic Noir, Điện ảnh 35mm.
    - Tập trung vào 1 chủ thể duy nhất (chống nhân bản xe, tránh lỗi ngón tay).
    """
    clean_concept = visual_concept.strip() if visual_concept else ""
    clean_scene = scene_text.strip() if scene_text else ""
    tmpl = get_style_template(art_style)

    fallback_core = clean_concept if clean_concept else clean_scene[:50]
    fallback_prompt = f"{tmpl['prefix']} a solitary subject inspired by {fallback_core}{tmpl['suffix']}"

    if not api_key:
        return fallback_prompt

    genai = init_gemini_client(api_key)
    if not genai:
        return fallback_prompt

    try:
        clean_model = "gemini-2.5-flash"
        if "pro" in str(model_name).lower():
            clean_model = "gemini-2.5-pro"
        elif "lite" in str(model_name).lower():
            clean_model = "gemini-2.5-flash-lite"

        model = genai.GenerativeModel(clean_model)
        prompt = (
            f"You are an expert art director. Describe ONLY the central subject for: {tmpl['director_instruction']}\n\n"
            "STRICT CONSTRAINTS (UNDER 18 WORDS):\n"
            "1. Focus strictly on ONE single main subject or atmospheric environment (e.g. 'a single vintage sedan parked on damp road', 'a solitary detective seen in profile', 'an empty rainy street').\n"
            "2. NEVER use plural words for subjects (avoid 'cars', 'people', 'buildings').\n"
            "3. If depicting a person, describe silhouette, profile, or medium shot. Do not describe open hands or fingers.\n"
            "4. DO NOT include style words like 'sketch', 'photo', 'drawing' (these will be added automatically).\n"
            "5. Output ONLY the raw subject description in under 18 English words.\n\n"
            f"Story Concept: {clean_concept}\nScene Text: {clean_scene}"
        )
        resp = model.generate_content(prompt)
        if resp and resp.text:
            raw_subj = resp.text.strip().replace('"', '').replace('\n', ' ')
            words = raw_subj.split()
            if len(words) > 18:
                raw_subj = " ".join(words[:18])
            # Tạo prompt hoàn chỉnh: Style Prefix + Subject Core + Style Suffix (< 40 words, an toàn tuyệt đối với CLIP 77 tokens)
            final_prompt = f"{tmpl['prefix']} {raw_subj}{tmpl['suffix']}"
            return final_prompt
    except Exception as e:
        print(f"ℹ️ Gemini visual prompt fallback: {e}")

    return fallback_prompt
