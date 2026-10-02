import os
from typing import Dict, Any

# Thẻ tags mặc định cho kênh Nỗi Sợ AudioBook (Trinh thám & Kinh dị Gothic)
DEFAULT_TAGS = (
    "trinh thám, kinh dị gothic, edgar allan poe, sherlock holmes, "
    "noi so audiobook, sach noi kinh di, vu an bi an, truyen trinh tham kinh dien"
)

# ==============================================================================
# HỆ THỐNG HỒ SƠ ĐA KÊNH 1-CLICK (MULTI-CHANNEL PRESET PROFILES) V20.0
# Cho phép 1 click đổi toàn bộ: Mỹ thuật SDXL, AI Đạo Diễn, Giọng đọc, Thẻ Tags & SEO
# ==============================================================================
CHANNEL_PROFILES_PRESET: Dict[str, Dict[str, Any]] = {
    "🕯️ Trinh Thám & Kinh Dị Gothic (Kênh Nỗi Sợ AudioBook)": {
        "channel_name": "Nỗi Sợ AudioBook",
        "genre_role": "Đạo diễn Hình ảnh Điện ảnh (Cinematic Storyboard Director) chuyên nghiệp cho các tác phẩm Trinh Thám & Kinh Dị Gothic (Victorian Gothic Noir)",
        "visual_concept": "19th century Victorian Gothic atmosphere, dark moody chiaroscuro lighting, London foggy cobblestone alleys, cinematic mystery, 35mm film still, 8k",
        "style_suffix": ", victorian gothic noir, chiaroscuro lighting, 35mm film still, 8k photorealistic",
        "voice": "Thiền Tâm Đức",
        "tags": "Nỗi Sợ AudioBook, truyện trinh thám, kinh dị gothic, edgar allan poe, sherlock holmes, audio book trinh tham, truyen kinh di, vu an bi an, sach noi kinh di",
        "desc_template": "Audiobook kinh dị gothic & trinh thám tâm lý kinh điển - Kênh Nỗi Sợ AudioBook.\nCùng bước vào không gian u tối của những bí ẩn thế kỷ 19.\n\n#NoiSoAudioBook #TruyenTrinhTham #KinhDiGothic #Audiobook",
        "token_filename": "token.json",
        "fallback_keywords": [
            "detective in black coat",
            "brass lantern in fog",
            "dark victorian alley",
            "mysterious mansion at night",
            "shadowy silhouette in candlelight"
        ]
    },
    "🪷 Phật Pháp, Thiền Định & Chữa Lành Tâm Hồn": {
        "channel_name": "Phật Pháp & Thiền Định",
        "genre_role": "Đạo diễn Hình ảnh Nghệ thuật (Cinematic Spiritual Director) chuyên về Phật Giáo, Thiền Tịnh & Chữa Lành Tâm Hồn",
        "visual_concept": "Serene ancient Buddhist temple, peaceful morning mist, gentle warm golden sunlight, blooming lotus ponds, tranquil zen monastery, 8k photorealistic",
        "style_suffix": ", peaceful zen atmosphere, golden morning light, serene buddhist temple, cinematic 8k",
        "voice": "Thiền Tâm Đức",
        "tags": "phật pháp nhiệm màu, nghe pháp thoại, thiền định chữa lành, nhạc thiền an lạc, bài học phật dạy, buông bỏ muộn phiền, tĩnh tâm, sách nói tâm linh, an nhiên",
        "desc_template": "Kênh Phật Pháp & Thiền Định Chữa Lành - Những lời dạy sâu sắc giúp tâm an lạc, buông bỏ âu lo muộn phiền giữa dòng đời hối hả.\nKính chúc quý Phật tử và các bạn một ngày an lành, thân tâm thường lạc.\n\n#PhatPhap #ThienDinh #ChuaLanh #KinhPhat #NghePhapThoai #AnNhien",
        "token_filename": "token.json",
        "fallback_keywords": [
            "ancient buddhist pagoda with peaceful garden",
            "pink lotus blooming on clear water pond",
            "golden morning rays through misty pine trees",
            "zen rock garden with bamboo water fountain",
            "monk walking mindfully in tranquil monastery"
        ]
    },
    "⚔️ Lịch Sử, Cổ Trang & Huyền Sử Hào Hùng": {
        "channel_name": "Huyền Sử & Lịch Sử",
        "genre_role": "Đạo diễn Sử thi Điện ảnh (Epic Cinematic History Director) chuyên tái hiện Lịch Sử, Cổ Trang & Huyền Sử Chiến Trận",
        "visual_concept": "Epic cinematic historical battle, ancient Asian imperial citadel, majestic palace, brave warriors in detailed traditional armor, dramatic sunset smoke, 8k",
        "style_suffix": ", epic cinematic history, ancient citadel, dramatic golden hour smoke, 35mm film still, 8k",
        "voice": "Minh Triết",
        "tags": "lịch sử việt nam, huyền sử, cổ trang, chiến tranh cổ đại, danh tướng việt nam, sử ký hào hùng, truyện lịch sử, đại việt sử ký, anh hùng dân tộc",
        "desc_template": "Kênh Lịch Sử & Huyền Sử - Tái hiện những trang sử vàng chói lọi, những chiến công oanh liệt và cuộc đời của các bậc tiền nhân.\n\n#LichSuVietNam #HuyenSu #CoTrang #DanhTuong #KhamPhaLichSu",
        "token_filename": "token.json",
        "fallback_keywords": [
            "ancient imperial throne hall with golden dragons",
            "warriors in traditional armor carrying banners",
            "panoramic view of ancient stone fortress at dusk",
            "historical royal court assembly in lanterns",
            "heroic commander on horseback looking at mountains"
        ]
    },
    "🚀 Khoa Học, Vũ Trụ & Khám Phá Tri Thức": {
        "channel_name": "Khoa Học & Vũ Trụ",
        "genre_role": "Đạo diễn Phim Khoa Học Viễn Tưởng (Sci-Fi & Astronomy Director) chuyên về Vũ Trụ, Khoa Học & Công Nghệ Tương Lai",
        "visual_concept": "Deep space cosmos, glowing colorful nebula, interstellar starships, mysterious alien exoplanets, futuristic cyberpunk city, ultra-detailed 8k",
        "style_suffix": ", deep space cosmos, cinematic sci-fi photorealism, glowing nebula, volumetric lighting, 8k",
        "voice": "Mai Anh",
        "tags": "khám phá vũ trụ, khoa học viễn tưởng, thiên văn học, bí ẩn vũ trụ, công nghệ tương lai, người ngoài hành tinh, hố đen, du hành không gian, khoa học kỳ thú",
        "desc_template": "Kênh Khám Phá Vũ Trụ & Khoa Học - Hành trình mở rộng tri thức về những bí ẩn kỳ vĩ ngoài không gian và bước tiến tương lai nhân loại.\n\n#KhamPhaVuTru #KhoaHoc #ThienVanHoc #CongNgheTuongLai #VuTruBaoLa",
        "token_filename": "token.json",
        "fallback_keywords": [
            "spiral galaxy with glowing interstellar dust",
            "futuristic spaceship exploring alien planet rings",
            "astronaut looking at Earth from orbital station",
            "high-tech futuristic control room holographic screens",
            "massive supermassive black hole with accretion disk"
        ]
    },
    "🌿 Bài Học Cuộc Sống, Tâm Lý & Podcast": {
        "channel_name": "Bài Học Cuộc Sống",
        "genre_role": "Đạo diễn Điện ảnh Đời Thường & Tâm Lý (Cinematic Lifestyle & Drama Director) chuyên về Câu Chuyện Cuộc Sống, Tâm Lý & Podcast",
        "visual_concept": "Warm modern aesthetic lifestyle, contemplative person by rainy window, cozy cafe with books and coffee, soft interior lighting, cinematic photography",
        "style_suffix": ", warm modern aesthetic, emotional cinematic lighting, shallow depth of field, 35mm photography, 8k",
        "voice": "Thanh Bình",
        "tags": "bài học cuộc sống, phát triển bản thân, podcast suy ngẫm, tâm lý học, động lực thành công, triết lý sống, thay đổi tư duy, hạt giống tâm hồn",
        "desc_template": "Kênh Bài Học Cuộc Sống & Podcast Phát Triển Bản Thân - Những câu chuyện sâu sắc giúp tiếp thêm năng lượng tích cực và định hướng tương lai.\n\n#BaiHocCuocSong #PhatTrienBanThan #PodcastSuyNgam #DongLucMoiNgay",
        "token_filename": "token.json",
        "fallback_keywords": [
            "person sitting thoughtfully by rainy cafe window",
            "cozy wooden desk with steaming coffee and open journal",
            "walking alone on autumn path with golden falling leaves",
            "warm ambient room with soft reading lamp and bookshelf",
            "peaceful sunset view over calm modern city skyline"
        ]
    },
    "🧚 Cổ Tích, Thần Thoại & Truyện Dân Gian": {
        "channel_name": "Cổ Tích & Thần Thoại",
        "genre_role": "Đạo diễn Hoạt Họa & Cổ Tích Thần Tiên (Fairy Tale & Fantasy Director) chuyên về Truyện Cổ Tích, Thần Thoại & Thế Giới Diệu Kỳ",
        "visual_concept": "Enchanted magical fairy tale forest, glowing fireflies, ancient mystical oak tree, whimsical cottage with warm window glow, Disney Pixar cinematic lighting, 8k",
        "style_suffix": ", magical fantasy atmosphere, whimsical fairy tale art, glowing enchanted lighting, vibrant 8k",
        "voice": "Thùy Dung",
        "tags": "truyện cổ tích, thần thoại, truyện dân gian, cổ tích việt nam, thế giới cổ tích, truyện thiếu nhi, cổ tích chọn lọc, kể chuyện bé nghe",
        "desc_template": "Kênh Truyện Cổ Tích & Thần Thoại - Đưa bạn bước vào thế giới diệu kỳ của những câu chuyện thần tiên bất hủ và bài học nhân văn sâu sắc.\n\n#TruyenCoTich #ThanThoai #DanGian #TheGioiCoTich #KeChuyen",
        "token_filename": "token.json",
        "fallback_keywords": [
            "magical enchanted forest with glowing mushrooms",
            "fairy tale cottage in wildflower meadow with smoking chimney",
            "grand mystical castle atop green floating hill",
            "sparkling magical brook with colorful river stones",
            "ancient wise talking tree with smiling wooden face"
        ]
    },
    "⚙️ Kênh Tùy Chỉnh (Custom Profile Của Riêng Bạn)": {
        "channel_name": "Kênh Tùy Chỉnh",
        "genre_role": "Đạo diễn Hình ảnh Điện ảnh (Cinematic Visual Storyboard Director)",
        "visual_concept": "Cinematic photorealistic 8k, detailed atmosphere, professional lighting, 35mm film still",
        "style_suffix": ", cinematic photorealistic, dramatic professional lighting, 8k",
        "voice": "Thiền Tâm Đức",
        "tags": "audiobook, podcast, video truyen, chia se kien thuc",
        "desc_template": "Chào mừng bạn đến với kênh! Đừng quên bấm Đăng Ký để theo dõi các video mới nhất.\n\n#Audiobook #Podcast",
        "token_filename": "token.json",
        "fallback_keywords": [
            "cinematic landscape at sunrise with golden light",
            "portrait of thoughtful person in soft ambient light",
            "detailed close-up shot with beautiful bokeh depth of field",
            "wide scenic view with dramatic sky and mountains"
        ]
    }
}


def get_channel_profile(profile_name: str) -> Dict[str, Any]:
    """Lấy dữ liệu cấu hình hồ sơ kênh."""
    if not profile_name or profile_name not in CHANNEL_PROFILES_PRESET:
        profile_name = "🕯️ Trinh Thám & Kinh Dị Gothic (Kênh Nỗi Sợ AudioBook)"
    return CHANNEL_PROFILES_PRESET[profile_name]


def get_channel_token_file(channel_profile: str = "", default_token: str = "token.json") -> str:
    """
    Tìm file token OAuth YouTube chung cho toàn bộ hệ thống (không cố định theo từng kênh).
    Tự động quét các file token hợp lệ ở thư mục hiện tại, /content, Google Drive (/content/drive/MyDrive).
    """
    search_dirs = [
        ".",
        "/content",
        "/content/drive/MyDrive",
        "configs",
        os.path.expanduser("~")
    ]
    # 1. Quét các file token chung chuẩn
    for fname in ["token.json", "youtube_token.json", default_token]:
        for d in search_dirs:
            cand = os.path.join(d, fname)
            if os.path.exists(cand):
                return cand

    # 2. Hỗ trợ nhận diện file token riêng nếu có sẵn
    if channel_profile and channel_profile in CHANNEL_PROFILES_PRESET:
        custom_name = CHANNEL_PROFILES_PRESET[channel_profile].get("token_filename")
        if custom_name:
            for d in search_dirs:
                cand = os.path.join(d, custom_name)
                if os.path.exists(cand):
                    return cand

    return default_token
