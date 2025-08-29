import os
import subprocess
from typing import List, Dict, Optional
from moviepy import VideoFileClip, concatenate_videoclips, CompositeVideoClip, TextClip


FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")


def cut_segments(video_path: str, segments: List[Dict], fade: float = 0.2) -> List[VideoFileClip]:
    clips: List[VideoFileClip] = []
    base = None
    use_subclip = False
    use_time_slice = False
    try:
        base = VideoFileClip(video_path)
        use_subclip = hasattr(base, "subclip")
        use_time_slice = hasattr(base, "time_slice")
    except Exception:
        base = None

    from pathlib import Path
    tmpdir = Path("work/tmp")
    tmpdir.mkdir(parents=True, exist_ok=True)

    for seg in segments:
        st = max(0.0, float(seg["start"]))
        et = float(seg["end"]) if base is None else min(base.duration, float(seg["end"]))
        if et <= st:
            continue
        c = None
        try:
            if base is not None and use_subclip:
                c = base.subclip(st, et)
            elif base is not None and use_time_slice:
                c = base.time_slice(st, et)
        except Exception:
            c = None
        if c is None:
            # Fallback: cut with ffmpeg to a temp file then load
            import subprocess, uuid
            tmp_path = tmpdir / f"seg_{uuid.uuid4().hex}.mp4"
            cmd = [
                "ffmpeg", "-y", "-ss", str(st), "-to", str(et),
                "-i", video_path,
                "-c", "copy",
                str(tmp_path)
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                c = VideoFileClip(str(tmp_path))
            except Exception as e:
                # As a last resort, try re-encoding the segment
                cmd = [
                    "ffmpeg", "-y", "-ss", str(st), "-to", str(et),
                    "-i", video_path,
                    "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
                    str(tmp_path)
                ]
                subprocess.run(cmd, check=False)
                try:
                    c = VideoFileClip(str(tmp_path))
                except Exception:
                    continue
        if fade > 0:
            try:
                c = c.crossfadein(fade).crossfadeout(fade)
            except Exception:
                pass
        clips.append(c)
    if base is not None:
        try:
            base.close()
        except Exception:
            pass
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
