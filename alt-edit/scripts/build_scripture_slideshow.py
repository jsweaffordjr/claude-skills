#!/usr/bin/env python3
"""Assemble a sequence of scripture-card PNG chunks (from `gen_overlay.py scripture-auto`)
into one alpha-channel slideshow video, each chunk held on screen for a given duration.

Why this exists: a long passage might auto-chunk into 5-7 cards. Composited as 5-7
separate overlay stages in the master ffmpeg filter_complex, a video with many long
passages (main-edit's whole reason for existing) can end up needing 60+ overlay stages,
which is unwieldy and slow to build/debug. Pre-assembling each passage into ONE video
means the master composite only needs one overlay stage per PASSAGE, not per chunk.

Implementation note: an earlier version used ffmpeg's concat demuxer with per-file
`duration` directives. That produced a video whose packet timestamps *looked* right
under ffprobe but played back with each chunk's content shifted about one chunk early
of its stated timestamp -- never fully root-caused, not worth the time given the
frame-sequence approach (used successfully for this skill's motion graphics) is
straightforward and was verified correct by direct frame extraction. Use that instead:
write each held chunk as its own run of real frames at a constant framerate.

Usage:
    python3 build_scripture_slideshow.py <output.mov> <chunk1.png> <dur1> [<chunk2.png> <dur2> ...]

Durations are in seconds (float). All chunks are bottom-aligned onto a shared canvas
(same width as the widest chunk, height as the tallest) so the assembled video has a
single consistent frame size while each chunk's text still reads as anchored to the
same baseline -- exactly like the individual cards would look composited directly.
"""
import subprocess
import sys
import tempfile
import os
from PIL import Image

FF = os.path.expanduser("~/.claude/skills/alt-edit/bin/ffmpeg")
if not os.path.exists(FF):
    FF = "ffmpeg"  # fall back to PATH if the bundled binary isn't found

FPS = 15


def main():
    if len(sys.argv) < 4 or len(sys.argv) % 2 != 0:
        print("usage: build_scripture_slideshow.py <output.mov> <chunk1.png> <dur1> [...]",
              file=sys.stderr)
        sys.exit(1)

    out_path = sys.argv[1]
    pairs = sys.argv[2:]
    chunk_paths = pairs[0::2]
    durations = [float(d) for d in pairs[1::2]]

    images = [Image.open(p) for p in chunk_paths]
    canvas_w = max(im.width for im in images)
    canvas_h = max(im.height for im in images)

    with tempfile.TemporaryDirectory() as tmp:
        frame_idx = 0
        for im, dur in zip(images, durations):
            canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            canvas.alpha_composite(im.convert("RGBA"), (0, canvas_h - im.height))
            n_frames = max(1, round(dur * FPS))
            for _ in range(n_frames):
                canvas.save(os.path.join(tmp, f"frame_{frame_idx:05d}.png"))
                frame_idx += 1

        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
        subprocess.run([
            FF, "-y", "-framerate", str(FPS), "-i", os.path.join(tmp, "frame_%05d.png"),
            "-c:v", "qtrle", "-pix_fmt", "argb", out_path,
        ], check=True, capture_output=True)

    total = sum(durations)
    print(f"{out_path}: {canvas_w}x{canvas_h}, {len(chunk_paths)} chunks, "
          f"{frame_idx} frames, {total:.1f}s total")


if __name__ == "__main__":
    main()
