#!/usr/bin/env bash
# Verify/install everything alt-edit needs. Safe to run every time -- each check is a no-op
# if already satisfied. Prints the ffmpeg/ffprobe paths to use at the end.
set -e

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FF="$SKILL_DIR/bin/ffmpeg"
FFPROBE="$SKILL_DIR/bin/ffprobe"

# 1. Modern ffmpeg/ffprobe bundled with the skill (fixes a real VFR/framesync bug in
#    older ffmpeg that corrupts audio/video sync when compositing overlays -- see
#    references/ffmpeg-compositing.md for the full story). Re-fetch only if missing.
if [ ! -x "$FF" ] || [ ! -x "$FFPROBE" ]; then
  echo "Bundled ffmpeg missing -- downloading a static build (~40MB)..."
  mkdir -p "$SKILL_DIR/bin"
  TMPDIR=$(mktemp -d)
  curl -sL -o "$TMPDIR/ffmpeg.tar.xz" https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
  tar xf "$TMPDIR/ffmpeg.tar.xz" -C "$TMPDIR"
  FFDIR=$(find "$TMPDIR" -maxdepth 1 -name "ffmpeg-*-amd64-static" | head -1)
  cp "$FFDIR/ffmpeg" "$FFDIR/ffprobe" "$SKILL_DIR/bin/"
  chmod +x "$FF" "$FFPROBE"
  rm -rf "$TMPDIR"
fi

# 2. Python deps: faster-whisper (transcription) and Pillow (graphics generation).
python3 -c "import faster_whisper" 2>/dev/null || pip3 install --user --quiet faster-whisper
python3 -c "import PIL" 2>/dev/null || pip3 install --user --quiet Pillow

echo "FFMPEG=$FF"
echo "FFPROBE=$FFPROBE"
echo "deps OK"
