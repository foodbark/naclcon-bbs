#!/usr/bin/env python3
"""Build the BBS and web art for one foodbark.io article, from source images.

    scripts/foodbark_art.py stand-up-soba img1.jpg img2.jpg
    scripts/foodbark_art.py stand-up-soba https://cdn.foodbark.io/images/a.jpg

For each source image it writes a matched pair:

    text/foodbark/<slug>-N.ans            CP437 half-block, for the board
    webv4/root/images/foodbark/<slug>-N.png   the same art, for the web

The PNG is decoded back OUT of the .ans rather than resized from the original.
That is the whole point: the browser and the terminal then show pixel-identical
images, because they are literally the same pixels. Serving the original photo
instead would give the web a sharp image and the terminal a chunky one, which
is exactly what we are trying to avoid. It also means the two can never drift,
since one is derived from the other.

mods/exec/post_foodbark.js picks these up by slug when it posts the article.
"""
import argparse
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ANS_DIR = os.path.join(REPO, "text", "foodbark")
PNG_DIR = os.path.join(REPO, "webv4", "root", "images", "foodbark")

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# 70 columns, not 78: at this aspect it lands in 23 rows, which fits an 80x24
# terminal with a line to spare. The eight extra columns are not worth making
# every reader scroll.
WIDTH = 70


def fetch(src, dest):
    if not src.startswith(("http://", "https://")):
        return src
    req = urllib.request.Request(src, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def run(*args):
    r = subprocess.run([sys.executable] + list(args),
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit("failed: %s" % " ".join(args))
    return r.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="article slug, the last path segment of its URL")
    ap.add_argument("images", nargs="+", help="source image paths or URLs")
    ap.add_argument("--width", type=int, default=WIDTH)
    args = ap.parse_args()

    os.makedirs(ANS_DIR, exist_ok=True)
    os.makedirs(PNG_DIR, exist_ok=True)
    tmp = os.path.join("/tmp", "foodbark_art_src")
    os.makedirs(tmp, exist_ok=True)

    for n, src in enumerate(args.images, 1):
        base = "%s-%d" % (args.slug, n)
        local = fetch(src, os.path.join(tmp, base + os.path.splitext(src)[1][:5]))
        ans = os.path.join(ANS_DIR, base + ".ans")
        png = os.path.join(PNG_DIR, base + ".png")

        print(run(os.path.join(HERE, "img2ans.py"), local, ans,
                  "--width", str(args.width), "--verify"))
        print(run(os.path.join(HERE, "ans2png.py"), ans, png))

    print("\nNow deploy, then post:")
    print("  rsync -a text/ /sbbs/text/ && rsync -a webv4/ /sbbs/webv4/")


if __name__ == "__main__":
    main()
