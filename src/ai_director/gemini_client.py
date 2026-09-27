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
    Sử dụng Gemini AI để tối ưu hóa mô tả phân cảnh thành English Prompt điện ảnh chuẩn SDXL.
    """
    if not api_key:
        fallback = f"{visual_concept if visual_concept else scene_text[:100]}, cinematic gothic documentary lighting, moody atmosphere, sharp focus, 8k"
        return fallback

    genai = init_gemini_client(api_key)
    if not genai:
        return scene_text[:100]

    try:
        clean_model = "gemini-2.5-flash"
        if "pro" in str(model_name).lower():
            clean_model = "gemini-2.5-pro"
        elif "lite" in str(model_name).lower():
            clean_model = "gemini-2.5-flash-lite"

        model = genai.GenerativeModel(clean_model)
        prompt = (
            "You are an award-winning cinematic director. Transform the following Vietnamese scene text and overall concept "
            "into a single, vivid, ultra-realistic English prompt for Stable Diffusion XL. Focus on camera angle, chiaroscuro lighting, "
            "dramatic atmosphere, textures, and photorealism. Keep it under 45 English words. Do not include markdown or explanations.\n\n"
            f"Concept: {visual_concept}\nScene: {scene_text}"
        )
        resp = model.generate_content(prompt)
        if resp and resp.text:
            return resp.text.strip().replace('"', '')
    except Exception as e:
        print(f"ℹ️ Gemini visual prompt fallback: {e}")

    return f"{visual_concept if visual_concept else scene_text[:80]}, cinematic mystery lighting, photorealistic, 8k"
