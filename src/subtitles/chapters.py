import re

def recalculate_and_inject_youtube_chapters(description: str, raw_script: str, segments_data, total_dur: float, gemini_api_key: str = "", gemini_model: str = "gemini-2.5-flash"):
    """
    TỰ ĐỘNG TÍNH TOÁN & GHI ĐÈ YOUTUBE CHAPTERS (TIMESTAMPS) CHUẨN XÁC V19.4:
    - Bóc tách danh sách Hồi/Chương từ kịch bản hoặc phần mô tả cũ.
    - Tìm mốc thời gian thực tế (giây) từ phụ đề Whisper chuẩn xác 100%.
    - Chuẩn hóa theo tiêu chuẩn YouTube: Mốc đầu tiên 00:00, tăng dần, cách nhau >= 10s, <= total_dur.
    - Ghi đè (Overwrite) lên mục TIMESTAMPS cũ trong mô tả video.
    """
    if not description and not raw_script:
        return description

    source_text = description if description and len(description.strip()) > 30 else raw_script

    def sec_to_yt(s):
        s = max(0, int(round(s)))
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{sec:02d}"
        return f"{m:02d}:{sec:02d}"

    extracted_chapters = []
    ts_block_patterns = [
        r'(?:⏱️?\s*(?:TIMESTAMPS|MỤC LỤC|DANH SÁCH CHƯƠNG):?)(.*?)(?=(?:\n\s*(?:📌|---|#|\[|\Z)))',
        r'((?:(?:\d{1,2}:)?\d{2}:\d{2}\s*[-–—:]\s*[^\r\n]+\n?){3,})'
    ]
    for pat in ts_block_patterns:
        m = re.search(pat, source_text, re.DOTALL | re.IGNORECASE)
        if m:
            block_text = m.group(1).strip()
            lines = [l.strip() for l in block_text.split('\n') if l.strip()]
            for line in lines:
                line_m = re.search(r'^(?:(?:\d{1,2}:)?\d{2}:\d{2})\s*[-–—:]\s*(.+)$', line)
                if line_m:
                    ch_title = line_m.group(1).strip()
                    if ch_title:
                        extracted_chapters.append(ch_title)
            if extracted_chapters:
                break

    if not extracted_chapters:
        act_matches = re.findall(r'(?:^|\n)\s*(Hồi\s+\d+[:\s][^\r\n]+|Chương\s+\d+[:\s][^\r\n]+)', source_text, re.IGNORECASE)
        if act_matches:
            extracted_chapters = [m.strip() for m in act_matches if len(m.strip()) > 4]

    calculated_chapters = []

    if extracted_chapters and segments_data:
        num_ch = len(extracted_chapters)
        cur_min_time = 0.0

        for i, ch_name in enumerate(extracted_chapters):
            if i == 0:
                calculated_chapters.append((0.0, ch_name))
                continue

            clean_name = re.sub(r'^(?:Hồi\s+\d+|Chương\s+\d+|Phần\s+\d+)[:\s-]*', '', ch_name, flags=re.IGNORECASE).strip()
            kw_candidates = [w for w in clean_name.split() if len(w) > 2]
            best_time = None

            min_step = 60.0 if i == 1 else 20.0
            search_start = cur_min_time + min_step

            for seg in segments_data:
                st = seg['start']
                if st < search_start:
                    continue
                txt = seg['text'].lower()
                matches = sum(1 for kw in kw_candidates if kw.lower() in txt)
                if matches >= 2 or (len(kw_candidates) == 1 and matches == 1):
                    best_time = st
                    break

            if best_time is None:
                remaining_dur = max(10.0, total_dur - search_start)
                step = remaining_dur / max(1, (num_ch - i))
                best_time = min(total_dur - 10.0, search_start + step * 0.4)

            best_time = max(search_start, min(best_time, total_dur - 5.0))
            cur_min_time = best_time
            calculated_chapters.append((best_time, ch_name))

    elif not extracted_chapters and segments_data and total_dur > 180:
        num_ch = 6
        step = total_dur / num_ch
        default_titles = [
            "Lời mở đầu & Giới thiệu hồ sơ",
            "Diễn biến kịch tính & Manh mối đầu tiên",
            "Cuộc điều tra sâu & Lời khai then chốt",
            "Nút thắt bất ngờ & Góc khuất đen tối",
            "Cao trào & Sự thật được phơi bày",
            "Kết luận & Bài học đọng lại"
        ]
        for i in range(num_ch):
            calculated_chapters.append((i * step, default_titles[i]))

    if not calculated_chapters:
        return description

    final_sorted = []
    last_t = -1.0
    for idx, (t, title) in enumerate(calculated_chapters):
        if idx == 0:
            final_sorted.append((0.0, title))
            last_t = 0.0
        else:
            t_adj = max(last_t + 10.0, min(float(t), total_dur - 5.0))
            if t_adj <= total_dur:
                final_sorted.append((t_adj, title))
                last_t = t_adj

    final_chapter_lines = ["⏱️ TIMESTAMPS:"]
    for t, title in final_sorted:
        final_chapter_lines.append(f"{sec_to_yt(t)} - {title}")
    new_timestamps_block = "\n".join(final_chapter_lines)

    target_desc = description if description else source_text

    match_in_desc = re.search(r'(⏱️?\s*(?:TIMESTAMPS|MỤC LỤC|DANH SÁCH CHƯƠNG):?.*?(?=(?:\n\s*(?:📌|---|#|\[|\Z))))', target_desc, re.DOTALL | re.IGNORECASE)
    if match_in_desc:
        updated_desc = target_desc[:match_in_desc.start()] + new_timestamps_block + "\n" + target_desc[match_in_desc.end():]
    else:
        hash_match = re.search(r'(\n\s*(?:📌|---|#))', target_desc)
        if hash_match:
            insert_pos = hash_match.start()
            updated_desc = target_desc[:insert_pos] + "\n\n" + new_timestamps_block + "\n" + target_desc[insert_pos:]
        else:
            updated_desc = target_desc.strip() + "\n\n" + new_timestamps_block + "\n"

    return updated_desc.strip()
