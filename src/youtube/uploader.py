import os
import time
import json
import logging
import random
from typing import Optional, Callable
try:
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
except ImportError:
    MediaFileUpload = None
    HttpError = Exception
from .oauth_auth import get_youtube_service, calculate_schedule_iso, resolve_file_path, YOUTUBE_SCOPES
from .gdrive_logger import record_successful_publish, auto_advance_lich_dang_file

logger = logging.getLogger("audiobook_automation.youtube_uploader")

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
MAX_RETRIES = 5
CHUNK_SIZE = 5 * 1024 * 1024


def parse_youtube_http_error(err: HttpError) -> str:
    """
    Bóc tách mã lỗi HttpError từ YouTube Data API thành thông báo tiếng Việt chi tiết.
    """
    status_code = getattr(err, "resp", {}).status if hasattr(err, "resp") else None
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

    if "quotaExceeded" in reasons or (status_code == 403 and "quota" in message.lower()):
        return (
            f"❌ Lỗi [403 quotaExceeded]: Đã dùng hết hạn mức Quota YouTube Data API trong ngày "
            f"(Mặc định 10.000 units/ngày, mỗi lần upload tốn 1.600 units). "
            f"Hạn mức sẽ tự động được làm mới vào lúc 14:00 (giờ VN). Chi tiết: {message}"
        )
    elif "youtubeSignupRequired" in reasons or "Access Not Configured. Please create a YouTube channel" in message:
        return (
            f"❌ Lỗi [403 youtubeSignupRequired]: Tài khoản Google được cấp quyền chưa từng Tạo Kênh trên YouTube. "
            f"Vui lòng truy cập youtube.com và tạo kênh cho tài khoản này trước."
        )
    elif "accessNotConfigured" in reasons or "has not been used in project" in message:
        return (
            f"❌ Lỗi [403 accessNotConfigured]: Dự án trên Google Cloud Console CHƯA ĐƯỢC BẬT 'YouTube Data API v3'. "
            f"Vui lòng bật 'YouTube Data API v3' trong Google Cloud Console."
        )
    elif "uploadLimitExceeded" in reasons:
        return f"❌ Lỗi [400 uploadLimitExceeded]: Kênh đã chạm giới hạn số lượng video được phép tải lên trong ngày."
    elif status_code == 401:
        return f"❌ Lỗi [401 Unauthorized]: Token xác thực đã hết hạn hoặc bị thu hồi. Vui lòng xác thực lại OAuth2."
    elif status_code == 400:
        return f"❌ Lỗi [400 Bad Request]: Yêu cầu không hợp lệ: {message}"

    return f"❌ Lỗi YouTube API [Mã {status_code}]: {message}"


def upload_to_youtube(*args, **kwargs) -> str:
    """
    HÀM ĐĂNG TẢI YOUTUBE V20 LINH HOẠT:
    Hỗ trợ gọi từ Tab 3 (12 hoặc 14 tham số giao diện), hoặc gọi trực tiếp từ orchestrator.
    """
    custom_thumbnail = kwargs.get("custom_thumbnail", None)
    channel_profile = kwargs.get("channel_profile", "")

    # Xử lý tham số linh hoạt
    if len(args) >= 14:
        video_source_mode = args[0]
        generated_video = args[1]
        history_video_choice = args[2]
        custom_video_file = args[3]
        title = args[4]
        description = args[5]
        tags = args[6]
        is_schedule = args[7]
        custom_schedule_time = args[8]
        privacy_status = args[9]
        editor_email = args[10]
        shared_drive_folder = args[11]
        custom_thumbnail = args[12] if args[12] else custom_thumbnail
        channel_profile = args[13] if args[13] else channel_profile
    elif len(args) == 12:
        (video_source_mode, generated_video, history_video_choice, custom_video_file,
         title, description, tags, is_schedule, custom_schedule_time,
         privacy_status, editor_email, shared_drive_folder) = args
    elif len(args) >= 8:
        video_source_mode = args[0]
        generated_video = args[1]
        history_video_choice = args[2] if len(args) > 2 else ""
        custom_video_file = args[3] if len(args) > 3 else None
        title = args[4] if len(args) > 4 else ""
        description = args[5] if len(args) > 5 else ""
        tags = args[6] if len(args) > 6 else ""
        is_schedule = args[7] if len(args) > 7 else False
        custom_schedule_time = args[8] if len(args) > 8 else kwargs.get("custom_schedule_time", "")
        privacy_status = args[9] if len(args) > 9 else kwargs.get("privacy_status", "private")
        editor_email = args[10] if len(args) > 10 else kwargs.get("editor_email", "")
        shared_drive_folder = args[11] if len(args) > 11 else kwargs.get("shared_drive_folder", "")
    else:
        video_source_mode = kwargs.get("video_source_mode", "outputs")
        generated_video = kwargs.get("generated_video", "")
        history_video_choice = kwargs.get("history_video_choice", "")
        custom_video_file = kwargs.get("custom_video_file", None)
        title = kwargs.get("title", "")
        description = kwargs.get("description", "")
        tags = kwargs.get("tags", "")
        is_schedule = kwargs.get("is_schedule", False)
        custom_schedule_time = kwargs.get("custom_schedule_time", "")
        privacy_status = kwargs.get("privacy_status", "private")
        editor_email = kwargs.get("editor_email", "")
        shared_drive_folder = kwargs.get("shared_drive_folder", "")

    outputs_dir = kwargs.get("outputs_dir", "outputs")

    custom_vid = resolve_file_path(custom_video_file)
    gen_vid = resolve_file_path(generated_video)
    hist_vid = None
    if history_video_choice and not str(history_video_choice).startswith("("):
        cand = history_video_choice if os.path.isabs(history_video_choice) else os.path.join(outputs_dir, history_video_choice)
        if os.path.exists(cand):
            hist_vid = cand

    target_video = None
    if "máy tính" in str(video_source_mode).lower():
        target_video = custom_vid
    elif "outputs" in str(video_source_mode).lower():
        target_video = hist_vid
    else:
        if hist_vid and gen_vid and os.path.basename(hist_vid) != os.path.basename(gen_vid):
            target_video = hist_vid
        elif gen_vid and os.path.exists(gen_vid):
            target_video = gen_vid
        elif hist_vid and os.path.exists(hist_vid):
            target_video = hist_vid

    if not target_video:
        target_video = custom_vid or hist_vid or gen_vid

    if not target_video or not os.path.exists(target_video):
        return f"❌ Lỗi: Không tìm thấy file video hợp lệ để đăng! (Nguồn đang chọn: {video_source_mode})"

    # Tìm token theo Hồ Sơ Kênh đã chọn
    from ..pipeline.channel_profiles import get_channel_token_file, get_channel_profile, DEFAULT_TAGS
    token_file = get_channel_token_file(channel_profile)
    service = get_youtube_service(token_path=token_file)

    if service is None:
        return (
            f"⚠️ CHƯA CÓ TOKEN XÁC THỰC YOUTUBE!\n"
            f"Vui lòng thực hiện 'Bước 1 & Bước 2' ở TAB 3 để xác thực tài khoản YouTube (Token: {os.path.basename(token_file)})."
        )

    try:
        prof = get_channel_profile(channel_profile) if channel_profile else {}
        clean_tags = tags.strip() if (tags and isinstance(tags, str) and len(tags.strip()) > 3) else prof.get("tags", DEFAULT_TAGS)
        tag_list = [t.strip() for t in clean_tags.split(",") if t.strip()]

        final_title = title.strip()[:100] if title else f"Audiobook - {os.path.basename(target_video)}"
        final_description = description.strip() if description else prof.get("desc_template", "Audiobook tự động sản xuất bởi AI.")

        status_body = {"selfDeclaredMadeForKids": False}
        scheduled_iso_str = None
        sched_desc = ""

        if is_schedule:
            scheduled_iso_str, sched_desc = calculate_schedule_iso(custom_schedule_time)
            status_body["privacyStatus"] = "private"
            status_body["publishAt"] = scheduled_iso_str
        else:
            status_body["privacyStatus"] = "public" if "công khai" in str(privacy_status).lower() else ("unlisted" if "không công khai" in str(privacy_status).lower() else "private")

        body = {
            "snippet": {
                "title": final_title,
                "description": final_description[:5000],
                "tags": tag_list,
                "categoryId": "27"
            },
            "status": status_body
        }

        media = MediaFileUpload(target_video, chunksize=CHUNK_SIZE, resumable=True)
        request = service.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        retry_count = 0
        while response is None:
            try:
                status, response = request.next_chunk()
            except HttpError as http_err:
                if http_err.resp.status in RETRIABLE_STATUS_CODES:
                    retry_count += 1
                    if retry_count > MAX_RETRIES:
                        return f"❌ Máy chủ YouTube gặp sự cố ({http_err.resp.status}) sau {MAX_RETRIES} lần thử lại."
                    sleep_sec = (2 ** retry_count) + random.random()
                    time.sleep(sleep_sec)
                else:
                    return parse_youtube_http_error(http_err)
            except Exception as net_err:
                retry_count += 1
                if retry_count > MAX_RETRIES:
                    return f"❌ Mất kết nối khi tải video: {net_err}"
                time.sleep(3)

        vid = response.get("id")
        video_url = f"https://youtu.be/{vid}"

        # Gán thumbnail
        thumb_status_msg = ""
        try:
            cand_thumb = None
            resolved_custom_thumb = resolve_file_path(custom_thumbnail) if custom_thumbnail else None
            if resolved_custom_thumb and os.path.exists(resolved_custom_thumb):
                cand_thumb = resolved_custom_thumb
            elif target_video:
                base_name = os.path.splitext(os.path.basename(target_video))[0]
                session_cand = base_name
                for pfx in ["video_", "final_video_", "rendered_"]:
                    if base_name.startswith(pfx):
                        session_cand = base_name[len(pfx):]
                        break

                candidates = [
                    os.path.join(outputs_dir, f"thumbnail_{session_cand}.jpg"),
                    os.path.join(outputs_dir, f"thumbnail_{session_cand}.png"),
                    os.path.join(outputs_dir, f"thumbnail_{base_name}.jpg"),
                    os.path.join(outputs_dir, f"thumbnail_{base_name}.png"),
                    os.path.join(outputs_dir, f"{base_name}.jpg"),
                    os.path.join(outputs_dir, f"{base_name}.png"),
                ]
                for c in candidates:
                    if os.path.exists(c):
                        cand_thumb = c
                        break

            if not cand_thumb:
                cand_latest = os.path.join(outputs_dir, "thumbnail_latest.jpg")
                if os.path.exists(cand_latest):
                    cand_thumb = cand_latest

            if cand_thumb and os.path.exists(cand_thumb):
                mime = "image/png" if str(cand_thumb).lower().endswith(".png") else "image/jpeg"
                service.thumbnails().set(
                    videoId=vid,
                    media_body=MediaFileUpload(cand_thumb, mimetype=mime)
                ).execute()
                thumb_status_msg = chr(10) + f"🖼️ ĐÃ TỰ ĐỘNG GÁN THUMBNAIL CTR BOOSTER: {os.path.basename(cand_thumb)}"
        except Exception as e_th:
            thumb_status_msg = chr(10) + f"Lưu ý Thumbnail: {e_th}"
        schedule_info_msg = ""
        if is_schedule and scheduled_iso_str:
            schedule_info_msg = f"\n⏰ ĐÃ HẸN GIỜ CÔNG KHAI: {sched_desc}"

        team_log_msg = ""
        ok_rec, rec_path = record_successful_publish(
            script_name=final_title if final_title else os.path.basename(target_video),
            editor_email=editor_email,
            schedule_time=sched_desc if (is_schedule and sched_desc) else ("Đăng công khai ngay" if not is_schedule else scheduled_iso_str),
            video_url=video_url,
            folder_path=shared_drive_folder
        )
        if ok_rec:
            team_log_msg = f"\n📊 ĐÃ GHI NHẬN TIẾN ĐỘ VÀO BẢNG: {os.path.basename(rec_path)}"

        return (
            f"🎉 ĐÃ TẢI LÊN YOUTUBE THÀNH CÔNG!\n"
            f"- File video: {os.path.basename(target_video)}\n"
            f"- Tiêu đề: {final_title}\n"
            f"- Video ID: {vid}\n"
            f"- Link xem video: {video_url}\n"
            f"- Chế độ: {'LÊN LỊCH TỰ ĐỘNG' if is_schedule else status_body['privacyStatus'].upper()}"
            f"{schedule_info_msg}{thumb_status_msg}{team_log_msg}"
        )

    except HttpError as err:
        return parse_youtube_http_error(err)
    except Exception as e:
        return f"❌ Lỗi tải lên YouTube: {e}"


def upload_video_to_youtube(video_file_path: str, title: str, description: str, tags: str = "", is_schedule: bool = False, custom_schedule_time: str = "", privacy_status: str = "private", editor_email: str = "", shared_drive_folder: str = "", outputs_dir: str = "outputs", channel_profile: str = "", progress_callback: Optional[Callable[[float, str], None]] = None) -> str:
    """Tương thích ngược."""
    return upload_to_youtube(
        "outputs", video_file_path, video_file_path, None,
        title, description, tags, is_schedule, custom_schedule_time,
        privacy_status, editor_email, shared_drive_folder,
        outputs_dir=outputs_dir, channel_profile=channel_profile
    )
