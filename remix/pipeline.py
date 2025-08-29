import os
import json
import subprocess
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

from .lyrics import split_lyrics_lines, fetch_lyrics_genius
from .search import search_youtube_covers, search_tiktok_covers, build_query
from .asr_align import transcribe_audio, align_lyrics_to_words
from .edit import cut_segments, concat_with_crossfade, build_subtitle_clip, export_video
from moviepy import CompositeVideoClip


@dataclass
class CoverMeta:
    title: str
    url: str
    duration: float
    view_count: int


@dataclass
class Config:
    song_name: str
    lyrics: Optional[str] = None
    num_covers: int = 5
    model_size: str = "small"
    out_path: str = "final_remix.mp4"
    fps: int = 30
    resolution: str = "1080p"  # not enforced in this prototype
    add_subtitles: bool = True
    local_videos: Optional[List[str]] = None


class RemixPipeline:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.workdir = Path("work")
        self.workdir.mkdir(exist_ok=True)

    def ensure_deps(self):
        # Ensure ffmpeg exists
        try:
            subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
        except Exception:
            raise RuntimeError("ffmpeg is required")

    def get_lyrics(self) -> str:
        if self.cfg.lyrics and self.cfg.lyrics.strip():
            return self.cfg.lyrics
        fetched = fetch_lyrics_genius(self.cfg.song_name)
        if not fetched:
            raise RuntimeError("Lyrics not provided and could not fetch from Genius. Set GENIUS_ACCESS_TOKEN or provide lyrics.")
        return fetched

    def search_covers(self) -> List[CoverMeta]:
        # Prefer TikTok for fewer bot prevention issues. Fall back to YouTube.
        query = build_query(self.cfg.song_name)
        items = search_tiktok_covers(query, num_covers=self.cfg.num_covers)
        if not items:
            items = search_youtube_covers(query, num_covers=self.cfg.num_covers)
        covers = [CoverMeta(
            title=it.get("title"), url=it.get("webpage_url"), duration=it.get("duration") or 0.0, view_count=it.get("view_count") or 0
        ) for it in items]
        return covers

    def download_video(self, url: str, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_tmpl = str(out_dir / "%(id)s.%(ext)s")
        formats = [
            # Prefer mp4 for easy processing
            "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
            "18/22",  # progressive mp4 360p/720p (YouTube)
            "best",
        ]
        last_err = None
        for fmt in formats:
            cmd = [
                "yt-dlp", url,
                "-f", fmt,
                "-o", out_tmpl,
                "--no-playlist",
                "--geo-bypass",
                "--force-ipv4",
                "-N", "4",
                "-R", "3",
                "--fragment-retries", "3",
            ]
            try:
                subprocess.run(cmd, check=True)
                # pick the largest mp4
                mp4s = list(out_dir.glob("*.mp4"))
                if mp4s:
                    return sorted(mp4s, key=lambda p: p.stat().st_size, reverse=True)[0]
                vids = list(out_dir.glob("*.*"))
                if vids:
                    return sorted(vids, key=lambda p: p.stat().st_size, reverse=True)[0]
            except subprocess.CalledProcessError as e:
                last_err = e
                continue
        raise RuntimeError(f"Failed to download video from {url}: {last_err}")

    def extract_audio(self, video_path: Path) -> Path:
        audio_path = video_path.with_suffix('.wav')
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-ac", "1", "-ar", "16000", str(audio_path)
        ]
        subprocess.run(cmd, check=True)
        return audio_path

    def assign_segments(self, aligned_by_cover: List[List[Dict]]) -> List[Dict]:
        # aligned_by_cover is parallel to covers order
        assigned = []
        cover_idx = 0
        for cover_lines in zip(*aligned_by_cover):
            # cover_lines is a tuple of dicts across covers for the same line
            seg = cover_lines[cover_idx % len(cover_lines)]
            assigned.append(seg)
            cover_idx += 1
        return assigned

    def run(self):
        self.ensure_deps()
        lyrics = self.get_lyrics()
        lines = split_lyrics_lines(lyrics)
        if self.cfg.local_videos:
            video_files = [Path(p) for p in self.cfg.local_videos]
        else:
            covers = self.search_covers()
            if not covers:
                raise RuntimeError("No covers found")
            video_files = []
            for c in covers:
                try:
                    vpath = self.download_video(c.url, self.workdir / "videos")
                    video_files.append(vpath)
                except Exception as e:
                    print(f"Skipping cover '{c.title}': {e}")
                    continue
            if not video_files:
                raise RuntimeError("No videos available. Provide --local_videos paths as a fallback.")

        aligned_per_cover: List[List[Dict]] = []
        for vpath in video_files:
            try:
                apath = self.extract_audio(vpath)
                words = transcribe_audio(str(apath), model_size=self.cfg.model_size)
                aligned = align_lyrics_to_words(lines, words)
                aligned_per_cover.append(aligned)
            except Exception as e:
                print(f"Skipping video {vpath}: {e}")
                continue
        if not aligned_per_cover:
            raise RuntimeError("Failed to process any videos (transcription/alignment failed). Try different inputs.")

        # assign per line, rotating covers
        assigned: List[Dict] = []
        for idx, line in enumerate(lines):
            ci = idx % len(aligned_per_cover)
            seg = aligned_per_cover[ci][idx]
            seg = dict(seg)
            seg["video_path"] = str(video_files[ci])
            assigned.append(seg)

        # cut segments and build final
        video_clips = []
        for seg in assigned:
            clips = cut_segments(seg["video_path"], [seg], fade=0.15)
            if clips:
                video_clips.extend(clips)
        if not video_clips:
            raise RuntimeError("No segments cut")
        final = concat_with_crossfade(video_clips, fade=0.15)
        # enforce resolution if requested
        try:
            if isinstance(self.cfg.resolution, str) and self.cfg.resolution.endswith('p'):
                target_h = int(self.cfg.resolution[:-1])
                if final.h != target_h:
                    final = final.resize(height=target_h)
        except Exception:
            pass
        if self.cfg.add_subtitles:
            sub = build_subtitle_clip(assigned, size=(final.w, final.h))
            if sub is not None:
                final = CompositeVideoClip([final, sub.set_duration(final.duration)])

        export_video(final, self.cfg.out_path, fps=self.cfg.fps)
        return str(self.cfg.out_path)
