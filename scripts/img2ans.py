#!/usr/bin/env python3
"""Encode an image or animation into truecolor half-block ANSI.

The exact inverse of ans2png.py. Each character cell holds two
vertically stacked pixels, drawn as an upper half block:

    ESC[38;2;r;g;b;48;2;r;g;bm  UPPER_HALF   ->  fg = top pixel
                                                 bg = bottom pixel

so an 80x32 pixel image becomes 80 columns by 16 character rows.

Round-trip check: encoding with this and decoding with ans2png.py must give
back the pixels you started with, exactly. --verify asserts it.

Output dialect:
  (default) raw byte 0xDF, the CP437 upper half block, which is what DOS-era
            terminals and SyncTERM expect. Written as latin-1 so the bytes
            round-trip 1:1.
  --utf8    real U+2580, for modern UTF-8 terminals.

Line breaks: at exactly 80 columns the trailing newline is omitted and the
terminal's own wrap is relied on, which is how classic 80-column .ans files
are built. Emitting a newline there costs a blank line per row. Narrower
output gets CRLF.

Two traps worth knowing, both of which only bite outside a classic terminal:
  * Auto-wrap art shears diagonally in any window that is not exactly 80
    columns wide. Use --positioned, which pins every row with ESC[row;1H.
  * Raw 0xDF is not valid UTF-8. In a modern terminal it renders as a
    replacement character unless something translates it. Use --utf8.

Usage:
  img2ans.py in.png  out.ans --width 80 --verify
  img2ans.py in.gif  out.ans --width 80 --utf8 --positioned
  img2ans.py in.webp out/    --width 80 --frames   # one .ans per frame
"""
import argparse
import os
import sys

from PIL import Image, ImageSequence

UPPER_UTF8 = "▀"
UPPER_CP437 = "\xdf"      # latin-1 for raw byte 0xDF


def load_frames(path, bg):
    """Return ([RGB frames], [durations ms])."""
    im = Image.open(path)
    frames, durs = [], []
    for f in ImageSequence.Iterator(im):
        d = f.info.get("duration", 0)
        rgba = f.convert("RGBA")
        # Composite transparency onto the terminal background rather than
        # letting it come through as black-ish garbage.
        plate = Image.new("RGBA", rgba.size, bg + (255,))
        plate.alpha_composite(rgba)
        frames.append(plate.convert("RGB"))
        durs.append(d)
    return frames, durs


def fit(img, cols, space=False):
    """Resize to `cols` wide, preserving aspect.

    Half-block mode packs two pixels into each cell, so the pixel height is
    twice the row count and must be even. Space mode paints one cell per
    pixel; since a character cell is about twice as tall as it is wide, the
    pixel height is halved instead, which keeps the aspect ratio identical
    between the two modes.
    """
    w, h = img.size
    if space:
        return img.resize((cols, max(1, round(h * cols / w / 2))), Image.BOX)
    new_h = max(2, round(h * cols / w))
    if new_h % 2:
        new_h += 1
    # BOX averages the source pixels, which keeps re-encoded pixel art from
    # picking up the ringing that LANCZOS adds around hard colour edges.
    return img.resize((cols, new_h), Image.BOX)


def encode(img, glyph, newline, positioned=False, top_row=1):
    """Encode one already-resized RGB image to an ANSI string.

    positioned=True prefixes each row with an absolute cursor move
    (ESC[row;1H) instead of depending on newlines or the terminal wrapping at
    the right column. That makes the output independent of the terminal's
    actual width, which matters for two cases: a window wider than 80 columns
    (no-newline art shears diagonally across it) and animation (each frame
    lands exactly on top of the last with no drift).
    """
    px = img.load()
    w, h = img.size
    out = []
    fg = bg = None
    for row, cy in enumerate(range(0, h, 2)):
        if positioned:
            # NOTE: `top` below is rebound per pixel, so the row offset must
            # not share that name.
            out.append("\x1b[%d;1H" % (top_row + row))
            # A cursor jump does not reset colours, but starting each row from
            # a known state keeps a frame from inheriting the previous one.
            fg = bg = None
        for x in range(w):
            top = px[x, cy]
            bot = px[x, cy + 1] if cy + 1 < h else (0, 0, 0)
            # Only emit the parts of the SGR that actually changed. Naively
            # re-stating both colours plus a reset per cell is what makes the
            # art/ files 100KB+; this keeps them a fraction of that.
            parts = []
            if top != fg:
                parts.append("38;2;%d;%d;%d" % top)
                fg = top
            if bot != bg:
                parts.append("48;2;%d;%d;%d" % bot)
                bg = bot
            if parts:
                out.append("\x1b[" + ";".join(parts) + "m")
            out.append(glyph)
        if positioned:
            # Clear to end of line so a wider terminal does not keep whatever
            # was sitting to the right of the image.
            out.append("\x1b[0m\x1b[K")
            continue
        if newline:
            out.append("\r\n")
            # A newline resets nothing, but SyncTERM paints the rest of the
            # row with the current background. Clear it so trailing cells do
            # not smear the last colour across the line.
            out.append("\x1b[0m")
            fg = bg = None
    out.append("\x1b[0m")
    return "".join(out)


def encode_space(img, positioned=False, top_row=1):
    """Encode using background-coloured ASCII spaces, one cell per pixel.

    No half block, no box drawing, nothing outside 0x20-0x7E. A terminal or
    font missing U+2580 substitutes the replacement character for it, which
    shows up as scattered black diamonds; a space cannot fail that way. The
    cost is half the vertical resolution.
    """
    px = img.load()
    w, h = img.size
    out = []
    bg = None
    for y in range(h):
        if positioned:
            out.append("\x1b[%d;1H" % (top_row + y))
            bg = None
        for x in range(w):
            c = px[x, y]
            if c != bg:
                out.append("\x1b[48;2;%d;%d;%dm" % c)
                bg = c
            out.append(" ")
        out.append("\x1b[0m\x1b[K" if positioned else "\x1b[0m")
        bg = None
        if not positioned:
            out.append("\r\n")
    out.append("\x1b[0m")
    return "".join(out)


def write_ans(text, path, utf8):
    data = text.encode("utf-8") if utf8 else text.encode("latin-1")
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst", help="output .ans, or a directory with --frames")
    ap.add_argument("--width", type=int, default=80, help="columns (default 80)")
    ap.add_argument("--frames", action="store_true",
                    help="write every frame as its own .ans into dst/")
    ap.add_argument("--frame", type=int, default=0,
                    help="which single frame to encode (default 0)")
    ap.add_argument("--utf8", action="store_true", help="U+2580 instead of 0xDF")
    ap.add_argument("--positioned", action="store_true",
                    help="absolute cursor move per row; width-independent")
    ap.add_argument("--space", action="store_true",
                    help="ASCII spaces + background colour, no half block")
    ap.add_argument("--bg", default="0,0,0", help="background r,g,b for alpha")
    ap.add_argument("--verify", action="store_true",
                    help="decode the result back and compare pixels")
    args = ap.parse_args()

    bg = tuple(int(v) for v in args.bg.split(","))
    glyph = UPPER_UTF8 if args.utf8 else UPPER_CP437
    # At exactly 80 columns, rely on terminal auto-wrap (see module docstring).
    newline = args.width != 80

    frames, durs = load_frames(args.src, bg)
    sized = [fit(f, args.width, args.space) for f in frames]

    def enc(img):
        if args.space:
            return encode_space(img, args.positioned)
        return encode(img, glyph, newline, args.positioned)

    if args.frames:
        os.makedirs(args.dst, exist_ok=True)
        total = 0
        for i, img in enumerate(sized):
            p = os.path.join(args.dst, "frame%02d.ans" % i)
            total += write_ans(enc(img), p, args.utf8)
        rows = sized[0].size[1] if args.space else sized[0].size[1] // 2
        print("%d frames -> %s  %dx%d cells  %d bytes total"
              % (len(sized), args.dst, args.width, rows, total))
        print("durations(ms): %s" % durs)
    else:
        img = sized[args.frame]
        n = write_ans(enc(img), args.dst, args.utf8)
        print("%s -> %s  %dx%d cells  %d bytes"
              % (args.src, args.dst, args.width, img.size[1] // 2, n))

        if args.verify:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from ans2png import decode
            back = decode(args.dst)
            if back.size != img.size:
                print("VERIFY FAIL: size %s != %s" % (back.size, img.size))
                return 1
            a, b = img.load(), back.load()
            bad = sum(1 for y in range(img.size[1]) for x in range(img.size[0])
                      if a[x, y] != b[x, y])
            total = img.size[0] * img.size[1]
            print("verify: %d/%d pixels differ -> %s"
                  % (bad, total, "LOSSLESS" if bad == 0 else "MISMATCH"))
            return 0 if bad == 0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
