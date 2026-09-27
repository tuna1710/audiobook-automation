import os
from .oauth_auth import get_youtube_service, calculate_schedule_iso
from .gdrive_logger import record_successful_publish

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
    outputs_dir: str = "outputs"
) -> str:
    """
    Tải video lên YouTube, tự động đặt metadata, hẹn giờ và gán Thumbnail CTR Booster.
    """
    if not video_file_path or not os.path.exists(video_file_path):
        return f"❌ Lỗi: Không tìm thấy file video tại '{video_file_path}'"

    youtube = get_youtube_service()
    if not youtube:
        return "❌ Lỗi: Chưa xác thực YouTube OAuth2 (Cần file youtube_token.json hợp lệ)."

    from googleapiclient.http import MediaFileUpload

    snippet = {
        "title": title[:100] if title else "Audiobook Tự Động",
        "description": description if description else "",
        "tags": [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    }

    status = {"privacyStatus": privacy_status}
    scheduled_iso_str = ""
    sched_desc = ""

    if is_schedule:
        scheduled_iso_str, sched_desc = calculate_schedule_iso(custom_schedule_time)
        status["privacyStatus"] = "private"
        status["publishAt"] = scheduled_iso_str

    body = {"snippet": snippet, "status": status}

    try:
        media = MediaFileUpload(video_file_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)

        response = None
        while response is None:
            _, response = request.next_chunk()

        vid = response.get("id")
        video_url = f"https://youtu.be/{vid}"

        # TỰ ĐỘNG GÁN THUMBNAIL YOUTUBE (CTR BOOSTER)
        thumb_status_msg = ""
        try:
            cand_thumb = os.path.join(outputs_dir, "thumbnail_latest.jpg")
            if os.path.exists(cand_thumb):
                youtube.thumbnails().set(
                    videoId=vid,
                    media_body=MediaFileUpload(cand_thumb, mimetype="image/jpeg")
                ).execute()
                thumb_status_msg = f"\n🖼️ ĐÃ TỰ ĐỘNG GÁN THUMBNAIL CTR BOOSTER: {os.path.basename(cand_thumb)}"
        except Exception as e_th:
            thumb_status_msg = f"\n⚠️ Lưu ý Thumbnail: {e_th}"

        # GHI NHẬN TIẾN ĐỘ
        team_log_msg = ""
        ok_rec, rec_path = record_successful_publish(
            script_name=title if title else os.path.basename(video_file_path),
            editor_email=editor_email,
            schedule_time=sched_desc if is_schedule else "Công khai ngay",
            video_url=video_url,
            folder_path=shared_drive_folder
        )
        if ok_rec:
            team_log_msg = f"\n📊 Đã ghi nhận tiến độ vào: {os.path.basename(rec_path)}"

        return f"🎉 ĐÃ TẢI LÊN YOUTUBE THÀNH CÔNG!\n- Video ID: {vid}\n- Link xem: {video_url}\n- Chế độ: {'LÊN LỊCH' if is_schedule else privacy_status.upper()}{thumb_status_msg}{team_log_msg}"
    except Exception as e:
        return f"❌ Lỗi tải lên YouTube: {e}"
