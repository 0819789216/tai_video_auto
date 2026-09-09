import os
import re
import subprocess
import sys
import time
from pathlib import Path

# ==========================================
# 1. KIỂM TRA VÀ TỰ ĐỘNG CÀI THƯ VIỆN CẦN THIẾT
# ==========================================
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

INPUT_FILE = "text.txt"
OUTPUT_DIR = "VIDEOS"
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
    f"📌 Tìm thấy {len(urls)} link trong file {INPUT_FILE}. Bắt đầu tải theo đúng thứ tự 1->{len(urls)}...\n"
)

# ==========================================
# 2. HÀM TẢI THREADS
# ==========================================
def download_threads_api(url, save_path):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }
    scraper = cloudscraper.create_scraper()
    clean_url = re.sub(r"threads\.com", "threads.net", url, flags=re.IGNORECASE)
    clean_url = re.sub(
        r"/media/?(?:\?.*)?$", "", clean_url, flags=re.IGNORECASE
    )
    clean_url = clean_url.split("?")[0].rstrip("/")

    for attempt in range(3):
        try:
            api_url = f"https://api.threadsphotodownloader.com/v2/media?url={clean_url}"
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
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
                        for chunk in v_res.iter_content(
                            chunk_size=1024 * 1024
                        ):
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
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}
    clean_url = url.split("?")[0].rstrip("/")
    for attempt in range(3):
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
    print(f"--------------------------------------------------")
    print(f"[{index}/{len(urls)}] Đang tải ...: {url}")
    save_path = os.path.join(OUTPUT_DIR, f"{index}.mp4")
    success = False

    # 1. Douyin
    if "douyin.com" in url or "iesdouyin.com" in url:
        if download_douyin_fast(url, save_path):
            print(f"✅ [Douyin HD] Thành công: {index}.mp4")
            success = True

    # 2. Google Drive
    elif "drive.google.com" in url:
        if download_gdrive_api(url, save_path):
            print(f"✅ [Google Drive HD] Thành công: {index}.mp4")
            success = True

    # 3. Threads
    elif "threads" in url.lower():
        if download_threads_api(url, save_path):
            print(f"✅ [Threads HD] Thành công: {index}.mp4")
            success = True

    # 4. Collab.inc
    elif "collab.inc" in url:
        if download_collab_inc_web(url, save_path):
            print(f"✅ [Collab.inc HD] Thành công: {index}.mp4")
            success = True

    # 5. Storyful
    elif "storyful.com" in url:
        if download_storyful_api(url, save_path):
            print(f"✅ [Storyful] Thành công: {index}.mp4")
            success = True

    # 6. Instagram
    elif "instagram.com" in url:
        if download_instagram_api(url, save_path):
            print(f"✅ [Instagram HD] Thành công: {index}.mp4")
            success = True

    # 7. TikTok
    elif "tiktok.com" in url:
        if download_tiktok_api(url, save_path):
            print(f"✅ [TikTok HD] Thành công: {index}.mp4")
            success = True

    # 8. Fallback: YouTube, Facebook & Tất cả trang còn lại
    if not success:
        ydl_opts = {
            "outtmpl": os.path.join(OUTPUT_DIR, f"{index}.%(ext)s"),
            "format": "best[ext=mp4]/best",
            "nocheckcertificate": True,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "retries": 5,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            },
        }
        if os.path.exists(COOKIES_FILE):
            ydl_opts["cookiefile"] = COOKIES_FILE

        try:
            # Điều hướng toàn bộ đầu ra tiêu chuẩn để khóa dòng log phần trăm %
            with open(os.devnull, 'w') as devnull:
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = devnull
                sys.stderr = devnull
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
            print(f"✅ [YouTube/FB/Web HD] Thành công: {index}.mp4")
            success = True
        except Exception:
            pass

    if not success:
        print(f"❌ Lỗi: Không thể tải video {index} ({url})")

print("\n Hoàn thành tải videos")
