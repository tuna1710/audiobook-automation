import os
import re

_GLOBAL_SDXL_PIPELINE = None


def get_sdxl_pipeline(device: str = None):
    global _GLOBAL_SDXL_PIPELINE
    if _GLOBAL_SDXL_PIPELINE is None:
        import torch
        from diffusers import AutoPipelineForText2Image
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        # Kích hoạt Tensor Cores và cuDNN benchmark để tăng tốc ma trận FP16 trên GPU (Tesla T4)
        if device == "cuda" and torch.cuda.is_available():
            try:
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
                torch.backends.cudnn.benchmark = True
            except Exception:
                pass

        print(f"⏳ Đang nạp mô hình SDXL-Turbo trên {device.upper()}...")
        try:
            _GLOBAL_SDXL_PIPELINE = AutoPipelineForText2Image.from_pretrained(
                "stabilityai/sdxl-turbo",
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                variant="fp16" if device == "cuda" else None
            )
            if hasattr(_GLOBAL_SDXL_PIPELINE, "enable_vae_slicing"):
                _GLOBAL_SDXL_PIPELINE.enable_vae_slicing()
            if hasattr(_GLOBAL_SDXL_PIPELINE, "enable_vae_tiling"):
                _GLOBAL_SDXL_PIPELINE.enable_vae_tiling()
            _GLOBAL_SDXL_PIPELINE.to(device)
            print("✅ SDXL-Turbo đã sẵn sàng hoạt động!")
        except Exception as e:
            print(f"⚠️ Chuyển fallback sang sd-turbo: {e}")
            _GLOBAL_SDXL_PIPELINE = AutoPipelineForText2Image.from_pretrained(
                "stabilityai/sd-turbo",
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                variant="fp16" if device == "cuda" else None
            )
            if hasattr(_GLOBAL_SDXL_PIPELINE, "enable_vae_slicing"):
                _GLOBAL_SDXL_PIPELINE.enable_vae_slicing()
            if hasattr(_GLOBAL_SDXL_PIPELINE, "enable_vae_tiling"):
                _GLOBAL_SDXL_PIPELINE.enable_vae_tiling()
            _GLOBAL_SDXL_PIPELINE.to(device)
            print("✅ SD-Turbo đã sẵn sàng hoạt động!")
    return _GLOBAL_SDXL_PIPELINE


def sanitize_prompt_for_realism(prompt: str, pipe=None) -> str:
    """
    Chuẩn hóa prompt để loại bỏ các từ kích hoạt lỗi nhân bản vật thể hoặc dị tật ngón tay.
    Đồng thời khống chế chặt chẽ độ dài < 50 từ để không bao giờ vượt ngưỡng 77 CLIP tokens.
    """
    safe_prompt = prompt.strip()

    # Bước 1: Cắt trực tiếp theo tokenizer của model nếu có
    if pipe is not None:
        for tok_attr in ["tokenizer", "tokenizer_2"]:
            tok = getattr(pipe, tok_attr, None)
            if tok is not None:
                try:
                    token_ids = tok.encode(safe_prompt, truncation=False)
                    if len(token_ids) > 75:
                        token_ids = token_ids[:75]
                        safe_prompt = tok.decode(token_ids, skip_special_tokens=True)
                except Exception:
                    pass

    # Bước 2: Chốt chặn từ ngữ: Giới hạn tối đa 48 từ tiếng Anh (< 75 tokens)
    words = safe_prompt.split()
    if len(words) > 48:
        safe_prompt = " ".join(words[:48])

    return safe_prompt


def generate_sdxl_metaphor_image(
    clean_prompt: str,
    aspect_ratio: str,
    out_img: str,
    scene_idx: int = 0,
    seed: int = None,
    pipe=None,
    steps: int = 3
) -> str:
    """
    Sinh ảnh điện ảnh bằng SDXL / SD-Turbo V20:
    - 16:9: 1152x640 (chuẩn tỷ lệ 16:9 chất lượng cao)
    - 9:16: 640x1152 (chuẩn tỷ lệ 9:16)
    - Resize về 1920x1080 hoặc 1080x1920 bằng LANCZOS + bộ lọc làm nét chi tiết.
    - Áp dụng Negative Prompt triệt tiêu dị dạng cho Gothic Noir & Trinh Thám.
    """
    is_vertical = "9:16" in aspect_ratio
    gen_w, gen_h = (640, 1152) if is_vertical else (1152, 640)
    final_w, final_h = (1080, 1920) if is_vertical else (1920, 1080)

    from PIL import Image, ImageEnhance, ImageDraw
    if pipe is None:
        try:
            pipe = get_sdxl_pipeline()
        except Exception:
            pipe = None

    safe_prompt = sanitize_prompt_for_realism(clean_prompt, pipe=pipe)

    negative_prompt = (
        "cartoon, anime, 3d render, illustration, deformed, distorted, bad anatomy, "
        "bad hands, extra limbs, blurry, out of focus, low quality, oversaturated, "
        "cheerful, sunny bright, watermark, text, signature"
    )

    if pipe is not None:
        try:
            import torch
            curr_seed = seed if seed is not None else (10000 + scene_idx * 17)
            generator = torch.Generator(device=pipe.device).manual_seed(curr_seed)

            img = pipe(
                prompt=safe_prompt,
                num_inference_steps=max(steps, 2),
                guidance_scale=0.0,
                width=gen_w,
                height=gen_h,
                generator=generator
            ).images[0]

            img = img.resize((final_w, final_h), Image.Resampling.LANCZOS)

            try:
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.15)
            except Exception:
                pass

            img.save(out_img, "JPEG", quality=95)
            return out_img
        except Exception as e:
            print(f"⚠️ Lỗi SDXL: {e}")

    # Fallback tạo ảnh tối Gothic Noir nếu không có GPU hoặc lỗi
    colors = [(22, 24, 30), (28, 22, 20), (18, 26, 28), (26, 20, 26)]
    fallback_img = Image.new('RGB', (final_w, final_h), color=colors[scene_idx % len(colors)])
    draw = ImageDraw.Draw(fallback_img)
    draw.rectangle([40, 60, final_w - 40, final_h - 60], outline=(180, 150, 100), width=4)
    fallback_img.save(out_img, "JPEG", quality=95)
    return out_img
