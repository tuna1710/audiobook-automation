import os
import torch
from PIL import Image

_GLOBAL_SDXL_PIPELINE = None

def get_sdxl_pipeline(device: str = None):
    global _GLOBAL_SDXL_PIPELINE
    if _GLOBAL_SDXL_PIPELINE is None:
        from diffusers import AutoPipelineForText2Image
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"⏳ Đang nạp mô hình SDXL-Turbo trên {device.upper()}...")
        try:
            _GLOBAL_SDXL_PIPELINE = AutoPipelineForText2Image.from_pretrained(
                "stabilityai/sdxl-turbo",
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                variant="fp16" if device == "cuda" else None
            )
            _GLOBAL_SDXL_PIPELINE.to(device)
            print("✅ SDXL-Turbo đã sẵn sàng hoạt động!")
        except Exception as e:
            print(f"⚠️ Chuyển fallback sang sd-turbo: {e}")
            _GLOBAL_SDXL_PIPELINE = AutoPipelineForText2Image.from_pretrained(
                "stabilityai/sd-turbo",
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                variant="fp16" if device == "cuda" else None
            )
            _GLOBAL_SDXL_PIPELINE.to(device)
            print("✅ SD-Turbo đã sẵn sàng hoạt động!")
    return _GLOBAL_SDXL_PIPELINE

def generate_sdxl_metaphor_image(clean_prompt: str, aspect_ratio: str, out_img: str, scene_idx: int = 0, seed: int = None, pipe=None) -> str:
    """
    Sinh ảnh ẩn dụ điện ảnh bằng SDXL / SD-Turbo:
    - 16:9: 1152x640 resize về 1920x1080
    - 9:16: 640x1152 resize về 1080x1920
    """
    is_vertical = "9:16" in aspect_ratio
    gen_w, gen_h = (640, 1152) if is_vertical else (1152, 640)
    final_w, final_h = (1080, 1920) if is_vertical else (1920, 1080)

    safe_prompt = clean_prompt.strip()
    words = safe_prompt.split()
    if len(words) > 50:
        safe_prompt = " ".join(words[:50])

    if pipe is None:
        try:
            pipe = get_sdxl_pipeline()
        except Exception:
            pipe = None

    if pipe is not None:
        try:
            generator = torch.Generator(device=pipe.device).manual_seed(seed if seed else 42 + scene_idx)
            img = pipe(
                prompt=safe_prompt,
                num_inference_steps=1,
                guidance_scale=0.0,
                width=gen_w,
                height=gen_h,
                generator=generator
            ).images[0]
            img = img.resize((final_w, final_h), Image.Resampling.LANCZOS)
            img.save(out_img, quality=95)
            return out_img
        except Exception as e:
            print(f"⚠️ Lỗi sinh ảnh SDXL: {e}")

    # Fallback tạo ảnh tối Gothic Noir
    bg = Image.new("RGB", (final_w, final_h), color=(18, 16, 22))
    bg.save(out_img, quality=90)
    return out_img
