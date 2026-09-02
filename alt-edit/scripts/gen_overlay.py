#!/usr/bin/env python3
"""Generate scripture lower-third and keyword-badge PNG overlays for a 4K (3840x2160) canvas.

Subcommands:

  gen_overlay.py scripture <reference> <verse_text> <output.png> [--width 2560]
  gen_overlay.py scripture-auto <reference> <full_text> <output_prefix> [--width] [--max-height 1300]
      Splits a long passage into as many card-sized chunks as needed (sentence ->
      semicolon -> comma break points, greedily packed), writing <prefix>_1.png,
      <prefix>_2.png, etc. Use this instead of manually testing/splitting text by
      hand for anything longer than a short phrase -- at current font sizes even one
      normal verse often needs 2+ cards, and doing that by hand for many passages in
      one video (main-edit territory) doesn't scale.
  gen_overlay.py badge <text> <output.png> [--width 900]
      Short single-line pill (e.g. "FAST WEEKLY"). Use when the badge text is
      genuinely short -- two or three words.
  gen_overlay.py badge <label> <output.png> --body "<description>" [--width 1400]
      Two-tier card: bold gold label line + wrapped white body text below, same
      visual grammar as the scripture card. Use this whenever the badge text is a
      fuller phrase or sentence (e.g. "MISTAKE 1" + "Ending the fast too quickly") --
      forcing a long sentence onto one line at badge size runs absurdly wide.

Font sizes below are the standing defaults as of the 2026-08 corrections:
  - scripture reference/verse text: 4x the original size (3x after the first correction was
    still too small; a second correction doubled that again, on scripture text only)
  - badge text: 2x the original size (this one was fine after the first correction)

These are DEFAULTS, not gospel. Always check the actual footage (see the safe-zone
step in SKILL.md) before finalizing position/size for a given video -- framing varies
shot to shot, and text that reads fine on one clip can crowd another.
"""
import argparse
import os
import re
from PIL import Image, ImageDraw, ImageFont

SERIF_IT = "/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"

GOLD = (212, 175, 100, 255)
WHITE = (255, 255, 255, 255)
BAR_BG = (10, 10, 12, 200)  # semi-transparent near-black

# Sizing history (2026-08): original -> 3x (still too small, badges 2x was fine) -> 2x on
# top of that (4x original) after the FastingMistakes video. Badges stay at 2x original --
# only scripture kept needing to grow. If a video's actual footage can't safely fit this,
# use --label-size/--body-size to scale down for that video specifically (see
# references/ffmpeg-compositing.md's note on the 1 Kings 19 case) -- don't quietly shrink
# the shared default because one tight shot needed it.
REF_FONT_SIZE = 276     # was 46 -> 138 -> 276
VERSE_FONT_SIZE = 252   # was 42 -> 126 -> 252
BADGE_FONT_SIZE = 116   # was 58
BADGE_LABEL_SIZE = 100  # gold label line on a two-tier badge card
BADGE_BODY_SIZE = 100   # wrapped white body line(s) on a two-tier badge card


def fit_font_size(draw, text, font_path, start_size, max_width, min_size=60, step=4):
    """Shrink font_size (from start_size down to min_size) until text fits max_width.
    Guards against silent clipping -- confirmed on WhatYouStopEating (2026-09): the
    scripture label ("PROVERBS 23:31-32 (WEB)") and the "EAT BIBLICALLY" badge both
    overflowed their own canvas at the then-current sizes, and neither the label line
    nor the single-line badge had any width check (only wrapped body text did). Returns
    (size, font). Prints a note when it actually had to shrink below start_size, so
    it's visible in the generation log rather than only caught by eye later."""
    size = start_size
    font = ImageFont.truetype(font_path, size)
    if draw.textlength(text, font=font) <= max_width:
        return size, font
    while size > min_size:
        size -= step
        font = ImageFont.truetype(font_path, size)
        if draw.textlength(text, font=font) <= max_width:
            print(f"  [fit_font_size] shrank {start_size}->{size} to fit {text[:40]!r} "
                  f"within {max_width}px (was overflowing)")
            return size, font
    print(f"  [fit_font_size] WARNING: {text[:40]!r} still overflows {max_width}px "
          f"even at floor size {min_size} -- consider shortening the text")
    return min_size, font


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def rounded_bar(size, radius=30, accent_width=14):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=BAR_BG)
    d.rounded_rectangle([0, 0, accent_width, size[1] - 1], radius=radius // 2, fill=GOLD)
    return img


def make_label_body_card(out_path, label, body_text, width, label_font_size,
                          body_font_size, body_font, radius=30, accent_width=14):
    """Shared renderer: bold gold label line + wrapped body text below. Used for both
    scripture cards (serif italic body) and long-form badges (sans bold body)."""
    pad_x = 70
    body_font_obj = ImageFont.truetype(body_font, body_font_size)

    scratch = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    max_w = width - pad_x * 2
    # Label is one line, never wrapped -- auto-shrink it if it would otherwise clip off
    # the card edge (e.g. a long reference like "PROVERBS 23:31-32 (WEB)"). See
    # fit_font_size's docstring for why this check exists.
    label_font_size, label_font = fit_font_size(scratch, label.upper(), SANS_BOLD,
                                                 label_font_size, max_w)
    lines = wrap_text(scratch, body_text, body_font_obj, max_w) if body_text else []

    line_h = int(body_font_size * 1.29)
    label_h = int(label_font_size * 1.7)  # space for label line + top padding
    bottom_pad = 50
    height = label_h + len(lines) * line_h + bottom_pad if lines else label_h + bottom_pad

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.alpha_composite(rounded_bar((width, height), radius=radius, accent_width=accent_width))
    d = ImageDraw.Draw(canvas)

    d.text((pad_x, 34), label.upper(), font=label_font, fill=GOLD)
    for i, line in enumerate(lines):
        d.text((pad_x, label_h + i * line_h), line, font=body_font_obj, fill=WHITE)

    canvas.save(out_path)
    print(f"{out_path}: {width}x{height}, {len(lines)} body line(s)")
    if height > 1200:
        print(f"  WARNING: {height}px is over half of a 2160-tall frame. At current font "
              f"sizes this text chunk is too long for a lower-third -- split it shorter "
              f"(e.g. half a verse instead of a full one) rather than shipping this size.")
    return width, height


def make_scripture_card(out_path, reference, verse_text, width=2560,
                         label_size=None, body_size=None):
    return make_label_body_card(out_path, reference, verse_text, width,
                                 label_size or REF_FONT_SIZE,
                                 body_size or VERSE_FONT_SIZE, SERIF_IT)


def estimate_height(body_text, width, label_font_size, body_font_size, body_font, pad_x=70):
    """Same math as make_label_body_card, without rendering -- used to test candidate
    chunks quickly while auto-splitting long passages."""
    body_font_obj = ImageFont.truetype(body_font, body_font_size)
    scratch = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    max_w = width - pad_x * 2
    lines = wrap_text(scratch, body_text, body_font_obj, max_w) if body_text else []
    line_h = int(body_font_size * 1.29)
    label_h = int(label_font_size * 1.7)
    bottom_pad = 50
    return label_h + len(lines) * line_h + bottom_pad if lines else label_h + bottom_pad


def split_into_atoms(text):
    """Break text into small pieces at natural pause points -- sentence ends first,
    then semicolons, then commas -- for auto_chunk to reassemble into card-sized chunks.
    Bible verse punctuation (lots of semicolons for compound clauses) makes this a
    reasonable proxy for 'natural reading breaks' without needing real NLP."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    atoms = []
    for s in sentences:
        pieces = re.split(r'(?<=;)\s+', s)
        atoms.extend(p for p in pieces if p)
    return atoms


def fit_atom(atom, width, label_font_size, body_font_size, body_font, max_height):
    """Guarantee a single piece of text fits under max_height, recursively splitting at
    the best available boundary (semicolon, then comma, then a word-count midpoint as a
    last resort) if it doesn't fit as-is. This is what makes auto_chunk's output safe to
    ship unseen -- every returned piece is pre-verified to fit, not just the common case."""
    if estimate_height(atom, width, label_font_size, body_font_size, body_font) <= max_height:
        return [atom]
    for pattern in (r'(?<=;)\s+', r'(?<=,)\s+'):
        parts = [p for p in re.split(pattern, atom) if p]
        if len(parts) > 1:
            result = []
            for p in parts:
                result.extend(fit_atom(p, width, label_font_size, body_font_size, body_font, max_height))
            return result
    words = atom.split()
    if len(words) <= 1:
        return [atom]  # can't split further (single oversized word) -- ship as last resort
    mid = len(words) // 2
    left, right = " ".join(words[:mid]), " ".join(words[mid:])
    return (fit_atom(left, width, label_font_size, body_font_size, body_font, max_height) +
            fit_atom(right, width, label_font_size, body_font_size, body_font, max_height))


def auto_chunk(full_text, width, label_font_size, body_font_size, body_font, max_height=1300):
    """Split text into card-sized pieces, then greedily merge adjacent pieces back
    together wherever the combined height still fits -- keeps chunk count as low as
    possible while guaranteeing every chunk renders under max_height. Returns a list of
    text chunks in reading order."""
    atoms = split_into_atoms(full_text)
    fitted = []
    for a in atoms:
        fitted.extend(fit_atom(a, width, label_font_size, body_font_size, body_font, max_height))

    chunks, current = [], ""
    for atom in fitted:
        trial = (current + " " + atom).strip()
        if estimate_height(trial, width, label_font_size, body_font_size, body_font) <= max_height:
            current = trial
        else:
            if current:
                chunks.append(current)
            current = atom
    if current:
        chunks.append(current)
    return chunks


def make_badge_card(out_path, label, body_text, width=1400, label_size=None, body_size=None):
    """Two-tier badge: gold label (e.g. 'MISTAKE 1') + wrapped white description."""
    return make_label_body_card(out_path, label, body_text, width,
                                 label_size or BADGE_LABEL_SIZE,
                                 body_size or BADGE_BODY_SIZE, SANS_BOLD,
                                 radius=24, accent_width=12)


BADGE_PAD_X = 50  # minimum breathing room on each side of single-line badge text


def make_badge(out_path, text, width=900, font_size=None):
    """Short single-line pill -- use only when text is genuinely 2-3 words."""
    requested_size = font_size or BADGE_FONT_SIZE
    height = int(requested_size * 2.05)  # box height stays put even if text auto-shrinks,
                                          # so a run of badges (FAST WEEKLY/EAT BIBLICALLY/
                                          # WALK DAILY) stays the same height as a set.
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.alpha_composite(rounded_bar((width, height), radius=24, accent_width=12))
    d = ImageDraw.Draw(canvas)
    # Confirmed on WhatYouStopEating (2026-09): "EAT BIBLICALLY" at the then-default
    # size measured wider than the 900px canvas itself (negative margin, both edges
    # cut off) while shorter badges looked fine -- this was never checked before.
    font_size, font = fit_font_size(d, text, SANS_BOLD, requested_size,
                                     width - BADGE_PAD_X * 2)
    tw = d.textlength(text, font=font)
    d.text(((width - tw) / 2, (height - font_size) / 2 - 10), text, font=font, fill=WHITE)
    canvas.save(out_path)
    print(f"{out_path}: {width}x{height}")
    return width, height


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    p_scripture = sub.add_parser("scripture")
    p_scripture.add_argument("reference")
    p_scripture.add_argument("verse_text")
    p_scripture.add_argument("output")
    p_scripture.add_argument("--width", type=int, default=2560)
    p_scripture.add_argument("--label-size", type=int, default=None,
                              help="override REF_FONT_SIZE for unusually tight footage")
    p_scripture.add_argument("--body-size", type=int, default=None,
                              help="override VERSE_FONT_SIZE for unusually tight footage")

    p_auto = sub.add_parser("scripture-auto",
                             help="split a long passage into as many card-sized chunks as needed")
    p_auto.add_argument("reference")
    p_auto.add_argument("full_text")
    p_auto.add_argument("output_prefix", help="writes <prefix>_1.png, <prefix>_2.png, ...")
    p_auto.add_argument("--width", type=int, default=2560)
    p_auto.add_argument("--max-height", type=int, default=1300)
    p_auto.add_argument("--label-size", type=int, default=None)
    p_auto.add_argument("--body-size", type=int, default=None)

    p_badge = sub.add_parser("badge")
    p_badge.add_argument("text", help="short pill text, or the label if --body is given")
    p_badge.add_argument("output")
    p_badge.add_argument("--body", default=None, help="if given, renders a two-tier label+body card")
    p_badge.add_argument("--width", type=int, default=None)
    p_badge.add_argument("--label-size", type=int, default=None,
                          help="override BADGE_LABEL_SIZE for unusually tight footage")
    p_badge.add_argument("--body-size", type=int, default=None,
                          help="override BADGE_BODY_SIZE (two-tier) or BADGE_FONT_SIZE (single-line)")

    args = p.parse_args()
    out_ref = args.output_prefix if args.cmd == "scripture-auto" else args.output
    os.makedirs(os.path.dirname(os.path.abspath(out_ref)) or ".", exist_ok=True)

    if args.cmd == "scripture":
        make_scripture_card(args.output, args.reference, args.verse_text, args.width,
                             args.label_size, args.body_size)
    elif args.cmd == "scripture-auto":
        label_size = args.label_size or REF_FONT_SIZE
        body_size = args.body_size or VERSE_FONT_SIZE
        chunks = auto_chunk(args.full_text, args.width, label_size, body_size, SERIF_IT,
                             args.max_height)
        print(f"split into {len(chunks)} chunk(s):")
        for i, chunk in enumerate(chunks, 1):
            out_path = f"{args.output_prefix}_{i}.png"
            make_scripture_card(out_path, args.reference, chunk, args.width,
                                 args.label_size, args.body_size)
            words = len(chunk.split())
            print(f"  [{i}] ~{words} words: {chunk[:70]}{'...' if len(chunk) > 70 else ''}")
    elif args.cmd == "badge":
        if args.body:
            make_badge_card(args.output, args.text, args.body, args.width or 1400,
                             args.label_size, args.body_size)
        else:
            make_badge(args.output, args.text, args.width or 900, args.body_size)


if __name__ == "__main__":
    main()
