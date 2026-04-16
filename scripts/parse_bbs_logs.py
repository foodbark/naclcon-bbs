#!/usr/bin/env python3
"""
Parse Synchronet .log files into Elasticsearch-ready JSON (ECS field names).
Each session block becomes one document.

Usage:
    python3 parse_bbs_logs.py [file ...] > out.ndjson
    python3 parse_bbs_logs.py           (defaults to /sbbs/data/logs/*.log)
"""

import re
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RE_START      = re.compile(r'^@\s+(\d{2}:\d{2})\s+\w+\s+(\w+\s+\d+\s+\d+)\s+Node\s+(\d+)')
RE_CONN       = re.compile(r'^@\+\s+(\S+)\s+(.*?)\s+\[(\d+\.\d+\.\d+\.\d+)\]')
RE_LOGON      = re.compile(r'^\+\+\s+\((\d+)\)\s+(.*?)\s+Logon\s+(\d+)\s+-\s+(\d+)')
RE_DOOR       = re.compile(r'^X-\s+Executing external user event:\s+(.+)')
RE_NEW_USER   = re.compile(r'^N\s+New user:\s+\S')
RE_END_FULL   = re.compile(
    r'^@-\s+(\d{2}:\d{2})\s+T:\s*(\d+)\s+R:\s*(\d+)\s+P:\s*(\d+)'
    r'\s+E:\s*(\d+)\s+F:\s*(\d+)\s+U:\s*(\d+)K\s+(\d+)\s+D:\s*(\d+)K\s+(\d+)'
)
RE_END_SEC    = re.compile(r'^@-\s+(\d{2}:\d{2})\s+T:\s*(\d+)\s+sec')
RE_END_ANY    = re.compile(r'^@-')
RE_CRASH      = re.compile(r'^L!\s+End of preexisting log entry')
RE_INACTIVITY = re.compile(r'Maximum user input inactivity exceeded')


def to_ts(date_str, time_str):
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%b %d %Y %H:%M")
        return dt.replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return None


def flush(session, out):
    if session is None:
        return
    s = session
    doc = {
        "@timestamp":        to_ts(s["date"], s["time"]),
        "source": {},
        "user":   {},
        "bbs": {
            "node":           s["node"],
            "protocol":       s["protocol"],
            "new_user":       s["new_user"],
            "inactivity_disconnect": s["inactivity"],
            "crashed":        s["crashed"],
            "events":         s["events"],
        },
    }

    if s["source_ip"]:
        doc["source"]["ip"] = s["source_ip"]
    if s["source_domain"] and s["source_domain"] != "<no name>":
        doc["source"]["domain"] = s["source_domain"]

    if s["user_name"]:
        doc["user"]["name"] = s["user_name"]
        doc["user"]["id"]   = s["user_id"]
        doc["bbs"]["logon_number"]   = s["logon_number"]
        doc["bbs"]["session_number"] = s["session_number"]

    if s["duration_minutes"] is not None:
        doc["bbs"]["duration_minutes"] = s["duration_minutes"]

    if s["stats"]:
        doc["bbs"]["stats"] = s["stats"]

    # drop empty dicts
    if not doc["source"]:
        del doc["source"]
    if not doc["user"]:
        del doc["user"]

    out.append(doc)


def parse_file(path):
    out = []
    cur = None

    with open(path, errors="replace") as f:
        for line in f:
            line = line.rstrip()

            m = RE_START.match(line)
            if m:
                flush(cur, out)
                cur = {
                    "time": m.group(1), "date": m.group(2), "node": int(m.group(3)),
                    "protocol": None, "source_ip": None, "source_domain": None,
                    "user_name": None, "user_id": None,
                    "logon_number": None, "session_number": None,
                    "new_user": False, "inactivity": False, "crashed": False,
                    "duration_minutes": None, "stats": {}, "events": [],
                }
                continue

            if cur is None:
                continue

            m = RE_CONN.match(line)
            if m:
                cur["protocol"]      = m.group(1)
                cur["source_domain"] = m.group(2).strip()
                cur["source_ip"]     = m.group(3)
                continue

            m = RE_LOGON.match(line)
            if m:
                cur["user_id"]        = m.group(1)
                cur["user_name"]      = m.group(2).strip()
                cur["logon_number"]   = int(m.group(3))
                cur["session_number"] = int(m.group(4))
                continue

            m = RE_DOOR.match(line)
            if m:
                cur["events"].append(m.group(1).strip())
                continue

            if RE_NEW_USER.match(line):
                cur["new_user"] = True
                continue

            if RE_INACTIVITY.search(line):
                cur["inactivity"] = True
                continue

            m = RE_END_FULL.match(line)
            if m:
                cur["duration_minutes"] = int(m.group(2))
                cur["stats"] = {
                    "messages_read":  int(m.group(3)),
                    "posts":          int(m.group(4)),
                    "email":          int(m.group(5)),
                    "files":          int(m.group(6)),
                    "uploaded_kb":    int(m.group(7)),
                    "uploads":        int(m.group(8)),
                    "downloaded_kb":  int(m.group(9)),
                    "downloads":      int(m.group(10)),
                }
                flush(cur, out)
                cur = None
                continue

            m = RE_END_SEC.match(line)
            if m:
                cur["duration_minutes"] = round(int(m.group(2)) / 60, 2)
                flush(cur, out)
                cur = None
                continue

            if RE_END_ANY.match(line):
                flush(cur, out)
                cur = None
                continue

            if RE_CRASH.match(line):
                if cur:
                    cur["crashed"] = True
                    flush(cur, out)
                    cur = None
                continue

    if cur:
        cur["crashed"] = True
        flush(cur, out)

    return out


if __name__ == "__main__":
    paths = [Path(p) for p in sys.argv[1:]] if sys.argv[1:] \
        else sorted(Path("/sbbs/data/logs").glob("*.log"))

    for path in paths:
        for doc in parse_file(str(path)):
            print(json.dumps(doc))
