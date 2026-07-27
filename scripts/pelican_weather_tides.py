#!/usr/bin/env python3
"""
Fetch the current NWS weather forecast for Missoula, MT and write a
plain-text block to ctrl/pelican_weather.txt. The Pelican's system prompt
loads this file alongside pelican_news.txt so she can reference live
conditions in chat.

Run from cron every 30 minutes. On fetch failure for a given source,
keeps the last successful block for that source (no torn writes).

The filename still says "tides" for cron-stability reasons, but there are
no tides in Montana. The board moved from Carolina Beach to Missoula in
July 2026, which retired the NOAA tide station and the two NDBC nearshore
buoys; wind now comes from the NWS hourly forecast instead of a buoy, and
it took over the two strip slots the high/low tide times used to hold.
"""

import datetime
import json
import os
import urllib.request
from zoneinfo import ZoneInfo

MOUNTAIN = ZoneInfo("America/Denver")
UTC = datetime.timezone.utc


def now_utc():
    return datetime.datetime.now(UTC)


def now_local():
    return datetime.datetime.now(MOUNTAIN)

LAT, LON = 46.8721, -113.9940              # Missoula, MT

REPO_PATH = "/home/ubuntu/naclcon-bbs/ctrl/pelican_weather.txt"
LIVE_PATH = "/sbbs/ctrl/pelican_weather.txt"

# Compact key=value snapshot consumed by the lbshell weather/tide strip.
SHELL_REPO_PATH = "/home/ubuntu/naclcon-bbs/data/weather_tides.txt"
SHELL_LIVE_PATH = "/sbbs/data/weather_tides.txt"
SHELL_LOCATION = "Missoula"
UV_ZIP = "59801"

# Logon splash files we rewrite with the weather strip appended after the
# trailing ===... separator. (path, colored?). The plain-ASCII pair is the
# pre-auth banner; the colored pair is rendered by bbs.menu("logon") post-auth.
LOGON_SPLASH_FILES = [
    ("/sbbs/text/logon.asc", False),
    ("/home/ubuntu/naclcon-bbs/text/logon.asc", False),
    ("/sbbs/text/menu/logon.asc", True),
    ("/home/ubuntu/naclcon-bbs/text/menu/logon.asc", True),
]

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


def fetch_current_conditions():
    """Return (temp_f, precip_pct, wind_mph, wind_dir) for the current hour from the
    NWS hourly forecast. Wind replaces the tide readings the strip used to carry;
    it comes free with this call, so it costs no extra request. wind_mph/wind_dir
    are None when the feed omits or malforms them."""
    point = get_json(f"https://api.weather.gov/points/{LAT},{LON}")
    fc = get_json(point["properties"]["forecastHourly"])
    p = fc["properties"]["periods"][0]
    temp = int(p["temperature"])
    precip_obj = p.get("probabilityOfPrecipitation") or {}
    precip = precip_obj.get("value")
    precip = int(precip) if precip is not None else 0

    # windSpeed arrives as e.g. "10 mph" or "5 to 10 mph"; take the leading number.
    wind_mph = None
    raw = (p.get("windSpeed") or "").strip()
    for tok in raw.split():
        if tok.isdigit():
            wind_mph = int(tok)
            break
    wind_dir = (p.get("windDirection") or "").strip() or None

    return temp, precip, wind_mph, wind_dir


def fetch_uv():
    """Return current-hour UV index (int) for UV_ZIP. 0 when there's no matching hour
    (the EPA feed usually omits overnight rows, which is fine — UV is 0 then anyway)."""
    data = get_json(
        f"https://data.epa.gov/efservice/getEnvirofactsUVHOURLY/ZIP/{UV_ZIP}/JSON"
    )
    target = now_local().strftime("%b/%d/%Y %I %p")
    for r in data:
        if r.get("DATE_TIME") == target:
            return int(r.get("UV_VALUE", 0))
    return 0


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
        temp, precip, wind_mph, wind_dir = fetch_current_conditions()
        shell["TEMP_F"] = str(temp)
        shell["PRECIP_PCT"] = str(precip)
        if wind_mph is not None:
            shell["WIND_MPH"] = str(wind_mph)
        if wind_dir:
            shell["WIND_DIR"] = wind_dir
    except Exception as e:
        print(f"current-conditions fetch failed: {e}")

    try:
        shell["UV_INDEX"] = str(fetch_uv())
    except Exception as e:
        print(f"UV fetch failed: {e}")

    # Carolina Beach leftovers. Drop them so a stale high/low tide can't linger
    # in the snapshot forever now that nothing writes them.
    shell.pop("HIGH_TIDE", None)
    shell.pop("LOW_TIDE", None)

    shell["UPDATED"] = now_local().strftime("%Y-%m-%d %H:%M %Z")

    body = "".join(f"{k}={shell[k]}\n" for k in sorted(shell))
    for path in (SHELL_LIVE_PATH, SHELL_REPO_PATH):
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            f.write(body)
        os.replace(tmp, path)


def _ival(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def render_weather_strip_color(data):
    """Ctrl-A coloured strip — mirrors nc_weather_strip() in mods/lbshell.js."""
    t = _ival(data.get("TEMP_F"))
    p = _ival(data.get("PRECIP_PCT"))
    uv = _ival(data.get("UV_INDEX"))

    temp_c = ("\x01h\x01w" if t is None
              else "\x01h\x01c" if t < 50
              else "\x01h\x01w" if t < 65
              else "\x01h\x01y" if t < 80
              else "\x01h\x01r")
    precip_c = ("\x01h\x01w" if p is None
                else "\x01h\x01w" if p < 20
                else "\x01h\x01c" if p < 50
                else "\x01h\x01m")
    uv_c = ("\x01h\x01w" if uv is None
            else "\x01h\x01g" if uv <= 2
            else "\x01h\x01y" if uv <= 5
            else "\x01h\x01r" if uv <= 7
            else "\x01h\x01m")
    w = _ival(data.get("WIND_MPH"))
    wind_c = ("\x01h\x01w" if w is None
              else "\x01h\x01w" if w < 8
              else "\x01h\x01c" if w < 20
              else "\x01h\x01m")

    pipe = "\x01h\x01m\xb3"
    lbl = "\x01h\x01w"
    loc = "\x01h\x01y" + data.get("LOCATION", "Missoula")
    temp_s = f"{t}\xf8F" if t is not None else "--"
    precip_s = f"{p}%" if p is not None else "--"
    uv_s = str(uv) if uv is not None else "--"
    wind_s = "--" if w is None else (
        f"{w} mph {data['WIND_DIR']}" if data.get("WIND_DIR") else f"{w} mph")

    return (
        "  " + loc
        + "  " + pipe + "  " + temp_c + temp_s
        + "  " + pipe + "  " + lbl + "Precip " + precip_c + precip_s
        + "  " + pipe + "  " + lbl + "UV " + uv_c + uv_s
        + "  " + pipe + "  " + lbl + "Wind " + wind_c + wind_s
        + "\x01n"
    )


def render_weather_strip_plain(data):
    """Plain-ASCII strip for the pre-auth banner (no Ctrl-A processing)."""
    loc = data.get("LOCATION", "Missoula")
    t = data.get("TEMP_F")
    p = data.get("PRECIP_PCT")
    uv = data.get("UV_INDEX")
    w = data.get("WIND_MPH")
    wd = data.get("WIND_DIR")
    temp_s = f"{t}F" if t else "--"
    precip_s = f"{p}%" if p else "--"
    uv_s = uv if uv else "--"
    wind_s = "--" if not w else (f"{w} mph {wd}" if wd else f"{w} mph")
    return f"  {loc}  |  {temp_s}  |  Precip {precip_s}  |  UV {uv_s}  |  Wind {wind_s}"


def _strip_ctrla(line):
    """Drop \\x01-prefixed Ctrl-A code pairs so we can inspect the visible chars."""
    out = []
    i = 0
    while i < len(line):
        if line[i] == "\x01" and i + 1 < len(line):
            i += 2
            continue
        out.append(line[i])
        i += 1
    return "".join(out)


def write_logon_splash():
    """Rewrite text/logon.asc + text/menu/logon.asc, replacing anything below the
    trailing ===... line with a fresh weather strip. Idempotent: each run truncates
    at the separator and re-emits, so running this 48x/day doesn't grow the file."""
    data = read_kv(SHELL_LIVE_PATH)
    if not data:
        return
    color_strip = render_weather_strip_color(data)
    plain_strip = render_weather_strip_plain(data)

    for path, color in LOGON_SPLASH_FILES:
        # latin-1 round-trips raw bytes 1:1, so CP437 high-bit chars (\xb3 pipe,
        # \xf8 degree, etc.) survive read+write without UnicodeDecodeError.
        try:
            with open(path, encoding="latin-1") as f:
                content = f.read()
        except FileNotFoundError:
            continue
        lines = content.splitlines()
        last_sep = None
        for i, line in enumerate(lines):
            visible = _strip_ctrla(line).strip()
            if visible and set(visible) == {"="}:
                last_sep = i
        if last_sep is None:
            continue
        new_lines = lines[: last_sep + 1]
        new_lines.append("")
        new_lines.append(color_strip if color else plain_strip)
        new_lines.append("")
        body = "\n".join(new_lines) + "\n"
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="latin-1") as f:
            f.write(body)
        os.replace(tmp, path)


def main():
    try:
        wx = fetch_weather()
        wx_ok = True
    except Exception as e:
        wx, wx_ok = [f"  (NWS fetch failed: {e})"], False

    if not wx_ok:
        # Nothing came back; don't clobber the last known good file.
        raise SystemExit("NWS fetch failed; keeping previous file")

    stamp = now_local().strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        f"LIVE LOCAL CONDITIONS (Missoula, MT) -- refreshed {stamp}:",
        "",
        "Weather forecast (NWS):",
        "",
    ]
    lines.extend(wx)
    lines.append("")
    lines.append(
        "There are no tides here and there is no surf report, because Missoula is a"
    )
    lines.append(
        "mountain valley about 700 miles from salt water. If somebody asks you about"
    )
    lines.append(
        "the tide, that is a joke you are allowed to enjoy."
    )
    lines.append("")
    lines.append(
        "Reading the valley: Missoula sits where five valleys meet, so the wind is"
    )
    lines.append(
        "channeled rather than steady, and Hellgate Canyon funnels it in from the east."
    )
    lines.append(
        "In August and September, check whether the air is smoke rather than cloud;"
    )
    lines.append(
        "wildfire haze is the local weather story that time of year. In winter, an"
    )
    lines.append(
        "inversion can park cold murk in the valley for days while the peaks stay clear"
    )
    lines.append(
        "and sunny above it. Summer days run hot and dry and the nights cool off hard."
    )
    lines.append("")
    lines.append(
        "You can weave these in when the conversation naturally touches weather, the"
    )
    lines.append(
        "river, the mountains, going outside, or what the day feels like. Don't recite"
    )
    lines.append(
        "them unprompted. Prefer these live facts over vague guesses about Montana."
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

    try:
        write_logon_splash()
    except Exception as e:
        print(f"logon splash write failed: {e}")

    print(f"ok ({stamp})")


if __name__ == "__main__":
    main()
