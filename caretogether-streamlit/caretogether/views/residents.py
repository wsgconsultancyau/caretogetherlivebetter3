"""Residents ranked by risk, with a detail panel for the selected resident."""
import pandas as pd
import streamlit as st

from .. import charts, ui
from ..data import num_text
from ..risk import top_reasons


def _table(rows):
    return pd.DataFrame([{
        "ID": r["resident_id"], "Resident": r["name"], "Age": num_text(r["age"]), "Setting": r["care_setting"],
        "Site": r["site"], "Sub-region": r["sub_region"],
        "Falls risk": f"{ui.ICON[r['falls_lvl']]} {r['falls_lvl']}", "Falls points": r["falls"],
        "Infection risk": f"{ui.ICON[r['inf_lvl']]} {r['inf_lvl']}", "Infection points": r["inf"],
        "Main reasons": " · ".join(top_reasons(r)) or "No notable signals",
        "Data gaps": "⚠ gaps" if r["completeness"] < 0.7 else "",
    } for r in rows])


def render(ctx):
    rows = ctx.rows
    ui.page_title("Residents ranked by risk", "Select a resident to see why they scored as they did, their trends and staff observations.")
    if not rows:
        st.info("No residents match these filters.")
        return
    left, right = st.columns([1.25, 1])
    with left, ui.card():
        st.caption(f"{len(rows)} shown · highest risk first · click a row to see the details")
        event = st.dataframe(
            _table(rows), hide_index=True, on_select="rerun", selection_mode="single-row", key="res_table", height=520,
            column_config={
                "Falls points": st.column_config.ProgressColumn("Falls points", min_value=0, max_value=15, format="%d"),
                "Infection points": st.column_config.ProgressColumn("Infection points", min_value=0, max_value=10, format="%d"),
                "Main reasons": st.column_config.TextColumn(width="large"),
            })
        picked = event.selection.rows if event and event.selection else []
        if picked:
            st.session_state["selected"] = rows[picked[0]]["resident_id"]
    ids = [r["resident_id"] for r in rows]
    if st.session_state.get("selected") not in ids:
        st.session_state["selected"] = ids[0]
    with right:
        detail(ctx, ctx.resident(st.session_state["selected"]))


def detail(ctx, r):
    with ui.card():
        sex = {"F": "Female", "M": "Male"}.get(r["sex"], r["sex"])
        ui.html_block(f'<div class="who">{ui.avatar(r)}<div><h3 style="margin:0">{ui.esc(r["name"])}</h3>'
                      f'<div class="muted">{ui.esc(r["resident_id"])} · {num_text(r["age"])} yrs, {ui.esc(sex)}</div></div></div>')
        b1, b2, b3 = st.columns(3)
        if b1.button("Medical history", key="d_mh", width="stretch"):
            ui.set_sticky("mh_id", r["resident_id"]); ui.set_sticky("mh_view", "overview"); ui.go("history")
        if b2.button("Care plan", key="d_cp", width="stretch"):
            ui.set_sticky("mh_id", r["resident_id"]); ui.set_sticky("mh_view", "plan"); ui.go("history")
        if b3.button("+ Add observation", key="d_obs", width="stretch"):
            st.session_state["obs_for"] = r["resident_id"]; ui.go("data")
        place = f"{r['site']}, {r['town']}" if r.get("town") else r["site"]
        chips = [r["care_setting"], place]
        if r.get("council_pc"):
            chips.append(r["council_pc"] + (f", {r['state']}" if r.get("state") else ""))
        chips += [f"{r['sub_region']} · {r['location_type']}" + (f" · {r['mmm']}" if r.get("mmm") else ""), r["conditions"],
                  f"Data last 7 days: {round(r['completeness'] * 100)}%"]
        ui.html_block("".join(ui.chip(c) for c in chips if c))

        def reasons(items):
            if not items:
                return '<div class="muted">No contributing factors</div>'
            return "".join(f'<div style="display:flex;justify-content:space-between;border-bottom:1px solid #E2E1DA;padding:4px 0">'
                           f'<span>{ui.esc(x["t"])}</span><b>+{x["p"]}</b></div>' for x in items)
        c1, c2 = st.columns(2)
        c1.markdown("**Falls risk**")
        c1.markdown(ui.badge(r["falls_lvl"], r["falls"]) + reasons(r["f_reasons"]), unsafe_allow_html=True)
        c2.markdown("**Infection risk**")
        c2.markdown(ui.badge(r["inf_lvl"], r["inf"]) + reasons(r["i_reasons"]), unsafe_allow_html=True)

        if r["readings"].empty:
            st.caption("No wearable readings for this resident.")
        else:
            charts_spec = [("Daily steps", "steps", r["B"]["steps"], 0), ("Gait speed (m/s)", "gait_speed_mps", r["B"]["gait"], None),
                           ("Resting heart rate (bpm)", "resting_heart_rate", r["B"]["rhr"], None),
                           ("Skin temperature (°C)", "skin_temp_c", r["B"]["temp"], None)]
            for i in range(0, 4, 2):
                cols = st.columns(2)
                for col, (title, key, base, lo) in zip(cols, charts_spec[i:i + 2]):
                    col.markdown(f"**{title}**")
                    col.plotly_chart(charts.mini(r, key, base, lo), config=charts.CONFIG, theme=None, key=f"mini_{key}_{r['resident_id']}")
            st.caption("Dashed line = baseline average.")
        st.markdown("**Clinical observations**")
        if r["obs"]:
            for o in r["obs"]:
                ui.html_block(ui.obs_html(o))
        else:
            st.caption("No observations recorded.")
