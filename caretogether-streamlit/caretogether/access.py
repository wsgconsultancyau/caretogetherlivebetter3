"""Who is signed in (demo only), the "why are you opening this?" step, and the access log.

Before a medical history or a location is shown, the person picks a reason (and can add a comment).
They are not asked again for the same record for 30 minutes. Every view is logged with their name,
the time and the reason.
"""
import time

import streamlit as st

from . import config as C
from . import store
from . import ui


def current_user():
    name = st.session_state.get("user", C.STAFF[0]["name"])
    return next((s for s in C.STAFF if s["name"] == name), C.STAFF[0])


def is_rn(role):
    """Registered nurses can approve care plan changes."""
    return str(role or "").startswith("Registered Nurse")


def _grants():
    return st.session_state.setdefault("grants", {})


def granted(area, item_id):
    """The saved reason if this person opened this record in the last 30 minutes, otherwise None."""
    g = _grants().get(f"{current_user()['name']}|{area}|{item_id}")
    if g and time.time() - g["at"] < C.GRANT_MINUTES * 60:
        return g
    return None


def grant(area, item_id, reason, comment):
    _grants()[f"{current_user()['name']}|{area}|{item_id}"] = {"at": time.time(), "reason": reason, "comment": comment}


def log(area, action, rid="", alert="", reason="", comment="", dedupe=True):
    u = current_user()
    store.log_access(u["name"], u["role"], area, action, rid=rid, alert=alert, reason=reason, comment=comment, dedupe=dedupe)


def reason_gate(area, item_id, subject, preferred=None, on_open=None):
    """Show the reason form. Returns True once the person has given a reason.

    on_open(reason, comment) is called when they press Open, to write the first log entry.
    """
    if granted(area, item_id):
        return True
    u = current_user()
    reasons = C.REASONS[area]
    with ui.card():
        st.markdown(f"#### Why are you opening {subject}?")
        st.caption(f"Signed in as **{u['name']}**, {u['role']}. Your name, the time, your reason and any comment are saved in the access log.")
        with st.form(key=f"gate_{area}_{item_id}"):
            c1, c2 = st.columns([1, 2])
            reason = c1.selectbox("Reason", reasons, index=reasons.index(preferred) if preferred in reasons else 0)
            placeholder = ("For example: daughter is on her way to the park" if area == C.EL
                           else "For example: weekly check before the GP visit")
            comment = c2.text_area("Comment (optional, but needed for “Other”)", placeholder=placeholder, height=80)
            if st.form_submit_button("Open", type="primary"):
                if reason.startswith("Other") and not comment.strip():
                    st.error("Please add a comment for “Other”.")
                    return False
                why = reason.replace(" (add a comment)", "")
                grant(area, item_id, why, comment.strip())
                if on_open:
                    on_open(why, comment.strip())
                st.toast("Reason saved in the access log")
                st.rerun()
    return False


def access_csv(entries, resident_name):
    """The access log as CSV text, ready to download."""
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["time", "user", "role", "resident_id", "resident_name", "area", "alert", "action", "reason", "comment"])
    for x in entries:
        w.writerow([x["t"], x["user"], x["role"], x["rid"], resident_name(x["rid"]) if x["rid"] else "All residents in view",
                    x["area"], x.get("alert", ""), x["action"], x.get("reason", ""), x.get("comment", "")])
    return buf.getvalue()
