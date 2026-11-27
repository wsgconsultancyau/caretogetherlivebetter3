"""Medical History: Client overview, Care plan, Prescription changes, Visit history and Access log.

Opening a record asks for a reason first; every view is saved in the access log.
"""
from datetime import date

import streamlit as st

from .. import access, config as C, ui
from ..data import num_text
from . import careplan_view

VIEWS = {"overview": "Client overview", "plan": "Care plan", "meds": "Prescription changes", "visits": "Visit history", "log": "Access log"}


def age_from(dmy):
    try:
        d, m, y = (int(x) for x in str(dmy).split("/"))
    except ValueError:
        return ""
    t = date.today()
    return t.year - y - ((t.month, t.day) < (m, d))


def action_for(rid, view):
    return C.MH_ACTION[view] if (rid in C.MED_HISTORY or view in ("log", "plan")) else "Viewed basic record"


def render(ctx):
    rows = ctx.rows
    ui.page_title("Medical History", "Client profile, care plan, current medicines, prescription changes and visits for one resident.")
    if not rows:
        st.info("No residents match these filters.")
        return
    full = [r for r in rows if r["resident_id"] in C.MED_HISTORY]
    basic = [r for r in rows if r["resident_id"] not in C.MED_HISTORY]
    ids = [r["resident_id"] for r in full + basic]
    default = st.session_state.get("selected") if st.session_state.get("selected") in ids else (full or basic)[0]["resident_id"]

    side, main = st.columns([1, 3.2])
    with side, ui.card():
        rid = ui.sticky(st.selectbox, "Resident", ids, key="mh_id", default=default,
                        format_func=lambda i: f"{ctx.name(i)} ({i})" + ("" if i in C.MED_HISTORY else " · basic record only"))
        view = ui.sticky(st.radio, "Show", list(VIEWS), key="mh_view", format_func=VIEWS.get, label_visibility="collapsed")
        st.caption("Opening a record asks for your reason. Every view is logged with your name and the time.")
    r, h = ctx.resident(rid), C.MED_HISTORY.get(rid)
    with main:
        header(r, h)
        opened = access.reason_gate(C.MH, rid, f"{r['name']}'s medical history",
                                    on_open=lambda why, cmt: access.log(C.MH, action_for(rid, view), rid=rid, reason=why, comment=cmt, dedupe=False))
        if not opened:
            return
        g = access.granted(C.MH, rid)
        access.log(C.MH, action_for(rid, view), rid=rid, reason=g["reason"])
        if view == "log":
            log_view(ctx, r)
        elif view == "plan":
            careplan_view.render(ctx, r)
        elif not h:
            none_view(r)
        else:
            {"overview": overview_view, "meds": meds_view, "visits": visits_view}[view](h, r)
        st.caption("All names, clinicians and details are fictional, for training and research demonstration only.")


def header(r, h):
    sex = {"F": "Female", "M": "Male"}.get(r["sex"], r["sex"])
    sub = (f"{h['demoId']} · {h['dob']} · {age_from(h['dob'])} years · {h['sex']}" if h
           else f"{r['resident_id']} · {num_text(r['age'])} years · {sex}")
    loc = (f"{r['state']} · " if r.get("state") else "") + f"{r['sub_region']} · {r['location_type']}" + (f" · {r['mmm']}" if r.get("mmm") else "")
    c1, c2 = st.columns([5, 1], vertical_alignment="center")
    c1.markdown(f'<div class="who">{ui.avatar(r, plain=True)}<div><h3 style="margin:0">{ui.esc(r["name"])} <span class="pill-demo">DEMO</span></h3>'
                f'<div class="muted">{ui.esc(sub)}</div></div></div><div style="margin-top:8px">{ui.chip(h["program"] if h else r["care_setting"])}'
                f'{ui.badge(r["falls_lvl"], label="Falls risk")}{ui.badge(r["inf_lvl"], label="Infection risk")}{ui.chip(loc)}'
                f'{ui.chip("Updated " + h["updated"]) if h else ""}</div>', unsafe_allow_html=True)
    if c2.button("Risk scores →", key="mh_risk"):
        ui.open_resident(r["resident_id"])


def tile(k, v, unit=""):
    return f'<div class="tile"><div class="k">{ui.esc(k)}</div><div class="v">{ui.esc(v)}{" <small>" + ui.esc(unit) + "</small>" if unit else ""}</div></div>'


def overview_view(h, r):
    allergies = "".join(f'<span><b>{ui.esc(a["name"])}</b> – {ui.esc(a["reaction"])}</span>' for a in h["allergies"]) or "<span>No known allergies</span>"
    ui.html_block(f'<div class="allergy"><b>⚠ Allergies</b>{allergies}</div>')
    c1, c2, c3 = st.columns(3)
    with c1, ui.card():
        st.markdown("**Client profile**")
        ui.html_block('<dl class="kv">' + "".join(f"<dt>{ui.esc(k)}</dt><dd>{ui.esc(v)}</dd>" for k, v in h["profile"]) + "</dl>")
    with c2, ui.card():
        st.markdown("**Care team**")
        ui.html_block('<div class="team">' + "".join(f'<div><span><b>{ui.esc(t["name"])}</b><br><span class="muted">{ui.esc(t["role"])}</span></span>'
                                                     f'<span class="r">{ui.esc(t["note"])}</span></div>' for t in h["team"]) + "</div>")
    with c3, ui.card():
        st.markdown("**Active conditions**")
        ui.html_block('<div class="cond">' + "".join(f"<span>{ui.esc(c)} · {ui.esc(y)}</span>" for c, y in h["conditions"]) + "</div>"
                      + '<div class="tiles">' + "".join(tile(l["label"], l["value"], l["unit"]) for l in h["labs"]) + "</div>")
    with ui.card():
        st.markdown(f"**Current medications** · {len(h['meds'])} medicines · {h['medsNote']}")
        ui.table(["Medicine", "Dose and time", "For", "Started and why", "Last change"],
                 [[f"<b>{ui.esc(m['med'])}</b>", ui.esc(m["dose"]), ui.esc(m["forWhat"]), ui.esc(m["started"]),
                   f'<span class="{"chg" if m["last"] else "nochg"}">{ui.esc(m["last"] or "No change")}</span>'] for m in h["meds"]])


def trend_tiles(r):
    def f(v, d):
        return "–" if v is None else f"{v:,.{d}f}"
    spec = [("Daily steps", "steps", 0, ""), ("Gait speed", "gait", 2, " m/s"), ("Resting heart rate", "rhr", 0, " bpm"), ("SpO₂", "spo2", 0, "%")]
    return '<div class="tiles">' + "".join(tile(k, f"{f(r['B'][key], d)} → {f(r['R'][key], d)}{u}") for k, key, d, u in spec) + "</div>"


def meds_view(h, r):
    st.markdown(f"#### Prescription changes")
    ui.html_block(f'<p class="lead">{len(h["changes"])} changes by {ui.esc(h["changesBy"])}, newest first &nbsp; '
                  '<span class="dot d-New"></span> New &nbsp; <span class="dot d-Change"></span> Dose or timing change &nbsp; '
                  '<span class="dot d-Stopped"></span> Stopped</p>')
    c1, c2 = st.columns([2, 1])
    with c1, ui.card():
        ui.html_block('<ol class="tl">' + "".join(
            f'<li><div class="tl-date">{ui.esc(c["date"])}</div><div><span class="dot d-{c["kind"]}"></span></div>'
            f'<div><span class="med">{ui.esc(c["med"])}</span><span class="tag t-{c["kind"]}">{ui.esc(c["type"])}</span> <span class="sm">{ui.esc(c["by"])}</span>'
            f'<div>{ui.esc(c["change"])}</div><div class="sm">Why: {ui.esc(c["why"])}</div><div class="sm">Monitoring: {ui.esc(c["monitor"])}</div></div></li>'
            for c in h["changes"]) + "</ol>")
    with c2:
        with ui.card():
            st.markdown("**Previously used**")
            ui.html_block("".join(f'<div style="padding:4px 0"><b>{ui.esc(p["med"])}</b><br><span class="muted">{ui.esc(p["when"])} · {ui.esc(p["why"])}</span></div>'
                                  for p in h["previous"]) or '<div class="muted">None recorded</div>')
        with ui.card():
            if h.get("wearableCheck"):
                st.markdown("**Wearable check after changes**")
                ui.html_block('<div class="tiles">' + "".join(tile(k, v) for k, v in h["wearableCheck"]) + "</div>")
            else:
                st.markdown("**Wearable trend**")
                st.caption("Baseline → last 3 days, from the wearable readings")
                ui.html_block(trend_tiles(r) if not r["readings"].empty else '<div class="muted">No wearable readings for this resident.</div>')


def visits_view(h, r):
    st.markdown("#### Visit history")
    st.caption(h["visitsNote"])
    cols = st.columns(len(h["visits"]) or 1)
    for col, g in zip(cols, h["visits"]):
        tone = C.VISIT_TONE.get(g["name"], {"bg": "#F1F0EA", "ink": "#13233A"})
        n = len(g["visits"])
        with col, ui.card():
            ui.html_block(f'<div class="vh" style="background:{tone["bg"]};color:{tone["ink"]}"><b>{ui.esc(g["name"])}</b><span>{n} visit{"" if n == 1 else "s"}</span></div>'
                          + "".join(f'<div class="visit"><b>{ui.esc(v["date"])}</b> <span class="muted">{ui.esc(v["place"])}</span>'
                                    f'<div><b>{ui.esc(v["doctor"])}</b> <span class="muted">· {ui.esc(v["name"])}</span></div>'
                                    f'<div>Why: {ui.esc(v["why"])}</div><div class="vo">{ui.esc(v["outcome"])}</div></div>' for v in g["visits"]))


def none_view(r):
    conds = [c.strip() for c in str(r.get("conditions") or "").split(";") if c.strip()]
    with ui.card():
        st.markdown("#### No detailed medical history yet")
        st.caption(f"A full record has not been added for {r['name']}. This is what the resident records CSV holds.")
        place = r["site"] + (f", {r['town']}" if r.get("town") else "")
        rows = [("Care setting", r["care_setting"]), ("Site", place), ("Council / postcode", (r.get("council_pc") or "–") + (f", {r['state']}" if r.get("state") else "")),
                ("Sub-region", f"{r['sub_region']} · {r['location_type']}" + (f" · {r['mmm']}" if r.get("mmm") else "")),
                ("Medications", f"{num_text(r['medication_count'])} (names not in the CSV)"), ("Falls, last 12 months", num_text(r["falls_last_12m"])),
                ("Walking aid", r["walking_aid"]), ("Cognition", r["cognitive_impairment"])]
        ui.html_block('<dl class="kv">' + "".join(f"<dt>{ui.esc(k)}</dt><dd>{ui.esc(v)}</dd>" for k, v in rows)
                      + f'<dt>Conditions</dt><dd><div class="cond">{"".join(f"<span>{ui.esc(c)}</span>" for c in conds) or "None recorded"}</div></dd></dl>')
        st.caption("To add a full record, copy the R001 block in data/medical_history.json and change the details.")


def comment_form(area, rid, alert=""):
    with st.form(key=f"cmt_{area}_{rid}_{alert}", clear_on_submit=True):
        txt = st.text_area("Add a comment to the log", placeholder="For example: spoke to daughter at 21:10")
        if st.form_submit_button("Add comment"):
            if txt.strip():
                g = access.granted(area, rid if area == C.MH else alert) or {}
                access.log(area, "Added a comment", rid=rid, alert=alert, reason=g.get("reason", ""), comment=txt.strip(), dedupe=False)
                st.toast("Comment added to the access log")
                st.rerun()
            else:
                st.error("Please type a comment first.")


def log_view(ctx, r):
    rid = r["resident_id"]
    entries = [x for x in access.store.all_access() if x["rid"] == rid]
    with ui.card():
        c1, c2 = st.columns([4, 1])
        c1.markdown("#### Access log")
        c2.download_button("Download log (CSV)", access.access_csv(entries, ctx.name), file_name=f"access_log_{rid}.csv", mime="text/csv",
                           on_click=lambda: access.log(C.MH, "Downloaded access log", rid=rid, dedupe=False))
        st.caption(f"Everyone who opened {r['name']}'s medical history or emergency location, newest first, with their reason and comments.")
        ui.log_table(entries, ctx.name, show_res=False, show_area=True)
        comment_form(C.MH, rid)
        st.caption("The log is saved in the app's database (caretogether.db). A real system would keep it on a secure server where entries cannot be changed or deleted.")
