"""The app's database (SQLite, a single file called caretogether.db).

It keeps what people add while using the app, for everyone who opens it on this computer:
observations, the access log, new care plan versions, RN approvals and rejections, and alert updates.

The sample files in the data folder are never changed. To start the demo again, use
"Reset demo data" on the Data and sources page (or close the app and delete caretogether.db).
"""
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta

import pandas as pd

from . import config as C

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY, resident_id TEXT, date TEXT, type TEXT, role TEXT, temp TEXT, note TEXT,
    added_by TEXT, added_at TEXT);
CREATE TABLE IF NOT EXISTS access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, t TEXT, user_name TEXT, role TEXT, rid TEXT, area TEXT,
    action TEXT, reason TEXT, comment TEXT, alert TEXT);
CREATE TABLE IF NOT EXISTS careplan_versions (
    rid TEXT, v INTEGER, data TEXT, PRIMARY KEY (rid, v));
CREATE TABLE IF NOT EXISTS careplan_decisions (
    rid TEXT, v INTEGER, status TEXT, decided_by TEXT, role TEXT, date TEXT, comment TEXT, PRIMARY KEY (rid, v));
CREATE TABLE IF NOT EXISTS alert_updates (
    alert_id TEXT PRIMARY KEY, status TEXT, found TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


def _connect():
    con = sqlite3.connect(C.DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    """Create the tables, and copy in the sample observations the first time."""
    with closing(_connect()) as con, con:
        con.executescript(SCHEMA)
        if con.execute("SELECT 1 FROM meta WHERE key='seeded'").fetchone():
            return
        sample = pd.read_csv(C.OBSERVATIONS_SAMPLE, dtype=str, keep_default_na=False)
        for o in sample.to_dict("records"):
            con.execute("INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?)",
                        (o["id"], o["resident_id"], o["date"], o["type"], o["role"], o["temp"], o["note"], "Sample data", ""))
        con.execute("INSERT INTO meta VALUES ('seeded', ?)", (datetime.now().isoformat(timespec="seconds"),))


def reset_demo():
    """Remove everything people added and start again from the sample data."""
    with closing(_connect()) as con, con:
        for table in ["observations", "access_log", "careplan_versions", "careplan_decisions", "alert_updates", "meta"]:
            con.execute(f"DROP TABLE IF EXISTS {table}")
    init_db()


def now_iso():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# ---------- observations ----------
def get_observations():
    with closing(_connect()) as con:
        rows = [dict(r) for r in con.execute("SELECT * FROM observations")]
    cols = ["id", "resident_id", "date", "type", "role", "temp", "note", "added_by", "added_at"]
    return pd.DataFrame(rows, columns=cols)


def add_observation(resident_id, date, obs_type, role, temp, note, added_by):
    oid = "u" + datetime.now().strftime("%Y%m%d%H%M%S%f")
    with closing(_connect()) as con, con:
        con.execute("INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?)",
                    (oid, resident_id, date, obs_type, role, temp, note, added_by, now_iso()))
    return oid


# ---------- access log ----------
def log_access(user, role, area, action, rid="", alert="", reason="", comment="", dedupe=True):
    """Add an entry. With dedupe, the same person seeing the same thing within 5 minutes is logged once."""
    t = now_iso()
    with closing(_connect()) as con, con:
        if dedupe:
            since = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S")
            same = con.execute("SELECT 1 FROM access_log WHERE user_name=? AND area=? AND rid=? AND alert=? AND action=? AND t>=?",
                               (user, area, rid, alert, action, since)).fetchone()
            if same:
                return
        con.execute("INSERT INTO access_log (t,user_name,role,rid,area,action,reason,comment,alert) VALUES (?,?,?,?,?,?,?,?,?)",
                    (t, user, role, rid, area, action, reason, comment, alert))


def all_access():
    """The sample log entries plus everything logged in the app, newest first."""
    with closing(_connect()) as con:
        live = [dict(r) for r in con.execute("SELECT t,user_name AS user,role,rid,area,action,reason,comment,alert FROM access_log")]
    return sorted(C.ACCESS_SEED + live, key=lambda x: x["t"], reverse=True)


# ---------- care plans ----------
def live_careplan_versions():
    """New care plan versions saved in the app: {resident_id: [version, ...]}."""
    out = {}
    with closing(_connect()) as con:
        for r in con.execute("SELECT rid, data FROM careplan_versions ORDER BY rid, v"):
            out.setdefault(r["rid"], []).append(json.loads(r["data"]))
    return out


def add_careplan_version(rid, version):
    with closing(_connect()) as con, con:
        con.execute("INSERT INTO careplan_versions VALUES (?,?,?)", (rid, version["v"], json.dumps(version)))


def careplan_decisions():
    """RN approvals and rejections: {'R008:5': {...}}."""
    with closing(_connect()) as con:
        return {f"{r['rid']}:{r['v']}": {"status": r["status"], "by": r["decided_by"], "role": r["role"],
                                         "date": r["date"], "comment": r["comment"]}
                for r in con.execute("SELECT * FROM careplan_decisions")}


def set_careplan_decision(rid, v, status, by, role, date, comment):
    with closing(_connect()) as con, con:
        con.execute("INSERT OR REPLACE INTO careplan_decisions VALUES (?,?,?,?,?,?,?)", (rid, v, status, by, role, date, comment))


# ---------- emergency alerts ----------
def alert_updates():
    with closing(_connect()) as con:
        return {r["alert_id"]: dict(r) for r in con.execute("SELECT * FROM alert_updates")}


def mark_alert_found(alert_id, found_iso, note):
    with closing(_connect()) as con, con:
        con.execute("INSERT OR REPLACE INTO alert_updates VALUES (?,?,?,?)", (alert_id, "Resolved", found_iso, note))
