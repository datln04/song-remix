import os
import re
from typing import List, Optional
import requests
from unidecode import unidecode

# Simple lyrics utilities and optional Genius fetch

GENIUS_API_URL = "https://api.genius.com"


def normalize_text(s: str) -> str:
    s = unidecode(s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9\n\s'-]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def split_lyrics_lines(lyrics: str) -> List[str]:
    # Keep line breaks, strip empty lines
    lines = [ln.strip() for ln in lyrics.splitlines()]
    lines = [ln for ln in lines if ln]
    return lines


def fetch_lyrics_genius(song_name: str, artist: Optional[str] = None, token: Optional[str] = None) -> Optional[str]:
    token = token or os.getenv("GENIUS_ACCESS_TOKEN")
    if not token:
        return None
    headers = {"Authorization": f"Bearer {token}"}
    q = song_name if not artist else f"{song_name} {artist}"
    resp = requests.get(f"{GENIUS_API_URL}/search", params={"q": q}, headers=headers, timeout=15)
    if resp.status_code != 200:
        return None
    data = resp.json()
    hits = data.get("response", {}).get("hits", [])
    if not hits:
        return None
    song = hits[0].get("result", {})
    url = song.get("url")
    if not url:
        return None
    # Genius HTML scraping for lyrics (simple approach)
    try:
        html = requests.get(url, timeout=15).text
        # crude extraction: look for data-lyrics-container divs
        chunks = re.findall(r'<div data-lyrics-container="true".*?</div>', html, flags=re.DOTALL)
        text = []
        for ch in chunks:
            # remove tags
            t = re.sub(r"<.*?>", "", ch)
            t = t.replace("\xa0", " ")
            text.append(t)
        lyrics = "\n".join(text).strip()
        return lyrics or None
    except Exception:
        return None
