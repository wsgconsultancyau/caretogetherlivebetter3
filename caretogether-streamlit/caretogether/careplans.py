"""Care plans: every version, what changed and how, RN approval, and reasons to review.

Version 1 lists every item. Later versions list only the changes:
    add    = new items
    change = [[item id, {field: new value}], ...]
    remove = [item ids]
A change saved by a registered nurse is approved straight away. A change saved by anyone else is a
draft: the current plan stays the same until an RN approves it, or rejects it with a reason.
"""
import re
from datetime import date, datetime, timedelta
from datetime import time as dtime

from . import config as C
from . import store
from .access import is_rn


# ---------- dates (care plans use dd/mm/yyyy) ----------
def dmy(s):
    d, m, y = (int(x) for x in str(s).split("/"))
    return date(y, m, d)


def fmt_dmy(d):
    return d.strftime("%d/%m/%Y")


def add_months(d, n):
    """Add months like a calendar does; 31 Jan + 1 month rolls on into early March, as in the dashboard."""
    years, month0 = divmod(d.month - 1 + n, 12)
    return date(d.year + years, month0 + 1, 1) + timedelta(days=d.day - 1)


def iso_to_dmy(s):
    s = str(s)
    return "/".join(reversed(s.split("-"))) if re.match(r"^\d{4}-\d{2}-\d{2}$", s) else s


def agreed_text(a):
    """Who agreed to a version. Older versions store a sentence; new ones store name, relationship, how and date."""
    if not a:
        return "not recorded"
    if isinstance(a, str):
        return a
    return f"{a['name']} ({a['rel']}) · {str(a['how']).lower()} · {iso_to_dmy(a['date'])}"


# ---------- loading ----------
def load_db():
    """New versions and RN decisions saved in the app (read once per page load)."""
    return {"live": store.live_careplan_versions(), "dec": store.careplan_decisions()}


def plan(rid, db):
    base = C.CARE_PLANS.get(rid)
    live = db["live"].get(rid, [])
    if not base and not live:
        return None
    return {"owner": base["owner"] if base else "Not set yet", "every": base["every"] if base else 6,
            "versions": (base["versions"] if base else []) + live}


def state(rid, v, db):
    """Approved, Draft or Rejected, and who decided."""
    d = db["dec"].get(f"{rid}:{v['v']}")
    if d:
        return d
    if v.get("status") == "Draft":
        return {"status": "Draft"}
    if v.get("approval"):
        return {"status": "Approved", **v["approval"]}
    if is_rn(v["role"]):
        return {"status": "Approved", "by": v["by"], "role": v["role"], "date": v["date"], "self": True}
    return {"status": "Approved", "by": "RN Sarah Mitchell", "role": "Registered Nurse", "date": v["date"]}


def snapshots(rid, db):
    """Rebuild every version. Only approved versions move the current plan forward."""
    P = plan(rid, db)
    if not P:
        return []
    current_items, out = [], []
    for v in P["versions"]:
        st, prev = state(rid, v, db), current_items
        if "items" in v:
            items = [dict(x) for x in v["items"]]
        else:
            removed = set(v.get("remove", []))
            changes = {cid: fields for cid, fields in v.get("change", [])}
            items = [{**x, **changes.get(x["id"], {})} for x in prev if x["id"] not in removed]
            items += [dict(x) for x in v.get("add", [])]
        if st["status"] == "Approved":
            current_items = items
        out.append({"ver": v, "st": st, "prev": prev, "items": items})
    return out


def current(S):
    """The newest approved version (the plan staff follow)."""
    return next((s for s in reversed(S) if s["st"]["status"] == "Approved"), None)


def draft(S):
    """A draft waiting for RN approval, if there is one."""
    cur, last = current(S), (S[-1] if S else None)
    return last if last and last["st"]["status"] == "Draft" and last is not cur else None


def diff(s):
    """What changed in one version, field by field."""
    v = s["ver"]
    if "items" in v:
        return [{"kind": "first", "n": len(v["items"])}]
    out = [{"kind": "add", "item": x} for x in v.get("add", [])]
    for cid, fields in v.get("change", []):
        old = next((x for x in s["prev"] if x["id"] == cid), None)
        if not old:
            continue
        for k, val in fields.items():
            if val != old.get(k):
                out.append({"kind": "change", "item": {**old, **fields}, "field": k, "from": old.get(k, ""), "to": val})
    for cid in v.get("remove", []):
        old = next((x for x in s["prev"] if x["id"] == cid), None)
        if old:
            out.append({"kind": "remove", "item": old})
    return out


def summary(s):
    D = diff(s)
    if D and D[0]["kind"] == "first":
        n = D[0]["n"]
        return f"First plan, {n} item{'' if n == 1 else 's'}"
    parts = [f"{sum(d['kind'] == k for d in D)} {label}" for k, label in [("add", "added"), ("change", "changed"), ("remove", "removed")]
             if any(d["kind"] == k for d in D)]
    return ", ".join(parts) or "No changes"


def review_status(P, cur, as_of):
    """Overdue, due in 30 days, or on track, counted from the last approved version."""
    nxt = add_months(dmy(cur["ver"]["date"]), P["every"])
    days = (nxt - as_of).days
    if days < 0:
        return {"k": "Overdue", "txt": f"Review overdue since {fmt_dmy(nxt)}"}
    if days <= 30:
        return {"k": "Due soon", "txt": f"Review due {fmt_dmy(nxt)}"}
    return {"k": "On track", "txt": f"Next review {fmt_dmy(nxt)}"}


def flags(r, db, as_of):
    """Reasons to look at a resident's plan: a draft, no plan, review due, risk went up, or alerts since."""
    rid = r["resident_id"]
    P, S = plan(rid, db), snapshots(rid, db)
    cur, dr, out = current(S), draft(S), []
    if dr:
        out.append({"k": "draft", "txt": f"Draft version {dr['ver']['v']} by {dr['ver']['by']} waiting for RN approval"})
    if not cur:
        if not dr:
            out.append({"k": "none", "txt": "No care plan yet"})
        return out
    last = cur["ver"]
    st = review_status(P, cur, as_of)
    if st["k"] != "On track":
        out.append({"k": "review", "txt": st["txt"]})
    if C.RANK[r["falls_lvl"]] > C.RANK[last["risk"]["falls"]]:
        out.append({"k": "risk", "txt": f"Falls risk up from {last['risk']['falls']} to {r['falls_lvl']} since {last['date']}"})
    if C.RANK[r["inf_lvl"]] > C.RANK[last["risk"]["inf"]]:
        out.append({"k": "risk", "txt": f"Infection risk up from {last['risk']['inf']} to {r['inf_lvl']} since {last['date']}"})
    since = datetime.combine(dmy(last["date"]), dtime())
    alerts = [a for a in C.EMG_ALERTS if a["rid"] == rid and (a["type"] in C.EMG_LOST or a["type"] == "Fall detected")
              and datetime.fromisoformat(a["start"]) > since]
    if alerts:
        types = list(dict.fromkeys(a["type"] for a in alerts))
        n = len(alerts)
        out.append({"k": "alert", "txt": f"{n} alert{'' if n == 1 else 's'} since {last['date']}: {', '.join(types)}"})
    return out


def can_start_review(r, db, as_of):
    f = flags(r, db, as_of)
    return not any(x["k"] == "draft" for x in f) and any(x["k"] in ("risk", "alert", "review") for x in f)


def review_prefill(r, db, as_of):
    """Reason and comment for the update form, filled in from the flags."""
    f = [x for x in flags(r, db, as_of) if x["k"] in ("risk", "alert", "review")]
    alerts = " ".join(x["txt"] for x in f if x["k"] == "alert")
    if alerts:
        reason = "After an emergency alert" if re.search(r"Left safe zone|Not home|SOS", alerts) else "After a fall"
    elif any(x["k"] == "risk" for x in f):
        reason = "Change in condition"
    else:
        reason = "Scheduled review"
    return {"reason": reason, "note": "Review started from: " + "; ".join(x["txt"] for x in f)}


def new_item(item_id, sec, text, who="", when="", area=""):
    return {"id": item_id, "sec": sec, "text": text, "who": who, "when": when, "area": area}


def save_version(rid, r, patch, reason, note, agreed, user, db):
    """Save a new version. An RN's change is approved on save; anyone else's is a draft."""
    S = snapshots(rid, db)
    cur = current(S)
    today = fmt_dmy(date.today())
    ver = {"v": len(S) + 1, "date": today, "by": user["name"], "role": user["role"], "reason": reason,
           "agreed": agreed, "risk": {"falls": r["falls_lvl"], "inf": r["inf_lvl"]}, "note": note}
    if is_rn(user["role"]):
        ver["approval"] = {"by": user["name"], "role": user["role"], "date": today, "self": True}
    else:
        ver["status"] = "Draft"
    if cur:
        ver.update(patch)
    else:
        ver["items"] = patch["add"]
    store.add_careplan_version(rid, ver)
    return ver


def decide(rid, v, approve, user, comment):
    store.set_careplan_decision(rid, v, "Approved" if approve else "Rejected", user["name"], user["role"],
                                fmt_dmy(date.today()), comment)
