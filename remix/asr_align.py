from typing import List, Dict, Tuple, Optional
from faster_whisper import WhisperModel
import numpy as np
from rapidfuzz import fuzz

# ASR transcription and heuristic alignment of lyrics lines to transcript segments.


def transcribe_audio(audio_path: str, model_size: str = "small") -> List[Dict]:
    """Transcribe audio with faster-whisper, returning list of word items.
    Each item: {"word": str, "start": float, "end": float}
    """
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_path, word_timestamps=True)
    words = []
    for seg in segments:
        for w in seg.words:
            words.append({"word": w.word.strip(), "start": w.start, "end": w.end})
    # filter empties
    words = [w for w in words if w["word"]]
    return words


def align_lyrics_to_words(lyrics_lines: List[str], words: List[Dict], window: int = 15) -> List[Dict]:
    """Align each lyric line to a time span in the transcript by fuzzy matching.

    Strategy:
    - Build a sliding window over transcript words (by count)
    - For each lyric line, compute similarity against concatenated window string
    - Choose the best window; if none, fall back to fixed 3s chunks appended sequentially
    """
    if not words:
        # Fallback: 3s per line, sequential
        results = []
        t = 0.0
        for line in lyrics_lines:
            results.append({"line": line, "start": t, "end": t + 3.0, "score": 0})
            t += 3.0
        return results

    joined_words = [w["word"].lower() for w in words]

    results = []
    for line in lyrics_lines:
        line_norm = " ".join(line.lower().split())
        best = (-1, None, None)
        # try multiple window sizes
        for win in range(5, max(6, min(window, len(joined_words))) + 1):
            for s in range(0, max(1, len(joined_words) - win + 1)):
                chunk = " ".join(joined_words[s:s+win])
                score = fuzz.partial_ratio(line_norm, chunk)
                if score > best[0]:
                    start_t = words[s]["start"]
                    end_t = words[min(s+win-1, len(words)-1)]["end"]
                    best = (score, start_t, end_t)
        score, st, et = best
        if score < 50 or st is None:
            # fallback: approximate by continuation after previous
            last_end = results[-1]["end"] if results else 0.0
            st = last_end
            et = st + 3.0
        results.append({"line": line, "start": st, "end": et, "score": score})
    # minor smoothing: ensure non-decreasing times
    for idx in range(1, len(results)):
        if results[idx]["start"] < results[idx-1]["end"]:
            shift = results[idx-1]["end"] - results[idx]["start"]
            results[idx]["start"] += shift
            results[idx]["end"] += shift
    return results
