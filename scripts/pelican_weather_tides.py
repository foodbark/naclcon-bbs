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
TIDE_STATION = "8658559"                   # Wilmington Beach, NC — at Carolina Beach (~0.3 mi)
TIDE_STATION_NAME = "Wilmington Beach"

REPO_PATH = "/home/ubuntu/naclcon-bbs/ctrl/pelican_weather.txt"
LIVE_PATH = "/sbbs/ctrl/pelican_weather.txt"

# Compact key=value snapshot consumed by the lbshell weather/tide strip.
SHELL_REPO_PATH = "/home/ubuntu/naclcon-bbs/data/weather_tides.txt"
SHELL_LIVE_PATH = "/sbbs/data/weather_tides.txt"
SHELL_LOCATION = "Carolina Beach"
UV_ZIP = "28428"

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


def fetch_current_conditions():
    """Return (temp_f, precip_pct) for the current hour from NWS hourly forecast."""
    point = get_json(f"https://api.weather.gov/points/{LAT},{LON}")
    fc = get_json(point["properties"]["forecastHourly"])
    p = fc["properties"]["periods"][0]
    temp = int(p["temperature"])
    precip_obj = p.get("probabilityOfPrecipitation") or {}
    precip = precip_obj.get("value")
    precip = int(precip) if precip is not None else 0
    return temp, precip


def fetch_uv():
    """Return current-hour UV index (int) for UV_ZIP. 0 when there's no matching hour
    (the EPA feed usually omits overnight rows, which is fine — UV is 0 then anyway)."""
    data = get_json(
        f"https://data.epa.gov/efservice/getEnvirofactsUVHOURLY/ZIP/{UV_ZIP}/JSON"
    )
    target = now_eastern().strftime("%b/%d/%Y %I %p")
    for r in data:
        if r.get("DATE_TIME") == target:
            return int(r.get("UV_VALUE", 0))
    return 0


def fetch_next_tide_times():
    """Return (next_high, next_low) as 'HH:MM' strings, or (None, None) on failure."""
    now = now_utc()
    start = now.strftime("%Y%m%d")
    end = (now + datetime.timedelta(hours=48)).strftime("%Y%m%d")
    url = (
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?"
        f"station={TIDE_STATION}&product=predictions&interval=hilo&"
        "datum=MLLW&units=english&time_zone=lst_ldt&format=json&"
        f"begin_date={start}&end_date={end}"
    )
    td = get_json(url)
    preds = td.get("predictions", [])
    now_local = now_eastern().replace(tzinfo=None)
    next_high = next_low = None
    for t in preds:
        pt = datetime.datetime.strptime(t["t"], "%Y-%m-%d %H:%M")
        if pt < now_local:
            continue
        if t["type"] == "H" and next_high is None:
            next_high = pt.strftime("%H:%M")
        elif t["type"] == "L" and next_low is None:
            next_low = pt.strftime("%H:%M")
        if next_high and next_low:
            break
    return next_high, next_low


def read_kv(path):
    try:
        out = {}
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
        return out
    except FileNotFoundError:
        return {}


def write_shell_snapshot():
    """Per-field merge with the existing file so a transient API failure for one
    source doesn't blank out the others on the strip."""
    shell = read_kv(SHELL_LIVE_PATH)
    shell["LOCATION"] = SHELL_LOCATION

    try:
        temp, precip = fetch_current_conditions()
        shell["TEMP_F"] = str(temp)
        shell["PRECIP_PCT"] = str(precip)
    except Exception as e:
        print(f"current-conditions fetch failed: {e}")

    try:
        shell["UV_INDEX"] = str(fetch_uv())
    except Exception as e:
        print(f"UV fetch failed: {e}")

    try:
        nh, nl = fetch_next_tide_times()
        if nh:
            shell["HIGH_TIDE"] = nh
        if nl:
            shell["LOW_TIDE"] = nl
    except Exception as e:
        print(f"tide-times fetch failed: {e}")

    shell["UPDATED"] = now_eastern().strftime("%Y-%m-%d %H:%M %Z")

    body = "".join(f"{k}={shell[k]}\n" for k in sorted(shell))
    for path in (SHELL_LIVE_PATH, SHELL_REPO_PATH):
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            f.write(body)
        os.replace(tmp, path)


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
        f"Tide predictions ({TIDE_STATION_NAME} NOAA station -- at Carolina Beach):"
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

    try:
        write_shell_snapshot()
    except Exception as e:
        print(f"shell snapshot write failed: {e}")

    print(f"ok ({stamp})")


if __name__ == "__main__":
    main()
