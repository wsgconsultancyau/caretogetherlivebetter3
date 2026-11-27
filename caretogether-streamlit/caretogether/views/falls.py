"""Falls risk by location (or by sub-region)."""
import streamlit as st

from .. import charts, config as C, ui

GROUPS = {"location": "By location", "subregion": "By sub-region"}


def group_picker():
    return ui.sticky(st.radio, "Group by", list(GROUPS), key="group_by", format_func=GROUPS.get, horizontal=True,
                     label_visibility="collapsed")


def group_columns(groups):
    """Cards three to a row."""
    for i in range(0, len(groups), 3):
        cols = st.columns(3)
        for col, g in zip(cols, groups[i:i + 3]):
            yield col, g


def render(ctx):
    rows = ctx.rows
    ui.page_title("Falls risk by location",
                  "How many residents are at high, moderate or low falls risk in metro, regional and remote sites, or in each sub-region.")
    by = group_picker()
    with ui.card():
        st.plotly_chart(charts.risk_bar(rows, "falls_lvl", by), config=charts.CONFIG, theme=None, key="falls_chart")
    for col, g in group_columns(charts.groups_for(rows, by)):
        rs = [r for r in rows if r[g["key"]] == g["name"]]
        n = len(rs)
        cnt = {l: sum(r["falls_lvl"] == l for r in rs) for l in C.LEVELS}
        with col, ui.card():
            bar = "".join(f'<span style="width:{cnt[l] / n * 100}%;background:{C.LEVEL_COLOURS[l]}"></span>' for l in C.LEVELS) if n else ""
            ui.html_block(f'<div style="border-top:5px solid {g["col"]};margin:-4px -4px 6px;border-radius:4px"></div>'
                          f'<h4 style="margin:0">{ui.esc(g["name"])}</h4>'
                          f'<div class="muted">{n} resident{"" if n == 1 else "s"} · {len({r["site"] for r in rs})} site(s)</div>'
                          f'<div class="muted">{ui.esc(g["note"])}</div><div class="groupbar">{bar}</div>'
                          + "".join(f'<span class="badge b-{l}">{ui.ICON[l]} {l}: {cnt[l]}</span>' for l in C.LEVELS))
            flagged = sorted([r for r in rs if r["falls_lvl"] != "Low"], key=lambda r: -r["falls"])
            if not n:
                st.caption("No residents in the current filter.")
            elif flagged:
                st.markdown("**Residents to review**")
                ui.resident_rows(flagged, f"falls_{g['name']}")
            else:
                st.caption("Everyone here is at low falls risk.")
