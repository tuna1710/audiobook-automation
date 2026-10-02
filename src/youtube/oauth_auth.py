import os
import re
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Any

# Google OAuth2 Libraries (Tải an toàn / Graceful Fallback)
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    import google_auth_oauthlib.flow
    import googleapiclient.discovery
except ImportError:
    Credentials = None
    Request = None
    google_auth_oauthlib = None
    googleapiclient = None

logger = logging.getLogger("audiobook_automation.youtube_oauth")

# Phạm vi quyền YouTube: Đăng tải, quản lý thumbnail và quản lý video
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

TOKEN_CANDIDATES = [
    "token.json",
    "youtube_token.json",
    "/content/token.json",
    "/content/youtube_token.json",
    "/content/drive/MyDrive/token.json",
    "/content/drive/MyDrive/youtube_token.json",
    "configs/token.json",
    "configs/youtube_token.json"
]

CLIENT_SECRET_CANDIDATES = [
    "client_secret.json",
    "client_secrets.json",
    "/content/client_secret.json",
    "/content/client_secrets.json",
    "/content/drive/MyDrive/client_secret.json",
    "/content/drive/MyDrive/client_secrets.json",
    "configs/client_secret.json",
    "configs/client_secrets.json"
]

# Lưu trữ phiên Flow OAuth đang hoạt động
_active_oauth_flow: Optional[Any] = None


def resolve_file_path(f: Any) -> Optional[str]:
    """
    Chuẩn hóa đường dẫn file từ nhiều kiểu đối tượng khác nhau (str, Gradio FileData, dict, tempfile).
    """
    if not f:
        return None
    if isinstance(f, str):
        return f.strip()
    if hasattr(f, "name") and isinstance(f.name, str):
        return f.name.strip()
    if isinstance(f, dict) and "name" in f:
        return str(f["name"]).strip()
    return str(f).strip()


def find_client_secret_file(custom_upload: Any = None) -> str:
    """
    Tự động dò tìm file client_secret.json từ file tải lên hoặc các đường dẫn mặc định trong dự án.
    """
    resolved_custom = resolve_file_path(custom_upload)
    if resolved_custom and os.path.exists(resolved_custom):
        return resolved_custom

    for candidate in CLIENT_SECRET_CANDIDATES:
        if os.path.exists(candidate):
            return candidate

    return "client_secret.json"


def find_token_file() -> Optional[str]:
    """
    Tự động tìm file token hợp lệ đã lưu trước đó.
    """
    for candidate in TOKEN_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    return None


def calculate_schedule_iso(custom_time_input: str = "") -> Tuple[str, str]:
    """
    Tính toán thời gian hẹn giờ ISO 8601 theo múi giờ Việt Nam (UTC+7),
    đảm bảo mốc thời gian luôn hợp lệ trong tương lai để YouTube API chấp nhận.
    """
    vn_tz = timezone(timedelta(hours=7))
    now_vn = datetime.now(vn_tz)
    target_vn = None

    if custom_time_input and len(str(custom_time_input).strip()) >= 10:
        cleaned_time = str(custom_time_input).strip().replace("/", "-")
        # Tìm kiếm mẫu YYYY-MM-DD HH:MM
        m = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{2})', cleaned_time)
        if m:
            y, mo, d, h, mi = map(int, m.groups())
            try:
                target_vn = datetime(y, mo, d, h, mi, 0, tzinfo=vn_tz)
            except Exception:
                target_vn = None

    # Nếu không nhập hoặc thời điểm trong quá khứ, tự động đặt vào 19:30 tối ngày mai (giờ vàng xem YouTube)
    if target_vn is None or target_vn <= now_vn:
        tmrw = now_vn + timedelta(days=1)
        target_vn = tmrw.replace(hour=19, minute=30, second=0, microsecond=0)

    target_utc = target_vn.astimezone(timezone.utc)
    iso_utc = target_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    desc_vn = target_vn.strftime("%d/%m/%Y lúc %H:%M (Giờ VN)")
    return iso_utc, desc_vn


def get_youtube_auth_url(
    client_secrets_upload: Any = None,
    redirect_uri_input: str = "https://localhost"
) -> Tuple[str, str]:
    """
    BƯỚC 1: Khởi tạo Flow xác thực OAuth2 và sinh đường dẫn đăng nhập Google cho người dùng.
    """
    global _active_oauth_flow
    secrets_file = find_client_secret_file(client_secrets_upload)

    if not os.path.exists(secrets_file):
        return (
            "❌ Không tìm thấy file client_secret.json!\n"
            "Vui lòng tải file client_secret.json lên WebUI hoặc đặt file vào thư mục gốc của dự án.",
            redirect_uri_input
        )

    target_uri = redirect_uri_input.strip() if (redirect_uri_input and len(redirect_uri_input.strip()) > 5) else "https://localhost"

    try:
        _active_oauth_flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            secrets_file,
            scopes=YOUTUBE_SCOPES,
            redirect_uri=target_uri
        )
        auth_url, _ = _active_oauth_flow.authorization_url(prompt="consent", access_type="offline")

        instruction_msg = (
            f"✅ ĐÃ KHỞI TẠO XÁC THỰC THÀNH CÔNG VỚI REDIRECT URI: {target_uri}\n\n"
            f"🔗 BẤM VÀO ĐƯỜNG LINK DƯỚI ĐÂY ĐỂ ĐĂNG NHẬP ỦY QUYỀN GOOGLE:\n"
            f"{auth_url}\n\n"
            f"👉 HƯỚNG DẪN 3 BƯỚC ĐƠN GIẢN:\n"
            f"1. Mở link trên trên trình duyệt của bạn và chọn tài khoản Google sở hữu Kênh YouTube.\n"
            f"2. Bấm 'Cho phép' (Allow) cấp quyền. Trình duyệt sẽ chuyển hướng sang một trang báo không kết nối được ({target_uri}).\n"
            f"3. COPY TOÀN BỘ ĐOẠN URL trên thanh địa chỉ (bắt đầu bằng {target_uri}/?state=...&code=...)\n"
            f"👉 Dán TOÀN BỘ link đó vào ô 'BƯỚC 2' bên dưới rồi bấm nút Xác thực & Lưu Token!"
        )
        return instruction_msg, target_uri
    except Exception as e:
        logger.error(f"Lỗi khởi tạo flow OAuth: {e}")
        return f"❌ Lỗi khởi tạo quy trình xác thực OAuth: {e}", target_uri


def verify_oauth_code_and_save_token(
    response_url_input: str,
    redirect_uri_used: str = "https://localhost",
    save_path: str = "token.json"
) -> str:
    """
    BƯỚC 2: Nhận URL chuyển hướng từ người dùng, đổi mã authorization code lấy Token và lưu lại vĩnh viễn.
    """
    global _active_oauth_flow
    if not response_url_input or len(response_url_input.strip()) < 5:
        return "❌ Vui lòng dán toàn bộ đường link bắt đầu bằng https://localhost/?state=... vào ô!"

    raw_input = response_url_input.strip()
    secrets_file = find_client_secret_file()

    if _active_oauth_flow is None:
        if os.path.exists(secrets_file):
            try:
                _active_oauth_flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                    secrets_file,
                    scopes=YOUTUBE_SCOPES,
                    redirect_uri=redirect_uri_used if redirect_uri_used else "https://localhost"
                )
            except Exception as e:
                return f"❌ Không thể tái tạo Flow xác thực từ {secrets_file}: {e}"
        else:
            return "❌ Thiếu file client_secret.json! Vui lòng tải file lên trước khi xác thực."

    try:
        # Nếu người dùng dán toàn bộ URL
        if raw_input.startswith("http://") or raw_input.startswith("https://"):
            _active_oauth_flow.fetch_token(authorization_response=raw_input)
        else:
            # Nếu người dùng chỉ dán mã code thuần
            _active_oauth_flow.fetch_token(code=raw_input)

        creds = _active_oauth_flow.credentials

        # Lưu đồng thời cả token.json và youtube_token.json để đảm bảo tương thích mọi module
        paths_to_save = list(set([save_path, "token.json", "youtube_token.json"]))
        for p in paths_to_save:
            try:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())
            except Exception as e_write:
                logger.warning(f"Không thể ghi token vào {p}: {e_write}")

        return (
            "🎉 XÁC THỰC THÀNH CÔNG!\n"
            f"Đã lưu token xác thực vĩnh viễn vào '{save_path}' & 'youtube_token.json'.\n"
            "Bây giờ hệ thống đã sẵn sàng đăng và lên lịch video lên YouTube bất kỳ lúc nào!"
        )
    except Exception as e:
        logger.error(f"Lỗi xác thực code đổi token: {e}")
        return (
            f"❌ Lỗi đổi token: {e}\n"
            "(Mẹo: Mã code chỉ sử dụng được 1 lần duy nhất. Nếu quá thời gian, vui lòng bấm BƯỚC 1 để lấy link mới)."
        )


def get_youtube_service(
    client_secrets_path: Optional[str] = None,
    token_path: Optional[str] = None
) -> Optional[Any]:
    """
    Khởi tạo và trả về YouTube API Client (v3) đã xác thực, tự động làm mới token nếu đã hết hạn.
    """
    actual_token = token_path if (token_path and os.path.exists(token_path)) else find_token_file()

    if not actual_token:
        logger.warning("Không tìm thấy file token xác thực YouTube nào.")
        return None

    creds = None
    try:
        creds = Credentials.from_authorized_user_file(actual_token, YOUTUBE_SCOPES)
    except Exception as e:
        logger.error(f"Lỗi đọc file token {actual_token}: {e}")
        return None

    # Tự động làm mới nếu token hết hạn nhưng vẫn còn refresh_token
    if creds and creds.expired and creds.refresh_token:
        try:
            logger.info("Token đã hết hạn. Đang tự động làm mới (refresh) token...")
            creds.refresh(Request())
            # Lưu lại token mới
            for p in list(set([actual_token, "token.json", "youtube_token.json"])):
                try:
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(creds.to_json())
                except Exception:
                    pass
            logger.info("Đã làm mới token thành công!")
        except Exception as e_refresh:
            logger.error(f"Không thể làm mới token: {e_refresh}")
            return None

    if not creds or not creds.valid:
        logger.warning("Thông tin xác thực YouTube không hợp lệ.")
        return None

    try:
        service = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        return service
    except Exception as build_err:
        logger.error(f"Lỗi khởi tạo YouTube service: {build_err}")
        return None
