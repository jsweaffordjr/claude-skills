# Visual style defaults

Standing defaults for Jerry's alt-channel thumbnails. This file intentionally mirrors
`~/.claude/skills/alt-edit/references/style-guide.md`'s brand constants (fonts/colors)
for visual consistency between the videos and their thumbnails — if that palette ever
changes, update both files by hand, there's no code-level import linking them.

## Canvas

1280x720 (YouTube's standard/minimum recommended thumbnail size), output as JPG.

## Fonts (already on this system)

- `/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf` -- headline text,
  same bold sans used for alt-edit's badges/references.

## Colors

- Gold accent: `#D4AF64` (RGB 212, 175, 100)
- White text: `#FFFFFF`
- Near-black background: `#0A0A0C` (RGB 10, 10, 12) -- same near-black alt-edit's
  overlay bars use, good default flat background color if no image background is
  wanted.

Default headline treatment: gold fill, dark stroke outline (`ImageDraw.text(...,
stroke_width=.., stroke_fill=(0,0,0,255))`) -- keeps it legible over a photo or
gradient background, not just a flat card.

## The small-scale-preview lesson

A thumbnail is only ever actually *seen* small -- YouTube's grid view renders it at
roughly 336x188, mobile smaller still (~168x94). This is the thumbnail-specific
version of alt-edit's "never judge a candidate size from an isolated/full-size view"
rule, and it matters more here than anywhere in alt-edit, because small *is* the real
viewing condition, not an edge case. Always render the finished composite down to
both realistic sizes (`scripts/gen_thumbnail.py preview`) and actually look at those
before calling a thumbnail done -- text or a cutout that reads fine at full 1280x720
can blur into illegibility or visually merge with the background once shrunk. If
something's lost at small scale, the fix is usually bigger/bolder/higher-contrast
text and simpler cutout placement, not more detail.

## Layout

No fixed template -- unlike alt-edit's overlays (which repeat the same card shape many
times per video), a thumbnail is a one-off bespoke composition each time. Ask Jerry
for the concept per thumbnail (which cutout goes where, roughly what scale, what the
headline says, what the background is) rather than assuming a layout that worked for
a previous thumbnail will fit this one's images.
