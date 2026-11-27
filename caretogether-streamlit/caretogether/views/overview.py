"""Overview: all data."""
import streamlit as st

from .. import charts, ui
from ..risk import worst_level


def render(ctx):
    rows = ctx.rows
    ui.page_title("Overview: all data", "Falls and infection risk for every resident, from wearables, resident records and staff observations.")
    n_sites = len({r["site"] for r in rows})
    comp = [r["completeness"] for r in rows]
    gaps = sum(1 for c in comp if c < 0.7)
    ui.kpis([
        ("Residents monitored", len(rows), f"{n_sites} sites", "metro"),
        ("High falls risk", sum(r["falls_lvl"] == "High" for r in rows), f"{sum(r['falls_lvl'] == 'Moderate' for r in rows)} moderate", "hi"),
        ("High infection risk", sum(r["inf_lvl"] == "High" for r in rows), f"{sum(r['inf_lvl'] == 'Moderate' for r in rows)} moderate", "mo"),
        ("Wearable data complete", f"{round(sum(comp) / len(comp) * 100)}%" if comp else "–", f"last 7 days · {gaps} with gaps", "teal"),
        ("Observations (7 days)", sum(r["obs7"] for r in rows), "entered by care staff", "plain"),
    ])

    c1, c2 = st.columns(2)
    with c1, ui.card():
        h1, h2 = st.columns([2.3, 1], vertical_alignment="center")
        h1.markdown("**Falls risk by location**  \nResidents at each risk level")
        if h2.button("Open page →", key="ov_falls"):
            ui.go("falls")
        st.plotly_chart(charts.risk_bar(rows, "falls_lvl"), config=charts.CONFIG, theme=None, key="ov_risk")
    with c2, ui.card():
        h1, h2 = st.columns([2.3, 1], vertical_alignment="center")
        h1.markdown("**Average daily steps by location**  \nMean steps per resident per day")
        if h2.button("Open page →", key="ov_steps"):
            ui.go("steps")
        st.plotly_chart(charts.steps_line(rows, ctx.wear), config=charts.CONFIG, theme=None, key="ov_steps_chart")

    c3, c4 = st.columns(2)
    with c3, ui.card():
        st.markdown("**Needs attention first**  \nHighest combined risk in the current filter")
        top = [r for r in rows if worst_level(r) != "Low"][:5]
        if top:
            ui.resident_rows(top, "ov_top")
        else:
            st.caption("No residents at moderate or high risk in this filter.")
        if st.button("See all residents →", key="ov_all"):
            ui.go("residents")
    with c4, ui.card():
        st.markdown("**Latest staff observations**  \nMost recent first")
        ids = {r["resident_id"] for r in rows}
        recent = ctx.obs[ctx.obs["resident_id"].isin(ids)].sort_values("date", ascending=False, kind="stable").head(5)
        if recent.empty:
            st.caption("No observations yet.")
        for o in recent.to_dict("records"):
            ui.html_block(ui.obs_html(o, ctx.name(o["resident_id"])))
        if st.button("Add an observation →", key="ov_add"):
            ui.go("data")
