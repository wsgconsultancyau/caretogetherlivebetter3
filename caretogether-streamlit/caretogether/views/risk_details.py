"""Risk details: infection risk by location, the most common reasons, and how the scores are worked out."""
import streamlit as st

from .. import charts, ui
from ..risk import FALLS_RULES, INFECTION_RULES


def _rules(rules):
    return '<div class="rules">' + "".join(f"<div><span>{ui.esc(t)}</span><b>{ui.esc(p)}</b></div>" for t, p in rules) + "</div>"


def render(ctx):
    rows = ctx.rows
    ui.page_title("Risk details", "Everything about how risk is spread and how it is calculated.")
    c1, c2 = st.columns(2)
    with c1, ui.card():
        st.markdown("**Infection risk by location**  \nResidents at each infection risk level")
        st.plotly_chart(charts.risk_bar(rows, "inf_lvl"), config=charts.CONFIG, theme=None, key="rd_inf")
    with c2, ui.card():
        st.markdown("**Most common risk reasons**  \nHow many residents each reason applies to")
        st.plotly_chart(charts.reasons_bar(rows), config=charts.CONFIG, theme=None, key="rd_reasons")
    c3, c4 = st.columns(2)
    with c3, ui.card():
        st.markdown("**How falls risk is scored**  \nPoints add up to a total")
        ui.html_block(_rules(FALLS_RULES))
        st.caption("High = 9 points or more · Moderate = 5 to 8 · Low = under 5")
    with c4, ui.card():
        st.markdown("**How infection risk is scored**  \nPoints add up to a total")
        ui.html_block(_rules(INFECTION_RULES))
        st.caption("High = 5 points or more · Moderate = 3 to 4 · Low = under 3")
    st.caption("Recent = the last 3 days of wearable readings. Baseline = readings from 7 or more days before the latest reading.")
