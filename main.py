import os
import re
import subprocess
import sys
import time
from pathlib import Path


class SilentLogger:

    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


def auto_install_packages():
    required_packages = ["requests", "yt-dlp", "cloudscraper", "gdown"]
    for pkg in required_packages:
        try:
            __import__(pkg)
        except ImportError:
            print(f"⏳ Đang cài đặt thư viện {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


auto_install_packages()

import cloudscraper
import gdown
import requests
import yt_dlp

INPUT_FILE = sys.argv[1] if len(sys.argv) > 1 else "text.txt"
OUTPUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "VIDEOS"
COOKIES_FILE = "cookies.txt"

os.makedirs(OUTPUT_DIR, exist_ok=True)

urls = []
if os.path.exists(INPUT_FILE):
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            found = re.findall(r"(?:https?://|www\.)[^\s\)]+", line)
            for url in found:
                clean_url = url.strip().rstrip('.,;)"\'\xa0')
                if not clean_url.startswith("http"):
                    clean_url = "https://" + clean_url
                urls.append(clean_url)

print(
    f"📌 Tìm thấy {len(urls)} link trong file dữ liệu. Bắt đầu tải theo đúng"
    f" thứ tự 1->{len(urls)}...\n"
)


# ==========================================
# 1. HÀM TẢI YOUTUBE / YOUTUBE SHORTS (CHUYÊN VƯỢT TƯỜNG LỬA CLOUD)
# ==========================================
def download_youtube_smart(url, save_path):
    clean_url = url
    shorts_match = re.search(
        r"(?:youtube\.com/shorts/|youtu\.be/|youtube\.com/watch\?v=)([a-zA-Z0-9_-]+)",
        url,
    )
    video_id = shorts_match.group(1) if shorts_match else None

    if video_id:
        clean_url = f"https://www.youtube.com/watch?v={video_id}"

    # Phương pháp 1: Dùng API Cobalt Proxy (Vượt qua 100% chặn IP Cloud của Youtube)
    try:
        cobalt_instances = [
            "https://api.cobalt.tools/api/json",
            "https://cobalt-api.kwippy.com/api/json",
        ]
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            ),
        }

        for instance in cobalt_instances:
            try:
                res = requests.post(
                    instance,
                    json={"url": clean_url, "videoQuality": "720"},
                    headers=headers,
                    timeout=10,
                )
                data = res.json()
                download_url = data.get("url")
                if download_url:
                    v_res = requests.get(download_url, stream=True, timeout=30)
                    if v_res.status_code == 200:
                        with open(save_path, "wb") as f:
                            for chunk in v_res.iter_content(
                                chunk_size=1024 * 1024
                            ):
                                if chunk:
                                    f.write(chunk)
                        if (
                            os.path.exists(save_path)
                            and os.path.getsize(save_path) > 50000
                        ):
                            return True
            except Exception:
                continue
    except Exception:
        pass

    # Phương pháp 2: yt-dlp giả lập Android Client
    ydl_opts = {
        "outtmpl": save_path,
        "format": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
        "nocheckcertificate": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "logger": SilentLogger(),
        "retries": 10,
        "extractor_args": {"youtube": {"player_client": ["android", "ios"]}},
        "http_headers": {
            "User-Agent": (
                "com.google.android.youtube/19.09.37 (Linux; U; Android 11;"
                " en_US)"
            ),
        },
    }
    if os.path.exists(COOKIES_FILE):
        ydl_opts["cookiefile"] = COOKIES_FILE

    try:
        with open(os.devnull, "w") as devnull:
            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = devnull, devnull
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([clean_url])
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr

        if os.path.exists(save_path) and os.path.getsize(save_path) > 30000:
            return True
    except Exception:
        pass

    return False


# ==========================================
# 2. HÀM TẢI THREADS
# ==========================================
def download_threads_api(url, save_path):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
    }
    scraper = cloudscraper.create_scraper()
    clean_url = re.sub(
        r"threads\.com", "threads.net", url, flags=re.IGNORECASE
    )
    clean_url = re.sub(
        r"/media/?(?:\?.*)?$", "", clean_url, flags=re.IGNORECASE
    )
    clean_url = clean_url.split("?")[0].rstrip("/")

    for attempt in range(3):
        try:
            api_url = (
                "https://api.threadsphotodownloader.com/v2/media?url="
                f"{clean_url}"
            )
            res = scraper.get(api_url, headers=headers, timeout=12).json()
            video_urls = [
                v.get("download_url") or v.get("url")
                for v in res.get("video_urls", [])
                if v
            ]
            if video_urls and video_urls[0]:
                v_data = scraper.get(video_urls[0], timeout=25).content
                if len(v_data) > 10000:
                    with open(save_path, "wb") as f:
                        f.write(v_data)
                    return True
        except Exception:
            time.sleep(1)
    return False


# ==========================================
# 3. HÀM TẢI COLLAB INC & STORYFUL
# ==========================================
def download_collab_inc_web(url, save_path):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Referer": "https://vl.collab.inc/",
        "Origin": "https://vl.collab.inc",
    }
    try:
        scraper = cloudscraper.create_scraper()
        res = scraper.get(url, headers=headers, timeout=15)
        video_matches = re.findall(
            r'https?://[^\s"\']+\.(?:mp4|m3u8)[^\s"\']*', res.text
        )
        for media_url in video_matches:
            media_url = media_url.replace("\\/", "/").replace("&amp;", "&")
            if ".mp4" in media_url and "m3u8" not in media_url:
                v_res = scraper.get(
                    media_url, headers=headers, stream=True, timeout=25
                )
                if v_res.status_code == 200:
                    with open(save_path, "wb") as f:
                        for chunk in v_res.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
                    if (
                        os.path.exists(save_path)
                        and os.path.getsize(save_path) > 100000
                    ):
                        return True
    except Exception:
        pass
    return False


def download_storyful_api(url, save_path):
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://storyful.com/"}
    record_id_match = re.search(r"/record/(\d+)", url)
    record_id = record_id_match.group(1) if record_id_match else None
    scraper = cloudscraper.create_scraper()
    if record_id:
        try:
            api_url = f"https://api.storyful.com/stories/{record_id}"
            res = scraper.get(api_url, headers=headers, timeout=12).json()
            for media in res.get("story", {}).get("media", []):
                video_url = media.get("video_url") or media.get("url")
                if video_url:
                    v_res = scraper.get(
                        video_url, headers=headers, stream=True, timeout=25
                    )
                    if v_res.status_code == 200:
                        with open(save_path, "wb") as f:
                            for chunk in v_res.iter_content(
                                chunk_size=1024 * 1024
                            ):
                                if chunk:
                                    f.write(chunk)
                        if (
                            os.path.exists(save_path)
                            and os.path.getsize(save_path) > 10000
                        ):
                            return True
        except Exception:
            pass
    return False


# ==========================================
# 4. HÀM TẢI INSTAGRAM, TIKTOK, GOOGLE DRIVE & DOUYIN
# ==========================================
def download_gdrive_api(url, save_path):
    try:
        gdown.download(url, save_path, quiet=True, fuzzy=True)
        if os.path.exists(save_path) and os.path.getsize(save_path) > 30000:
            return True
    except Exception:
        pass
    return False


def download_instagram_api(url, save_path):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "*/*",
    }
    clean_url = url.split("?")[0].rstrip("/")

    try:
        dd_url = clean_url.replace("instagram.com", "ddinstagram.com")
        scraper = cloudscraper.create_scraper()
        res = scraper.get(dd_url, headers=headers, timeout=12)
        v_urls = re.findall(r'property="og:video" content="([^"]+)"', res.text)
        if v_urls:
            v_data = scraper.get(
                v_urls[0].replace("&amp;", "&"), timeout=25
            ).content
            if len(v_data) > 100000:
                with open(save_path, "wb") as f:
                    f.write(v_data)
                return True
    except Exception:
        pass

    for attempt in range(2):
        try:
            scraper = cloudscraper.create_scraper()
            res = scraper.post(
                "https://indown.io/fetch",
                data={"link": clean_url, "referer": "https://indown.io/"},
                headers=headers,
                timeout=12,
            )
            v_urls = re.findall(
                r'href="(https?://[^\s"]+\.mp4[^\s"]*)"', res.text
            )
            if v_urls:
                v_data = scraper.get(
                    v_urls[0].replace("&amp;", "&"), timeout=25
                ).content
                if len(v_data) > 100000:
                    with open(save_path, "wb") as f:
                        f.write(v_data)
                    return True
        except Exception:
            time.sleep(1)
    return False


def download_tiktok_api(url, save_path):
    for attempt in range(3):
        try:
            api_url = f"https://www.tikwm.com/api/?url={url}&hd=1"
            res = requests.get(api_url, timeout=12).json()
            if res.get("code") == 0 and res.get("data"):
                v_url = res["data"].get("hdplay") or res["data"].get("play")
                if not v_url.startswith("http"):
                    v_url = "https://www.tikwm.com" + v_url
                v_data = requests.get(v_url, timeout=20).content
                with open(save_path, "wb") as f:
                    f.write(v_data)
                return True
        except Exception:
            time.sleep(1)
    return False


def download_douyin_fast(url, save_path):
    cmd = [
        "yt-dlp",
        url,
        "-o",
        save_path,
        "--no-playlist",
        "--no-progress",
        "--quiet",
        "--no-warnings",
        "--referer",
        "https://www.douyin.com/",
        "--concurrent-fragments",
        "8",
        "--retries",
        "10",
        "--fragment-retries",
        "10",
    ]
    if os.path.exists(COOKIES_FILE):
        cmd.extend(["--cookies", COOKIES_FILE])

    try:
        res = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if (
            res.returncode == 0
            and os.path.exists(save_path)
            and os.path.getsize(save_path) > 30000
        ):
            return True
    except Exception:
        pass

    try:
        api_url = f"https://www.tikwm.com/api/?url={url}&hd=1"
        res = requests.get(api_url, timeout=8).json()
        if res.get("code") == 0 and res.get("data"):
            v_url = res["data"].get("hdplay") or res["data"].get("play")
            if not v_url.startswith("http"):
                v_url = "https://www.tikwm.com" + v_url
            v_res = requests.get(v_url, stream=True, timeout=15)
            if v_res.status_code == 200:
                with open(save_path, "wb") as f:
                    for chunk in v_res.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                if (
                    os.path.exists(save_path)
                    and os.path.getsize(save_path) > 30000
                ):
                    return True
    except Exception:
        pass

    return False


# ==========================================
# 5. VÒNG LẶP ĐIỀU PHỐI TẢI TUẦN TỰ
# ==========================================
for index, url in enumerate(urls, start=1):
    print("--------------------------------------------------")
    print(f"[{index}/{len(urls)}] Đang tải ...: {url}")
    save_path = os.path.join(OUTPUT_DIR, f"{index}.mp4")
    success = False

    # 1. YouTube & YouTube Shorts
    if "youtube.com" in url or "youtu.be" in url:
        if download_youtube_smart(url, save_path):
            print(f"✅ [YouTube HD] Thành công: {index}.mp4")
            success = True

    # 2. Douyin
    elif "douyin.com" in url or "iesdouyin.com" in url:
        if download_douyin_fast(url, save_path):
            print(f"✅ [Douyin HD] Thành công: {index}.mp4")
            success = True

    # 3. Google Drive
    elif "drive.google.com" in url:
        if download_gdrive_api(url, save_path):
            print(f"✅ [Google Drive HD] Thành công: {index}.mp4")
            success = True

    # 4. Threads
    elif "threads" in url.lower():
        if download_threads_api(url, save_path):
            print(f"✅ [Threads HD] Thành công: {index}.mp4")
            success = True

    # 5. Collab.inc
    elif "collab.inc" in url:
        if download_collab_inc_web(url, save_path):
            print(f"✅ [Collab.inc HD] Thành công: {index}.mp4")
            success = True

    # 6. Storyful
    elif "storyful.com" in url:
        if download_storyful_api(url, save_path):
            print(f"✅ [Storyful] Thành công: {index}.mp4")
            success = True

    # 7. Instagram
    elif "instagram.com" in url:
        if download_instagram_api(url, save_path):
            print(f"✅ [Instagram HD] Thành công: {index}.mp4")
            success = True

    # 8. TikTok
    elif "tiktok.com" in url:
        if download_tiktok_api(url, save_path):
            print(f"✅ [TikTok HD] Thành công: {index}.mp4")
            success = True

    # 9. Fallback cho các trang còn lại
    if not success:
        if download_youtube_smart(url, save_path):
            print(f"✅ [Web Video HD] Thành công: {index}.mp4")
            success = True

    if not success:
        print(f"❌ Lỗi: Không thể tải video {index} ({url})")

print("\n Hoàn thành tải videos")
