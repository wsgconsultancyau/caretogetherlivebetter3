"""Care plans: every resident's plan, review dates, suggested reviews, drafts waiting for an RN, and the change log."""
import streamlit as st

from .. import careplans as cp, ui
from .careplan_view import diffs_html, start_review, state_chip


def render(ctx):
    rows, as_of = ctx.rows, ctx.as_of_date
    ui.page_title("Care plans", "Every resident's care plan: review dates, reviews suggested by the risk scores or alerts, and a log of every change.")
    st.caption(f"Review dates as of {as_of.day} {as_of:%b %Y}")
    info = []
    for r in rows:
        rid = r["resident_id"]
        P, S = cp.plan(rid, ctx.db), cp.snapshots(rid, ctx.db)
        cur = cp.current(S)
        info.append({"r": r, "S": S, "cur": cur, "dr": cp.draft(S), "st": cp.review_status(P, cur, as_of) if cur else None,
                     "flags": cp.flags(r, ctx.db, as_of)})
    have = sum(1 for x in info if x["cur"])
    ui.kpis([
        ("Residents with a care plan", f"{have} of {len(rows)}", f"{len(rows) - have} still to start", "teal"),
        ("Reviews overdue", sum(1 for x in info if x["st"] and x["st"]["k"] == "Overdue"), "past the review date", "hi"),
        ("Reviews due in 30 days", sum(1 for x in info if x["st"] and x["st"]["k"] == "Due soon"), "book the review", "mo"),
        ("Review suggested", sum(1 for x in info if any(f["k"] in ("risk", "alert") for f in x["flags"])), "risk went up or an alert happened", "hi"),
        ("Waiting for RN approval", sum(1 for x in info if x["dr"]), "draft changes to check", "metro"),
    ])

    def order(x):
        if x["dr"]:
            return 0
        if not x["cur"]:
            return 1
        if x["st"]["k"] == "Overdue":
            return 2
        if any(f["k"] in ("risk", "alert") for f in x["flags"]):
            return 3
        return 4 if x["st"]["k"] == "Due soon" else 5

    with ui.card():
        st.markdown("#### Plans and reviews")
        st.caption("Residents who need attention first. Open a plan to see it in full, with its change history.")
        widths = [2.2, 2.0, 1.9, 1.3, 2.2, 1.5]
        head = st.columns(widths)
        for col, h in zip(head, ["Resident", "Current version", "Next review", "Risk now", "Review suggested because", ""]):
            col.markdown(f"<span class='muted'><b>{h.upper()}</b></span>", unsafe_allow_html=True)
        if not info:
            st.caption("No residents match these filters.")
        for x in sorted(info, key=order):
            r, v = x["r"], x["cur"]["ver"] if x["cur"] else None
            c = st.columns(widths, vertical_alignment="center")
            c[0].markdown(f'<div class="who">{ui.avatar(r)}<div><div class="nm">{ui.esc(r["name"])}</div>'
                          f'<div class="muted">{ui.esc(r["resident_id"])} · {ui.esc(r["site"])}</div></div></div>', unsafe_allow_html=True)
            cur_txt = (f'<b>Version {v["v"]}</b> · {ui.esc(v["date"])}<div class="muted">{ui.esc(v["by"])} · {ui.esc(v["reason"])}</div>' if v
                       else ui.status_chip("Pending", "No approved plan"))
            if x["dr"]:
                cur_txt += f'<div style="margin-top:4px">{ui.status_chip("Draft", "Draft v" + str(x["dr"]["ver"]["v"]) + " waiting")}</div>'
            c[1].markdown(cur_txt, unsafe_allow_html=True)
            c[2].markdown(ui.status_chip(x["st"]["k"], x["st"]["txt"]) if x["st"] else "–", unsafe_allow_html=True)
            if v:
                up_f = f' <span class="muted">(was {v["risk"]["falls"]})</span>' if cp.C.RANK[r["falls_lvl"]] > cp.C.RANK[v["risk"]["falls"]] else ""
                up_i = f' <span class="muted">(was {v["risk"]["inf"]})</span>' if cp.C.RANK[r["inf_lvl"]] > cp.C.RANK[v["risk"]["inf"]] else ""
                c[3].markdown(f"Falls <b>{r['falls_lvl']}</b>{up_f}<br>Infection <b>{r['inf_lvl']}</b>{up_i}", unsafe_allow_html=True)
            else:
                c[3].markdown("–")
            why = [f["txt"] for f in x["flags"] if f["k"] != "review"]
            c[4].markdown(f'<span class="muted">{"<br>".join(ui.esc(w) for w in why) or "–"}</span>', unsafe_allow_html=True)
            with c[5]:
                if cp.can_start_review(r, ctx.db, as_of) and st.button("Start review", key=f"pl_rev_{r['resident_id']}", type="primary", width="stretch"):
                    start_review(ctx, r)
                    ui.go("history")
                label = "Check draft" if x["dr"] else "Open" if v else "Start"
                if st.button(label, key=f"pl_open_{r['resident_id']}", width="stretch"):
                    ui.set_sticky("mh_id", r["resident_id"])
                    ui.set_sticky("mh_view", "plan")
                    if label == "Start":
                        st.session_state["cp_editing"], st.session_state["cp_prefill"] = r["resident_id"], None
                    ui.go("history")

    with ui.card():
        st.markdown("#### Care plan change log")
        st.caption("Every care plan change across these residents, newest first: who changed it, why, and what changed.")
        changes = [(x["r"], s) for x in info for s in x["S"]]
        changes.sort(key=lambda rs: (cp.dmy(rs[1]["ver"]["date"]), rs[1]["ver"]["v"]), reverse=True)
        if not changes:
            st.caption("No care plan changes for these residents.")
        else:
            ui.table(["When", "Resident", "Version", "Changed by", "Why", "Status", "What changed and how"],
                     [[f'<span style="white-space:nowrap">{ui.esc(s["ver"]["date"])}</span>', f"<b>{ui.esc(r['name'])}</b>", f"v{s['ver']['v']}",
                       f'{ui.esc(s["ver"]["by"])}<div class="muted">{ui.esc(s["ver"]["role"])}</div>',
                       ui.esc(s["ver"]["reason"]) + (f'<div class="muted">{ui.esc(s["ver"]["note"])}</div>' if s["ver"].get("note") else ""),
                       state_chip(s["st"]), f"<b>{ui.esc(cp.summary(s))}</b>{diffs_html(s, limit=3)}"] for r, s in changes[:20]])
