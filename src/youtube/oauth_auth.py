import os
import json
from datetime import datetime, timedelta, timezone

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

def calculate_schedule_iso(custom_time_input: str = ""):
    """
    Tính toán thời gian hẹn giờ ISO 8601 theo múi giờ Việt Nam (UTC+7).
    """
    vn_tz = timezone(timedelta(hours=7))
    now_vn = datetime.now(vn_tz)
    target_vn = None

    if custom_time_input and len(custom_time_input.strip()) >= 10:
        cleaned_time = custom_time_input.strip().replace("/", "-")
        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M"]:
            try:
                target_vn = datetime.strptime(cleaned_time, fmt).replace(tzinfo=vn_tz)
                break
            except Exception:
                pass

    if target_vn is None or target_vn <= now_vn:
        tmrw = now_vn + timedelta(days=1)
        target_vn = tmrw.replace(hour=20, minute=0, second=0, microsecond=0)

    target_utc = target_vn.astimezone(timezone.utc)
    return target_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), target_vn.strftime("%d/%m/%Y lúc %H:%M")

def get_youtube_service(client_secrets_path: str = "client_secrets.json", token_path: str = "youtube_token.json"):
    """
    Lấy YouTube API client đã xác thực OAuth2.
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    import googleapiclient.discovery

    creds = None
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, YOUTUBE_SCOPES)
        except Exception:
            creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        except Exception:
            creds = None

    if not creds or not creds.valid:
        return None

    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)
