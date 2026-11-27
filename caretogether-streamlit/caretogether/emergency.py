"""Helpers for Emergency Location Tracking: alerts with saved updates, distances, times and consent.

The demo uses a fixed clock (EMG_NOW = Fri 13 Nov 2026, 21:05) so "30 min ago" always makes sense.
"""
import math
import re
from datetime import datetime

from . import config as C
from . import store


def alerts_with_updates():
    """The sample alerts, with any 'Mark as found' updates saved in the app."""
    upd = store.alert_updates()
    out = []
    for a in C.EMG_ALERTS:
        a = dict(a)
        u = upd.get(a["id"])
        if u:
            a["status"], a["found"] = u["status"], u["found"]
            a["log"] = list(a.get("log") or []) + [[u["found"][11:16], "Marked as found"]]
            a["outcome"] = ((a.get("outcome") or "") + " " + u["note"]).strip()
        out.append(a)
    return out


def minutes(iso):
    return datetime.fromisoformat(iso).timestamp() / 60


def dur(m):
    """A length of time in words: 25 min, 1 h 5 min, 2 days."""
    if m < 60:
        return f"{round(m)} min"
    if m < 1440:
        return f"{int(m // 60)} h {round(m % 60)} min"
    return f"{round(m / 1440)} days"


def ago(iso):
    m = round(minutes(C.EMG_NOW) - minutes(iso))
    return "just now" if m < 1 else f"{dur(m)} ago"


def fmt_when(iso):
    """'Fri, 13 Nov, 20:35' (written this way so it also works on Windows)."""
    d = datetime.fromisoformat(iso)
    return f"{d:%a}, {d.day} {d:%b}, {d:%H:%M}"


def point_iso(a, t):
    """Turn a trail time such as '21:02' or '08/11 18:20' into a full date and time."""
    m = re.match(r"^(\d\d)/(\d\d) (\d\d:\d\d)$", t)
    if m:
        return f"{a['start'][:4]}-{m.group(2)}-{m.group(1)}T{m.group(3)}"
    return a["start"][:11] + t


def last_point(trail):
    return trail[-1] if trail else None


def km_between(a, b):
    """Straight-line distance in km between two [lat, lon] points."""
    R, rad = 6371, math.radians
    d_lat, d_lon = rad(b[0] - a[0]), rad(b[1] - a[1])
    h = math.sin(d_lat / 2) ** 2 + math.cos(rad(a[0])) * math.cos(rad(b[0])) * math.sin(d_lon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def consent(rid):
    return C.EMG_CONSENT.get(rid) or {"status": "Pending", "by": "No consent recorded", "date": "–", "when": "Not shared",
                                      "zone": "–", "device": "–", "battery": None}


def share_text(a):
    c = C.EMG_CONSENT.get(a["rid"]) or {}
    return "" if c.get("status") == "Agreed" else f"Location not shared (consent {str(c.get('status') or 'not recorded').lower()})"


def location_shared(a):
    return bool(a and a.get("home") and (C.EMG_CONSENT.get(a["rid"]) or {}).get("status") == "Agreed")


def alert_name(a, resident_name):
    return f"{resident_name(a['rid'])} & {a['companion']}" if a.get("companion") else resident_name(a["rid"])


def first_name(n):
    return str(n).split(" ")[0]


def initials(n):
    return "".join(w[0] for w in str(n).split()[:2]).upper()


def median(values):
    v = sorted(values)
    if not v:
        return None
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2
