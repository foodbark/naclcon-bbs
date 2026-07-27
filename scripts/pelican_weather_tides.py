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
import time
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

# USGS gauge 12340500, "Clark Fork above Missoula MT": the in-town gauge, and the
# one that reflects the water at Brennan's Wave. 12353000 ("below Missoula") is
# downstream of the Bitterroot confluence and reads substantially higher.
RIVER_SITE = "12340500"
RIVER_NAME = "Clark Fork above Missoula"

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


def get_json(url, timeout=15, attempts=3):
    """GET + parse JSON, retrying transient truncations.

    USGS in particular will occasionally hand back a short body and raise
    IncompleteRead; a retry a second later almost always succeeds."""
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            if i < attempts - 1:
                time.sleep(1.5)
    raise last


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


def aqi_category(aqi):
    """EPA AQI category name for an index value."""
    if aqi is None:
        return None
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def fetch_air_quality():
    """Return (us_aqi, pm2_5) from Open-Meteo's air quality API. No key required.

    This replaced the EPA UV index on the strip: in a mountain valley that spends
    August and September under wildfire smoke, particulate is the number people
    actually want, and UV was never the local story."""
    d = get_json(
        "https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={LAT}&longitude={LON}&current=us_aqi,pm2_5"
        "&timezone=America%2FDenver"
    )
    cur = d.get("current") or {}
    aqi = cur.get("us_aqi")
    pm = cur.get("pm2_5")
    return (int(aqi) if aqi is not None else None,
            float(pm) if pm is not None else None)


def fetch_river():
    """Return {cfs, stage_ft, water_f} for the Clark Fork from the USGS gauge.

    RIVER_SITE is 'Clark Fork above Missoula' (12340500), the in-town gauge, the
    one that reflects the water at Brennan's Wave. The 'below Missoula' gauge
    (12353000) sits downstream of the Bitterroot confluence and reads much higher,
    so don't swap them casually. Any individual parameter can be absent, so each
    is read independently and missing ones are simply left out."""
    d = get_json(
        "https://waterservices.usgs.gov/nwis/iv/?format=json"
        f"&sites={RIVER_SITE}&parameterCd=00060,00065,00010&siteStatus=all"
    )
    out = {}
    for ts in d.get("value", {}).get("timeSeries", []):
        code = ts["variable"]["variableCode"][0]["value"]
        vals = ts["values"][0]["value"] if ts.get("values") else []
        if not vals:
            continue
        raw = vals[-1].get("value")
        if raw in (None, "", "-999999"):
            continue
        try:
            v = float(raw)
        except ValueError:
            continue
        if code == "00060":
            out["cfs"] = int(round(v))
        elif code == "00065":
            out["stage_ft"] = round(v, 2)
        elif code == "00010":
            out["water_f"] = round(v * 9 / 5 + 32)
    return out


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


def write_shell_snapshot(aqi=None, pm=None, river=None):
    """Per-field merge with the existing file so a transient API failure for one
    source doesn't blank out the others on the strip.

    Air quality and river readings are passed in rather than re-fetched: main()
    already pulled them for the prose block, and fetching twice per run both
    doubled the request count and doubled the chance of a transient failure
    leaving the strip without a value it had just successfully retrieved."""
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

    if aqi is not None:
        shell["AQI"] = str(aqi)
    if pm is not None:
        shell["PM25"] = f"{pm:.1f}"

    river = river or {}
    if "cfs" in river:
        shell["RIVER_CFS"] = str(river["cfs"])
    if "stage_ft" in river:
        shell["RIVER_FT"] = str(river["stage_ft"])
    if "water_f" in river:
        shell["RIVER_TEMP_F"] = str(river["water_f"])

    # Retired fields. Drop them so stale values can't linger in the snapshot
    # forever now that nothing writes them: tides went with the move off the
    # coast, UV was displaced by air quality.
    for dead in ("HIGH_TIDE", "LOW_TIDE", "UV_INDEX"):
        shell.pop(dead, None)

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


def aqi_colour(aqi, bg=""):
    """Ctrl-A colour for an AQI value, following the six AirNow categories
    (airnow.gov/aqi/aqi-basics): green, yellow, orange, red, purple, maroon.

    The 16-colour BBS palette has no orange and no maroon, so brown (low
    intensity yellow) and dark red (low intensity red) stand in for them, which
    is the usual ANSI substitution. Those two are the only ones that need
    \\x01n to clear the high-intensity bit, and \\x01n also clears the
    background, hence `bg`: callers drawing onto a coloured background pass the
    background code to re-establish it. The lbshell status row does; the logon
    splash, drawn on normal background, passes nothing."""
    if aqi is None:
        return "\x01h\x01w"
    if aqi <= 50:                       # Good
        return "\x01h\x01g"
    if aqi <= 100:                      # Moderate
        return "\x01h\x01y"
    if aqi <= 150:                      # Unhealthy for Sensitive Groups
        return "\x01n" + bg + "\x01y"
    if aqi <= 200:                      # Unhealthy
        return "\x01h\x01r"
    if aqi <= 300:                      # Very Unhealthy
        return "\x01h\x01m"
    return "\x01n" + bg + "\x01r"       # Hazardous


def _wind_str(data, unit=True):
    w = _ival(data.get("WIND_MPH"))
    if w is None:
        return "--"
    return f"{w}mph {data['WIND_DIR']}" if data.get("WIND_DIR") else f"{w}mph"


def render_weather_strip_color(data):
    """Ctrl-A coloured strip — mirrors nc_weather_strip() in mods/lbshell.js.

    Six fields at 79 columns is tight, so the separators are a single space
    either side of the bar rather than two. Worst realistic case (freezing,
    high precip, gusty with a direction, spring runoff at five digits) lands
    around 78 visible characters."""
    t = _ival(data.get("TEMP_F"))
    p = _ival(data.get("PRECIP_PCT"))
    aqi = _ival(data.get("AQI"))
    w = _ival(data.get("WIND_MPH"))
    cfs = _ival(data.get("RIVER_CFS"))

    temp_c = ("\x01h\x01w" if t is None
              else "\x01h\x01c" if t < 50
              else "\x01h\x01w" if t < 65
              else "\x01h\x01y" if t < 80
              else "\x01h\x01r")
    precip_c = ("\x01h\x01w" if p is None
                else "\x01h\x01w" if p < 20
                else "\x01h\x01c" if p < 50
                else "\x01h\x01m")
    aqi_c = aqi_colour(aqi, bg="")
    wind_c = ("\x01h\x01w" if w is None
              else "\x01h\x01w" if w < 8
              else "\x01h\x01c" if w < 20
              else "\x01h\x01m")
    # Rough local bands for the Clark Fork above Missoula: summer low, normal,
    # and runoff. Approximate on purpose; it's a colour hint, not a gauge.
    river_c = ("\x01h\x01w" if cfs is None
               else "\x01h\x01w" if cfs < 1000
               else "\x01h\x01c" if cfs < 5000
               else "\x01h\x01m")

    pipe = "\x01h\x01m\xb3"
    lbl = "\x01h\x01w"
    loc = "\x01h\x01y" + data.get("LOCATION", "Missoula")
    temp_s = f"{t}\xf8F" if t is not None else "--"
    precip_s = f"{p}%" if p is not None else "--"
    aqi_s = str(aqi) if aqi is not None else "--"
    river_s = f"{cfs}cfs" if cfs is not None else "--"

    sep = " " + pipe + " "
    return (
        "  " + loc
        + sep + temp_c + temp_s
        + sep + lbl + "Precip " + precip_c + precip_s
        + sep + lbl + "AQI " + aqi_c + aqi_s
        + sep + wind_c + _wind_str(data)
        + sep + lbl + "Clark Fork " + river_c + river_s
        + "\x01n"
    )


def render_weather_strip_plain(data):
    """Plain-ASCII strip for the pre-auth banner (no Ctrl-A processing)."""
    loc = data.get("LOCATION", "Missoula")
    t = data.get("TEMP_F")
    p = data.get("PRECIP_PCT")
    aqi = data.get("AQI")
    cfs = data.get("RIVER_CFS")
    temp_s = f"{t}F" if t else "--"
    precip_s = f"{p}%" if p else "--"
    aqi_s = aqi if aqi else "--"
    river_s = f"{cfs}cfs" if cfs else "--"
    return (f"  {loc} | {temp_s} | Precip {precip_s} | AQI {aqi_s}"
            f" | {_wind_str(data)} | Clark Fork {river_s}")


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

    aqi, pm = None, None
    try:
        aqi, pm = fetch_air_quality()
    except Exception as e:
        print(f"air-quality fetch failed: {e}")
    if aqi is not None:
        lines.append("Air quality (Open-Meteo, US AQI):")
        lines.append("")
        detail = f"  AQI {aqi} ({aqi_category(aqi)})"
        if pm is not None:
            detail += f", PM2.5 {pm:.1f} ug/m3"
        lines.append(detail)
        if aqi > 100:
            lines.append(
                "  That is smoke you can feel. Worth mentioning if somebody asks about"
            )
            lines.append(
                "  going outside, and worth grumbling about: it is your air too."
            )
        lines.append("")

    river = {}
    try:
        river = fetch_river()
    except Exception as e:
        print(f"river fetch failed: {e}")
    if river:
        lines.append(f"The Clark Fork ({RIVER_NAME}, USGS {RIVER_SITE}):")
        lines.append("")
        if "cfs" in river:
            lines.append(f"  Flow: {river['cfs']} cfs")
        if "stage_ft" in river:
            lines.append(f"  Stage: {river['stage_ft']} ft")
        if "water_f" in river:
            lines.append(f"  Water temp: {river['water_f']} F")
        lines.append("")
        lines.append(
            "  Rough reading: under about 1,000 cfs is low summer water, a few thousand"
        )
        lines.append(
            "  is normal, and anything above roughly 5,000 is spring runoff pushing"
        )
        lines.append(
            "  hard. High and cold means the tubers stay home and the surfers at"
        )
        lines.append(
            "  Brennan's Wave are having the time of their lives."
        )
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
        "In August and September, check the AQI above before assuming haze is cloud;"
    )
    lines.append(
        "wildfire smoke is the local weather story that time of year. In winter, an"
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
        write_shell_snapshot(aqi=aqi, pm=pm, river=river)
    except Exception as e:
        print(f"shell snapshot write failed: {e}")

    try:
        write_logon_splash()
    except Exception as e:
        print(f"logon splash write failed: {e}")

    print(f"ok ({stamp})")


if __name__ == "__main__":
    main()
