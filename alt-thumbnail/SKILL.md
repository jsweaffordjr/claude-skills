---
name: alt-thumbnail
description: Compose a YouTube thumbnail for Jerry's alt (biblical-health/carnivore-diet)
  channel from existing cutout images (transparent-background PNGs Jerry already has,
  typically sitting next to the source video) plus a headline, collaborating with Jerry
  on layout/background/text, then rendering a finished 1280x720 thumbnail. Only run this
  when Jerry explicitly invokes it via /alt-thumbnail and tells you which images to use.
---

# alt-thumbnail

Composites a finished YouTube thumbnail from cutout images Jerry already has (headshot
reactions, product/subject shots, etc. — transparent-background PNGs) plus a headline,
in the alt channel's established gold/white/near-black brand look.

**Scope**: the input is pre-made transparent cutout PNGs Jerry points you at — this
skill does **not** do background removal/matting itself. If a needed cutout doesn't
exist yet, say so rather than trying to generate one. Starts at "cutouts + a concept,"
ends at "finished 1280x720 thumbnail file."

**Standing defaults** (confirmed with Jerry, don't re-ask each time):
- Canvas: 1280x720 (YouTube's standard/minimum recommended thumbnail size)
- Output: JPG
- Palette/fonts: reused from alt-edit's brand — see references/style-guide.md
- Headline: gold fill with a dark stroke outline, for legibility over any background
- These can still be overridden per-thumbnail if Jerry asks for something different.

## Workflow

### 0. Setup
Confirm Pillow is importable (`python3 -c "import PIL"`); `pip install --user Pillow`
if not. No bundled binaries needed — this skill only composites static images, no
video/ffmpeg work.

### 1. Gather inputs — interactive, do not skip
This is the step that actually needs Jerry. Nail down:
- **Which cutout image(s)** to use — ask; default assumption is they're sitting in the
  same folder as the source video (confirmed pattern: e.g. `headshot2.png` +
  `toe_sneakers.png` next to `ToeSneakers.mp4`).
- **Layout concept**: which image goes where, roughly what scale, relative to the
  others.
- **Headline text**.
- **Background**: solid color, gradient, or an actual video frame — ask, don't assume.

Treat exact pixel placement as *tentative* until step 3's real composite check — same
"don't trust your own visual estimate" discipline alt-edit uses for overlay placement.

### 2. Compose
```
python3 scripts/gen_thumbnail.py compose \
  --canvas 1280x720 \
  --background-color "#141414" \
  --layer path=<cutout1.png>,x=<X>,y=<Y>,w=<WIDTH> \
  --layer path=<cutout2.png>,x=<X>,y=<Y>,w=<WIDTH> \
  --text "<headline>" --text-x=<X> --text-y=<Y> --text-size=<SIZE> \
  --out <thumbnail.jpg>
```
`--layer` is repeatable, one per cutout, in paint order (later layers draw on top).
Each layer's height derives from its own image's aspect ratio — only specify width.
`--background-image <path>` can replace `--background-color` if Jerry wants an actual
frame behind the cutouts instead of a flat/gradient color.

### 3. Check at actual small size — do not skip
A thumbnail is only ever actually *seen* small (YouTube grid ~336x188, mobile
~168x94) — this is the thumbnail-specific version of alt-edit's "never judge from an
isolated/full-size view" lesson, and it matters even more here.
```
python3 scripts/gen_thumbnail.py preview <thumbnail.jpg>
```
Writes downscaled copies at both sizes. Look at all three (full-size + both previews)
with the Read tool. Confirm the headline and every cutout still read clearly at the
small sizes, not just at full 1280x720 — text that looks fine full-size can vanish or
blur into the background once shrunk. Iterate on position/size/stroke-width and re-run
`compose`/`preview` if anything gets lost.

### 4. Deliver
Report the output path, ask Jerry about the final filename (default suggestion:
`<VideoName>_thumbnail.jpg` next to the source video) and whether to keep or discard
any rejected intermediate attempts — don't delete anything without asking.

## Reference files
- `references/style-guide.md` — canvas size, brand colors/fonts (mirrors alt-edit's
  palette), the small-scale-preview lesson. Read before step 2.
