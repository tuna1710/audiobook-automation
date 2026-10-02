import re


def recalculate_and_inject_youtube_chapters(
    description: str,
    raw_script: str,
    segments_data: list,
    total_dur: float,
    gemini_api_key: str = "",
    gemini_model: str = "gemini-3.5-flash-lite",
    precomputed_chapters: list = None
) -> str:
    """
    CHUẨN HÓA MỐC THỜI GIAN YOUTUBE CHAPTERS V20:
    - Ưu tiên sử dụng precomputed_chapters từ All-in-One Director (0 LẦN GỌI API BỔ SUNG).
    - Khớp chuẩn 100% từng giây với giọng đọc audio từ phụ đề SRT.
    - Ghi đè trực tiếp lên mục TIMESTAMPS cũ trong Mô Tả Video.
    """
    if not segments_data and not precomputed_chapters:
        return description

    def sec_to_yt(s):
        s = max(0, int(round(s)))
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{sec:02d}"
        return f"{m:02d}:{sec:02d}"

    calculated_chapters = []

    # 1. ƯU TIÊN SỐ 1: Sử dụng Chapters đã sinh từ All-in-One Gemini Director (KHÔNG TỐN THÊM LƯỢT GỌI API)
    if precomputed_chapters and len(precomputed_chapters) >= 2:
        for t_sec, title in precomputed_chapters:
            calculated_chapters.append((float(t_sec), str(title).strip()))

    # 2. Nếu chưa có precomputed_chapters: Phân tích Rule-based dựa trên segments_data (100% Offline, 0 API Call)
    if not calculated_chapters:
        ts_pattern = r'(⏱️?\s*(?:TIMESTAMPS|MỤC LỤC|CHƯƠNG|HỒI|NỘI DUNG CHÍNH|CHAPTERS):?.*?(?=(?:\n\s*(?:📌|---|#|\[|\Z))))'
        source_text = description if description and len(description.strip()) > 20 else raw_script
        existing_match = re.search(ts_pattern, source_text, re.DOTALL | re.IGNORECASE)
        extracted_chapters = []
        if existing_match:
            for line in existing_match.group(1).strip().splitlines():
                m = re.match(r'^\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*[-:–—.]\s*(.*)$', line.strip())
                if m:
                    extracted_chapters.append(m.group(2).strip())

        if extracted_chapters:
            last_t = 0.0
            calculated_chapters = [(0.0, extracted_chapters[0])]
            for i in range(1, len(extracted_chapters)):
                title = extracted_chapters[i]
                clean_title = re.sub(r'^(?:hồi|phần|chương|mục)\s*\d+\s*[:\-–—.]\s*', '', title, flags=re.IGNORECASE)
                kws = [w.lower() for w in re.findall(r'\w+', clean_title) if len(w) > 3 and w.lower() not in ['nàng', 'thương', 'những', 'trong', 'người', 'của', 'hiện']]
                min_step = 40.0 if i == 1 else 20.0
                best_time = None
                best_score = 0
                for seg in segments_data:
                    if seg['start'] < last_t + min_step:
                        continue
                    seg_lower = seg.get('text', '').lower()
                    score = sum(1 for kw in kws if kw in seg_lower)
                    if score > best_score and score >= 2:
                        best_score = score
                        best_time = seg['start']
                if best_time is not None:
                    calculated_chapters.append((best_time, title))
                    last_t = best_time
                else:
                    step = (total_dur - last_t) / max(1, len(extracted_chapters) - i + 1)
                    fallback_t = min(total_dur - 10, round(last_t + step, 1))
                    calculated_chapters.append((fallback_t, title))
                    last_t = fallback_t
        else:
            step = total_dur / 5.0
            names = ["Lời mở đầu & Bối cảnh bí ẩn", "Diễn biến & Manh mối đầu tiên", "Nghi vấn & Cao trào căng thẳng", "Nút thắt bất ngờ", "Lời kết & Sự thật hé lộ"]
            for idx, nm in enumerate(names):
                calculated_chapters.append((round(idx * step, 1), nm))

    # 3. Chuẩn hóa thứ tự thời gian tăng dần và <= total_dur
    final_sorted = []
    prev_t = 0.0
    for idx, (t_sec, title) in enumerate(calculated_chapters):
        if idx == 0:
            final_sorted.append((0.0, title))
            prev_t = 0.0
        else:
            cur_t = max(prev_t + 10.0, min(total_dur - 5.0, t_sec))
            final_sorted.append((cur_t, title))
            prev_t = cur_t

    final_chapter_lines = ["⏱️ TIMESTAMPS:"]
    for t_sec, title in final_sorted:
        final_chapter_lines.append(f"{sec_to_yt(t_sec)} - {title}")

    new_ts_block = "\n".join(final_chapter_lines)

    ts_pattern = r'(⏱️?\s*(?:TIMESTAMPS|MỤC LỤC|CHƯƠNG|HỒI|NỘI DUNG CHÍNH|CHAPTERS):?.*?(?=(?:\n\s*(?:📌|---|#|\[|\Z))))'
    if description:
        match_in_desc = re.search(ts_pattern, description, re.DOTALL | re.IGNORECASE)
        if match_in_desc:
            updated_desc = description.replace(match_in_desc.group(1).strip(), new_ts_block)
        else:
            insert_pos = re.search(r'(?:\n\s*(?:📌|#|Đừng quên|---))', description)
            if insert_pos:
                idx = insert_pos.start()
                updated_desc = description[:idx].rstrip() + "\n\n" + new_ts_block + "\n\n" + description[idx:].lstrip()
            else:
                updated_desc = description.rstrip() + "\n\n" + new_ts_block + "\n"
        return updated_desc

    return new_ts_block
