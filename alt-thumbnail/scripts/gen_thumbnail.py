#!/usr/bin/env python3
"""Compose YouTube thumbnails from existing cutout PNGs for Jerry's alt channel.

Subcommands:

  gen_thumbnail.py compose --canvas WxH [--background-color '#RRGGBB' |
      --background-image path] --layer path=P,x=X,y=Y,w=W [--layer ...]
      [--text "headline" --text-x X --text-y Y --text-size N
       [--text-color '#RRGGBB'] [--stroke-color '#RRGGBB'] [--stroke-width N]]
      --out output.jpg
      Builds the canvas, paints the background, alpha-composites each --layer
      cutout (aspect-ratio-preserving resize to width W, positioned at x,y, in the
      order given -- later layers draw on top), then draws the headline text.

  gen_thumbnail.py preview thumbnail.jpg
      Writes <stem>_preview_336x188.jpg and <stem>_preview_168x94.jpg next to the
      input -- realistic YouTube grid/mobile display sizes. Always check these
      before calling a thumbnail done; see references/style-guide.md.

This does NOT do background removal -- cutout PNGs (transparent background) are
expected to already exist. See SKILL.md.
"""
import argparse
import os
import sys
from PIL import Image, ImageDraw, ImageFont

SANS_BOLD = "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
GOLD = (212, 175, 100, 255)
NEAR_BLACK = (10, 10, 12, 255)


def parse_kv(spec):
    """Parse a 'k1=v1,k2=v2' string into a dict."""
    out = {}
    for part in spec.split(","):
        k, v = part.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def hex_to_rgba(s, alpha=255):
    s = s.lstrip("#")
    r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    return (r, g, b, alpha)


def paste_layer(canvas, spec):
    kv = parse_kv(spec)
    path, x, y, w = kv["path"], int(kv["x"]), int(kv["y"]), int(kv["w"])
    img = Image.open(path).convert("RGBA")
    ratio = w / img.width
    h = round(img.height * ratio)
    img = img.resize((w, h), Image.LANCZOS)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(img, (x, y), img)
    return Image.alpha_composite(canvas, layer)


def cmd_compose(args):
    w, h = (int(v) for v in args.canvas.lower().split("x"))
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    if args.background_image:
        bg = Image.open(args.background_image).convert("RGBA")
        bg = bg.resize((w, h), Image.LANCZOS)
        canvas = Image.alpha_composite(canvas, bg)
    else:
        color = hex_to_rgba(args.background_color) if args.background_color else NEAR_BLACK
        canvas = Image.alpha_composite(canvas, Image.new("RGBA", (w, h), color))

    for spec in args.layer or []:
        canvas = paste_layer(canvas, spec)

    if args.text:
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.truetype(SANS_BOLD, args.text_size)
        fill = hex_to_rgba(args.text_color) if args.text_color else GOLD
        stroke_fill = hex_to_rgba(args.stroke_color) if args.stroke_color else NEAR_BLACK
        draw.text((args.text_x, args.text_y), args.text, font=font, fill=fill,
                   stroke_width=args.stroke_width, stroke_fill=stroke_fill)

    out_path = args.out
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    canvas.convert("RGB").save(out_path, "JPEG", quality=92)
    print(f"wrote {out_path} ({w}x{h})")


def cmd_preview(args):
    img = Image.open(args.thumbnail).convert("RGB")
    stem, _ = os.path.splitext(args.thumbnail)
    for pw, ph in ((336, 188), (168, 94)):
        small = img.resize((pw, ph), Image.LANCZOS)
        out_path = f"{stem}_preview_{pw}x{ph}.jpg"
        small.save(out_path, "JPEG", quality=90)
        print(f"wrote {out_path}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    p_compose = sub.add_parser("compose")
    p_compose.add_argument("--canvas", default="1280x720")
    p_compose.add_argument("--background-color")
    p_compose.add_argument("--background-image")
    p_compose.add_argument("--layer", action="append")
    p_compose.add_argument("--text")
    p_compose.add_argument("--text-x", type=int, default=0)
    p_compose.add_argument("--text-y", type=int, default=0)
    p_compose.add_argument("--text-size", type=int, default=100)
    p_compose.add_argument("--text-color")
    p_compose.add_argument("--stroke-color")
    p_compose.add_argument("--stroke-width", type=int, default=4)
    p_compose.add_argument("--out", required=True)

    p_preview = sub.add_parser("preview")
    p_preview.add_argument("thumbnail")

    args = p.parse_args()
    if args.cmd == "compose":
        cmd_compose(args)
    elif args.cmd == "preview":
        cmd_preview(args)


if __name__ == "__main__":
    main()
