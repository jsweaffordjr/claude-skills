#!/usr/bin/env python3
"""Transcribe an audio file to a timestamped script using faster-whisper (local, CPU).

Usage:
    python3 transcribe.py <input_audio> <output_txt>

Produces lines like:
    [00:01:23] And this is what I mean by that...
"""
import sys
import time


def fmt(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def main():
    if len(sys.argv) != 3:
        print("usage: transcribe.py <input_audio> <output_txt>", file=sys.stderr)
        sys.exit(1)
    audio_path, out_path = sys.argv[1], sys.argv[2]

    from faster_whisper import WhisperModel

    t0 = time.time()
    # "small" model: good speed/accuracy balance on CPU for an ~10-20 min talking-head video.
    # Bump to "medium" if names/terms keep coming out garbled and it's worth the extra time.
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_path, beam_size=5, vad_filter=True)

    print(f"Detected language: {info.language} (prob {info.language_probability:.2f})")
    lines = []
    for seg in segments:
        line = f"[{fmt(seg.start)}] {seg.text.strip()}"
        lines.append(line)
        print(line)

    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"--- done in {time.time()-t0:.1f}s, {len(lines)} segments -> {out_path} ---")


if __name__ == "__main__":
    main()
