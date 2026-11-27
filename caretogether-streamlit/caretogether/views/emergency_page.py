"""Emergency Location Tracking: find a resident who may be lost while out walking or shopping,
including couples who go out together. Location is shown only during an alert, and every view is logged.
"""
import pandas as pd
import streamlit as st

from .. import access, charts, config as C, emergency as em, store, ui
from .history import comment_form


def render(ctx):
    rows = ctx.rows
    ids = {r["resident_id"] for r in rows}
    name = ctx.name
    ui.page_title("Emergency Location Tracking",
                  "Find a resident who may be lost while out walking or shopping, including couples who go out together. "
                  "Location is shown only during an alert, and every view is logged.")
    ui.html_block(ui.chip("Demo clock: " + em.fmt_when(C.EMG_NOW)))
    A = sorted([a for a in ctx.alerts if a["rid"] in ids], key=lambda a: a["start"], reverse=True)

    open_ = [a for a in A if a["status"] == "Open"]
    found = [a for a in A if a["type"] in C.EMG_LOST and a.get("found")]
    med = em.median([em.minutes(a["found"]) - em.minutes(a["start"]) for a in found])
    agreed = sum(1 for r in rows if em.consent(r["resident_id"])["status"] == "Agreed")
    low = sum(1 for r in rows if (c := C.EMG_CONSENT.get(r["resident_id"])) and ((c.get("battery") or 100) < 20 or (c.get("battery2") is not None and c["battery2"] < 20)))
    ui.kpis([
        ("Active searches", len(open_), f"{em.alert_name(open_[0], name)} · {em.ago(open_[0]['start'])}" if open_ else "no one missing now", "hi"),
        ("People found (14 days)", len(found), f"median {em.dur(med)} to find" if med is not None else "none in this filter", "teal"),
        ("Location sharing agreed", f"{agreed} of {len(rows)}", f"{len(rows) - agreed} pending or declined", "metro"),
        ("Devices below 20%", low, "charge before going out", "mo"),
    ])

    # which alert is selected: an open alert first, until someone picks another
    choices = ["ALL"] + [a["id"] for a in A]
    by_id = {a["id"]: a for a in A}

    left, right = st.columns([1, 1.7])
    with left, ui.card():
        st.markdown("#### Alerts")
        st.caption(f"{len(A)} alert{'' if len(A) == 1 else 's'} in the last 14 days, newest first. Select one to see it on the map."
                   if A else "No alerts for the residents in the current filter.")
        sel = ui.sticky(st.radio, "Alert", choices, key="emg_sel", default=open_[0]["id"] if open_ else "ALL", label_visibility="collapsed",
                        format_func=lambda i: "Show all on map" if i == "ALL" else f"{ui.ICON.get({'Open': 'High', 'Acknowledged': 'Moderate'}.get(by_id[i]['status'], 'Low'))} {em.alert_name(by_id[i], name)} · {by_id[i]['status']}",
                        captions=[""] + [caption(a) for a in A])
    a = by_id.get(sel)

    with right, ui.card():
        st.markdown(f"#### Map · {em.alert_name(a, name) if a else 'all alerts'}")
        gid = a["id"] if a else "ALL"
        shared = em.location_shared(a) if a else any(em.location_shared(x) for x in A)
        need_gate = shared and not access.granted(C.EL, gid)
        if not need_gate:
            g = access.granted(C.EL, gid) or {}
            if a:
                access.log(C.EL, "Opened location" if shared else "Viewed alert – location not shared", rid=a["rid"], alert=a["id"], reason=g.get("reason", ""))
            elif shared:
                access.log(C.EL, "Viewed map of all alerts", reason=g.get("reason", ""))
        fig, n = charts.alert_map(A, a, need_gate, name)
        st.plotly_chart(fig, config={"displayModeBar": False, "scrollZoom": True}, theme=None, key="emg_map")
        if need_gate:
            st.caption("Location hidden until you give a reason. This is recorded in the access log.")
            pref = ("Searching for a missing person" if a["type"] in C.EMG_LOST else "Responding to this alert") if a else "Reviewing alerts"
            subject = f"the location of {em.alert_name(a, name)}" if a else "the map of all alert locations"
            access.reason_gate(C.EL, gid, subject, preferred=pref, on_open=lambda why, cmt: access.log(
                C.EL, "Opened location" if a else "Viewed map of all alerts", rid=a["rid"] if a else "", alert=a["id"] if a else "",
                reason=why, comment=cmt, dedupe=False))
        elif a:
            st.caption("Trail points are approximate (demo). Hover a dot to see the time." if a.get("home") else em.share_text(a))
            detail(ctx, a)
        else:
            st.caption(f"{n} alert location{'' if n == 1 else 's'}. Each circle is the last known position for an alert: "
                       "red = open, amber = acknowledged, grey = resolved. Pick an alert on the left to zoom in.")

    with ui.card():
        st.markdown("#### Location consent and safe zones")
        st.caption("Who agreed to share location, when it is shown, and each person's device.")
        def bat(v):
            return "–" if v is None else f"{v}%" + (" ⚠" if v < 20 else "")
        rows_html = []
        for r in rows:
            c = em.consent(r["resident_id"])
            rows_html.append([f'<b>{ui.esc(r["name"])}</b><div class="muted">{ui.esc(r["resident_id"])} · {ui.esc(r["council_pc"] or r["site"])}</div>',
                              ui.status_chip(c["status"]), ui.esc(c["by"]), ui.esc(c["date"]), ui.esc(c["when"]), ui.esc(c["zone"]),
                              ui.esc(f"{c['device']} · {bat(c.get('battery'))}" + (f" / tag {bat(c['battery2'])}" if c.get("battery2") is not None else ""))])
        ui.table(["Resident", "Consent", "Agreed by", "Date", "When location is shown", "Safe zone or check", "Device · battery"], rows_html)

    with ui.card():
        entries = [x for x in store.all_access() if x["area"] == C.EL and (not x["rid"] or x["rid"] in ids)]
        c1, c2 = st.columns([4, 1])
        c1.markdown("#### Emergency location access log")
        c2.download_button("Download log (CSV)", access.access_csv(entries, name), file_name="emergency_location_access_log.csv", mime="text/csv",
                           on_click=lambda: access.log(C.EL, "Downloaded access log", dedupe=False))
        st.caption("Everyone who opened a location, with the time, their reason and any comments. Newest first.")
        ui.log_table(entries, name, show_res=True)


def caption(a):
    line = f"{a['type']} · {em.fmt_when(a['start'])}" + (f" · {em.ago(a['start'])}" if a["status"] == "Open" else "")
    where = a["home"]["label"] if a.get("home") else em.share_text(a)
    if a.get("found") and a["type"] in C.EMG_LOST:
        where += f" · found after {em.dur(em.minutes(a['found']) - em.minutes(a['start']))}"
    return f"{line}  \n{where}"


def detail(ctx, a):
    name = ctx.name
    lp = em.last_point(a.get("trail"))
    second = em.first_name(a["companion"]) if a.get("companion") else ""
    tiles = []
    if a.get("last"):
        L = a["last"]
        tiles.append(("Last update", L["time"] + (f" · {em.ago(em.point_iso(a, L['time']))}" if len(L["time"]) == 5 and a["status"] == "Open" else "")))
        tiles.append(("Accuracy", f"± {L['acc']} m"))
        tiles.append(("Battery", f"{L['battery']}%" + (f" · {second} {a['last2']['battery']}%" if a.get("last2") else "")))
        if a.get("home") and lp:
            tiles.append(("From home or site", f"{em.km_between([a['home']['lat'], a['home']['lon']], [lp[1], lp[2]]):.1f} km"))
        tiles.append(("Movement", L["move"]))
    else:
        tiles.append(("Location", em.share_text(a) or "Not available"))
    ui.html_block(f'<div class="vhd"><h4 style="margin:0">{ui.esc(em.alert_name(a, name))}</h4>{ui.status_chip(a["status"])}</div>'
                  f'<div class="muted">{ui.esc(a["type"])} · {ui.esc(em.fmt_when(a["start"]))} · {ui.esc(a.get("raisedBy", ""))}</div>'
                  '<div class="tiles">' + "".join(f'<div class="tile"><div class="k">{ui.esc(k)}</div><div class="v" style="font-size:15px">{ui.esc(v)}</div></div>'
                                                  for k, v in tiles) + "</div>")
    if a.get("describe"):
        st.markdown("**Description for searchers**")
        st.write(a["describe"])
    if a["status"] == "Open":
        st.markdown("**Search steps**")
        st.markdown("1. Call the watch, then the person's own phone.\n"
                    "2. Send the nearest staff or family member to the last known position, and refresh the map as they go.\n"
                    "3. Call the next of kin on file.\n"
                    "4. Follow your organisation's missing person procedure. If the person may be at risk, call Police on 000 "
                    "and give the last known position and the description above.")
        b1, b2, b3, _ = st.columns([1, 1.3, 1.2, 1.5])
        g = access.granted(C.EL, a["id"]) or {}
        if b1.button("Call watch", key="emg_call"):
            access.log(C.EL, "Called watch (demo)", rid=a["rid"], alert=a["id"], reason=g.get("reason", ""), dedupe=False)
            st.toast("Demo only: no call is made")
        if b2.button("Call next of kin", key="emg_kin"):
            access.log(C.EL, "Called next of kin (demo)", rid=a["rid"], alert=a["id"], reason=g.get("reason", ""), dedupe=False)
            st.toast("Demo only: no call is made")
        if b3.button("Mark as found", type="primary", key="emg_found"):
            access.log(C.EL, "Marked as found", rid=a["rid"], alert=a["id"], reason=g.get("reason", ""), dedupe=False)
            store.mark_alert_found(a["id"], C.EMG_NOW, "Marked as found in this demo.")
            st.toast("Marked as found (saved in the app; use Reset demo data to undo)")
            st.rerun()
    if a.get("outcome"):
        st.markdown(f"**{'Notes' if a['status'] == 'Open' else 'Outcome'}**")
        st.write(a["outcome"])
    if a.get("trail") and len(a["trail"]) > 1:
        st.markdown(f"**Trail{' (' + em.first_name(name(a['rid'])) + ')' if a.get('companion') else ''}**")
        home = a.get("home")
        st.dataframe(pd.DataFrame([{"Time": p[0], "Where": p[3] if len(p) > 3 and p[3] else "On the move",
                                    "From home": f"{em.km_between([home['lat'], home['lon']], [p[1], p[2]]):.1f} km" if home else "–"}
                                   for p in a["trail"]]), hide_index=True)
    st.markdown("**Who opened the location**")
    ui.log_table([x for x in store.all_access() if x["area"] == C.EL and x.get("alert") == a["id"]], name, show_res=False)
    comment_form(C.EL, a["rid"], a["id"])
    st.markdown("**Alert timeline**")
    ui.html_block('<div class="emg-log">' + ("".join(f"<div><b>{ui.esc(t)}</b> · {ui.esc(e)}</div>" for t, e in a.get("log") or [])
                                             or "No events yet") + "</div>")
