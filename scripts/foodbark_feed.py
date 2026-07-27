#!/usr/bin/env python3
"""
Fetch the foodbark.io RSS feed and split it into the two things the BBS wants:

  1. ctrl/pelican_foodbark.txt  - recent /foodporn/ captions plus recent essay
     titles, loaded into the Pelican's system prompt so she knows what the
     sysop has been cooking and writing about.

  2. data/foodbark_pending.json - essays from /posts/ that have not yet been
     posted to the Local:FOODBARK sub.

Why the split: Synchronet message bases can only be written through the JS
MsgBase object, so this script cannot post them itself. It stages the work and
mods/exec/post_foodbark.js does the posting. Cron runs the two in sequence.

Pattern mirrors pelican_weather_tides.py and pelican_naclcom_scrape.py: atomic
.tmp + rename, write to both repo and live paths, keep the last good copy on
failure rather than truncating.

Run from cron a few times a day; the feed is not busy.
"""

import datetime
import html
import io
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

FEED = "https://foodbark.io/index.xml"

# foodbark.io 403s a default urllib User-Agent, so present as a browser.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
}

REPO = "/home/ubuntu/naclcon-bbs/"
LIVE = "/sbbs/"

KNOWLEDGE_REL = "ctrl/pelican_foodbark.txt"
PENDING_REL   = "data/foodbark_pending.json"
POSTED_REL    = "data/foodbark_posted.txt"

# How much to carry. The feed holds 1000+ captions; the Pelican only needs a
# recent sense of it, and every line costs prompt tokens on every chat turn.
CAPTIONS = 40
TITLES   = 12
# Guard against a runaway first run flooding the sub.
MAX_POST_PER_RUN = 50


def fetch(url, timeout=30, attempts=3):
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = e
            if i < attempts - 1:
                import time
                time.sleep(2)
    raise last


def strip_html(s):
    """RSS descriptions carry markup and entities. Flatten to BBS-safe text."""
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</p\s*>", "\n\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    # Curly quotes and dashes render as junk in CP437; fold to ASCII.
    for a, b in (("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'),
                 ("–", "-"), ("—", ", "), ("…", "..."), (" ", " ")):
        s = s.replace(a, b)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def wrap(text, width=76):
    import textwrap
    out = []
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        out.append("\n".join(textwrap.wrap(para, width)) if para else "")
    return "\n\n".join(out)


def parse_date(s):
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.datetime.strptime(s.strip(), fmt)
        except ValueError:
            pass
    return None


def load_posted(path):
    try:
        with io.open(path, encoding="utf-8") as f:
            return {l.strip() for l in f if l.strip()}
    except FileNotFoundError:
        return set()


def write_both(rel, body):
    """Atomic write to repo and live. Non-fatal if the live tree is absent."""
    for base in (REPO, LIVE):
        path = base + rel
        if not os.path.isdir(os.path.dirname(path)):
            continue
        tmp = path + ".tmp"
        with io.open(tmp, "w", encoding="cp437", errors="replace", newline="\n") as f:
            f.write(body)
        os.replace(tmp, path)


def main():
    raw = fetch(FEED)
    root = ET.fromstring(raw)
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("no <channel> in feed; refusing to overwrite good files")

    posts, porn = [], []
    for it in channel.findall("item"):
        link = (it.findtext("link") or "").strip()
        entry = {
            "guid":  (it.findtext("guid") or link).strip(),
            "title": strip_html(it.findtext("title") or "").strip(),
            "link":  link,
            "date":  (it.findtext("pubDate") or "").strip(),
            "body":  strip_html(it.findtext("description") or ""),
        }
        if "/posts/" in link:
            posts.append(entry)
        elif "/foodporn/" in link:
            porn.append(entry)

    if not posts and not porn:
        raise SystemExit("feed parsed but held no items; keeping previous files")

    def keyed(e):
        d = parse_date(e["date"])
        return d.timestamp() if d else 0
    posts.sort(key=keyed, reverse=True)
    porn.sort(key=keyed, reverse=True)

    # --- 1. the Pelican's knowledge file ---------------------------------
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    L = []
    L.append("THE SYSOP'S BLOG, foodbark.io (refreshed %s)." % stamp)
    L.append("")
    L.append("This is the sysop's own site: long-form posts under /posts/ and a very")
    L.append("large running photo feed of what he cooks under /foodporn/. You follow it")
    L.append("the way you'd follow a friend's cooking. Bring it up when food, cooking or")
    L.append("what he's been up to comes up naturally; don't recite the list, and don't")
    L.append("pretend you were at the table.")
    L.append("")
    L.append("RECENT WRITING (%d most recent of %d posts):" % (min(TITLES, len(posts)), len(posts)))
    L.append("")
    for e in posts[:TITLES]:
        d = parse_date(e["date"])
        L.append("  %s  %s" % (d.strftime("%Y-%m-%d") if d else "          ", e["title"]))
    L.append("")
    L.append("These are also posted to the foodbark.io message sub on this board, so you")
    L.append("can point people there to read them.")
    L.append("")
    L.append("RECENT COOKING (%d most recent of %d captions):" % (min(CAPTIONS, len(porn)), len(porn)))
    L.append("")
    for e in porn[:CAPTIONS]:
        d = parse_date(e["date"])
        cap = " ".join(e["body"].split())
        if len(cap) > 150:
            cap = cap[:147].rstrip() + "..."
        L.append("  %s  %s" % (d.strftime("%Y-%m-%d") if d else "          ", cap))
    L.append("")
    write_both(KNOWLEDGE_REL, "\n".join(L) + "\n")

    # --- 2. stage unposted essays for the JS half -------------------------
    posted = load_posted(REPO + POSTED_REL)
    pending = [e for e in posts if e["guid"] not in posted]
    pending.sort(key=keyed)          # oldest first, so the sub reads chronologically
    truncated = len(pending) > MAX_POST_PER_RUN
    if truncated:
        pending = pending[:MAX_POST_PER_RUN]
    for e in pending:
        e["body"] = wrap(e["body"])
    write_both(PENDING_REL, json.dumps(pending, indent=1) + "\n")

    print("posts=%d foodporn=%d  knowledge=%d lines  pending=%d%s"
          % (len(posts), len(porn), len(L), len(pending),
             "  (capped at %d)" % MAX_POST_PER_RUN if truncated else ""))


if __name__ == "__main__":
    main()
