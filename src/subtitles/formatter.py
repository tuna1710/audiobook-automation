import re

def format_timestamp_srt(seconds: float) -> str:
    """
    Chuyển đổi số giây thành định dạng tem thời gian SRT chuẩn HH:MM:SS,mmm
    """
    secs = max(0.0, float(seconds))
    hrs = int(secs // 3600)
    mins = int((secs % 3600) // 60)
    rem_secs = int(secs % 60)
    msecs = int(round((secs - int(secs)) * 1000))
    if msecs >= 1000:
        rem_secs += 1
        msecs = 0
    return f"{hrs:02d}:{mins:02d}:{rem_secs:02d},{msecs:03d}"

def format_srt_max_two_lines(segments, max_chars_per_line: int = 44, max_chars_two_lines: int = 88):
    """
    CHUẨN HÓA PHỤ ĐỀ ĐIỆN ẢNH V19.3:
    - Đảm bảo mỗi block subtitle hiển thị trên màn hình tối đa đúng 2 dòng.
    - Tự động ngắt dòng thông minh theo cụm từ, tránh ngắt giữa từ tiếng Việt.
    - Chia nhỏ các câu quá dài thành các phân đoạn mượt mà theo tỷ lệ thời gian.
    - Giữ nguyên mốc cắt cảnh cuts của video gốc (không phân mảnh video).
    """
    if not segments:
        return []

    def wrap_into_two_lines(txt: str, limit: int = 44) -> str:
        words = txt.strip().split()
        if not words:
            return ""
        if len(txt) <= limit:
            return txt

        # Tìm điểm ngắt tốt nhất gần chính giữa câu
        best_break = len(words) // 2
        min_diff = 999
        for i in range(1, len(words)):
            line1 = " ".join(words[:i])
            line2 = " ".join(words[i:])
            diff = abs(len(line1) - len(line2))
            if len(line1) <= limit + 8 and len(line2) <= limit + 8 and diff < min_diff:
                min_diff = diff
                best_break = i

        return " ".join(words[:best_break]) + "\n" + " ".join(words[best_break:])

    output_items = []
    for seg in segments:
        st = float(seg.get("start", 0.0))
        et = float(seg.get("end", 0.0))
        dur = max(0.1, et - st)
        raw_text = seg.get("text", "").replace("\r", " ").replace("\n", " ").strip()
        raw_text = re.sub(r'\s+', ' ', raw_text)

        if not raw_text:
            continue

        words = raw_text.split()
        total_chars = len(raw_text)

        # Trường hợp 1: Đoạn văn vừa vặn trong 2 dòng
        if total_chars <= max_chars_two_lines and len(words) <= 18:
            output_items.append({
                "start": st,
                "end": et,
                "text": wrap_into_two_lines(raw_text, limit=max_chars_per_line)
            })
            continue

        # Trường hợp 2: Câu quá dài, chia thành các block nhỏ hơn
        num_chunks = max(2, (total_chars + max_chars_two_lines - 1) // max_chars_two_lines)
        words_per_chunk = max(4, len(words) // num_chunks)

        chunk_words_list = []
        cur_idx = 0
        for c in range(num_chunks):
            if c == num_chunks - 1:
                chunk_words_list.append(words[cur_idx:])
            else:
                chunk_words_list.append(words[cur_idx : cur_idx + words_per_chunk])
                cur_idx += words_per_chunk

        chunk_words_list = [cw for cw in chunk_words_list if cw]
        chunk_dur = dur / max(1, len(chunk_words_list))

        for c_idx, cw in enumerate(chunk_words_list):
            c_text = " ".join(cw).strip()
            c_st = st + c_idx * chunk_dur
            c_et = min(et, c_st + chunk_dur)
            output_items.append({
                "start": c_st,
                "end": c_et,
                "text": wrap_into_two_lines(c_text, limit=max_chars_per_line)
            })

    return output_items
