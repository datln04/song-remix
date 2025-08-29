import re
import subprocess
from typing import List, Dict, Optional

# We use yt-dlp for YouTube and TikTok via metadata extraction.


def search_youtube_covers(query: str, num_covers: int = 5) -> List[Dict]:
    """Search YouTube for cover videos using yt-dlp. Returns list sorted by view_count desc.

    Each item: {"id","title","webpage_url","duration","view_count","like_count","uploader"}
    """
    overfetch = max(num_covers * 3, 15)
    ytdlp_query = f"ytsearch{overfetch}:{query} cover"
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--skip-download",
        "--ignore-errors",
        "--no-warnings",
        "--default-search",
        "ytsearch",
        ytdlp_query,
    ]
    items: List[Dict] = []
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                import json
                data = json.loads(line)
                if not data:
                    continue
                dur = data.get("duration") or 0
                if dur and dur > 8 * 60:
                    continue
                title = (data.get("title") or "").lower()
                items.append({
                    "id": data.get("id"),
                    "title": data.get("title"),
                    "webpage_url": data.get("webpage_url"),
                    "duration": dur,
                    "view_count": data.get("view_count") or 0,
                    "like_count": data.get("like_count") or 0,
                    "uploader": data.get("uploader"),
                })
            except Exception:
                continue
        items.sort(key=lambda x: (x.get("view_count", 0), x.get("like_count", 0), - (x.get("duration") or 0)), reverse=True)
        return items[:num_covers]
    except FileNotFoundError:
        raise RuntimeError("yt-dlp not installed. Please install requirements.txt")


def search_tiktok_covers(query: str, num_covers: int = 5, cookies: Optional[str] = None) -> List[Dict]:
    """Search TikTok for cover videos by scraping the public search page via yt-dlp.
    Returns list sorted by view_count/diggCount (likes) desc.
    """
    # Build TikTok search URL; let yt-dlp extract items from the page
    search_url = f"https://www.tiktok.com/search?q={query}%20cover"
    cmd = ["yt-dlp", "--dump-json", "--skip-download", "--ignore-errors", "--no-warnings", search_url]
    if cookies:
        cmd += ["--cookies", cookies]
    items: List[Dict] = []
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                import json
                data = json.loads(line)
                if not data:
                    continue
                dur = data.get("duration") or 0
                if dur and dur > 8 * 60:
                    continue
                items.append({
                    "id": data.get("id"),
                    "title": data.get("title"),
                    "webpage_url": data.get("webpage_url") or data.get("url"),
                    "duration": dur,
                    "view_count": data.get("view_count") or (data.get("stats") or {}).get("playCount", 0) or 0,
                    "like_count": data.get("like_count") or (data.get("stats") or {}).get("diggCount", 0) or 0,
                    "uploader": data.get("uploader") or data.get("uploader_id"),
                })
            except Exception:
                continue
        items.sort(key=lambda x: (x.get("view_count", 0), x.get("like_count", 0), - (x.get("duration") or 0)), reverse=True)
        return items[:num_covers]
    except FileNotFoundError:
        raise RuntimeError("yt-dlp not installed. Please install requirements.txt")


def build_query(song_name: str) -> str:
    return f"{song_name} cover"
