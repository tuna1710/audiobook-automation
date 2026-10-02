import os
import csv
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional

SHARED_DRIVE_FOLDER_ID = "1GCWzDry94uvLRZM5B97Alddfrm9uvjQH"
CSV_COLUMNS = ['Ten_Kich_Ban', 'Email_Nguoi_Lam', 'Lich_Dang', 'Trang_Thai', 'Link_Video', 'Thoi_Gian_Cap_Nhat']


def find_shared_drive_folder(custom_folder: str = "") -> str:
    """
    Tìm thư mục Google Drive dùng chung 'BAO CAO CONG VIEC'.
    Hỗ trợ kiểm tra đường dẫn nhập vào, hoặc tự động tìm theo tên/ID trong /content/drive/MyDrive.
    """
    if custom_folder and str(custom_folder).strip() and os.path.isdir(str(custom_folder).strip()):
        return str(custom_folder).strip()

    target_names = [
        "BAO CAO CONG VIEC",
        "Báo cáo công việc",
        "BAO_CAO_CONG_VIEC",
        "bao cao cong viec",
        SHARED_DRIVE_FOLDER_ID,
        "NoiSoAudiobook",
        "Audiobook_Shared"
    ]

    drive_base = "/content/drive/MyDrive"
    if os.path.exists(drive_base):
        for name in target_names:
            p = os.path.join(drive_base, name)
            if os.path.isdir(p):
                return p
        for root, dirs, _ in os.walk(drive_base):
            for d in dirs:
                if any(tn.lower() in d.lower() for tn in target_names):
                    return os.path.join(root, d)
            if root.count(os.sep) - drive_base.count(os.sep) >= 2:
                break
        default_shared = os.path.join(drive_base, "BAO CAO CONG VIEC")
        try:
            os.makedirs(default_shared, exist_ok=True)
            return default_shared
        except Exception:
            return drive_base

    return os.path.abspath(".")


def check_script_already_published(script_name: str, folder_path: str = "") -> Tuple[bool, Optional[dict]]:
    """
    Kiểm tra xem kịch bản đã được ĐĂNG THÀNH CÔNG trong quan_ly_san_xuat.csv hay chưa.
    Nếu đã đăng (Trạng thái == 'ĐÃ ĐĂNG' và có link video) -> Bỏ qua tránh làm trùng.
    """
    target_dir = find_shared_drive_folder(folder_path)
    csv_file = os.path.join(target_dir, "quan_ly_san_xuat.csv")
    if not os.path.exists(csv_file):
        return False, None

    clean_name = os.path.basename(script_name).strip().lower()
    clean_stem = os.path.splitext(clean_name)[0]
    try:
        with open(csv_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                r_name = os.path.basename(row.get("Ten_Kich_Ban", "")).strip().lower()
                r_stem = os.path.splitext(r_name)[0]
                r_status = row.get("Trang_Thai", "").strip().upper()
                r_link = row.get("Link_Video", "").strip()
                if (clean_name == r_name or clean_stem == r_stem) and "ĐÃ ĐĂNG" in r_status and r_link.startswith("http"):
                    return True, row
    except Exception as e:
        print(f"⚠️ Lỗi đọc file quan_ly_san_xuat.csv: {e}")
    return False, None


def record_successful_publish(
    script_name: str,
    editor_email: str = "",
    schedule_time: str = "",
    video_url: str = "",
    folder_path: str = ""
) -> Tuple[bool, str]:
    """
    CHỈ KHI NÀO ĐĂNG YOUTUBE THÀNH CÔNG MỚI THÊM DÒNG VÀO FILE quan_ly_san_xuat.csv!
    Ghi nhận email người phụ trách, ngày đăng, trạng thái ĐÃ ĐĂNG và link video.
    """
    target_dir = find_shared_drive_folder(folder_path)
    os.makedirs(target_dir, exist_ok=True)
    csv_file = os.path.join(target_dir, "quan_ly_san_xuat.csv")

    vn_tz = timezone(timedelta(hours=7))
    now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

    file_exists = os.path.exists(csv_file)
    try:
        with open(csv_file, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            if not file_exists or os.path.getsize(csv_file) == 0:
                writer.writerow(CSV_COLUMNS)
            writer.writerow([
                os.path.basename(script_name) if script_name else "Kịch bản trực tiếp",
                editor_email.strip() if editor_email else "Chưa khai báo email",
                schedule_time if schedule_time else now_str[:16],
                "ĐÃ ĐĂNG",
                video_url,
                now_str
            ])
        print(f"📊 Đã ghi nhận thành công vào bảng quản lý: {csv_file}")
        return True, csv_file
    except Exception as e:
        print(f"⚠️ Lỗi ghi file quan_ly_san_xuat.csv: {e}")
        return False, str(e)


def auto_advance_lich_dang_file(file_path: str, published_iso_str: str, video_url: str) -> Tuple[bool, str]:
    """Cập nhật mốc đăng tiếp theo vào lich_dang.txt sau khi đăng thành công."""
    try:
        lines = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

        current_date = datetime.strptime(published_iso_str.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
        next_date = current_date + timedelta(days=1)
        next_date_str = next_date.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

        if lines:
            lines[-1] = f"{published_iso_str} {video_url}"
        else:
            lines.append(f"{published_iso_str} {video_url}")
        lines.append(next_date_str)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return True, next_date_str
    except Exception as e:
        return False, str(e)
