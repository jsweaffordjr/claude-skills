---
name: vidclip
description: Trim dead air off the start/end of a raw video and convert it to a 4K master, ready to hand to alt-edit or main-edit as their "raw clipped video" input. Only run this when Jerry explicitly invokes it via /vidclip and gives you a video (or a folder containing one).
---

# vidclip

Takes a raw, untrimmed video and produces a trimmed 4K master: exactly the "already
clipped raw video" that alt-edit and main-edit expect as their starting point. Reuses
alt-edit's bundled ffmpeg (`~/.claude/skills/alt-edit/bin`) -- **alt-edit must be
installed for this skill to work.**

**Scope**: start/end trim + resolution conversion only. No audio extraction,
transcription, scripture, or graphics -- that's alt-edit/main-edit's job, done next as
a separate step once vidclip hands off its output.

## Invocation and the trim notation

Jerry invokes this as `/vidclip` on a video or a folder, with a parenthetical like
`(6/2)` meaning: trim **6 seconds off the beginning, 2 seconds off the end**. First
number = seconds cut from the start, second number = seconds cut from the end.

- **If the parenthetical is missing, ask Jerry for it before doing anything else** --
  don't guess a trim amount or assume 0. A wrong trim burned into a 4K re-encode is
  exactly the kind of mistake alt-edit/main-edit's own "confirm before encoding"
  discipline exists to avoid; the same reasoning applies here.
- `0` is valid for either side (e.g. `(0/3)` trims only the end).
- If Jerry writes something ambiguous (e.g. a bare `1:30`), confirm whether that's
  minutes:seconds or two separate second counts rather than assuming.

**Locating the file**: if given a folder, look for the video file inside it. If there's
more than one, ask Jerry which one. If given a direct file path, use it as-is.

## Standing defaults

- Output resolution: **3840x2160 (4K)**, matching alt-edit/main-edit's master format --
  see their `references/ffmpeg-compositing.md`.
- Encode settings mirror that doc's "8K sources" Pass 1 recipe (`-preset fast -crf 16
  -pix_fmt yuv420p`), since this step *is* that pass -- just with a trim added.
- Output file: same folder as the source, named `<original-stem>_4k.mp4` unless Jerry
  asks for something else.
- These can be overridden per-video if Jerry asks for something different.

## Workflow

### 0. Setup
Run `~/.claude/skills/alt-edit/scripts/ensure_deps.sh` and use the printed
`$FFMPEG`/`$FFPROBE` paths for every call below -- same VFR-sync-bug reasons as
alt-edit/main-edit.

### 1. Inspect the source
```
$FFPROBE -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate -of default=noprint_wrappers=0 source.mp4
$FFPROBE -v error -show_entries format=duration -of default=noprint_wrappers=0 source.mp4
```
Note width/height (source can arrive at 8K -- confirmed on real footage, see
ffmpeg-compositing.md) and total duration. If the source's aspect ratio isn't 16:9,
flag it to Jerry before scaling -- a plain `scale=3840:2160` will stretch it.

### 2. Compute the trim window
`target_duration = source_duration - start_trim - end_trim`. Sanity-check this is
positive and roughly matches what Jerry expects (e.g. flag it if the requested trim
would remove more than a minute or leave under 10 seconds -- likely a mistyped
parenthetical, not necessarily wrong, so confirm rather than silently proceeding).

### 3. Trim and convert in one pass
```
$FFMPEG -y -ss <start_trim> -i source.mp4 -t <target_duration> \
  -vf scale=3840:2160 \
  -c:v libx264 -preset fast -crf 16 -pix_fmt yuv420p \
  -c:a copy \
  "<original-stem>_4k.mp4"
```
- `-ss` before `-i` seeks to the start trim point; `-t` after `-i` caps the output at
  `target_duration`, which is what actually removes the end trim.
- **Audio is `-c:a copy`, not re-encoded -- confirmed the hard way on WhatElseForFitness
  (2026-09).** Re-encoding already-lossy source audio introduces real, audible
  "pre-echo"-style artifacts (transform-codec compression smearing a loud transient
  backward into the quiet moment just before it) that get WORSE with every additional
  lossy re-encode generation it passes through downstream (e.g. alt-edit/main-edit's own
  compositing). Jerry could hear it and correctly diagnosed the generational pattern
  (original clean -> one re-encode mildly echoey -> two re-encodes clearly echoey)
  before the actual cause was confirmed by direct waveform comparison (bit-identical
  correlation between `-c:a copy` output and the source, vs. audible artifacts with
  `-c:a aac` re-encoding). `-c:a copy` through a `-ss` trim only cuts on the nearest
  audio frame boundary (~10-20ms for AAC) -- utterly inaudible for a "trim N seconds"
  request, and it preserves the source bit-for-bit otherwise. **Never re-encode audio
  in this pipeline unless a specific downstream requirement forces it** (e.g. a codec
  YouTube/the container won't accept -- AAC almost always already satisfies that, so
  this should be rare). If alt-edit/main-edit need to touch audio again downstream
  (transcription extraction, etc.), prefer `-c:a copy` there too for the same reason.
- For a long/high-resolution source this can take a while (8K decode alone runs as low
  as ~0.3-0.5x realtime on this machine, per ffmpeg-compositing.md) -- launch it with
  the Bash tool's `run_in_background: true` directly on the ffmpeg command itself, the
  same way alt-edit backgrounds its full encode, so the completion notification is
  trustworthy.

### 4. Verify
```
$FFPROBE -v error -select_streams v:0 -show_entries stream=width,height,duration -of default=noprint_wrappers=0 output.mp4
$FFPROBE -v error -select_streams a:0 -show_entries stream=duration -of default=noprint_wrappers=0 output.mp4
```
Confirm: resolution is 3840x2160, video/audio durations match within ~2 frames, and
the duration is close to `target_duration`. Pull a frame near the very start and one
near the very end (`ffmpeg -ss <t> -vframes 1`) and look at them -- confirm the trim
actually cut what it was supposed to (no leftover dead air, nothing important clipped).

### 5. Deliver
Report the output path, resolution, and final duration. This file is a **raw clipped
video** in alt-edit/main-edit's sense -- if Jerry's next step is one of those skills,
hand this path to it directly as the starting input, no further conversion needed.
