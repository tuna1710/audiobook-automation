import re

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

def enhance_visual_prompt_gemini(scene_text: str, visual_concept: str, api_key: str, model_name: str = "gemini-2.5-flash") -> str:
    """
    Sử dụng Gemini AI để tối ưu hóa mô tả phân cảnh thành English Prompt điện ảnh chuẩn SDXL:
    - Quy tắc nghiêm ngặt: Tập trung vào 1 chủ thể duy nhất (tránh nhân bản 3 xe, méo hình).
    - Loại bỏ mô tả chi tiết bàn tay/ngón tay (chống lỗi AI vẽ nhiều ngón tay).
    - Bổ sung từ khóa nhiếp ảnh điện ảnh (35mm photograph, Kodak Portra, 8k, sharp focus).
    """
    clean_concept = visual_concept.strip() if visual_concept else ""
    clean_scene = scene_text.strip() if scene_text else ""

    if not api_key:
        sub_subj = clean_concept if clean_concept else clean_scene[:80]
        return f"A single subject inspired by {sub_subj}, award-winning 35mm cinematic photograph, authentic realism, 8k sharp focus"

    genai = init_gemini_client(api_key)
    if not genai:
        return f"A single subject inspired by {clean_scene[:60]}, award-winning 35mm cinematic photograph, authentic realism, 8k"

    try:
        clean_model = "gemini-2.5-flash"
        if "pro" in str(model_name).lower():
            clean_model = "gemini-2.5-pro"
        elif "lite" in str(model_name).lower():
            clean_model = "gemini-2.5-flash-lite"

        model = genai.GenerativeModel(clean_model)
        prompt = (
            "You are an expert Hollywood cinematography director and AI image prompt engineer.\n"
            "Transform the following Vietnamese scene and concept into a single, high-fidelity, ultra-photorealistic English prompt for Stable Diffusion XL.\n\n"
            "CRITICAL RULES TO AVOID AI ARTIFACTS AND DISTORTIONS:\n"
            "1. SINGLE SUBJECT ONLY: Focus strictly on ONE main subject or an atmospheric setting (e.g., 'a single sleek black vintage sedan parked', 'a solitary male detective seen in profile', 'an empty rain-slicked city avenue'). NEVER use plural nouns for main objects (avoid 'cars', 'people', 'buildings').\n"
            "2. PREVENT HAND & ANATOMY ERRORS: If a human is depicted, use medium shot, profile view, or dramatic silhouette. Never describe open hands or exposed fingers to prevent deformities.\n"
            "3. CINEMATIC REALISM: Use strong photographic keywords: 'award-winning 35mm film photography, Kodak Portra 400, crisp depth of field, natural lighting, photorealistic textures, master composition, 8k resolution, cinematic still'.\n"
            "4. AVOID SURREALISM: Do not include words like 'abstract', 'surreal', 'distorted', 'multiple', 'collage', 'concept art'.\n"
            "5. Under 35 English words. Output ONLY the raw prompt text without markdown, quotes or explanation.\n\n"
            f"Concept: {clean_concept}\nScene: {clean_scene}"
        )
        resp = model.generate_content(prompt)
        if resp and resp.text:
            cleaned = resp.text.strip().replace('"', '').replace('\n', ' ')
            return cleaned
    except Exception as e:
        print(f"ℹ️ Gemini visual prompt fallback: {e}")

    return f"A single subject inspired by {clean_concept if clean_concept else clean_scene[:60]}, award-winning 35mm cinematic photograph, photorealistic, 8k sharp focus"
