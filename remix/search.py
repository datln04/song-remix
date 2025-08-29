import re
import subprocess
from typing import List, Dict, Optional

# We use yt-dlp for YouTube search. TikTok search via yt-dlp is possible but less stable.
# Strategy: use ytsearch to query and extract metadata without downloading.


def search_youtube_covers(query: str, num_covers: int = 5) -> List[Dict]:
    """Search YouTube for cover videos using yt-dlp. Returns list sorted by view_count desc.

    Each item: {"id","title","webpage_url","duration","view_count","like_count","uploader"}
    """
    # ytsearchN, where N is over-fetch factor to later sort by views and pick top num_covers
    overfetch = max(num_covers * 3, 15)
    ytdlp_query = f"ytsearch{overfetch}:{query} cover"
    # Use --dump-json --skip-download to only retrieve metadata
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
                # basic filtering: prefer videos under 8 minutes to increase ASR speed
                dur = data.get("duration") or 0
                if dur and dur > 8 * 60:
                    continue
                # heuristics: title contains 'cover' or 'acoustic' or 'live' etc.
                title = (data.get("title") or "").lower()
                if not re.search(r"cover|acoustic|live|karaoke|piano|guitar", title):
                    # still allow, but give lower priority later
                    pass
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
        # sort by views desc then likes desc then shorter duration
        items.sort(key=lambda x: (x.get("view_count", 0), x.get("like_count", 0), - (x.get("duration") or 0)), reverse=True)
        return items[:num_covers]
    except FileNotFoundError:
        raise RuntimeError("yt-dlp not installed. Please install requirements.txt")


def build_query(song_name: str) -> str:
    return f"{song_name} cover"
