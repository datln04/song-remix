import os
import subprocess
from typing import List, Dict, Optional
from moviepy import VideoFileClip, concatenate_videoclips, CompositeVideoClip, TextClip


FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")


def cut_segments(video_path: str, segments: List[Dict], fade: float = 0.2) -> List[VideoFileClip]:
    clips = []
    base = VideoFileClip(video_path)
    for seg in segments:
        st, et = max(0, seg["start"]), min(base.duration, seg["end"])
        if et <= st:
            continue
        c = base.subclip(st, et)
        if fade > 0:
            c = c.crossfadein(fade).crossfadeout(fade)
        clips.append(c)
    return clips


def build_subtitle_clip(assigned: List[Dict], size=(1920,1080), fontsize=48) -> Optional[CompositeVideoClip]:
    # Build a simple karaoke-style subtitle layer
    txt_clips = []
    for seg in assigned:
        text = seg["line"]
        st, et = seg["start"], seg["end"]
        try:
            tc = TextClip(txt=text, fontsize=fontsize, color='white', stroke_color='black', stroke_width=2, method='caption', size=(int(size[0]*0.9), None))
            tc = tc.set_start(st).set_end(et).set_position(('center', size[1]-200))
            txt_clips.append(tc)
        except Exception:
            continue
    if not txt_clips:
        return None
    return CompositeVideoClip(txt_clips, size=size)


def concat_with_crossfade(video_segments: List[VideoFileClip], fade: float = 0.2) -> VideoFileClip:
    if not video_segments:
        raise ValueError("No video segments to concatenate")
    return concatenate_videoclips(video_segments, method="compose", padding=-fade)


def export_video(clip: VideoFileClip, out_path: str = "final_remix.mp4", fps: int = 30):
    clip.write_videofile(out_path, codec='libx264', audio_codec='aac', fps=fps, preset='medium')
