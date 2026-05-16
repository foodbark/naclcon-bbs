#!/usr/bin/env python3
"""
Fetch naclcon.com pages and write a flat plain-text reference to
ctrl/pelican_naclcom.txt for Pelican to load at session start.

Pattern mirrors pelican_weather_tides.py: atomic .tmp + rename,
write to both repo and live paths, keep last-good copy on total failure.

Run from cron weekly (the site doesn't change minute-to-minute).
"""

import datetime
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")

BASE = "https://naclcon.com"
# Pages worth pulling. Order is the order they appear in the output file.
PAGES = [
    ("/about-naclcon",          "ABOUT NaClCON"),
    ("/schedule",               "SCHEDULE"),
    ("/speakers",               "SPEAKERS"),
    ("/venue-and-must-visits",  "VENUE & MUST-VISITS"),
    ("/event-registration",     "REGISTRATION"),
    ("/faqs",                   "FAQs"),
    ("/sponsors-and-partners",  "SPONSORS & PARTNERS"),
]

REPO_PATH = "/home/ubuntu/naclcon-bbs/ctrl/pelican_naclcom.txt"
LIVE_PATH = "/sbbs/ctrl/pelican_naclcom.txt"

HEADERS = {"User-Agent": "NaClCON-BBS-Pelican (foodbark@gmail.com)"}

# Block-level tags whose end produces a newline (preserves rough paragraph structure).
BLOCK_TAGS = {
    "p", "div", "section", "article", "li", "tr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "table", "blockquote", "pre", "main",
}
# Tags whose entire content we drop (navigation chrome, scripts, etc.).
# Only tags with closing tags go here. Void elements (meta, link, br, img,
# input, hr) have no content to skip and would unbalance the depth counter.
SKIP_TAGS = {
    "script", "style", "nav", "header", "footer", "noscript",
    "svg", "form", "button", "iframe", "aside",
}


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.buf = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip_depth += 1
        elif tag == "br":
            self.buf.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif tag in BLOCK_TAGS:
            self.buf.append("\n")

    def handle_data(self, data):
        if self.skip_depth == 0:
            self.buf.append(data)

    def get_text(self):
        text = "".join(self.buf)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Drop common navigation/footer leftovers that survive tag stripping.
        lines = []
        for ln in text.split("\n"):
            s = ln.strip()
            if s in {"Home", "Menu", "Close", "Open Menu", "Close Menu", "Skip to Content"}:
                continue
            lines.append(ln)
        return "\n".join(lines).strip()


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8", errors="replace")
    parser = TextExtractor()
    parser.feed(raw)
    return parser.get_text()


def main():
    stamp = datetime.datetime.now(EASTERN).strftime("%Y-%m-%d %H:%M %Z")
    sections = [
        f"NACLCON.COM REFERENCE (refreshed {stamp})",
        "",
        "Authoritative reference for everything on naclcon.com: con info, schedule, "
        "speakers, venue, registration, FAQs, sponsors. When a user asks about anything "
        "con-related, draw from here first. The canonical URL is https://naclcon.com; "
        "each section below names the page slug.",
        "",
    ]
    failures = []
    ok = 0
    for path, title in PAGES:
        url = BASE + path
        try:
            text = fetch(url)
        except Exception as e:
            failures.append((path, str(e)))
            print(f"  fetch failed: {path}: {e}", file=sys.stderr)
            continue
        if not text:
            failures.append((path, "empty body"))
            continue
        sections.append(f"=== {title}  ({url}) ===")
        sections.append("")
        sections.append(text)
        sections.append("")
        ok += 1

    if ok == 0:
        raise SystemExit("all fetches failed; keeping previous file")

    if failures:
        sections.append("")
        sections.append(
            "(note: " + str(len(failures)) + " page(s) failed this refresh: " +
            ", ".join(p for p, _ in failures) + ")"
        )

    content = "\n".join(sections) + "\n"
    for path in (LIVE_PATH, REPO_PATH):
        tmp = path + ".tmp"
        try:
            with open(tmp, "w") as f:
                f.write(content)
            os.replace(tmp, path)
        except Exception as e:
            print(f"  write failed: {path}: {e}", file=sys.stderr)

    print(f"ok ({stamp}, {ok}/{len(PAGES)} pages, {len(content)} bytes)")


if __name__ == "__main__":
    main()
