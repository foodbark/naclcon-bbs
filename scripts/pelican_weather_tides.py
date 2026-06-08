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

# NDBC nearshore buoys. 41110 reports wave height/period/direction + water
# temp; 41037 reports observed wind. Either station's sensors can drop in
# and out, so we read them independently and only emit fields that arrived.
NDBC_WAVE_STATION = "41110"
NDBC_WAVE_STATION_NAME = "Masonboro Inlet"
NDBC_WIND_STATION = "41037"
NDBC_WIND_STATION_NAME = "Wrightsville Beach Nearshore"

REPO_PATH = "/home/ubuntu/naclcon-bbs/ctrl/pelican_weather.txt"
LIVE_PATH = "/sbbs/ctrl/pelican_weather.txt"

# Compact key=value snapshot consumed by the lbshell weather/tide strip.
SHELL_REPO_PATH = "/home/ubuntu/naclcon-bbs/data/weather_tides.txt"
SHELL_LIVE_PATH = "/sbbs/data/weather_tides.txt"
SHELL_LOCATION = "Carolina Beach"
UV_ZIP = "28428"

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


def get_text(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def deg_to_compass(deg):
    if deg is None:
        return None
    pts = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return pts[int((deg / 22.5) + 0.5) % 16]


def parse_ndbc(text):
    """Parse NDBC realtime2 .txt. Returns rows newest-first; 'MM' becomes None."""
    headers = None
    rows = []
    for line in text.splitlines():
        if line.startswith("#YY"):
            headers = line.lstrip("#").split()
            continue
        if line.startswith("#") or not headers:
            continue
        cols = line.split()
        if len(cols) != len(headers):
            continue
        rows.append({h: (None if v == "MM" else v) for h, v in zip(headers, cols)})
    return rows


def ndbc_first_with(rows, fields):
    """Return the newest row where every named field is present (not MM)."""
    for r in rows:
        if all(r.get(f) is not None for f in fields):
            return r
    return None


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


def fetch_surf():
    """Wave height/period/direction + water temp from NDBC 41110; observed wind
    from NDBC 41037. Sensors drop in and out independently, so each line is
    emitted only when its source has a recent good reading."""
    out = []

    try:
        wave_rows = parse_ndbc(get_text(
            f"https://www.ndbc.noaa.gov/data/realtime2/{NDBC_WAVE_STATION}.txt"
        ))
    except Exception as e:
        wave_rows = []
        out.append(f"  (wave fetch failed: {e})")

    try:
        wind_rows = parse_ndbc(get_text(
            f"https://www.ndbc.noaa.gov/data/realtime2/{NDBC_WIND_STATION}.txt"
        ))
    except Exception as e:
        wind_rows = []
        out.append(f"  (wind fetch failed: {e})")

    wv = ndbc_first_with(wave_rows, ["WVHT", "DPD", "MWD"])
    if wv:
        height_ft = round(float(wv["WVHT"]) * 3.281, 1)
        period = wv["DPD"]
        dir_deg = int(float(wv["MWD"]))
        ts = f"{wv['YY']}-{wv['MM']}-{wv['DD']} {wv['hh']}:{wv['mm']} UTC"
        out.append(
            f"  Waves ({NDBC_WAVE_STATION_NAME} buoy {NDBC_WAVE_STATION}, {ts}): "
            f"{height_ft} ft @ {period}s from {deg_to_compass(dir_deg)} ({dir_deg}°)"
        )
    elif wave_rows:
        out.append(f"  (no recent wave data from buoy {NDBC_WAVE_STATION})")

    wt = ndbc_first_with(wave_rows, ["WTMP"])
    if wt:
        wtmp_c = float(wt["WTMP"])
        wtmp_f = round(wtmp_c * 9 / 5 + 32)
        out.append(f"  Water temp: {wtmp_f}°F ({wtmp_c:.1f}°C)")

    wd = ndbc_first_with(wind_rows, ["WDIR", "WSPD"])
    if wd:
        wspd_mph = round(float(wd["WSPD"]) * 2.237)
        wdir_deg = int(float(wd["WDIR"]))
        ts = f"{wd['YY']}-{wd['MM']}-{wd['DD']} {wd['hh']}:{wd['mm']} UTC"
        out.append(
            f"  Wind observed ({NDBC_WIND_STATION_NAME} buoy {NDBC_WIND_STATION}, {ts}): "
            f"{wspd_mph} mph from {deg_to_compass(wdir_deg)} ({wdir_deg}°)"
        )
    elif wind_rows:
        out.append(f"  (no recent wind data from buoy {NDBC_WIND_STATION})")

    return out or ["  (no surf data available)"]


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

    pipe = "\x01h\x01m\xb3"
    lbl = "\x01h\x01w"
    loc = "\x01h\x01y" + data.get("LOCATION", "Carolina Beach")
    temp_s = f"{t}\xf8F" if t is not None else "--"
    precip_s = f"{p}%" if p is not None else "--"
    uv_s = str(uv) if uv is not None else "--"
    hi = data.get("HIGH_TIDE", "--:--")
    lo = data.get("LOW_TIDE", "--:--")

    return (
        "  " + loc
        + "  " + pipe + "  " + temp_c + temp_s
        + "  " + pipe + "  " + lbl + "Precip " + precip_c + precip_s
        + "  " + pipe + "  " + lbl + "UV " + uv_c + uv_s
        + "  " + pipe + "  " + lbl + "High " + "\x01h\x01c" + hi
        + "  " + pipe + "  " + lbl + "Low " + "\x01h\x01w" + lo
        + "\x01n"
    )


def render_weather_strip_plain(data):
    """Plain-ASCII strip for the pre-auth banner (no Ctrl-A processing)."""
    loc = data.get("LOCATION", "Carolina Beach")
    t = data.get("TEMP_F")
    p = data.get("PRECIP_PCT")
    uv = data.get("UV_INDEX")
    hi = data.get("HIGH_TIDE", "--:--")
    lo = data.get("LOW_TIDE", "--:--")
    temp_s = f"{t}F" if t else "--"
    precip_s = f"{p}%" if p else "--"
    uv_s = uv if uv else "--"
    return f"  {loc}  |  {temp_s}  |  Precip {precip_s}  |  UV {uv_s}  |  High {hi}  |  Low {lo}"


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

    try:
        tides = fetch_tides()
        tides_ok = True
    except Exception as e:
        tides, tides_ok = [f"  (NOAA fetch failed: {e})"], False

    try:
        surf = fetch_surf()
        surf_ok = True
    except Exception as e:
        surf, surf_ok = [f"  (NDBC fetch failed: {e})"], False

    if not (wx_ok or tides_ok or surf_ok):
        # All failed -- don't clobber last known good file
        raise SystemExit("all fetches failed; keeping previous file")

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
    lines.append("Surf conditions (NDBC nearshore buoys):")
    lines.append("")
    lines.extend(surf)
    lines.append("")
    lines.append(
        "Carolina Beach faces roughly east-southeast: winds from the W are offshore"
    )
    lines.append(
        "(clean faces), winds from the E are onshore (blown-out, choppy). Anything"
    )
    lines.append(
        "from N or S is cross-shore. Period matters: 8s+ is groundswell with shape,"
    )
    lines.append(
        "5-7s is local windswell that's mushier."
    )
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

    try:
        write_logon_splash()
    except Exception as e:
        print(f"logon splash write failed: {e}")

    print(f"ok ({stamp})")


if __name__ == "__main__":
    main()
