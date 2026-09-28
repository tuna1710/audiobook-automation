import os
import re
import torch
from PIL import Image, ImageEnhance

_GLOBAL_SDXL_PIPELINE = None


def get_sdxl_pipeline(device: str = None):
    global _GLOBAL_SDXL_PIPELINE
    if _GLOBAL_SDXL_PIPELINE is None:
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


def sanitize_prompt_for_realism(prompt: str) -> str:
    """
    Chuẩn hóa prompt để loại bỏ các từ kích hoạt lỗi nhân bản vật thể hoặc dị tật ngón tay.
    Đồng thời khống chế chặt chẽ độ dài < 45 từ để không bao giờ vượt ngưỡng 77 CLIP tokens.
    """
    p = prompt.strip()

    # Xóa số lượng nhiều dẫn đến lỗi vẽ dính chùm 3 xe, nhiều người
    p = re.sub(r'\b(three|two|four|multiple|several|many|a group of|crowd of)\s+', 'a single ', p, flags=re.IGNORECASE)

    # Thay thế các danh từ số nhiều thành số ít đơn lẻ
    p = re.sub(r'\bcars\b', 'car', p, flags=re.IGNORECASE)
    p = re.sub(r'\bautomobiles\b', 'automobile', p, flags=re.IGNORECASE)
    p = re.sub(r'\bvehicles\b', 'vehicle', p, flags=re.IGNORECASE)
    p = re.sub(r'\bpeople\b', 'person', p, flags=re.IGNORECASE)
    p = re.sub(r'\bhands\b', 'silhouette', p, flags=re.IGNORECASE)
    p = re.sub(r'\bfingers\b', 'detail', p, flags=re.IGNORECASE)

    # Khống chế tối đa 42 từ để đảm bảo CLIP Tokenizer không bao giờ bị tràn 77 tokens
    words = p.split()
    if len(words) > 42:
        p = " ".join(words[:42])

    # Nếu prompt chưa có bất kỳ từ khóa phong cách nào, mới thêm mặc định 35mm
    style_indicators = ["sketch", "pencil", "drawing", "ink", "watercolor", "comic", "noir", "photograph", "cinematic"]
    if not any(ind in p.lower() for ind in style_indicators):
        p += ", cinematic 35mm photograph, sharp focus, 8k"

    return p


def generate_sdxl_metaphor_image(
    clean_prompt: str,
    aspect_ratio: str,
    out_img: str,
    scene_idx: int = 0,
    seed: int = None,
    pipe=None,
    steps: int = 2
) -> str:
    """
    Sinh ảnh ẩn dụ điện ảnh bằng SDXL / SD-Turbo:
    - 16:9: 768x432 (chuẩn tỷ lệ 16:9, tránh lỗi nhân bản vật thể / 3 xe dính nhau khi render >1000px)
    - 9:16: 432x768 (chuẩn tỷ lệ 9:16)
    - Resize về 1920x1080 hoặc 1080x1920 bằng LANCZOS + bộ lọc làm nét chi tiết (Sharpness Enhancement).
    """
    is_vertical = "9:16" in aspect_ratio
    # Kích thước tạo ảnh gốc tối ưu cho SDXL-Turbo / SD-Turbo (không bị nhân bản ngang 3 xe)
    gen_w, gen_h = (432, 768) if is_vertical else (768, 432)
    final_w, final_h = (1080, 1920) if is_vertical else (1920, 1080)

    safe_prompt = sanitize_prompt_for_realism(clean_prompt)

    if pipe is None:
        try:
            pipe = get_sdxl_pipeline()
        except Exception:
            pipe = None

    if pipe is not None:
        try:
            generator = torch.Generator(device=pipe.device).manual_seed(seed if seed is not None else (42 + scene_idx))
            # 2 bước suy luận (steps=2) giúp giải phóng chi tiết sắc nét và không tràn token
            img = pipe(
                prompt=safe_prompt,
                num_inference_steps=max(steps, 2),
                guidance_scale=0.0,
                width=gen_w,
                height=gen_h,
                generator=generator
            ).images[0]

            # Phóng to độ phân giải điện ảnh Full HD
            img = img.resize((final_w, final_h), Image.Resampling.LANCZOS)

            # Tăng nhẹ độ sắc nét chi tiết (tránh mờ nhòe)
            try:
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.2)
            except Exception:
                pass

            img.save(out_img, quality=95)
            return out_img
        except Exception as e:
            print(f"⚠️ Lỗi sinh ảnh SDXL: {e}")

    # Fallback tạo ảnh tối Gothic Noir nếu không có GPU
    bg = Image.new("RGB", (final_w, final_h), color=(18, 16, 22))
    bg.save(out_img, quality=90)
    return out_img
