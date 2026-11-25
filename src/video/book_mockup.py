import os
import numpy as np
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance


# Các bối cảnh bàn cafe, bàn trà, bàn đọc sách trống tự nhiên để đặt sách 3D
BOOK_SCENE_BACKGROUNDS: List[str] = [
    "empty rustic wooden cafe table with a steaming cup of latte coffee on the left, soft morning sunlight through window, warm bokeh cafe background, slightly angled top-down view, 8k photorealistic",
    "minimalist wooden tea table with a traditional ceramic teapot and small teacup on the side, soft warm afternoon sunlight, peaceful zen atmosphere, empty table center, 8k photorealistic",
    "cozy wooden reading desk near sunlit window with small green plant and warm desk lamp, empty wooden surface in foreground, shallow depth of field, 35mm photography, 8k",
    "warm oak library table with soft golden candlelight and blurred bookshelves in background, empty wooden tabletop space in center, cinematic editorial lighting, 8k photorealistic"
]


def _solve_perspective_coeffs(src_pts: List[Tuple[float, float]], dst_pts: List[Tuple[float, float]]) -> Tuple[float, ...]:
    """
    Tính ma trận 8 tham số cho Image.Transform.PERSPECTIVE của Pillow.
    Pillow ánh xạ ngược từ dst (ảnh đích) -> src (ảnh nguồn).
    """
    matrix = []
    for (sx, sy), (dx, dy) in zip(src_pts, dst_pts):
        matrix.append([dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy])
        matrix.append([0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy])
    a = np.array(matrix, dtype=np.float64)
    b = np.array([c for pt in src_pts for c in pt], dtype=np.float64)
    res = np.linalg.solve(a, b)
    return tuple(res.tolist())


def create_3d_book_layer(cover_path: str, target_h: int = 720) -> Image.Image:
    """
    Biến ảnh bìa 2D thành lớp sách bìa cứng 3D có gáy/mép trang giấy và ánh sáng nhẹ.
    """
    cover = Image.open(cover_path).convert("RGBA")
    cw, ch = cover.size
    aspect = cw / max(1, ch)
    new_h = max(200, int(target_h))
    new_w = max(140, int(new_h * aspect))
    cover = cover.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Độ dày giả lập của mép trang giấy bên phải và cạnh dưới
    thickness_x = max(12, int(new_w * 0.045))
    thickness_y = max(10, int(new_h * 0.025))

    canvas = Image.new("RGBA", (new_w + thickness_x, new_h + thickness_y), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Vẽ khối trang giấy bên phải (màu kem ấm có sọc nhẹ)
    right_poly = [
        (new_w - 2, 0),
        (new_w + thickness_x, thickness_y),
        (new_w + thickness_x, new_h + thickness_y),
        (new_w - 2, new_h)
    ]
    draw.polygon(right_poly, fill=(235, 226, 208, 255))

    # Vẽ khối trang giấy cạnh dưới (tối hơn một chút để tạo khối 3D)
    bottom_poly = [
        (0, new_h - 2),
        (new_w - 2, new_h - 2),
        (new_w + thickness_x, new_h + thickness_y),
        (thickness_x, new_h + thickness_y)
    ]
    draw.polygon(bottom_poly, fill=(205, 194, 174, 255))

    # Dán bìa chính lên trên
    canvas.paste(cover, (0, 0), cover)

    # Vẽ đường rãnh gáy sách nhẹ ở mép trái bìa
    spine_w = max(4, int(new_w * 0.025))
    spine_overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(spine_overlay)
    s_draw.rectangle([spine_w, 0, spine_w + 3, new_h], fill=(0, 0, 0, 45))
    s_draw.rectangle([0, 0, spine_w, new_h], fill=(255, 255, 255, 18))
    canvas = Image.alpha_composite(canvas, spine_overlay)

    return canvas


def compose_book_on_scene(
    cover_path: str,
    bg_image_path: str,
    output_path: str,
    target_size: Tuple[int, int] = (1920, 1080),
    layout_idx: int = 0
) -> str:
    """
    Ghép cuốn sách 3D nằm nghiêng phối cảnh tự nhiên lên ảnh nền (bàn cafe, bàn trà, bàn đọc sách)
    kèm bóng đổ mềm và cân bằng ánh sáng ấm.
    """
    vid_w, vid_h = target_size
    is_vertical = vid_h > vid_w

    # 1. Chuẩn hóa ảnh nền đúng tỷ lệ khung hình (center crop)
    if bg_image_path and os.path.exists(bg_image_path):
        bg = Image.open(bg_image_path).convert("RGBA")
        bw, bh = bg.size
        scale = max(vid_w / max(1, bw), vid_h / max(1, bh))
        rw, rh = int(bw * scale), int(bh * scale)
        bg = bg.resize((rw, rh), Image.Resampling.LANCZOS)
        left = (rw - vid_w) // 2
        top = (rh - vid_h) // 2
        bg = bg.crop((left, top, left + vid_w, top + vid_h))
    else:
        # Fallback nền gỗ ấm nếu chưa có ảnh nền
        bg = Image.new("RGBA", (vid_w, vid_h), (68, 48, 34, 255))

    # 2. Tạo lớp sách 3D
    book_layer = create_3d_book_layer(cover_path, target_h=int(min(vid_w, vid_h) * 0.65))
    lw, lh = book_layer.size
    src_pts = [(0.0, 0.0), (float(lw), 0.0), (float(lw), float(lh)), (0.0, float(lh))]

    # 3. Các góc phối cảnh nằm trên mặt bàn (tọa độ chuẩn hóa theo khung hình)
    if is_vertical:
        # Khung 9:16 (TikTok / Shorts): đặt sách ở vùng giữa-dưới tránh tiêu đề trên và sub dưới
        layouts = [
            # Nằm nghiêng nhẹ giữa bàn
            [(0.24, 0.36), (0.76, 0.39), (0.86, 0.72), (0.16, 0.69)],
            # Nằm chéo hướng từ trái sang phải
            [(0.18, 0.39), (0.70, 0.35), (0.84, 0.68), (0.24, 0.73)],
            # Nằm lệch phải (chừa bên trái cho tách cafe/trà)
            [(0.32, 0.37), (0.84, 0.40), (0.90, 0.71), (0.26, 0.68)],
        ]
    else:
        # Khung 16:9 (YouTube): đặt sách ở nửa phải hoặc trung tâm mặt bàn
        layouts = [
            # Nằm nghiêng tự nhiên bên phải bàn (chừa bên trái cho tách cafe/trà)
            [(0.50, 0.25), (0.80, 0.29), (0.86, 0.80), (0.44, 0.74)],
            # Nằm chéo giữa bàn hướng về người xem
            [(0.36, 0.26), (0.68, 0.23), (0.76, 0.76), (0.30, 0.80)],
            # Nằm nghiêng bên trái bàn
            [(0.18, 0.28), (0.48, 0.24), (0.55, 0.75), (0.14, 0.80)],
        ]

    norm_pts = layouts[layout_idx % len(layouts)]
    dst_pts = [(px * vid_w, py * vid_h) for (px, py) in norm_pts]

    coeffs = _solve_perspective_coeffs(src_pts, dst_pts)
    warped_book = book_layer.transform((vid_w, vid_h), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC)

    # 4. Tạo bóng đổ mềm trên mặt bàn dựa trên alpha channel của sách
    alpha = warped_book.split()[3]
    shadow = Image.new("RGBA", (vid_w, vid_h), (12, 8, 5, 0))
    shadow_alpha = alpha.point(lambda p: int(p * 0.58))
    shadow.putalpha(shadow_alpha)

    # Dịch bóng lệch xuống dưới và sang phải nhẹ theo ánh sáng cửa sổ
    dx = max(10, int(vid_w * 0.012))
    dy = max(14, int(vid_h * 0.018))
    shifted_shadow = Image.new("RGBA", (vid_w, vid_h), (0, 0, 0, 0))
    shifted_shadow.paste(shadow, (dx, dy))
    shifted_shadow = shifted_shadow.filter(ImageFilter.GaussianBlur(radius=max(12, int(vid_w * 0.012))))

    # 5. Hòa trộn ánh sáng nhẹ để sách tiệp màu ấm với không gian cafe/trà
    warm_book = ImageEnhance.Brightness(warped_book).enhance(0.96)
    warm_book = ImageEnhance.Contrast(warm_book).enhance(1.03)

    composed = Image.alpha_composite(bg, shifted_shadow)
    composed = Image.alpha_composite(composed, warm_book)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    composed.convert("RGB").save(output_path, quality=95)
    return output_path
