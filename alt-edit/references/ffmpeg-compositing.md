# Compositing graphics onto the video: the exact recipe

This is the part that's easy to get subtly wrong. Read this fully before running the
final encode -- a mistake here means a corrupted or out-of-sync deliverable that looks
fine in a spot-check and only shows itself late.

## The VFR bug (why we bundle our own ffmpeg)

Jerry's camera (and phones generally) shoot **variable frame rate** video -- the true
frame timing isn't a clean 30.000fps, it drifts slightly (e.g. 30.04fps). The system's
default ffmpeg on this machine (4.2.7, from 2020) mishandles this when a filter graph
combines the VFR main video with secondary CFR inputs (looped PNG overlays, an alpha
motion-graphic clip): it silently duplicates or drops frames, producing a final video
track whose duration doesn't match the audio track. This is NOT cosmetic -- it means
the last several seconds of the video play with no matching audio, or content gets
dropped outright.

Symptoms if you hit this: `ffprobe` shows the video stream duration differing from the
audio stream duration by more than a couple frames.

**The fix**: use the modern ffmpeg bundled in `bin/ffmpeg` / `bin/ffprobe` (7.0.2 static
build; `scripts/ensure_deps.sh` fetches it if it's ever missing). With that build, the
correct incantation is:

- Default vsync behavior -- do **not** add an `fps=30` filter or `-vsync 0` /
  `-fps_mode passthrough`. Both of those were tried during development and made things
  *worse* (dropped frames) with the old ffmpeg, and the modern ffmpeg doesn't need them.
- Add **`-shortest`** on the output, with both `[vout]` (filtered video) and `0:a`
  (copied audio) mapped. Without graphics, video and audio already agree almost
  perfectly on duration (confirmed on real footage: 661.599s video vs 661.600s audio).
  With the overlay chain in place, the video track comes out ~100 frames longer than
  it should (duplicate frames from the CFR loop-image inputs) -- `-shortest` trims that
  excess back to the audio's true duration, which is the one you can trust.

**Always verify** after encoding, before telling Jerry it's done:
```
ffprobe -v error -select_streams v:0 -show_entries stream=duration,nb_frames -of default=noprint_wrappers=0 output.mp4
ffprobe -v error -select_streams a:0 -show_entries stream=duration -of default=noprint_wrappers=0 output.mp4
```
Video and audio duration should match within ~2 frames (~0.07s). If they don't, do not
ship it -- go back and check the filter graph / flags above rather than guessing at
another workaround.

**This total-duration check is necessary but NOT sufficient for a segmented build --
confirmed the hard way on main-edit's StopSpeeding video.** Matching totals only prove
the very end lines up; they say nothing about whether video and audio drifted apart
and back together somewhere in the middle, which is exactly what happened: real,
audible lag appeared a few minutes in even though the final numbers looked clean. See
"segment, don't mega-chain" below for the actual mechanism and fix -- if you built the
output as many concatenated segments, do the per-segment check described there, not
just this top-level one.

## The filter_complex template

One ffmpeg invocation does everything: scale to 4K, then chain one `overlay` stage per
graphic, each gated by `enable='between(t,start,end)'` (or a sum of multiple
`between()` calls if the same image reappears at several disjoint time windows -- see
the FEW-framework badges example below, which flash briefly then hold).

```bash
FF="$SKILL_DIR/bin/ffmpeg"

FILTER="[0:v]scale=3840:2160[base];\
[base][1:v]overlay=X1:Y1:enable='between(t,S1,E1)'[v1];\
[v1][2:v]overlay=X2:Y2:enable='between(t,S2,E2)'[v2];\
...
[vN-1][N:v]overlay=XN:YN:enable='between(t,SN,EN)'[vout]"

"$FF" -y -i "clipped_raw.mp4" \
  -loop 1 -framerate 30 -t <source_duration_plus_buffer> -i scripture1.png \
  -loop 1 -framerate 30 -t <source_duration_plus_buffer> -i badge1.png \
  ... \
  -itsoffset <motion_graphic_start_seconds> -i motion_graphic.mov \
  -filter_complex "$FILTER" \
  -map "[vout]" -map 0:a -shortest \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -c:a copy \
  "output.mp4"
```

Notes:
- **Static overlays** (scripture cards, keyword badges) are single PNGs fed in with
  `-loop 1 -framerate 30 -t <duration>`. Set the `-t` value to at least the source
  video's duration so the loop never runs dry mid-encode.
- **Motion graphics** (an animated clip with alpha) use `-itsoffset <seconds>` instead
  of `-loop`, which shifts the clip's own timeline so it starts playing at the right
  moment in the master timeline. Pair with `enable='between(...)'` matching its actual
  on-screen window as a second safety net.
- **A badge reused at multiple non-adjacent moments** (e.g. a quick flash-reveal early
  on, then a long persistent hold later, then a recap flash near the end) needs only
  one input and one overlay stage -- just sum the windows in one `enable` expression:
  `enable='between(t,15,18)+between(t,124,278)+between(t,569,572)'`. Each `between()`
  is 0 or 1; the sum is nonzero (true) whenever any window is active, and since the
  windows never overlap in practice this is safe.
- Order overlay stages so nothing draws over something that needs to stay visible --
  in practice this has never mattered here because our overlays don't spatially
  collide, but keep it in mind if a design ever calls for stacked/layered graphics.

## Validate before committing to the full encode

Re-encoding a full ~10-20 minute 4K video takes 20-30 minutes on this machine (no GPU
available -- confirmed via `nvidia-smi` and no `/dev/dri` nodes, so it's CPU-only x264).
Never run the full-length encode as your first attempt at a given overlay plan:

1. Run the exact same filter graph with `-t 60` to `-t 250` or so (enough to cover at
   least one instance of each graphic type) before running the full thing.
2. Pull a handful of frames from the test render with `ffmpeg -ss <t> -vframes 1` at
   moments covering each graphic type, and actually look at them (the Read tool
   displays images) -- check text is readable, doesn't clip the frame edge, and doesn't
   sit over the speaker's face.
3. Only then launch the full-length encode.

## Background execution

The full encode takes 20-30+ minutes. Launch it with the Bash tool's
`run_in_background: true` **directly on the ffmpeg command itself** -- do not wrap it
in your own `nohup ... &` and background that shell script. If you background your own
wrapper, the harness tracks the wrapper (which returns in under a second after
launching the detached child) and sends a false "completed" notification almost
immediately, while the real encode keeps running unmonitored. Run `ffmpeg ... > log
2>&1` as the foregrounded body of a `run_in_background: true` Bash call so the harness
tracks the actual process and the completion notification is trustworthy.

## 8K sources and many overlays: the chained-overlay memory ceiling

This machine has 14GB RAM, no GPU, and (as of 2026-08, on Jerry's main-channel
footage) source video can arrive at 8K (7680x4320) rather than 4K. Both push the
filter-graph memory usage in ways that don't show up on typical alt-edit-sized jobs
(one motion graphic + a handful of badges), so treat the following as required reading
before compositing a video with either an 8K source or more than ~5 overlay graphics.

**Two-pass for 8K sources.** Never run the overlay filter_complex directly against an
8K input. Confirmed by direct memory measurement (`ps`/`dmesg`) on a 7680x4320 source:
decoding 8K while also running a many-stage overlay chain OOM-kills the ffmpeg process
(observed anon-rss 12-13GB, machine has 14GB + a nearly-always-full 2GB swap). Instead:
1. Pass 1: `ffmpeg -i source.mp4 -vf scale=3840:2160 -c:v libx264 -preset fast -crf 16
   -pix_fmt yuv420p -c:a copy 4k_master.mp4` -- no overlays, just downscale. This alone
   confirmed stable at ~3-5GB RSS. Slow (8K decode is inherently expensive, observed as
   low as ~0.3-0.5x realtime depending on system load) but safe.
2. Pass 2: run the overlay filter_complex against `4k_master.mp4`, not the original.
   Decoding an already-4K source is far cheaper than 8K.

**The chained-overlay stage ceiling exists independent of source resolution.** Even
compositing against the already-4K master, chaining many `overlay=...:enable=between(...)`
stages in a single filter_complex has a sharp, non-linear memory cliff -- it is NOT
roughly-linear-per-stage the way you'd guess. Directly measured on this machine: 1
stage ~3.3GB (stable), 3 stages ~4.2GB (stable, mild creep), 4 stages ~5.6GB (stable),
6 stages exploded from 5.5GB to 12.4GB in under 20 seconds and got OOM-killed. The
threshold sits somewhere between 4 and 6 chained stages and is not worth searching for
more precisely -- **cap any single ffmpeg invocation at 3 chained overlay stages** and
restructure around that ceiling instead of trusting a bigger number "because it might
be fine this time."

**The restructure: segment, don't mega-chain.** For a video with many scripture cards
(main-edit videos routinely have 30-40+ chunks across a whole video), split the
timeline into segments at the boundaries between overlay groups (≤3 cards each) and
the plain stretches between them:
- "Active" segments: `-ss <start> -t <dur> -i 4k_master.mp4` + up to 3 looped PNG
  overlay inputs + a short filter_complex (≤3 `overlay=...` stages), re-encoded.
- "Gap" segments (no cards active): same `-ss`/`-t` trim, no filter_complex, re-encoded
  plain (fast -- close to realtime, since no 8K decode and no overlay chain).
- Concatenate all segments at the end with the concat *demuxer* (`ffmpeg -f concat
  -safe 0 -i list.txt -c copy final.mp4`) -- safe because every segment shares
  identical encode settings, so no re-encoding needed at concat time.
This does the same total amount of encoding work as one full-length pass (each second
of source is encoded exactly once, just split across many small invocations), so it
does not meaningfully cost more wall-clock time than a single mega-pass *would* have
taken if it worked -- it just avoids the crash. Verify every segment's actual duration
against its intended duration with `ffprobe` before concatenating (see the next
section for why this check matters).

**Audio desync bug, confirmed the hard way on main-edit's StopSpeeding video: give
each segment its own audio, don't pair the concatenated video against one global
audio track.** Each segment's video is independently re-encoded, and output-side `-t`
duration always rounds UP to the nearest whole frame (never down) when it doesn't land
exactly on a frame boundary. That per-segment rounding is individually tiny (a
fraction of a frame) and harmless -- but if all N segments are video-only and get
concatenated, then muxed as a group against ONE continuous audio track pulled straight
from the source, those small one-directional roundings add together across every
segment boundary. The drift grows roughly linearly through the video: small and
inaudible for the first segment or two, then increasingly noticeable. On StopSpeeding
this was audible within the first few minutes despite the *total* video duration
matching the *total* audio duration closely at the very end -- `-shortest` on the final
mux only trims the tail, it does nothing to fix drift that already accumulated in the
middle, and the top-level duration check above cannot detect it because it only looks
at final totals.

The fix: never carry one global audio track through a multi-segment build. Instead,
for each segment, extract a matching audio slice from the source using the *same*
`-ss`/`-t` window used for that segment's video, then mux that segment's own video
with its own audio slice (`-c:v copy -c:a copy -shortest`) *before* concatenating.
`-shortest` on this small per-segment mux only ever trims a sub-frame sliver local to
that one segment -- video and audio drift together, imperceptibly, rather than the
video drifting away from an unrelated continuous audio track. Concatenate the
resulting audio+video segments together as the final step (concat demuxer, `-c copy`
for both streams); do not re-introduce a separate global audio mux afterward. Verify
per segment before concatenating, not just on the final file:
```
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 segment.mp4
```
Container-level `format=duration` is the trustworthy number here -- per-stream
`duration` metadata on a `-shortest`-trimmed track can still report a stale, untrimmed
value even after the container was correctly truncated, which reads as a false
mismatch if you compare stream-level durations instead.

**`-t` placement bug, confirmed the hard way:** input options like `-ss` and `-t` bind
to whichever `-i` comes *next* in the argument list, not the one before them. Writing
`-ss 400 -i 4k_master.mp4 -t 23 -loop 1 -framerate 30 -t 24 -i card.png` does NOT trim
the master to 23s -- the stray `-t 23` binds to `card.png` (the next `-i`), gets
silently clobbered by the following `-t 24` for that same input, and the master input
ends up completely untrimmed, running to the end of the file. This is exactly the kind
of bug that hides in a working-looking test (a short `-t <n>` on the *output* happens
to mask it) and only surfaces on the full run. **Always place `-ss`/`-t` immediately
before the `-i` they're meant to trim**: `-ss 400 -t 23 -i 4k_master.mp4 -loop 1
-framerate 30 -t 24 -i card.png ...`. After building any multi-input command like this,
sanity-check by `ffprobe`-ing one output segment's actual duration against what you
intended -- don't assume the flag went where you meant it to.
