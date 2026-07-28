#!/usr/bin/env python3
"""Decode truecolor half-block .ans art into a PNG.

Each character cell holds two vertically stacked pixels, so an 80x56 cell
grid is really an 80x112 RGB bitmap.

Half-block semantics:
  lower half block -> fg paints the BOTTOM pixel, bg the TOP
  upper half block -> fg paints the TOP pixel,    bg the BOTTOM

Two things vary independently between files, and conflating them corrupts
the result, so they are detected separately.

Glyph encoding:
  UTF-8 : U+2580 (upper half) / U+2584 (lower half)
  CP437 : raw byte 0xDF (upper half). A trailing SAUCE metadata record may
          follow, introduced by 0x1A; it is stripped.

How rows are delimited:
  newlines        the file's own LF/CRLF breaks define the rows
  cursor moves    rows begin with an absolute ESC[row;1H, so the file has no
                  newlines at all and works at any terminal width
  neither         the classic 80-column form, which relies on the terminal
                  wrapping; the row width has to be assumed (wrap_width)

CP437 art is often newline-less and UTF-8 art often is not, but that is a
convention rather than a rule, and either glyph encoding can appear with any
of the three row conventions.
"""
import re
import sys

from PIL import Image

SGR = re.compile(r"\x1b\[([0-9;]*)m")
ANY_ESC = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
ROWPOS = re.compile(r"\x1b\[\d+;1H")      # absolute row move, see load_text

UPPER = "▀"
LOWER = "▄"


def load_text(path, wrap_width=80):
    """Return (text, wrap) with SAUCE stripped and CP437 normalised.

    `wrap` is the column count to wrap at when the file carries no line
    breaks, or None when its own newlines define the rows.
    """
    raw = open(path, "rb").read()

    # SAUCE record (and any EOF padding) starts at the first 0x1A.
    eof = raw.find(b"\x1a")
    if eof != -1:
        raw = raw[:eof]

    if b"\xdf" in raw:
        # CP437 dialect: 0xDF is the upper half block. Decode as latin-1 so
        # every byte round-trips, then map the one glyph we care about.
        text = raw.decode("latin-1").replace("\xdf", UPPER)
    else:
        text = raw.decode("utf-8")

    # Art written with --positioned delimits its rows with absolute cursor
    # moves and has no newlines at all, so treat each move as a row break.
    # Without this such a file is wrapped at wrap_width, which is only ever
    # right by luck: a 64-column positioned frame would be cut every 80 cells.
    if ROWPOS.search(text):
        # Each substitution inserts the break BEFORE its row, so the first one
        # produces a leading empty row; drop it.
        return ROWPOS.sub("\n", text).lstrip("\n"), None

    # Otherwise, decide whether the file's own newlines delimit the rows by
    # asking whether they produce UNIFORM ones. Merely containing a newline
    # proves nothing: wrap-style art in the wild often carries a stray break
    # at the end or middle, and treating that as a row delimiter collapses
    # the whole image into one enormous row. Requiring uniformity also keeps
    # genuinely newline-delimited art working at any width, which a simple
    # "is any line longer than wrap_width" test would break at width > 80.
    #
    # Note this is independent of the glyph encoding. Pairing the two is
    # wrong in both directions.
    counts = [len(line) for line in
              ANY_ESC.sub("", text).replace("\r", "").split("\n")]
    while counts and counts[-1] == 0:
        counts.pop()
    # Uniform means every row matches the first, except that the last is
    # allowed to be short (a final row that was never padded out).
    uniform = (len(counts) >= 2
               and all(c == counts[0] for c in counts[:-1])
               and counts[-1] <= counts[0])
    return text, (None if uniform else wrap_width)


def decode(path, wrap_width=80):
    text, wrap = load_text(path, wrap_width)

    fg = (0, 0, 0)
    bg = (0, 0, 0)
    rows = [[]]

    def put(cell):
        if wrap and len(rows[-1]) >= wrap:
            rows.append([])
        rows[-1].append(cell)

    def emit(chunk):
        nonlocal rows
        for ch in chunk:
            if ch == "\n":
                rows.append([])
            elif ch == "\r":
                continue
            elif ch == LOWER:
                put((bg, fg))       # top, bottom
            elif ch == UPPER:
                put((fg, bg))
            else:
                put((bg, bg))       # spaces and stray text paint background

        return

    pos = 0
    for m in SGR.finditer(text):
        emit(ANY_ESC.sub("", text[pos:m.start()]))
        pos = m.end()
        params = m.group(1).split(";") if m.group(1) else ["0"]
        i = 0
        while i < len(params):
            p = params[i]
            if p in ("", "0"):
                fg = bg = (0, 0, 0)
                i += 1
            elif p in ("38", "48") and i + 4 < len(params) and params[i + 1] == "2":
                rgb = (int(params[i + 2]), int(params[i + 3]), int(params[i + 4]))
                if p == "38":
                    fg = rgb
                else:
                    bg = rgb
                i += 5
            else:
                i += 1
    emit(ANY_ESC.sub("", text[pos:]))

    while rows and not rows[-1]:
        rows.pop()

    width = max(len(r) for r in rows)
    height = len(rows) * 2
    img = Image.new("RGB", (width, height), (0, 0, 0))
    px = img.load()
    for y, row in enumerate(rows):
        for x, (top, bottom) in enumerate(row):
            px[x, y * 2] = top
            px[x, y * 2 + 1] = bottom
    return img


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    im = decode(src)
    im.save(dst)
    print(f"{src} -> {dst}  {im.size[0]}x{im.size[1]}")
