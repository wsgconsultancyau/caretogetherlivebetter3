"""The Care plan section inside Medical History: current plan, draft for RN approval, editor and change history."""
from datetime import date

import pandas as pd
import streamlit as st

from .. import access, careplans as cp, config as C, ui

FIELD_LABEL = {"text": "", "who": "Who: ", "when": "When: ", "area": "Area: "}


def diff_html(d):
    if d["kind"] == "first":
        n = d["n"]
        return f'<li><span class="cpb cpb-first">Created</span> First care plan with {n} item{"" if n == 1 else "s"}</li>'
    x = d["item"]
    where = f'<b>{ui.esc(x["sec"])}{" · " + ui.esc(x["area"]) if x.get("area") else ""}:</b> '
    if d["kind"] == "add":
        extra = ", ".join(v for v in [x.get("who"), x.get("when")] if v)
        return f'<li><span class="cpb cpb-add">Added</span> {where}{ui.esc(x["text"])}' + (f' <span class="muted">({ui.esc(extra)})</span>' if extra else "") + "</li>"
    if d["kind"] == "remove":
        return f'<li><span class="cpb cpb-rm">Removed</span> {where}<del>{ui.esc(x["text"])}</del></li>'
    return (f'<li><span class="cpb cpb-chg">Changed</span> {where}{FIELD_LABEL.get(d["field"], "")}'
            f'<del>{ui.esc(d["from"] or "(blank)")}</del> → <ins>{ui.esc(d["to"] or "(blank)")}</ins></li>')


def diffs_html(s, limit=None):
    D = cp.diff(s)
    if limit:
        D = [d for d in D if d["kind"] != "first"][:limit]
    return '<ul class="cpd">' + "".join(diff_html(d) for d in D) + "</ul>"


def state_chip(st_):
    if st_["status"] == "Draft":
        return ui.status_chip("Draft", "Draft · waiting for RN approval")
    if st_["status"] == "Rejected":
        return ui.status_chip("Rejected", f"Rejected by {st_['by']} · {st_['date']}")
    return ui.status_chip("Approved", ("Approved on save" if st_.get("self") else f"Approved by {st_['by']}") + f" · {st_['date']}")


def start_review(ctx, r):
    """Used by 'Start review' buttons: open the editor with the reason and comment filled in."""
    st.session_state["cp_prefill"] = cp.review_prefill(r, ctx.db, ctx.as_of_date)
    st.session_state["cp_editing"] = r["resident_id"]
    ui.set_sticky("mh_id", r["resident_id"])
    ui.set_sticky("mh_view", "plan")


def render(ctx, r):
    rid, user = r["resident_id"], access.current_user()
    if st.session_state.get("cp_editing") == rid:
        return editor(ctx, r)
    S, P = cp.snapshots(rid, ctx.db), cp.plan(rid, ctx.db)
    cur, dr = cp.current(S), cp.draft(S)

    if dr:   # a draft waiting for a registered nurse
        v = dr["ver"]
        with ui.card():
            ui.html_block(f'<div class="vhd"><h4 style="margin:0">Draft version {v["v"]} waiting for RN approval</h4>{state_chip(dr["st"])}</div>'
                          f'<div class="muted">Saved {ui.esc(v["date"])} by {ui.esc(v["by"])}, {ui.esc(v["role"])} · Why: {ui.esc(v["reason"])}'
                          f'{" — " + ui.esc(v["note"]) if v.get("note") else ""}</div>'
                          f'<div class="muted">Agreed: {ui.esc(cp.agreed_text(v.get("agreed")))}</div>{diffs_html(dr)}')
            if access.is_rn(user["role"]):
                note = st.text_area("Comment (needed if you reject)", key=f"dec_{rid}", placeholder="For example: checked with Teresa; physio agrees")
                b1, b2, _ = st.columns([1, 1, 4])
                if b1.button("Approve", type="primary", key=f"ap_{rid}"):
                    decide(ctx, rid, v["v"], True, note)
                if b2.button("Reject", key=f"rj_{rid}"):
                    if not note.strip():
                        st.error("Please say why you are rejecting this draft.")
                    else:
                        decide(ctx, rid, v["v"], False, note)
            else:
                st.caption(f"Only a registered nurse can approve or reject this draft. You are signed in as {user['name']}, {user['role']}.")

    if not cur:
        with ui.card():
            st.markdown("#### Care plan")
            if dr:
                st.caption("There is no approved care plan yet. The first plan is waiting for RN approval.")
            else:
                st.caption(f"No care plan yet for {r['name']}. The first assessment is still to be done.")
                if st.button("Start a care plan", type="primary", key=f"start_{rid}"):
                    st.session_state["cp_editing"], st.session_state["cp_prefill"] = rid, None
                    st.rerun()
        return

    v, status = cur["ver"], cp.review_status(P, cur, ctx.as_of_date)
    with ui.card():
        h1, h2 = st.columns([4, 1])
        h1.markdown(f'<h4 style="margin:0">Care plan <span class="chip">Version {v["v"]}</span></h4>'
                    f'<div class="muted">Last updated {ui.esc(v["date"])} by {ui.esc(v["by"])}, {ui.esc(v["role"])} · Why: {ui.esc(v["reason"])}</div>'
                    f'<div class="muted">Agreed: {ui.esc(cp.agreed_text(v.get("agreed")))}</div>'
                    f'<div style="margin-top:4px">{state_chip(cur["st"])} <span class="muted">· Plan owner: {ui.esc(P["owner"])} · Reviewed every '
                    f'{P["every"]} month{"" if P["every"] == 1 else "s"} ·</span> {ui.status_chip(status["k"], status["txt"])}</div>',
                    unsafe_allow_html=True)
        if not dr and h2.button("Update care plan", type="primary", key=f"upd_{rid}", width="stretch"):
            st.session_state["cp_editing"], st.session_state["cp_prefill"] = rid, None
            st.rerun()
        flags = [f for f in cp.flags(r, ctx.db, ctx.as_of_date) if f["k"] in ("risk", "alert")]
        texts = [f["txt"] for f in flags] + ([status["txt"]] if status["k"] != "On track" and not dr else [])
        if texts:
            f1, f2 = st.columns([5, 1], vertical_alignment="center")
            f1.markdown(f'<div class="flag"><b>Review suggested:</b> {ui.esc("; ".join(texts))}.</div>', unsafe_allow_html=True)
            if cp.can_start_review(r, ctx.db, ctx.as_of_date) and f2.button("Start review", key=f"rev_{rid}", width="stretch"):
                start_review(ctx, r)
                st.rerun()

        new_ids = {x["id"] for x in v.get("add", [])}
        chg_ids = {c[0] for c in v.get("change", [])}

        def mark(item_id):
            if "items" in v or item_id not in new_ids | chg_ids:
                return ""
            return f'<span class="mark">{"New" if item_id in new_ids else "Changed"} in v{v["v"]}</span>'

        def section(name):
            items = [x for x in cur["items"] if x["sec"] == name]
            if not items:
                return '<div class="muted">None recorded</div>'
            return '<ul class="cpl">' + "".join(
                f'<li>{ui.esc(x["text"])}{mark(x["id"])}' + (f'<div class="muted">{ui.esc(" · ".join(y for y in [x.get("who"), x.get("when")] if y))}</div>'
                                                              if x.get("who") or x.get("when") else "") + "</li>" for x in items) + "</ul>"
        c1, c2 = st.columns(2)
        c1.markdown("**Goals**" + section("Goals"), unsafe_allow_html=True)
        c2.markdown("**What matters to me**" + section("What matters to me"), unsafe_allow_html=True)
        daily = [x for x in cur["items"] if x["sec"] == "Daily support"]
        st.markdown("**Daily support**")
        if daily:
            ui.table(["Area", "Support", "Who", "When"],
                     [[f'<b>{ui.esc(x.get("area") or "–")}</b>', ui.esc(x["text"]) + mark(x["id"]), ui.esc(x.get("who") or "–"),
                       ui.esc(x.get("when") or "–")] for x in daily])
        else:
            st.caption("None recorded")
        c1, c2, c3 = st.columns(3)
        for col, name in zip([c1, c2, c3], ["Falls prevention", "Infection prevention", "Safety when out"]):
            col.markdown(f"**{name}**" + section(name), unsafe_allow_html=True)
        st.caption(f"Falls risk now: {r['falls_lvl']} ({v['risk']['falls']} when this version was saved) · "
                   f"Infection risk now: {r['inf_lvl']} ({v['risk']['inf']} then).")

    with ui.card():
        st.markdown("#### Change history")
        st.caption("Every version of this care plan, newest first: what changed and how, who changed it, why, who agreed, and who approved it.")
        out = []
        for s in reversed(S):
            sv, cls = s["ver"], "cur" if s is cur else s["st"]["status"].lower() if s["st"]["status"] != "Approved" else ""
            extra = ""
            if s["st"].get("comment"):
                extra = f' · {"Reason for rejecting" if s["st"]["status"] == "Rejected" else "RN comment"}: {ui.esc(s["st"]["comment"])}'
            out.append(f'<div class="ver {cls}"><div class="vhd"><span class="chip">v{sv["v"]}</span><b>{ui.esc(sv["date"])}</b>'
                       f'<span>· {ui.esc(sv["by"])}, {ui.esc(sv["role"])}</span>{ui.status_chip("Current") if s is cur else ""}{state_chip(s["st"])}</div>'
                       f'<div class="muted">Why: {ui.esc(sv["reason"])}{" — " + ui.esc(sv["note"]) if sv.get("note") else ""}</div>'
                       f'<div class="muted">Agreed: {ui.esc(cp.agreed_text(sv.get("agreed")))}{extra}</div>{diffs_html(s)}</div>')
        ui.html_block("".join(out))


def decide(ctx, rid, v, approve, note):
    user = access.current_user()
    cp.decide(rid, v, approve, user, note.strip())
    g = access.granted(C.MH, rid) or {}
    access.log(C.MH, f"{'Approved' if approve else 'Rejected'} care plan draft version {v}", rid=rid, reason=g.get("reason", ""),
               comment=note.strip(), dedupe=False)
    st.toast(f"Version {v} {'approved' if approve else 'rejected'}")
    st.rerun()


def editor(ctx, r):
    """Update the plan: edit items in the table, tick Remove, add rows, then record why and who agreed."""
    rid, user = r["resident_id"], access.current_user()
    S = cp.snapshots(rid, ctx.db)
    cur = cp.current(S)
    items = sorted(cur["items"] if cur else [], key=lambda x: C.CP_SECTIONS.index(x["sec"]) if x["sec"] in C.CP_SECTIONS else 99)
    pre = st.session_state.get("cp_prefill") or {}
    rn = access.is_rn(user["role"])
    with ui.card():
        h1, h2 = st.columns([5, 1])
        h1.markdown(f"#### {'Update care plan (saves as version ' + str(len(S) + 1) + ')' if cur else 'Start a care plan'}")
        if h2.button("Cancel", key="cp_cancel", width="stretch"):
            st.session_state["cp_editing"], st.session_state["cp_prefill"] = None, None
            st.rerun()
        st.caption("Edit any item in the table, tick Remove to take one out, or add new items below. "
                   + ("You are a registered nurse, so the new version is approved when you save it." if rn else
                      f"You are signed in as {user['name']}, {user['role']}: your change is saved as a draft until a registered nurse approves it."))
        if pre.get("note"):
            ui.html_block(f'<div class="flag"><b>Started from a review flag:</b> {ui.esc(pre["note"].replace("Review started from: ", ""))}</div>')
        edited = None
        if items:
            df = pd.DataFrame([{"id": x["id"], "Section": x["sec"], "Area": x.get("area", ""), "Item": x["text"], "Who": x.get("who", ""),
                                "When": x.get("when", ""), "Remove": False} for x in items])
            edited = st.data_editor(df, key=f"cp_items_{rid}", hide_index=True, disabled=["id", "Section", "Area"],
                                    column_config={"id": None, "Item": st.column_config.TextColumn(width="large")})
        st.markdown("**Add items**")
        new = st.data_editor(pd.DataFrame(columns=["Section", "Area", "Item", "Who", "When"]), key=f"cp_new_{rid}", num_rows="dynamic",
                             hide_index=True, column_config={
                                 "Section": st.column_config.SelectboxColumn(options=C.CP_SECTIONS, required=True),
                                 "Area": st.column_config.TextColumn(help="Only for Daily support, for example Personal care"),
                                 "Item": st.column_config.TextColumn(width="large")})
        reasons = C.CP_REASONS if cur else ["First care plan", *C.CP_REASONS]
        reason = st.selectbox("Why are you changing the plan?", reasons, index=reasons.index(pre["reason"]) if pre.get("reason") in reasons else 0)
        last_ag = S[-1]["ver"].get("agreed") if S else None
        ag = last_ag if isinstance(last_ag, dict) else {"name": last_ag or "", "rel": "Enduring guardian" if "guardian" in str(last_ag or "").lower() else "Family member"}
        c1, c2, c3, c4 = st.columns(4)
        ag_name = c1.text_input("Agreed by: name", value=ag.get("name", ""))
        ag_rel = c2.selectbox("Relationship", C.CP_REL, index=C.CP_REL.index(ag["rel"]) if ag.get("rel") in C.CP_REL else 0)
        ag_how = c3.selectbox("How they agreed", C.CP_HOW, index=C.CP_HOW.index(ag["how"]) if ag.get("how") in C.CP_HOW else 0)
        ag_date = c4.date_input("Date agreed", value=date.today(), format="DD/MM/YYYY")
        note = st.text_area("Comment", value=pre.get("note", ""), placeholder="For example: after the fall on 11/11; discussed with the family")
        if st.button("Save and approve new version" if rn else "Save draft for RN approval", type="primary", key="cp_save"):
            save(ctx, r, items, edited, new, reason, note, {"name": ag_name.strip(), "rel": ag_rel, "how": ag_how,
                                                             "date": ag_date.isoformat() if ag_date else ""})


def save(ctx, r, items, edited, new, reason, note, agreed):
    rid, user = r["resident_id"], access.current_user()
    patch = {"add": [], "change": [], "remove": []}
    if edited is not None:
        by_id = {x["id"]: x for x in items}
        for row in edited.to_dict("records"):
            x = by_id[row["id"]]
            if row["Remove"]:
                patch["remove"].append(x["id"])
                continue
            ch = {}
            text, who, when = (str(row[k] or "").strip() for k in ["Item", "Who", "When"])
            if text and text != x["text"]:
                ch["text"] = text
            if who != x.get("who", ""):
                ch["who"] = who
            if when != x.get("when", ""):
                ch["when"] = when
            if ch:
                patch["change"].append([x["id"], ch])
    stamp = pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
    for i, row in enumerate(new.to_dict("records")):
        text = str(row.get("Item") or "").strip()
        if text and row.get("Section"):
            patch["add"].append(cp.new_item(f"u{stamp}{i}", row["Section"], text, str(row.get("Who") or "").strip(),
                                            str(row.get("When") or "").strip(), str(row.get("Area") or "").strip()))
    reason = reason.replace(" (add a comment)", "")
    if not (patch["add"] or patch["change"] or patch["remove"]):
        return st.error("Nothing has changed yet.")
    if reason == "Other" and not note.strip():
        return st.error("Please add a comment for “Other”.")
    if not agreed["name"]:
        return st.error("Please enter who agreed to the change.")
    if not agreed["date"]:
        return st.error("Please enter the date they agreed.")
    ver = cp.save_version(rid, r, patch, reason, note.strip(), agreed, user, ctx.db)
    rn = access.is_rn(user["role"])
    g = access.granted(C.MH, rid) or {}
    access.log(C.MH, f"Updated and approved care plan version {ver['v']}" if rn else f"Saved care plan draft version {ver['v']} for RN approval",
               rid=rid, reason=g.get("reason", ""), comment=reason + (f": {note.strip()}" if note.strip() else ""), dedupe=False)
    st.session_state["cp_editing"], st.session_state["cp_prefill"] = None, None
    st.toast(f"Care plan version {ver['v']} saved and approved" if rn else f"Draft version {ver['v']} saved, waiting for RN approval")
    st.rerun()
