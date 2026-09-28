import os
import time
import json
import logging
import random
from typing import Optional, Callable
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from .oauth_auth import get_youtube_service, calculate_schedule_iso
from .gdrive_logger import record_successful_publish

# Cấu hình logging
logger = logging.getLogger("audiobook_automation.youtube_uploader")

# Các mã lỗi HTTP phía máy chủ có thể thử lại an toàn (Transient errors)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
MAX_RETRIES = 5
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB mỗi chunk (chuẩn bội số 256KB cho Resumable Upload)


def parse_youtube_http_error(err: HttpError) -> str:
    """
    Bóc tách mã lỗi HttpError từ YouTube Data API thành thông báo tiếng Việt chi tiết và dễ hiểu.
    """
    status_code = getattr(err, "resp", {}).status if hasattr(err, "resp") else None
    error_content = ""
    reasons = []
    message = str(err)

    try:
        if hasattr(err, "content"):
            content_json = json.loads(err.content.decode("utf-8") if isinstance(err.content, bytes) else str(err.content))
            error_data = content_json.get("error", {})
            message = error_data.get("message", message)
            errors_list = error_data.get("errors", [])
            for item in errors_list:
                if "reason" in item:
                    reasons.append(item["reason"])
    except Exception:
        pass

    # Phân loại các lỗi phổ biến nhất
    if "quotaExceeded" in reasons or status_code == 403 and "quota" in message.lower():
        return (
            f"❌ Lỗi [403 quotaExceeded]: Đã dùng hết hạn mức Quota YouTube Data API trong ngày "
            f"(Mặc định 10.000 units/ngày, mỗi lần upload tốn 1.600 units). "
            f"Hạn mức sẽ tự động được làm mới vào lúc 14:00 (giờ Việt Nam). Chi tiết: {message}"
        )
    elif "youtubeSignupRequired" in reasons or "Access Not Configured. Please create a YouTube channel" in message:
        return (
            f"❌ Lỗi [403 youtubeSignupRequired]: Tài khoản Google được cấp quyền chưa từng Tạo Kênh trên YouTube "
            f"(hoặc kênh của bạn là Brand Account nhưng bạn lại đăng nhập bằng tài khoản chính). "
            f"Vui lòng truy cập youtube.com và bấm 'Tạo kênh' cho tài khoản này trước."
        )
    elif "accessNotConfigured" in reasons or "has not been used in project" in message:
        return (
            f"❌ Lỗi [403 accessNotConfigured]: Dự án trên Google Cloud Console CHƯA ĐƯỢC BẬT 'YouTube Data API v3'. "
            f"Vui lòng vào Google Cloud Console > APIs & Services > Library > Tìm 'YouTube Data API v3' và bấm ENABLE."
        )
    elif "uploadLimitExceeded" in reasons:
        return (
            f"❌ Lỗi [403 uploadLimitExceeded]: Kênh đã đạt giới hạn số lượng video được phép tải lên trong 24h của YouTube. "
            f"Vui lòng thử lại sau ít nhất 15-30 phút hoặc ngày hôm sau."
        )
    elif "invalidPublishAt" in reasons:
        return (
            f"❌ Lỗi [400 invalidPublishAt]: Mốc thời gian hẹn giờ công khai không hợp lệ hoặc nằm trong quá khứ. "
            f"Vui lòng kiểm tra lại ngày giờ phát hành."
        )
    elif "insufficientPermissions" in reasons or status_code == 401:
        return (
            f"❌ Lỗi [401/403 insufficientPermissions]: Token xác thực không đủ quyền hoặc đã hết hạn. "
            f"Vui lòng xóa file token.json và thực hiện xác thực lại từ đầu."
        )

    return f"❌ Lỗi YouTube API (Mã {status_code}): {message}"


def upload_to_youtube(
    video_file_path: str,
    title: str,
    description: str,
    tags: str = "",
    is_schedule: bool = False,
    custom_schedule_time: str = "",
    privacy_status: str = "private",
    editor_email: str = "",
    shared_drive_folder: str = "",
    outputs_dir: str = "outputs",
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> str:
    """
    Tải video lên YouTube qua giao thức Resumable Upload có cơ chế Retry tự động và gán Thumbnail CTR Booster.
    """
    if not video_file_path or not os.path.exists(video_file_path):
        return f"❌ Lỗi: Không tìm thấy file video tại '{video_file_path}'"

    youtube = get_youtube_service()
    if not youtube:
        return (
            "❌ Lỗi: Chưa xác thực YouTube OAuth2 hợp lệ! "
            "Vui lòng hoàn tất Bước 1 & Bước 2 tại TAB 3 để tạo file token.json."
        )

    snippet = {
        "title": title[:100] if title else f"Audiobook - {os.path.basename(video_file_path)}",
        "description": description[:5000] if description else "",
        "tags": [t.strip() for t in tags.split(",") if t.strip()] if tags else ["Audiobook", "Kinh Dị", "Trinh Thám"],
        "categoryId": "27"  # Education
    }

    status = {
        "selfDeclaredMadeForKids": False
    }

    scheduled_iso_str = ""
    sched_desc = ""

    if is_schedule:
        scheduled_iso_str, sched_desc = calculate_schedule_iso(custom_schedule_time)
        status["privacyStatus"] = "private"
        status["publishAt"] = scheduled_iso_str
    else:
        status["privacyStatus"] = privacy_status.lower() if privacy_status else "private"

    body = {"snippet": snippet, "status": status}

    try:
        if progress_callback:
            progress_callback(0.05, "Đang kết nối đến YouTube Resumable Upload Server...")

        # Khởi tạo Resumable Upload với chunksize chuẩn 5MB
        media = MediaFileUpload(
            video_file_path,
            chunksize=CHUNK_SIZE,
            resumable=True
        )
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        retry_count = 0

        # Vòng lặp Resumable Upload có cơ chế Exponential Backoff Retry chống đứt kết nối
        while response is None:
            try:
                if progress_callback:
                    progress_callback(0.2, "Đang đẩy các khối dữ liệu video lên YouTube...")

                status_chunk, response = request.next_chunk()
                if status_chunk:
                    pct = int(status_chunk.progress() * 100)
                    msg = f"🚀 Đang tải video lên YouTube: {pct}%"
                    logger.info(msg)
                    if progress_callback:
                        progress_callback(0.2 + (status_chunk.progress() * 0.7), msg)
                # Đặt lại bộ đếm retry khi có chunk thành công
                retry_count = 0

            except HttpError as http_err:
                # Nếu gặp lỗi phía server (5xx), thử lại
                if http_err.resp.status in RETRIABLE_STATUS_CODES:
                    retry_count += 1
                    if retry_count > MAX_RETRIES:
                        return f"❌ Máy chủ YouTube phản hồi lỗi tạm thời ({http_err.resp.status}) và đã vượt quá {MAX_RETRIES} lần thử lại."
                    sleep_sec = (2 ** retry_count) + random.random()
                    logger.warning(f"Lỗi tạm thời từ YouTube ({http_err.resp.status}), đang thử lại lần {retry_count}/{MAX_RETRIES} sau {sleep_sec:.1f}s...")
                    time.sleep(sleep_sec)
                else:
                    # Các lỗi 4xx (quota, permissions, syntax) không nên retry mà trả về giải thích cụ thể
                    return parse_youtube_http_error(http_err)

            except (IOError, TimeoutError, ConnectionError, Exception) as net_err:
                # Bắt các lỗi rớt mạng / socket timeout / connection reset
                retry_count += 1
                if retry_count > MAX_RETRIES:
                    return f"❌ Lỗi mất kết nối mạng khi tải video sau {MAX_RETRIES} lần thử lại: {net_err}"
                sleep_sec = (2 ** retry_count) + random.random()
                logger.warning(f"Mạng gián đoạn ({net_err}), đang thử lại lần {retry_count}/{MAX_RETRIES} sau {sleep_sec:.1f}s...")
                time.sleep(sleep_sec)

        vid = response.get("id")
        video_url = f"https://youtu.be/{vid}"

        # =========================================================================
        # TỰ ĐỘNG GÁN THUMBNAIL YOUTUBE (CTR BOOSTER)
        # =========================================================================
        thumb_status_msg = ""
        try:
            cand_thumb = os.path.join(outputs_dir, "thumbnail_latest.jpg")
            if not os.path.exists(cand_thumb):
                base_name = os.path.splitext(os.path.basename(video_file_path))[0].replace("final_video_", "thumbnail_")
                cand_specific = os.path.join(outputs_dir, f"{base_name}.jpg")
                if os.path.exists(cand_specific):
                    cand_thumb = cand_specific

            if os.path.exists(cand_thumb):
                if progress_callback:
                    progress_callback(0.95, "Đang tự động gán Thumbnail CTR Booster...")
                youtube.thumbnails().set(
                    videoId=vid,
                    media_body=MediaFileUpload(cand_thumb, mimetype="image/jpeg")
                ).execute()
                thumb_status_msg = f"\n🖼️ ĐÃ TỰ ĐỘNG GÁN THUMBNAIL: {os.path.basename(cand_thumb)}"
                logger.info(f"Đã gán Thumbnail thành công cho video {vid}")
        except HttpError as e_th_http:
            thumb_status_msg = f"\n⚠️ Lưu ý Thumbnail: Kênh cần xác minh số điện thoại để gán thumbnail tùy chỉnh ({e_th_http.resp.status})."
            logger.warning(f"Không thể gán thumbnail: {e_th_http}")
        except Exception as e_th:
            thumb_status_msg = f"\n⚠️ Lưu ý Thumbnail: {e_th}"
            logger.warning(f"Lỗi gán thumbnail: {e_th}")

        schedule_info_msg = ""
        if is_schedule and scheduled_iso_str:
            schedule_info_msg = f"\n⏰ ĐÃ HẸN GIỜ CÔNG KHAI: {sched_desc}"

        # =========================================================================
        # GHI NHẬN TIẾN ĐỘ VÀO GOOGLE DRIVE DÙNG CHUNG
        # =========================================================================
        team_log_msg = ""
        ok_rec, rec_path = record_successful_publish(
            script_name=title if title else os.path.basename(video_file_path),
            editor_email=editor_email,
            schedule_time=sched_desc if (is_schedule and sched_desc) else ("Công khai ngay" if not is_schedule else scheduled_iso_str),
            video_url=video_url,
            folder_path=shared_drive_folder
        )
        if ok_rec:
            team_log_msg = f"\n📊 Đã ghi nhận tiến độ vào: {os.path.basename(rec_path)}"

        if progress_callback:
            progress_callback(1.0, "Đã đăng video lên YouTube thành công!")

        return (
            f"🎉 ĐÃ TẢI LÊN YOUTUBE THÀNH CÔNG!\n"
            f"- Video ID: {vid}\n"
            f"- Link xem video: {video_url}\n"
            f"- Chế độ: {'LÊN LỊCH' if is_schedule else privacy_status.upper()}"
            f"{schedule_info_msg}{thumb_status_msg}{team_log_msg}"
        )

    except HttpError as err:
        return parse_youtube_http_error(err)
    except Exception as e:
        return f"❌ Lỗi tải lên YouTube: {e}"
