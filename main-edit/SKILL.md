---
name: main-edit
description: Edit a raw, already-clipped video for Jerry's main YouTube channel by extracting audio, generating a timestamped transcript, collaborating with Jerry on NKJV scripture references, then compositing scripture lower-thirds burned into an upload-ready 4K video. Only run this when Jerry explicitly invokes it via /main-edit and gives you a video file.
---

# main-edit

Sister skill to alt-edit (`~/.claude/skills/alt-edit`), reusing its scripts and bundled
ffmpeg -- **alt-edit must be installed for this skill to work.** If it's ever missing,
reinstall it or copy its `scripts/` and `bin/` over before proceeding.

Turns a clipped raw video into a finished video with scripture lower-thirds burned in,
ready to upload. Simpler than alt-edit: main channel videos don't use keyword badges or
motion graphics (confirmed with Jerry) -- just scripture, but a lot more of it, and
read prominently since Jerry reads aloud from his Bible on camera.

**Scope**: the input video is already trimmed. This skill starts at "raw clipped
video" and ends at "finished 4K file." Visuals/motion graphics aren't expected on this
channel, but if it's ever unclear whether a particular video wants one, ask Jerry
during planning rather than assuming.

**Standing defaults** (confirmed with Jerry, don't re-ask each time):
- Bible translation: **NKJV** (New King James Version) -- copyrighted, unlike
  alt-edit's WEB. See "NKJV text and copyright" below -- this changes how you source
  verse text and what you hand Jerry alongside the finished video.
- Delivery: burn graphics directly into a 4K master via ffmpeg.
- No keyword badges, no motion graphics, by default -- confirm with Jerry per video if
  that seems like it might not hold.
- These can still be overridden per-video if Jerry asks for something different.

## Footage style: different from alt-edit

Jerry is **seated, looking directly into the camera** -- not walking/handheld. This is
much more stable and predictable framing than alt-edit's roaming close-up, but still
do the safe-zone check (see alt-edit's references/style-guide.md, "Layout" section)
rather than assuming -- confirm with real frames each video.

Important difference: **when Jerry reads scripture aloud, he looks down at his Bible,
not at the camera.** He doesn't mind the scripture block sitting higher/more
prominently on screen during those moments, since his own gaze is already off camera
and the viewer is meant to be reading along with him. This means scripture cards for
main-edit can be larger and more centrally placed than alt-edit's corner-anchored
lower-thirds -- lean into a prominent "read-along" placement during active reading
moments rather than a small tucked-away lower-third. Still verify against actual
frames each time; his exact framing may vary video to video.

## NKJV text and copyright

NKJV is commercially licensed (Thomas Nelson), not public domain like WEB. Two
consequences:

1. **Sourcing the text**: there's no confirmed-compliant free API for NKJV text
   available here (bible-api.com only serves public-domain translations; a proper NKJV
   API needs a registered key that isn't set up). **Ask Jerry to supply the exact
   verse text himself** (he reads from his own Bible/app on camera, so this is easy
   for him) during the planning step, rather than sourcing it from an uncertain
   website. Don't scrape or paraphrase from memory.
2. **Attribution**: Thomas Nelson's standard policy permits quoting up to 500 verses
   without written permission, but requires a credit line wherever NKJV text is used.
   Jerry wants this as description text, not an on-screen graphic. **Every time you
   deliver a video that quotes NKJV scripture, include this exact line for him to
   paste into the YouTube description:**
   > Scripture taken from the New King James Version®. Copyright © 1982 by Thomas
   > Nelson. Used by permission. All rights reserved.

## Workflow

Same shape as alt-edit, using alt-edit's bundled tools throughout.

### 0. Setup
Run `~/.claude/skills/alt-edit/scripts/ensure_deps.sh` and use the `$FFMPEG`/`$FFPROBE`
paths it prints -- same VFR-sync-bug reasons as alt-edit (see alt-edit's
references/ffmpeg-compositing.md).

### 1. Extract audio
```
$FFMPEG -y -i raw.mp4 -vn -c:a copy raw-audio.m4a
```

### 2. Transcribe
```
python3 ~/.claude/skills/alt-edit/scripts/transcribe.py raw-audio.m4a transcript.txt
```
Show Jerry the transcript and ask him to flag mis-transcribed names/terms before
treating it as ground truth (same reasoning as alt-edit -- Whisper garbles proper nouns).

### 3. Plan the graphics -- interactive, do not skip
Go through the transcript with Jerry and identify every scripture passage referenced.
For each: confirm the exact book/chapter/verse, then **ask Jerry for the exact NKJV
text** (don't source it yourself -- see "NKJV text and copyright" above). Given main
channel videos "use a lot more scripture," expect more passages per video than
alt-edit's videos -- pace through them methodically rather than trying to hold it all
in one pass.

Confirm with Jerry whether this particular video needs any badges/motion graphics
(default assumption is no, but ask rather than silently assume every time).

**Present a full plan as a table** (timestamp window, exact NKJV text per card) and
get explicit sign-off before building or encoding anything -- same reasoning as
alt-edit: a 20-30 minute encode is expensive to redo over a wrong timestamp or a typo
caught too late.

### 4. Check the safe zone
Pull sample frames at each scripture window's specific timestamps and look at them.
Remember the "reads down at Bible = can go bigger/higher" allowance above, but verify
it against this video's actual framing rather than assuming it always applies.
Composite the actual rendered card onto the actual worst-looking frame before treating
a position as final -- an estimate from a thumbnail alone missed a real overlap on
alt-edit's second video; the real composite caught it.

### 5. Build the graphics

**main-edit's font size is NOT the same as alt-edit's, and does not inherit alt-edit's
default.** Always pass explicit overrides:
```
python3 ~/.claude/skills/alt-edit/scripts/gen_overlay.py scripture "<ref> (NKJV)" "<text>" <out.png> --label-size 138 --body-size 126
python3 ~/.claude/skills/alt-edit/scripts/gen_overlay.py scripture-auto "<ref> (NKJV)" "<full text>" <out_prefix> --label-size 138 --body-size 126
```
138/126 is main-edit's standing default -- confirmed correct *in true proportion on
this channel's actual seated footage* (AIdolatry video, 2026-08). Do not omit
`--label-size`/`--body-size` and let the tool fall back to its built-in default (276/252
as of this writing) -- that default was tuned for alt-edit's tight close-up footage and
reads as noticeably oversized on main-edit's wider, more stable seated shot. The two
channels have different footage styles and legitimately need different absolute pixel
sizes for the same *perceived* prominence -- this isn't a case of one channel being
"right" and needing to match the other.

**Lesson learned the hard way, worth repeating:** don't judge a candidate font size
from an isolated, cropped card image -- it reads as much larger than it actually is
once placed in the full 4K frame. Always composite candidate sizes onto a real frame
(`ffmpeg -i frame.png -i card.png -filter_complex overlay=X:Y ...`) before asking Jerry
to compare sizes, the same way you'd verify position. A size judged "too small" or "too
large" from a cropped preview is not a reliable verdict.

Scripture-only for this channel -- no badge/motion-graphic generation needed unless
step 3 turned up an exception. Given "a lot more scripture" and the read-along
philosophy above, split text by whatever renders at a reasonable height rather than by
verse boundaries (see alt-edit's style-guide.md, "Scripture chunking") -- use
`scripture-auto` for anything longer than a short phrase, and
`~/.claude/skills/alt-edit/scripts/build_scripture_slideshow.py` to pack a passage's
chunks into one timed video rather than one overlay stage per chunk (essential once a
video has many passages -- see alt-edit's ffmpeg-compositing.md).

**Timing each chunk's on-screen start/end**: derive these from word-level transcript
timestamps, not line-level guessing or a reading-speed floor -- see alt-edit's
style-guide.md, "Overlay timing," before computing timestamps for any video on this
channel. It documents two failed attempts (cards cutting off early, then the opposite
overcorrection of lingering too long) so you land on the actual fix directly instead
of repeating either mistake.

### 6. Composite
Follow alt-edit's references/ffmpeg-compositing.md exactly -- same filter_complex
template (typically simpler here: just scripture-card overlay stages, no badges/motion
graphics), same `-shortest` flag, same warning about not adding `fps=30`/`-vsync 0`,
same care around backgrounding the real ffmpeg process correctly.

### 7. Verify before calling it done
```
$FFPROBE -v error -select_streams v:0 -show_entries stream=duration,nb_frames -of default=noprint_wrappers=0 output.mp4
$FFPROBE -v error -select_streams a:0 -show_entries stream=duration -of default=noprint_wrappers=0 output.mp4
```
Video/audio duration must match within ~2 frames. Pull frames across the timeline and
look at them -- readable text, correct positioning, no frozen/black tail.

### 8. Deliver
Report the output path and a short summary of what's included. **Include the NKJV
credit line from above** for Jerry to paste into the video description. Ask about
output filename and whether to clean up intermediate files -- don't delete anything
without asking.

## Reference files
Reuses alt-edit's reference docs rather than duplicating them:
- `~/.claude/skills/alt-edit/references/ffmpeg-compositing.md` -- compositing recipe,
  VFR bug/fix, background-execution gotcha.
- `~/.claude/skills/alt-edit/references/style-guide.md` -- fonts, colors, safe-zone
  discipline, scripture chunking. Its translation section doesn't apply here (this
  file's NKJV section governs instead); everything else does.
