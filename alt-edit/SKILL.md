---
name: alt-edit
description: Edit a raw, already-clipped video for Jerry's biblical-health/carnivore-diet YouTube channel by extracting audio, generating a timestamped transcript, collaborating with Jerry on scripture references and on-screen graphics, then compositing everything into an upload-ready 4K video. Only run this when Jerry explicitly invokes it via /alt-edit and gives you a video file.
---

# alt-edit

Turns a clipped raw video into a finished video with scripture lower-thirds, keyword/
framework badges, and motion graphics burned in, ready to upload. This captures the
workflow from Jerry's first two videos on this channel ("FEW framework" and "Fasting
Mistakes"), including several hard-won fixes -- read the reference files, don't
rederive from scratch.

**Scope**: the input video is already trimmed (dead air at start/end already cut).
This skill starts at "raw clipped video" and ends at "finished 4K file." If the
transcript reveals an obvious long silence at the very start or end, flag it to Jerry
rather than assuming it's fine or re-trimming it yourself.

**Standing defaults** (confirmed with Jerry, don't re-ask each time):
- Bible translation: WEB (public domain) -- see references/style-guide.md
- Delivery: burn graphics directly into a 4K master via ffmpeg
- These can still be overridden per-video if Jerry asks for something different.

## Workflow

### 0. Setup
Run `scripts/ensure_deps.sh` -- installs faster-whisper/Pillow if missing, and fetches
the bundled modern ffmpeg if it's ever absent (e.g. skill copied to a new machine).
Use the printed `$FFMPEG`/`$FFPROBE` paths for every ffmpeg/ffprobe call in this
workflow -- **not** the system `ffmpeg`. The system one has a real bug that corrupts
audio/video sync on this kind of footage; see references/ffmpeg-compositing.md for why.

### 1. Extract audio
Fast stream-copy, no re-encoding:
```
$FFMPEG -y -i raw.mp4 -vn -c:a copy raw-audio.m4a
```

### 2. Transcribe
```
python3 scripts/transcribe.py raw-audio.m4a transcript.txt
```
Runs locally on CPU (~1-2 minutes for a 10-20 minute video), no data leaves the
machine. Produces `[hh:mm:ss] text` lines.

**Write `transcript.txt` into the same folder as the raw source video, not a scratch/
working directory (confirmed with Jerry, 2026-08).** Unlike the other intermediates
(audio extract, PNG/mov assets), the transcript is a keeper on this channel going
forward -- don't lump it in with step 8's "clean up intermediates?" question, and
don't delete it during cleanup even if Jerry says yes to the rest.

**Show Jerry the transcript and ask him to flag any mis-transcribed names/terms**
before treating it as ground truth -- Whisper garbled a book title and an author's
name in the first video ("Biblio Diet", "Jordan Reuben" instead of the real names).
Don't silently trust proper nouns.

### 3. Plan the graphics -- interactive, do not skip

This is the step that actually needs Jerry, not just his footage. Go through the
transcript with him and nail down, for each of the three graphic types (see
references/style-guide.md for what each one is):

- **Scripture**: every passage he references or quotes. For each one, confirm the
  exact book/chapter/verse with him, then fetch the precise WEB text yourself from
  `https://bible-api.com/<ref>?translation=web` -- don't quote from memory. At the
  current font size, don't assume a whole verse fits one card -- see "Scripture
  chunking" in references/style-guide.md and expect to split longer verses shorter.
- **Keyword/framework badges**: whatever recurring terms or steps the video's
  framework uses (varies video to video -- ask what they are, don't assume "FEW").
  Identify start/end timestamps for each occurrence from the transcript -- derive the
  actual end time from word-level timestamps, not a line-level guess or a flat
  reading-speed floor; see "Overlay timing" in references/style-guide.md, it covers
  exactly this and documents two ways it went wrong before landing on the fix.
- **Motion graphics**: ask Jerry which moments, if any, would benefit from an
  illustrative animation rather than just text. Confirm the concept before building
  anything -- these are bespoke and take real time to design well.

**Present a full plan as a table** (graphic type, timestamp window, exact text/content)
**and get explicit sign-off before building or encoding anything.** The final encode
takes 20-30 minutes; catching a wrong timestamp or misquoted verse at the plan stage
costs nothing, catching it after a full render costs half an hour.

### 4. Check the safe zone
Pull sample frames from the actual raw video at the specific timestamps each graphic
will appear (not generic points elsewhere in the video -- framing can vary by scene).
Look at them and find where the speaker's face/body is NOT, per references/style-guide.md.
Decide tentative pixel positions from what you actually see, not from the layout that
happened to work on a previous video -- then, once you have real assets built (step 5),
**composite each one onto the actual worst-looking frame in its window and look at the
result** before treating the position as final. A thumbnail estimate missed a real
overlap in video 2; the actual composite caught it.

### 5. Build the graphics
- Scripture cards and badges: `python3 scripts/gen_overlay.py scripture <ref> <verse> <out.png>`
  and `python3 scripts/gen_overlay.py badge <text> <out.png>` (add `--body "<description>"`
  for longer badge text). Sizes are pre-corrected per Jerry's feedback -- don't shrink
  them back down; if a card comes out too tall, split the text shorter instead (see
  references/style-guide.md).
- Motion graphics: bespoke PIL frame sequence per references/style-guide.md.

### 6. Composite
Follow references/ffmpeg-compositing.md exactly -- the filter_complex template, the
`-shortest` flag, and what NOT to add (`fps=30`, `-vsync 0`) are all there for reasons
discovered the hard way. Validate on a short test segment before the full-length run.
Launch the full encode as a properly-tracked background process (see that file's
"Background execution" section -- getting this wrong means losing track of a real
30-minute job).

### 7. Verify before calling it done
```
$FFPROBE -v error -select_streams v:0 -show_entries stream=duration,nb_frames -of default=noprint_wrappers=0 output.mp4
$FFPROBE -v error -select_streams a:0 -show_entries stream=duration -of default=noprint_wrappers=0 output.mp4
```
Video/audio duration must match within ~2 frames. Then pull frames across the whole
timeline (one per graphic type, plus a moment near the very end) and actually look at
them -- confirm correct positioning, readable text, no overlap, no frozen/black tail.

### 8. Deliver
Report the output path, a short summary of what's included and when, and ask Jerry
about the output filename and whether to clean up intermediate files (audio extract,
PNG/mov assets) -- don't delete anything he might want without asking, same as last
time. **The transcript is excluded from that cleanup question** -- it already lives
in the raw video's folder per step 2 and stays there.

## Reference files
- `references/ffmpeg-compositing.md` -- the compositing recipe, the VFR sync bug and
  its fix, background-execution gotcha. Read before step 6.
- `references/style-guide.md` -- fonts, colors, sizes, translation policy, layout
  philosophy. Read before steps 3-5.
