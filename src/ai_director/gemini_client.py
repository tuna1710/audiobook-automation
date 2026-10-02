import os
import re
import time
import json
import urllib.parse
from typing import List, Optional, Dict, Any, Tuple

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


def extract_gemini_candidate_text(candidates: list) -> str:
    """
    Trích xuất nội dung văn bản chuẩn xác từ danh sách candidates của Gemini API.
    Tự động lọc bỏ các khối 'thought' (suy nghĩ nội bộ / chain-of-thought) của Gemini 3.x & 2.5
    để trả về 100% kết quả thực sự (JSON hoặc Subtitles).
    """
    if not candidates or not isinstance(candidates, list):
        return ""
    cand = candidates[0]
    if not isinstance(cand, dict):
        return ""
    content = cand.get("content", {})
    parts = content.get("parts", []) if isinstance(content, dict) else []
    if not parts:
        return ""

    # 1. Thu thập tất cả các part KHÔNG phải suy nghĩ nội bộ (thought != True)
    non_thought_parts = []
    for p in parts:
        if isinstance(p, dict) and not p.get("thought", False):
            t = p.get("text", "")
            if t:
                non_thought_parts.append(t)
    if non_thought_parts:
        return "".join(non_thought_parts).strip()

    # 2. Nếu không tìm thấy non-thought part, thu thập toàn bộ text
    all_parts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")]
    return "".join(all_parts).strip()


def clean_gemini_model_name(raw_model_str: str, default_model: str = "gemini-3.5-flash-lite") -> str:
    """
    Chuẩn hóa tên model Gemini từ giao diện Gradio thành tên model API chính thức mới nhất theo tài liệu Google AI (Thế hệ Gemini 3).
    Hỗ trợ 100% các endpoint Active & Stable: gemini-3.5-flash-lite, gemini-3.1-flash-lite, gemini-3.5-flash, gemini-3.6-flash, gemini-3.7-flash, gemini-3.8-flash.
    Loại bỏ hoàn toàn các model đã tắt hoặc bị chặn 404.
    """
    if not raw_model_str:
        return default_model
    s = str(raw_model_str).lower().strip()
    if '3.8' in s:
        return 'gemini-3.8-flash'
    if '3.7' in s:
        return 'gemini-3.7-flash'
    if '3.6' in s:
        return 'gemini-3.6-flash'
    if '3.5-flash-lite' in s or ('3.5' in s and 'lite' in s):
        return 'gemini-3.5-flash-lite'
    if '3.1-flash-lite' in s or ('3.1' in s and 'lite' in s) or '3.1' in s:
        return 'gemini-3.1-flash-lite'
    if '3.5' in s:
        return 'gemini-3.5-flash'
    if '3-flash' in s:
        return 'gemini-3-flash-preview'
    if '2.5-flash' in s:
        return 'gemini-2.5-flash'
    if 'flash-lite' in s or 'lite' in s:
        return 'gemini-3.5-flash-lite'
    if 'flash' in s:
        return 'gemini-3.5-flash-lite'
    return default_model


def parse_all_in_one_gemini_response(raw_text: str) -> Tuple[Dict[int, str], List[Tuple[float, str]]]:
    """
    Bộ giải mã JSON siêu cấp cho All-in-One Gemini Director.
    Tự động bóc tách cả mảng scenes và chapters mà không quăng ngoại lệ.
    Hỗ trợ các khối markdown ```json ... ``` hoặc JSON lồng trong văn bản tự nhiên.
    """
    if not raw_text or not raw_text.strip():
        return {}, []

    clean = raw_text.strip()

    # Tìm block JSON nằm giữa ```json ... ``` hoặc giữa { ... }
    json_target = clean
    m_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, re.DOTALL)
    if m_block:
        json_target = m_block.group(1).strip()
    else:
        s_idx = clean.find('{')
        e_idx = clean.rfind('}')
        if s_idx != -1 and e_idx != -1 and e_idx > s_idx:
            json_target = clean[s_idx:e_idx + 1].strip()

    def sec_to_float(val):
        try:
            if isinstance(val, (int, float)):
                return float(val)
            s_val = str(val).strip()
            if ':' in s_val:
                parts = s_val.split(':')
                if len(parts) == 2:
                    return float(parts[0]) * 60 + float(parts[1])
                elif len(parts) == 3:
                    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            return float(s_val)
        except Exception:
            return 0.0

    scenes_dict = {}
    chapters_list = []

    # 1. Parse JSON chuẩn
    try:
        data = json.loads(json_target)
        if isinstance(data, dict):
            for ch in data.get('chapters', []):
                t = sec_to_float(ch.get('time', 0))
                title = str(ch.get('title', '')).strip()
                if title:
                    chapters_list.append((t, title))
            for sc in data.get('scenes', []):
                idx = int(sc.get('index', 0))
                p = str(sc.get('prompt', '')).strip()
                if idx > 0 and p:
                    scenes_dict[idx] = p
            if scenes_dict:
                return scenes_dict, chapters_list
    except Exception:
        pass

    # 2. Regex fallback quét scenes
    p_scenes = r'\{\s*"index"\s*:\s*(\d+)\s*,\s*"prompt"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"'
    for m in re.finditer(p_scenes, clean, re.DOTALL):
        idx = int(m.group(1))
        p = m.group(2).replace('\"', '"').replace('\n', ' ').strip()
        scenes_dict[idx] = p

    # 3. Regex fallback quét chapters
    p_chap = r'\{\s*"time"\s*:\s*([^,}\s]+)\s*,\s*"title"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"'
    for m in re.finditer(p_chap, clean, re.DOTALL):
        t = sec_to_float(m.group(1).replace('"', '').strip())
        title = m.group(2).replace('\"', '"').strip()
        if title:
            chapters_list.append((t, title))

    return scenes_dict, chapters_list


def parse_gemini_json_response(raw_text: str) -> dict:
    """Tương thích ngược với hàm parse_gemini_json_response cũ."""
    sc, _ = parse_all_in_one_gemini_response(raw_text)
    return sc


def analyze_sentence_to_detective_prompt(
    sentence_text: str,
    cut_part: int,
    cut_index: int,
    topic_title: str = "",
    visual_concept: str = "",
    recent_concepts: list = None,
    channel_profile: str = ""
) -> str:
    """
    Chế độ Dự phòng Thông minh (Smart Fallback Engine) Chuẩn Trinh Thám & Gothic Noir.
    100% bóc tách từ khóa hung khí, hiện trường, nhân vật, bối cảnh trực tiếp từ câu sub.
    Loại bỏ sạch 100% từ khóa thiền định / chữa lành lạc đề.
    Nếu là hồ sơ kênh khác, sử dụng kho từ khóa của hồ sơ đó.
    """
    from ..pipeline.channel_profiles import get_channel_profile
    prof = get_channel_profile(channel_profile) if channel_profile else {}
    if prof and "Gothic" not in channel_profile and "Trinh Thám" not in channel_profile and "Nỗi Sợ" not in channel_profile:
        fallback_kws = prof.get("fallback_keywords", [])
        p_suffix = prof.get("style_suffix", "")
        if fallback_kws:
            kw = fallback_kws[cut_index % len(fallback_kws)]
            v_desc = visual_concept[:60] if visual_concept else prof.get("visual_concept", "")[:60]
            return f"Cinematic scene of {kw}, atmospheric lighting, visual setting: {v_desc}{p_suffix}"

    clean_txt = sentence_text.lower()
    if recent_concepts is None:
        recent_concepts = []

    semantic_map = [
        # 1. Hung khí & Nguy hiểm (Ưu tiên nhận diện đồ vật cụ thể)
        (["dao", "súng", "hung khí", "đạn", "đâm", "bắn", "vũ khí", "lưỡi dao", "khẩu súng", "thuốc độc", "độc dược", "bột trắng", "lọ thuốc"],
         "extreme close-up of antique silver revolver and tarnished dagger resting on worn velvet desk beside spilled amber poison vial, dramatic candle light, 8k"),

        # 2. Thư từ, Mật mã, Nhật ký & Bằng chứng
        (["thư", "nhật ký", "tài liệu", "hồ sơ", "di chúc", "bức ảnh", "phong bì", "niêm phong", "chữ ký", "mật mã", "trang giấy", "bút mực"],
         "close-up of handwritten cryptic letter sealed with cracked crimson wax lying on dark mahogany desk beside extinguished cigar smoke, atmospheric 35mm"),

        # 3. Đồng hồ, Nửa đêm & Áp lực thời gian
        (["đồng hồ", "nửa đêm", "thời gian", "tích tắc", "chuông", "hồi hộp", "chờ đợi", "khoảnh khắc", "giây", "12 giờ"],
         "antique ornate grandfather clock pendulum swinging inside dark study, clock hands pointing exactly at midnight, dramatic chiaroscuro lighting"),

        # 4. Thám tử, Điều tra & Manh mối dấu vết
        (["thám tử", "kính lúp", "manh mối", "dấu vết", "dấu chân", "điều tra", "soi", "kiểm tra", "vân tay", "suy luận", "chứng cứ", "đèn bão"],
         "sharp silhouette of Victorian detective holding brass magnifying glass closely examining muddy footprints on carpet, dust motes in gaslight, 35mm photo"),

        # 5. Hiện trường vụ án, Thi thể & Vết máu
        (["chết", "thi thể", "xác chết", "máu", "vết máu", "ám sát", "sát hại", "giết", "tử thi", "nạn nhân", "nghi phạm", "tội ác", "hiện trường"],
         "Victorian crime scene inside dimly lit parlor with chalk outline and bloodstains on dark wooden floorboards, moody gaslamp chiaroscuro, 35mm film still"),

        # 6. Kiến trúc Gothic, Cửa, Cầu thang & Ngục tối
        (["cửa", "cầu thang", "hành lang", "phòng", "gác mái", "hầm", "ngục", "lâu đài", "biệt thự", "khóa", "chìa khóa", "két sắt", "cửa sổ", "rèm"],
         "eerie Victorian gothic mansion hallway with creaking wooden spiral staircase, cold moonlight streaming through arched stained-glass window, heavy shadows"),

        # 7. Bóng đen, Rình rập, Bước chân & Kinh hoàng
        (["bóng", "bóng đen", "bước chân", "tiếng động", "kinh hoàng", "sợ hãi", "rình rập", "đuổi theo", "trốn", "hắn", "kẻ sát nhân", "tiếng gõ", "tiếng thét"],
         "tall menacing shadowy silhouette in dark trench coat and top hat standing motionless under flickering gaslamp, intense psychological thriller"),

        # 8. Mưa đêm, Sương mù & Ngoại cảnh bí ẩn
        (["mưa", "đêm", "tối", "sương mù", "bão", "sấm sét", "nghĩa trang", "mộ", "bia mộ", "xe ngựa", "đường phố", "hẻm", "sông", "cầu", "tháp"],
         "deserted cobblestone London street enveloped in dense swirling night fog, glowing gas streetlamps, distant lone black horse carriage, gothic noir"),

        # 9. Nhà xác, Y tế cổ & Khám nghiệm
        (["bác sĩ", "khám nghiệm", "nhà xác", "bệnh viện", "thuốc", "y tế", "dụng cụ", "hộp sọ", "xương", "mổ", "băng ca"],
         "Victorian medical laboratory with glass specimen jars, vintage brass surgical instruments and dim green banker lamp, macabre gothic atmosphere")
    ]

    matched_concept = None
    for keywords, concept in semantic_map:
        if any(k in clean_txt for k in keywords):
            if concept not in recent_concepts[-3:]:
                matched_concept = concept
                break

    if not matched_concept:
        fallback_vault = [
            "dimly lit 19th century Victorian study with leather armchairs, dusty manuscripts and flickering green banker lamp, gothic noir, chiaroscuro",
            "mysterious shadowy silhouette of detective in trench coat holding brass lantern in foggy cobblestone alley at midnight, 35mm film",
            "antique wooden floorboards in dark bedroom with eerie moonlight streaming through arched window, gothic suspense",
            "close-up of intricate antique brass pocket watch resting on aged bloodstained telegram, dramatic shadows, 8k",
            "creepy Victorian gothic manor standing isolated on misty moor under cold full moon, dark cinematic atmosphere",
            "flickering candle flame casting grotesque distorted shadows against cracked stone cellar wall, macabre mystery",
            "heavy wrought-iron cemetery gates shrouded in dense swirling twilight fog, bare twisted dead trees",
            "detective magnifying glass examining mysterious muddy footprint on vintage wooden floor, moody chiaroscuro lighting",
            "half-open secret bookcase doorway revealing dark hidden spiral stone staircase leading down into blackness",
            "solitary oil lamp flickering in window of remote Victorian cottage on cliff edge overlooking crashing dark waves"
        ]
        available_fallbacks = [f for f in fallback_vault if f not in recent_concepts[-4:]]
        if not available_fallbacks:
            available_fallbacks = fallback_vault
        matched_concept = available_fallbacks[cut_index % len(available_fallbacks)]

    recent_concepts.append(matched_concept)

    if cut_part == 2:
        part2_angles = [
            f"dramatic low-angle cinematic perspective of {matched_concept}, intense moody atmosphere",
            f"extreme close-up macro detail of {matched_concept}, shallow depth of field, dust motes in gaslight",
            f"over-the-shoulder atmospheric POV shot of {matched_concept}, rich cinematic contrast",
            f"wide aerial view looking down at {matched_concept}, gothic composition"
        ]
        matched_concept = part2_angles[cut_index % len(part2_angles)]

    full_prompt = f"cinematic 35mm photograph of {matched_concept}, gothic noir, chiaroscuro lighting, 8k resolution"
    return " ".join(full_prompt.split()[:42])


# Alias tương thích ngược
analyze_sentence_to_metaphor_prompt = analyze_sentence_to_detective_prompt


def call_gemini_all_in_one_director(
    cuts: list,
    full_speech: str,
    topic_title: str,
    visual_concept: str,
    gemini_key: str,
    selected_model: str = "gemini-3.5-flash-lite",
    channel_profile: str = "🕯️ Trinh Thám & Kinh Dị Gothic (Kênh Nỗi Sợ AudioBook)"
) -> Tuple[Dict[int, str], List[Tuple[float, str]]]:
    """
    TỐI ƯU HÓA 1 LẦN GỌI DUY NHẤT (ALL-IN-ONE SINGLE REQUEST) - HỖ TRỢ GÓI MIỄN PHÍ:
    Sinh đồng thời:
    1. Prompts chi tiết bám sát 100% câu chữ từng cảnh (Subtitle-Locked Visuals, NO METAPHOR).
    2. Danh sách mốc YouTube Chapters chuẩn SEO từ các mốc thời gian thực tế.
    Tự động Fallback đa tầng qua các Model Free Tier ổn định nhất kèm Exponential Backoff Retry chống lỗi 503 / 429.
    """
    if not gemini_key or not gemini_key.strip():
        return {}, []

    import requests
    cleaned_key = gemini_key.strip().strip('"').strip("'").strip()
    clean_model = clean_gemini_model_name(selected_model, default_model="gemini-3.5-flash-lite")
    total_cuts = len(cuts)

    from ..pipeline.channel_profiles import get_channel_profile
    prof = get_channel_profile(channel_profile)
    genre_role = prof.get("genre_role", "Đạo diễn Hình ảnh Điện ảnh (Cinematic Storyboard Director)")
    active_concept = visual_concept if (visual_concept and len(visual_concept.strip()) > 5) else prof.get("visual_concept", "")
    profile_style_suffix = prof.get("style_suffix", ", cinematic photorealistic, 35mm film still, 8k photorealistic")

    print(f"🤖 Đang kết nối AI Đạo Diễn (Gemini {clean_model}) - Chế độ All-in-One (1 Request duy nhất cho {total_cuts} cảnh & Chapters)...")

    # Tối ưu kích thước batch: 45 cảnh/đợt (Tránh lỗi 503 quá tải máy chủ Google khi kịch bản dài)
    chunk_size = 45
    if total_cuts <= chunk_size:
        batches = [cuts]
    else:
        batches = [cuts[i:i + chunk_size] for i in range(0, total_cuts, chunk_size)]
        print(f"📦 Kịch bản dài ({total_cuts} cảnh): Chia làm {len(batches)} đợt gọi Gemini (tối ưu {chunk_size} cảnh/lần)...")

    all_prompts = {}
    all_chapters = []

    for b_idx, batch_cuts in enumerate(batches):
        if b_idx > 0:
            time.sleep(2.5)

        cuts_summary = []
        for c in batch_cuts:
            st_m = int(c["start"]) // 60
            st_s = int(c["start"]) % 60
            time_tag = f"{st_m:02d}:{st_s:02d}"
            cuts_summary.append(f'Cảnh {c["index"]} [{time_tag}]: "{c["text"]}"')

        formatted_cuts_text = "\n".join(cuts_summary)

        system_prompt = f"""Bạn là {genre_role}.
Nhiệm vụ của bạn:
1. Đọc danh sách các phân cảnh phụ đề dưới đây.
2. Xây dựng 5-8 Chương YouTube (Chapters) kịch tính chuẩn SEO tương ứng với mốc thời gian thực tế (chỉ cần tạo ở đợt đầu).
3. Với MỖI CÂU PHỤ ĐỀ, hãy viết 1 mô tả hình ảnh TẢ THỰC ĐIỆN ẢNH bằng tiếng Anh (15-25 từ) để sinh ảnh SDXL.

QUY TẮC BẮT BUỘC ĐỂ HÌNH ĐI CÙNG SUB 100%:
- TUYỆT ĐỐI KHÔNG DÙNG HÌNH ẨN DỤ (NO METAPHORS / NO ABSTRACT SYMBOLS).
- PHẢI TẢ THỰC TRỰC DIỆN: Câu phụ đề đang nói về ai, làm gì, đồ vật gì, ở đâu thì hình ảnh PHẢI THỂ HIỆN CHÍNH XÁC điều đó (Ví dụ: câu nói "Hắn rút khẩu súng lục bạc" -> "extreme close-up of a sinister man drawing an antique silver revolver, cold moonlight, chiaroscuro").
- Cấu trúc prompt SDXL: [Chủ thể & Hành động cụ thể đang diễn ra trong câu], [Góc máy: Close-up / POV / Over-the-shoulder / Low-angle], Victorian Gothic 19th Century setting, moody chiaroscuro lighting, 35mm cinematic film still, 8k.
- Duy trì tính nhất quán nhân vật và không gian gothic u ám.

TÁC PHẨM: {topic_title}
KHÔNG GIAN/CONCEPT CHỦ ĐẠO: {active_concept}

DANH SÁCH {len(batch_cuts)} PHÂN CẢNH PHỤ ĐỀ:
{formatted_cuts_text}

HÃY TRẢ VỀ ĐÚNG ĐỊNH DẠNG JSON SAU (không dùng markdown ```json):
{{
  "chapters": [
    {{"time": 0, "title": "Lời Mở Đầu & Hiện Trường Bí Ẩn"}},
    {{"time": {int(batch_cuts[min(len(batch_cuts)-1, 15)]['start'])}, "title": "Manh Mối Trong Đêm Tối"}}
  ],
  "scenes": [
    {{"index": {batch_cuts[0]["index"]}, "prompt": "a shadowy detective in black trenchcoat holding a brass lantern in foggy alley, 35mm film still, chiaroscuro, 8k"}},
    {{"index": {batch_cuts[-1]["index"]}, "prompt": "extreme close-up of terrified pale man with wide bloodshot eyes in shadows, 35mm photography"}}
  ]
}}"""

        target_models = [clean_model]
        for fm in ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.8-flash", "gemini-3-flash-preview", "gemini-2.5-flash"]:
            if fm not in target_models:
                target_models.append(fm)

        payload = {
            "contents": [{"parts": [{"text": system_prompt}]}],
            "generationConfig": {
                "maxOutputTokens": 8192,
                "responseMimeType": "application/json"
            }
        }

        batch_succeeded = False

        for model_name in target_models:
            if batch_succeeded:
                break
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={cleaned_key}"
            headers = {"Content-Type": "application/json"}

            max_retries = 3
            backoff_delays = [3.0, 6.0, 10.0]

            for attempt in range(max_retries):
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=65)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            raw_out = extract_gemini_candidate_text(candidates)
                            sc_dict, ch_list = parse_all_in_one_gemini_response(raw_out)
                            if sc_dict:
                                for c_idx, raw_p in sc_dict.items():
                                    p_clean = raw_p.strip()
                                    if "gothic" not in p_clean.lower() and "chiaroscuro" not in p_clean.lower():
                                        p_clean = f"Cinematic shot of {p_clean}{profile_style_suffix}"
                                    all_prompts[c_idx] = p_clean

                                if ch_list and not all_chapters:
                                    all_chapters = ch_list

                                batch_succeeded = True
                                print(f"  ✨ [Đợt {b_idx+1}/{len(batches)}] Thành công với model {model_name}: Đã sinh {len(sc_dict)} prompt bám sát phụ đề & {len(ch_list)} chapters!")
                                break
                            else:
                                print(f"  ⚠️ [Đợt {b_idx+1}/{len(batches)}] Model {model_name} trả về HTTP 200 nhưng cấu trúc JSON chưa khớp, chuyển sang model dự phòng...")
                                break
                    elif resp.status_code in [429, 503]:
                        if attempt < max_retries - 1:
                            wait_time = backoff_delays[attempt]
                            reason = "máy chủ Google quá tải (Mã 503)" if resp.status_code == 503 else "chạm giới hạn tạm thời (Mã 429)"
                            print(f"  ⏳ [Đợt {b_idx+1}/{len(batches)}] Model {model_name} {reason}. Thử lại lần {attempt+2}/{max_retries} sau {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        else:
                            print(f"  ⚠️ [Đợt {b_idx+1}/{len(batches)}] Model {model_name} vẫn bận sau {max_retries} lần thử (Mã {resp.status_code}). Chuyển model dự phòng...")
                            break
                    elif resp.status_code == 404:
                        print(f"  ⚠️ Model {model_name} không khả dụng (Mã 404). Chuyển model dự phòng...")
                        break
                    else:
                        print(f"  ⚠️ Model {model_name} phản hồi HTTP {resp.status_code}. Chuyển model dự phòng...")
                        break
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = backoff_delays[attempt]
                        time.sleep(wait_time)
                        continue
                    else:
                        break

        # Nếu cả đợt này tất cả model Gemini đều không phản hồi: Cứu hộ cục bộ từng cảnh
        if not batch_succeeded:
            print(f"  🛡️ [Đợt {b_idx+1}/{len(batches)}] Kích hoạt Smart Engine cứu hộ cho {len(batch_cuts)} cảnh theo Hồ Sơ Kênh...")
            for b_cut in batch_cuts:
                fb_p = analyze_sentence_to_detective_prompt(
                    b_cut.get("text", ""),
                    b_cut.get("part", 0),
                    b_cut.get("index", 1),
                    topic_title=topic_title,
                    visual_concept=active_concept,
                    channel_profile=channel_profile
                )
                all_prompts[b_cut["index"]] = fb_p

    if all_prompts:
        print(f"🎉 Hoàn tất AI Đạo Diễn All-in-One: Đã sinh thành công {len(all_prompts)}/{total_cuts} prompt bám sát phụ đề & {len(all_chapters)} YouTube Chapters!")
        return all_prompts, all_chapters

    print("⚠️ Tất cả các model Gemini đều không phản hồi. Tự động chuyển sang Chế Độ Dự Phòng Thông Minh (Nội bộ 100%).")
    return {}, []


def call_gemini_ai_director(cuts, full_speech: str, topic_title: str, visual_concept: str, gemini_key: str, selected_model: str = "gemini-3.5-flash-lite"):
    """Alias tương thích ngược."""
    prompts, _ = call_gemini_all_in_one_director(cuts, full_speech, topic_title, visual_concept, gemini_key, selected_model)
    return prompts if prompts else None


def generate_micro_batch_visual_prompts(cuts, visual_concept: str, api_key: str, model_name: str = "gemini-3.5-flash-lite", art_style: str = "cinematic", batch_size: int = 45):
    """Tương thích với các gọi hàm cũ."""
    sc_dict, _ = call_gemini_all_in_one_director(cuts, "", "", visual_concept, api_key, selected_model=model_name)
    res = []
    for c in cuts:
        idx = c.get("index", len(res) + 1)
        res.append(sc_dict.get(idx, ""))
    return res


def enhance_visual_prompt_gemini(scene_text: str, visual_concept: str, api_key: str, model_name: str = "gemini-3.5-flash-lite", art_style: str = "cinematic") -> str:
    """Tương thích ngược đơn lẻ."""
    return analyze_sentence_to_detective_prompt(scene_text, 0, 0, visual_concept=visual_concept)
