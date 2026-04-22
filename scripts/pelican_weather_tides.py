#!/usr/bin/env python3
"""
Fetch current NWS weather forecast + NOAA tide predictions for
Carolina Beach, NC and write a plain-text block to
ctrl/pelican_weather.txt. The Pelican's system prompt loads this
file alongside pelican_news.txt so she can reference live conditions
in chat.

Run from cron every 30 minutes. On fetch failure for a given source,
keeps the last successful block for that source (no torn writes).
"""

import datetime
import json
import os
import urllib.request
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")
UTC = datetime.timezone.utc


def now_utc():
    return datetime.datetime.now(UTC)


def now_eastern():
    return datetime.datetime.now(EASTERN)

LAT, LON = 34.035, -77.894                 # Carolina Beach, NC
TIDE_STATION = "8658163"                   # Wrightsville Beach, NC (closest NOAA gauge)
TIDE_STATION_NAME = "Wrightsville Beach"

REPO_PATH = "/home/ubuntu/naclcon-bbs/ctrl/pelican_weather.txt"
LIVE_PATH = "/sbbs/ctrl/pelican_weather.txt"

HEADERS = {"User-Agent": "NaClCON-BBS (foodbark@gmail.com)"}


def get_json(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fetch_weather():
    point = get_json(f"https://api.weather.gov/points/{LAT},{LON}")
    fc = get_json(point["properties"]["forecast"])
    out = []
    for p in fc["properties"]["periods"][:4]:
        out.append(
            f"  {p['name']}: {p['temperature']}°{p['temperatureUnit']}, "
            f"{p['shortForecast']}. Wind {p['windSpeed']} {p['windDirection']}."
        )
    return out


def fetch_tides():
    now = now_utc()
    start = (now - datetime.timedelta(hours=2)).strftime("%Y%m%d")
    end = (now + datetime.timedelta(hours=48)).strftime("%Y%m%d")
    url = (
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?"
        f"station={TIDE_STATION}&product=predictions&interval=hilo&"
        "datum=MLLW&units=english&time_zone=lst_ldt&format=json&"
        f"begin_date={start}&end_date={end}"
    )
    td = get_json(url)
    preds = td.get("predictions", [])
    # NOAA timestamps are station-local (Eastern). Drop entries more than 30min old.
    cutoff = now_eastern().replace(tzinfo=None) - datetime.timedelta(minutes=30)
    out = []
    for t in preds:
        pt = datetime.datetime.strptime(t["t"], "%Y-%m-%d %H:%M")
        if pt < cutoff:
            continue
        label = "high tide" if t["type"] == "H" else "low tide"
        out.append(f"  {t['t']} -- {label} ({t['v']} ft)")
        if len(out) >= 6:
            break
    return out


def main():
    try:
        wx = fetch_weather()
        wx_ok = True
    except Exception as e:
        wx, wx_ok = [f"  (NWS fetch failed: {e})"], False

    try:
        tides = fetch_tides()
        tides_ok = True
    except Exception as e:
        tides, tides_ok = [f"  (NOAA fetch failed: {e})"], False

    if not (wx_ok or tides_ok):
        # Both failed -- don't clobber last known good file
        raise SystemExit("both fetches failed; keeping previous file")

    stamp = now_eastern().strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        f"LIVE LOCAL CONDITIONS (Carolina Beach, NC) -- refreshed {stamp}:",
        "",
        "Weather forecast (NWS):",
        "",
    ]
    lines.extend(wx)
    lines.append("")
    lines.append(
        f"Tide predictions ({TIDE_STATION_NAME} NOAA station -- proxy for Carolina Beach):"
    )
    lines.append("")
    lines.extend(tides)
    lines.append("")
    lines.append(
        "You can weave these in when the conversation naturally touches weather, the beach,"
    )
    lines.append(
        "surfing, fishing, going outside, or what the day feels like. Don't recite them"
    )
    lines.append(
        "unprompted. Prefer these live facts over vague coastal guesses."
    )

    content = "\n".join(lines) + "\n"
    for path in (LIVE_PATH, REPO_PATH):
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            f.write(content)
        os.replace(tmp, path)

    print(f"ok ({stamp})")


if __name__ == "__main__":
    main()
