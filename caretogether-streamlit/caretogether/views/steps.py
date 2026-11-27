"""Daily steps by location (or by sub-region)."""
import streamlit as st

from .. import charts, ui
from .falls import group_columns, group_picker


def _avg(values):
    v = [x for x in values if x is not None]
    return sum(v) / len(v) if v else None


def render(ctx):
    rows = ctx.rows
    ui.page_title("Average daily steps by location", "A steady drop in steps can be an early sign of falls or infection risk.")
    by = group_picker()
    with ui.card():
        st.plotly_chart(charts.steps_line(rows, ctx.wear, by), config=charts.CONFIG, theme=None, key="steps_chart")
    for col, g in group_columns(charts.groups_for(rows, by)):
        rs = [r for r in rows if r[g["key"]] == g["name"] and r["R"]["steps"] is not None]
        recent, base = _avg([r["R"]["steps"] for r in rs]), _avg([r["B"]["steps"] for r in rs])
        with col, ui.card():
            ui.html_block(f'<div style="border-top:5px solid {g["col"]};margin:-4px -4px 6px;border-radius:4px"></div>'
                          f'<h4 style="margin:0">{ui.esc(g["name"])}</h4><div class="muted">{ui.esc(g["note"])}</div>')
            if recent is None:
                st.caption("No wearable data here in the current filter.")
                continue
            change = round((recent / base - 1) * 100) if base else None
            arrow = ("▲ +" if change and change > 0 else "▼ " if change and change < 0 else "")
            words = "lower" if change and change < 0 else "higher" if change and change > 0 else "no change"
            ui.html_block(f'<div><span class="big">{recent:,.0f}</span> <span class="muted">steps a day, last 3 days</span></div>'
                          f'<div class="muted">Baseline {base:,.0f} · <span class="{"down" if change and change < 0 else "up"}">'
                          f'{arrow}{change}% {words}</span></div>')
            down = [r for r in rs if r["step_drop"] is not None and r["step_drop"] >= 0.3]
            if down:
                st.markdown("**Activity down 30% or more**")
                ui.resident_rows(down, f"steps_{g['name']}")
            else:
                st.caption("No resident here has dropped 30% or more.")
