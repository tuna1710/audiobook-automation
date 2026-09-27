import os
import csv
from datetime import datetime, timezone, timedelta

def record_successful_publish(
    script_name: str,
    editor_email: str = "",
    schedule_time: str = "",
    video_url: str = "",
    folder_path: str = ""
):
    """
    Ghi nhận dòng tiến độ xuất bản thành công vào file CSV báo cáo công việc nhóm.
    """
    vn_tz = timezone(timedelta(hours=7))
    now_vn = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

    target_dir = folder_path.strip() if folder_path and os.path.exists(folder_path.strip()) else "outputs"
    os.makedirs(target_dir, exist_ok=True)
    report_file = os.path.join(target_dir, "TIEN_DO_DANG_BAI_YOUTUBE.csv")

    is_new = not os.path.exists(report_file)
    try:
        with open(report_file, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow([
                    "Thời gian hoàn tất",
                    "Tên kịch bản / Video",
                    "Email người phụ trách",
                    "Lịch công khai",
                    "Link YouTube",
                    "Trạng thái"
                ])
            writer.writerow([
                now_vn,
                script_name,
                editor_email if editor_email else "Không khai báo",
                schedule_time if schedule_time else "Công khai ngay",
                video_url,
                "Hoàn thành xuất sắc"
            ])
        return True, report_file
    except Exception as e:
        print(f"⚠️ Lỗi ghi nhận tiến độ: {e}")
        return False, ""
