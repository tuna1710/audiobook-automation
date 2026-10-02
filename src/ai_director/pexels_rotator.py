import os
import re
import json
import random
import urllib.parse
import urllib.request
from typing import List, Set, Optional

DEFAULT_PEXELS_KEYS = [
    "ZgMJoHbxcFbQNzKht6rh4lfnvZYzLQX48mhnnGlzHwy1vDXqqvTep6aO",
    "aADpkT4x5udb8uQtBfMdFhssOTOwl2cF24UiG9ozYagXAbfZOLlg8Egz"
]

_USED_VIDEO_URLS: Set[str] = set()


def parse_key_pool(raw_keys_input: str) -> List[str]:
    """Phân tách danh sách Pexels API Keys từ chuỗi text."""
    keys = list(DEFAULT_PEXELS_KEYS)
    if raw_keys_input and isinstance(raw_keys_input, str):
        entries = re.split(r'[,\n\r]+', raw_keys_input)
        for e in entries:
            clean_k = e.strip()
            if len(clean_k) >= 20 and clean_k not in keys:
                keys.append(clean_k)
    return keys


def robust_download_video_file(url: str, dest_path: str) -> bool:
    """Tải file video an toàn với User-Agent chuẩn trình duyệt."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Referer': 'https://coverr.co/'
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=25) as resp, open(dest_path, 'wb') as f:
            while chunk := resp.read(1024 * 1024):
                f.write(chunk)
        return os.path.exists(dest_path) and os.path.getsize(dest_path) > 30000
    except Exception:
        return False


def fetch_pexels_videos_with_rotation(query: str, aspect_ratio: str, key_pool: List[str]) -> List[str]:
    """Tìm video trên Pexels với xoay vòng khóa API và lọc chuẩn tỉ lệ."""
    is_vertical = "9:16" in aspect_ratio
    orientation = "portrait" if is_vertical else "landscape"
    clean_q = urllib.parse.quote(query.strip())
    url = f"https://api.pexels.com/videos/search?query={clean_q}&per_page=15&orientation={orientation}"

    for idx, key in enumerate(key_pool):
        if not key or len(key.strip()) < 20:
            continue
        try:
            req = urllib.request.Request(url, headers={"Authorization": key.strip(), "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                videos = data.get("videos", [])
                valid_links = []
                for v in videos:
                    w, h = v.get("width", 0), v.get("height", 0)
                    if is_vertical and h <= w:
                        continue
                    if not is_vertical and w <= h:
                        continue

                    v_files = v.get("video_files", [])
                    best_url = None
                    for vf in v_files:
                        vw = vf.get("width", 0)
                        vh = vf.get("height", 0)
                        if is_vertical:
                            if vw == 1080 and vh == 1920:
                                best_url = vf.get("link")
                                break
                            elif vw >= 720 and vh > vw:
                                best_url = vf.get("link")
                        else:
                            if vw == 1920 and vh == 1080:
                                best_url = vf.get("link")
                                break
                            elif vw >= 1280 and vw > vh:
                                best_url = vf.get("link")

                    if not best_url and v_files:
                        best_url = v_files[0].get("link")
                    if best_url and best_url not in valid_links:
                        valid_links.append(best_url)

                if valid_links:
                    return valid_links
        except urllib.error.HTTPError as e:
            print(f"⚠️ Pexels Key #{idx+1} chạm hạn ngạch ({e.code}). Tự động chuyển sang Key tiếp theo...")
        except Exception:
            pass

    return []


def fetch_clean_coverr_videos(query: str) -> List[str]:
    """Tìm video miễn phí không bản quyền từ Coverr."""
    try:
        clean_q = urllib.parse.quote(query.strip())
        url = f"https://coverr.co/s?q={clean_q}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            links = re.findall(r'https://cdn\.coverr\.co/videos/[^\s"\'<>]+\.mp4', html)
            clean_links = [
                l for l in links
                if not any(bad in l.lower() for bad in ['paywall', 'modal', 'subscription', 'promo', 'ad-', 'advert', 'temp-coverr', 'shutterstock'])
            ]
            v1080 = [l for l in clean_links if '1080p' in l]
            return list(dict.fromkeys(v1080 if v1080 else clean_links))
    except Exception:
        return []


def fetch_clean_mixkit_videos(keyword: str) -> List[str]:
    """Tìm video miễn phí không bản quyền từ Mixkit."""
    try:
        clean_kw = urllib.parse.quote(keyword.strip())
        url = f"https://mixkit.co/free-stock-video/{clean_kw}/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            mp4s = list(dict.fromkeys(re.findall(r"https://assets\.mixkit\.co/videos/\d+/\d+-(?:1080|720)\.mp4", content)))
            return mp4s
    except Exception:
        return []


def download_unique_stock_video(query: str, aspect_ratio: str, key_pool: List[str], out_video: str) -> Optional[str]:
    """Tải video stock duy nhất từ Pexels, Coverr hoặc Mixkit (chống trùng lặp)."""
    global _USED_VIDEO_URLS
    candidates = []

    candidates.extend(fetch_pexels_videos_with_rotation(query, aspect_ratio, key_pool))
    if not candidates:
        candidates.extend(fetch_clean_coverr_videos(query))
    if not candidates:
        candidates.extend(fetch_clean_mixkit_videos("night"))

    selected_url = None
    for url in candidates:
        if url not in _USED_VIDEO_URLS:
            selected_url = url
            break

    if not selected_url and candidates:
        selected_url = random.choice(candidates)

    if selected_url:
        ok = robust_download_video_file(selected_url, out_video)
        if ok:
            _USED_VIDEO_URLS.add(selected_url)
            return out_video

    return None


class PexelsRotator:
    """Class bọc tương thích ngược."""
    def __init__(self, api_keys_input: str = ""):
        self.key_pool = parse_key_pool(api_keys_input)

    def search_and_download_video(self, query: str, output_path: str, orientation: str = "landscape", min_duration: int = 5) -> str:
        ratio = "9:16" if orientation == "portrait" else "16:9"
        res = download_unique_stock_video(query, ratio, self.key_pool, output_path)
        return res if res else ""
