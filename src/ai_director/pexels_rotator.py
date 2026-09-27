import os
import requests
import random

class PexelsRotator:
    """
    Quản lý cụm API Key Pexels xoay tua (Round-robin) để tải video stock HD không giới hạn quota.
    """
    def __init__(self, api_keys_input: str = ""):
        self.keys = []
        if api_keys_input:
            self.keys = [k.strip() for k in api_keys_input.replace('\n', ',').split(',') if k.strip()]
        self.curr_idx = 0
        self.used_urls = set()

    def get_next_key(self) -> str:
        if not self.keys:
            return ""
        key = self.keys[self.curr_idx % len(self.keys)]
        self.curr_idx += 1
        return key

    def search_and_download_video(self, query: str, output_path: str, orientation: str = "landscape", min_duration: int = 5) -> str:
        """
        Tìm kiếm video stock trên Pexels theo từ khóa và tải về máy.
        orientation: 'landscape' (16:9) hoặc 'portrait' (9:16)
        """
        key = self.get_next_key()
        if not key:
            return ""

        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": key}
        params = {
            "query": query,
            "per_page": 15,
            "orientation": orientation
        }

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                videos = data.get("videos", [])
                for v in videos:
                    files = v.get("video_files", [])
                    # Tìm file HD
                    best_file = None
                    for f in files:
                        if orientation == "portrait" and f.get("width", 0) < f.get("height", 0):
                            best_file = f.get("link")
                            break
                        elif orientation == "landscape" and f.get("width", 0) > f.get("height", 0):
                            best_file = f.get("link")
                            break

                    if best_file and best_file not in self.used_urls:
                        self.used_urls.add(best_file)
                        # Tải video
                        v_resp = requests.get(best_file, stream=True, timeout=30)
                        if v_resp.status_code == 200:
                            with open(output_path, "wb") as f_out:
                                for chunk in v_resp.iter_content(chunk_size=1024*1024):
                                    if chunk:
                                        f_out.write(chunk)
                            return output_path
        except Exception as e:
            print(f"⚠️ Lỗi Pexels: {e}")

        return ""
