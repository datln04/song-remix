import re
import subprocess
from typing import List, Dict, Optional
import os
import requests


YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY') or os.environ.get('GOOGLE_API_KEY')

USER_AGENT = os.environ.get('YTDLP_UA') or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'

# We use yt-dlp for YouTube and TikTok via metadata extraction.


def search_youtube_covers(query: str, num_covers: int = 5, cookies: Optional[str] = None) -> List[Dict]:
    """Search YouTube for cover videos.
    Prefer the official Data API if YOUTUBE_API_KEY is present; fallback to yt-dlp scraping.

    Each item: {"id","title","webpage_url","duration","view_count","like_count","uploader"}
    """
    items: List[Dict] = []

    if YOUTUBE_API_KEY:
        try:
            # Use Search API to get video IDs
            params = {
                'part': 'snippet',
                'q': f'{query} cover',
                'type': 'video',
                'maxResults': min(50, max(num_covers * 3, 15)),
                'key': YOUTUBE_API_KEY,
                'relevanceLanguage': 'en',
                'safeSearch': 'none',
                'videoDuration': 'short',  # short/medium/long; heuristic
            }
            r = requests.get('https://www.googleapis.com/youtube/v3/search', params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            ids = [it['id']['videoId'] for it in data.get('items', []) if it.get('id', {}).get('videoId')]
            if ids:
                # Fetch stats and duration via Videos API
                params2 = {
                    'part': 'contentDetails,statistics,snippet',
                    'id': ','.join(ids[:50]),
                    'key': YOUTUBE_API_KEY,
                }
                r2 = requests.get('https://www.googleapis.com/youtube/v3/videos', params=params2, timeout=15)
                r2.raise_for_status()
                vdata = {it['id']: it for it in r2.json().get('items', [])}
                import isodate
                for vid in ids:
                    it = vdata.get(vid)
                    if not it:
                        continue
                    cd = it.get('contentDetails', {})
                    dur_iso = cd.get('duration') or 'PT0S'
                    try:
                        dur = isodate.parse_duration(dur_iso).total_seconds()
                    except Exception:
                        dur = 0
                    if dur and dur > 8 * 60:
                        continue
                    snip = it.get('snippet', {})
                    stats = it.get('statistics', {})
                    items.append({
                        'id': vid,
                        'title': snip.get('title'),
                        'webpage_url': f'https://www.youtube.com/watch?v={vid}',
                        'duration': dur,
                        'view_count': int(stats.get('viewCount', 0) or 0),
                        'like_count': int(stats.get('likeCount', 0) or 0),
                        'uploader': snip.get('channelTitle'),
                    })
                items.sort(key=lambda x: (x.get('view_count', 0), x.get('like_count', 0), - (x.get('duration') or 0)), reverse=True)
                return items[:num_covers]
        except Exception:
            # Fall back to yt-dlp
            pass

    # Fallback: yt-dlp search scraping
    overfetch = max(num_covers * 3, 15)
    ytdlp_query = f"ytsearch{overfetch}:{query} cover"
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--skip-download",
        "--ignore-errors",
        "--no-warnings",
        "--user-agent", USER_AGENT,
        "--default-search",
        "ytsearch",
        ytdlp_query,
    ]
    if cookies:
        cmd += ["--cookies", cookies]
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
