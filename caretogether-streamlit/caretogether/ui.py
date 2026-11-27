"""Shared look and building blocks: styles, header, filter bar, badges, tiles and tables.

Everything shown with unsafe_allow_html goes through esc() first, so text from CSV files can't break the page.
"""
import html

import streamlit as st

from . import config as C
from .risk import top_reasons, worst_level

PAGES = {}   # filled in by app.py: short name -> st.Page, so buttons can move between pages
ICON = {"High": "▲", "Moderate": "■", "Low": "●"}   # shapes as well as colours, for colour-blind users


def esc(x):
    return html.escape("" if x is None else str(x))


CSS = """
<style>
.block-container{padding-top:1.2rem;max-width:1500px}
h2.pt{font-size:1.75rem;margin:.2rem 0 0}
p.lead{color:#3E4C5E;margin:.1rem 0 .8rem;font-size:15px}
.ctl-head{background:#13233A;color:#fff;border-radius:14px;padding:14px 20px;display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:10px}
.ctl-head .t{font-size:24px;font-weight:700;letter-spacing:-.2px}
.ctl-head .sub{color:#C9D3E0;font-size:14px}
.ctl-head .asof{text-align:right;font-size:13px;color:#C9D3E0}
.ctl-head .asof b{color:#fff;font-size:14px}
.pill-demo{background:#FDF1D8;color:#7A4E00;font-size:12px;font-weight:700;border-radius:999px;padding:2px 10px;margin-left:8px;vertical-align:middle}
.badge{display:inline-flex;gap:5px;align-items:center;border-radius:999px;padding:2px 10px;font-size:13px;font-weight:600;white-space:nowrap;margin:1px 3px 1px 0}
.b-High{background:#FCE7E3;color:#9C2416}.b-Moderate{background:#FDF1D8;color:#7A4E00}.b-Low{background:#E2F3E8;color:#1F6B42}
.st{display:inline-flex;gap:5px;align-items:center;border-radius:12px;padding:2px 10px;font-size:12.5px;font-weight:700;white-space:normal;max-width:100%}
.st-Open,.st-Rejected,.st-Overdue{background:#FCE7E3;color:#9C2416}
.st-Acknowledged,.st-Pending,.st-Draft,.st-Due{background:#FDF1D8;color:#7A4E00}
.st-Resolved,.st-Declined{background:#ECEEF1;color:#4B5563}
.st-Agreed,.st-Approved,.st-Ontrack,.st-Current{background:#E2F3E8;color:#1F6B42}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:4px 0 14px}
.kpi{background:#fff;border:1px solid #E2E1DA;border-radius:14px;padding:14px 16px;border-left-width:5px}
.kpi .l{color:#3E4C5E;font-size:14px;font-weight:600}.kpi .v{font-size:30px;font-weight:700;line-height:1.15;color:#13233A}.kpi .n{color:#6B7787;font-size:13px}
.k-hi{border-left-color:#C8412F}.k-mo{border-left-color:#E3A02F}.k-lo{border-left-color:#2F8F5B}.k-teal{border-left-color:#0F6E61}.k-metro{border-left-color:#1F6FD6}.k-plain{border-left-color:#CFCEC5}
.rcard{display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap}
.who{display:flex;gap:10px;align-items:center}
.av{width:38px;height:38px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;flex:none}
.av-High{background:#FCE7E3;color:#9C2416}.av-Moderate{background:#FDF1D8;color:#7A4E00}.av-Low{background:#E2F3E8;color:#1F6B42}.av-plain{background:#E6F2EF;color:#0F6E61}
.nm{font-weight:700;color:#13233A}.why,.muted{color:#6B7787;font-size:13px}
.chip{display:inline-block;background:#F1F0EA;color:#3E4C5E;border-radius:999px;padding:2px 10px;font-size:13px;margin:2px 4px 2px 0}
.obs{border-left:3px solid #0F6E61;padding:6px 10px;margin:6px 0;background:#FAFAF7;border-radius:0 8px 8px 0;font-size:14px}
.obs .m{color:#6B7787;font-size:12.5px}
.tblwrap{overflow-x:auto}
table.tbl{width:100%;border-collapse:collapse;font-size:14px}
table.tbl th{text-align:left;color:#6B7787;font-size:12px;text-transform:uppercase;letter-spacing:.3px;border-bottom:1px solid #CFCEC5;padding:8px;white-space:nowrap}
table.tbl td{border-bottom:1px solid #E2E1DA;padding:8px;vertical-align:top}
.allergy{background:#FDF1D8;border:1px solid #F2D9A4;border-radius:12px;padding:10px 14px;display:flex;gap:16px;flex-wrap:wrap;color:#7A4E00;margin-bottom:12px}
dl.kv{margin:0}dl.kv dt{color:#6B7787;font-size:13px}dl.kv dd{margin:0 0 8px 0;font-size:14.5px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-top:8px}
.tile{background:#F4F3EE;border-radius:10px;padding:8px 10px}.tile .k{font-size:12.5px;color:#6B7787}.tile .v{font-weight:700;font-size:17px;color:#13233A}
.cond span{display:inline-block;background:#E6F2EF;color:#0A4F47;border-radius:999px;padding:2px 10px;font-size:13px;margin:2px 4px 2px 0}
.team div{display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-bottom:1px solid #E2E1DA;font-size:14px}
.team .r{color:#6B7787;text-align:right;font-size:13px}
.chg{color:#7A4E00;font-weight:600}.nochg{color:#6B7787}
ol.tl{list-style:none;padding:0;margin:0}
ol.tl li{display:grid;grid-template-columns:96px 18px 1fr;gap:10px;padding-bottom:14px}
.tl-date{color:#3E4C5E;font-weight:600;font-size:13.5px;text-align:right}
.dot{display:inline-block;width:12px;height:12px;border-radius:50%;margin-top:4px}
.d-New{background:#2F8F5B}.d-Change{background:#1F6FD6}.d-Stopped{background:#C8412F}
.tag{font-size:11.5px;font-weight:700;border-radius:999px;padding:1px 8px;margin-left:6px}
.t-New{background:#E2F3E8;color:#1F6B42}.t-Change{background:#E1ECF8;color:#153F70}.t-Stopped{background:#FCE7E3;color:#9C2416}
.med{font-weight:700}.sm{color:#6B7787;font-size:13px}
.vh{border-radius:10px;padding:8px 12px;display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.vh b{font-size:16px}
.visit{border-bottom:1px solid #E2E1DA;padding:8px 2px;font-size:14px}.visit .vo{color:#0A4F47;font-weight:600}
.flag{background:#FDF1D8;border:1px solid #F2D9A4;color:#7A4E00;border-radius:10px;padding:10px 14px;margin:8px 0;font-size:14px}
ul.cpl{margin:0;padding-left:18px}ul.cpl li{margin:4px 0;font-size:14.5px}
.mark{font-size:11px;font-weight:700;background:#E1ECF8;color:#153F70;border-radius:999px;padding:1px 7px;margin-left:6px}
ul.cpd{list-style:none;padding:0;margin:6px 0}ul.cpd li{padding:5px 0;border-top:1px dashed #E2E1DA;font-size:14px}
.cpb{font-size:10.5px;font-weight:700;border-radius:999px;padding:1px 8px;text-transform:uppercase;letter-spacing:.3px;margin-right:6px}
.cpb-add{background:#E2F3E8;color:#1F6B42}.cpb-chg{background:#E1ECF8;color:#153F70}.cpb-rm{background:#FCE7E3;color:#9C2416}.cpb-first{background:#E6F2EF;color:#0A4F47}
del{color:#9C2416;background:#FCE7E3;text-decoration:line-through}ins{text-decoration:none;color:#1F6B42;background:#E2F3E8;font-weight:600}
.ver{border:1px solid #E2E1DA;border-radius:12px;padding:10px 14px;margin:8px 0;background:#fff}
.ver.cur{border:2px solid #0F6E61}.ver.draft{border:2px dashed #E3A02F;background:#FFFCF4}.ver.rejected{background:#FBFBFA;opacity:.92}
.vhd{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.groupbar{display:flex;height:12px;border-radius:999px;overflow:hidden;margin:8px 0}
.groupbar span{display:block;height:100%}
.big{font-size:30px;font-weight:700;color:#13233A}
.up{color:#1F6B42;font-weight:700}.down{color:#9C2416;font-weight:700}
.rules div{display:flex;justify-content:space-between;border-bottom:1px solid #E2E1DA;padding:6px 0;font-size:14.5px}
.emg-log div{padding:4px 0;border-bottom:1px solid #E2E1DA;font-size:14px}
</style>
"""

# The same skin as the HTML dashboard: navy sidebar, teal highlight, white cards, teal buttons.
SKIN = """
<style>
html, body, .stApp, .stMarkdown, p, label, input, textarea, button, h1, h2, h3, h4, li, td, th {
  font-family: "Helvetica Neue", Arial, Helvetica, sans-serif;
}
[data-testid="stSidebar"]{background:#13233A}
[data-testid="stSidebarNavLink"]{border-radius:12px;padding:9px 12px;margin:2px 0}
[data-testid="stSidebarNavLink"] span{color:#C9D6E2 !important;font-weight:600;font-size:14.5px;white-space:normal !important;overflow:visible !important;text-overflow:clip !important;line-height:1.3}
[data-testid="stSidebarNavLink"]:hover{background:#1E3554 !important}
[data-testid="stSidebarNavLink"][aria-current="page"]{background:#0F6E61 !important}
[data-testid="stSidebarNavLink"][aria-current="page"] span{color:#FFFFFF !important}
[data-testid="stSidebarNavSeparator"]{border-color:#2C4466}
[data-testid="stSidebarUserContent"] label, [data-testid="stSidebarUserContent"] p{color:#C9D6E2 !important}
[class*="st-key-card"]{background:#FFFFFF;border:1px solid #E2E1DA !important;border-radius:14px !important;
  box-shadow:0 1px 2px rgba(19,35,58,.06),0 4px 14px rgba(19,35,58,.06);padding:18px 20px !important}
[data-testid="stBaseButton-secondary"],[data-testid="stBaseButton-secondaryFormSubmit"],[data-testid="stDownloadButton"] button{
  background:#FFFFFF !important;border:1px solid #0F6E61 !important;color:#0F6E61 !important;border-radius:10px !important;font-weight:700}
[data-testid="stBaseButton-secondary"] p,[data-testid="stBaseButton-secondaryFormSubmit"] p,[data-testid="stDownloadButton"] button p{color:#0F6E61 !important;font-weight:700}
[data-testid="stBaseButton-primary"],[data-testid="stBaseButton-primaryFormSubmit"]{
  background:#0F6E61 !important;border:1px solid #0F6E61 !important;border-radius:10px !important}
[data-testid="stBaseButton-primary"] p,[data-testid="stBaseButton-primaryFormSubmit"] p{color:#FFFFFF !important;font-weight:700}
[data-testid="stBaseButton-secondary"] p,[data-testid="stBaseButton-primary"] p,[data-testid="stDownloadButton"] button p{font-size:14px;white-space:nowrap}
[data-testid="stBaseButton-secondary"]:hover,[data-testid="stBaseButton-primary"]:hover{filter:brightness(.96)}
</style>
"""


def inject_css():
    st.markdown(CSS + SKIN, unsafe_allow_html=True)
    st.session_state["_cards"] = 0


def card():
    """A white rounded card with a soft shadow (a bordered container with a name the styles can find)."""
    st.session_state["_cards"] = st.session_state.get("_cards", 0) + 1
    return st.container(border=True, key=f"card_{st.session_state['_cards']}")


def go(name):
    """Move to another page (for buttons such as 'Open' or 'Start review')."""
    st.switch_page(PAGES[name])


# ---------- remembering choices across pages ----------
def sticky(widget, label, options, key, default=None, **kwargs):
    """A selectbox or radio that keeps its value when you move to another page and back."""
    keep = f"_keep_{key}"
    if st.session_state.get(keep) not in options:
        st.session_state[keep] = default if default in options else options[0]
    st.session_state[key] = st.session_state[keep]

    def _save():
        st.session_state[keep] = st.session_state[key]
    return widget(label, options, key=key, on_change=_save, **kwargs)


def set_sticky(key, value):
    st.session_state[f"_keep_{key}"] = value


# ---------- header and titles ----------
def header(as_of):
    when = f"{as_of:%a}, {as_of.day} {as_of:%b %Y}"
    st.markdown(f"""<div class="ctl-head"><div><div class="t">{esc(C.APP_NAME)}<span class="pill-demo">DEMO DATA</span></div>
      <div class="sub">{esc(C.TAGLINE)}</div></div>
      <div class="asof">Latest wearable reading<br><b>{esc(when)}</b></div></div>""", unsafe_allow_html=True)


def page_title(title, lead=""):
    st.markdown(f'<h2 class="pt">{esc(title)}</h2>' + (f'<p class="lead">{esc(lead)}</p>' if lead else ""), unsafe_allow_html=True)


def html_block(markup):
    st.markdown(markup, unsafe_allow_html=True)


# ---------- small pieces ----------
def badge(level, pts=None, label=None):
    text = f"{label}: {level}" if label else level
    if pts is not None:
        text += f" · {pts} pt{'' if pts == 1 else 's'}"
    return f'<span class="badge b-{level}">{ICON[level]} {esc(text)}</span>'


def status_chip(status, text=None):
    cls = {"Due soon": "Due", "On track": "Ontrack"}.get(status, status)
    icon = {"Open": "▲", "Rejected": "▲", "Overdue": "▲", "Acknowledged": "■", "Pending": "■", "Draft": "■", "Due soon": "■"}.get(status, "●")
    return f'<span class="st st-{esc(cls)}">{icon} {esc(text or status)}</span>'


def chip(text):
    return f'<span class="chip">{esc(text)}</span>'


def avatar(r, plain=False):
    lvl = "plain" if plain else worst_level(r)
    initials = "".join(w[0] for w in str(r["name"]).split()[:2]).upper()
    return f'<div class="av av-{lvl}" aria-hidden="true">{esc(initials)}</div>'


def resident_card(r, reasons=2):
    why = " · ".join(top_reasons(r, reasons)) or "No notable signals"
    return (f'<div class="rcard"><div class="who">{avatar(r)}<div><div class="nm">{esc(r["name"])}</div>'
            f'<div class="why">{esc(why)}</div></div></div><div>{badge(r["falls_lvl"])}{badge(r["inf_lvl"])}</div></div>')


def resident_rows(rows, key_prefix, reasons=2):
    """Resident cards, each with an Open button that shows the resident on 'Residents ranked by risk'."""
    for r in rows:
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(resident_card(r, reasons), unsafe_allow_html=True)
        if c2.button("Open", key=f"{key_prefix}_{r['resident_id']}"):
            open_resident(r["resident_id"])


def open_resident(rid):
    st.session_state["selected"] = rid
    st.session_state.pop("res_table", None)   # forget an older row click in the table
    go("residents")


def kpis(items):
    """items: (label, value, note, tone) with tone hi / mo / lo / teal / metro / plain."""
    cards = "".join(f'<div class="kpi k-{tone}"><div class="l">{esc(l)}</div><div class="v">{esc(v)}</div><div class="n">{esc(n)}</div></div>'
                    for l, v, n, tone in items)
    st.markdown(f'<div class="kpis">{cards}</div>', unsafe_allow_html=True)


def obs_html(o, name=None):
    temp = f" · {esc(o['temp'])} °C" if o.get("temp") else ""
    who = f" · {esc(name)}" if name else ""
    return (f'<div class="obs"><b>{esc(o["type"])}</b>{who}{temp}<div>{esc(o.get("note")) or "No note"}</div>'
            f'<div class="m">{esc(pretty_date(o["date"]))} · {esc(o["role"])}</div></div>')


def pretty_date(s):
    """'2026-11-13' -> '13 Nov'."""
    import pandas as pd
    try:
        d = pd.Timestamp(s)
        return f"{d.day} {d:%b}"
    except (ValueError, TypeError):
        return str(s)


def table(headers, rows_html):
    """A simple HTML table. rows_html is a list of lists of HTML cell contents (already escaped)."""
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows_html)
    st.markdown(f'<div class="tblwrap"><table class="tbl"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>',
                unsafe_allow_html=True)


def log_table(entries, resident_name, show_res=True, show_area=False):
    from .emergency import fmt_when
    if not entries:
        st.caption("No access recorded yet.")
        return
    headers = ["When", "Who"] + (["Resident"] if show_res else []) + ["What", "Why opened", "Comment"]
    rows = []
    for x in entries:
        what = ("Emergency location · " if show_area and x["area"] == C.EL else "") + esc(x["action"])
        if x.get("alert"):
            what += " " + chip(x["alert"])
        row = [f'<span style="white-space:nowrap">{esc(fmt_when(x["t"]))}</span>', f'<b>{esc(x["user"])}</b><div class="muted">{esc(x["role"])}</div>']
        if show_res:
            row.append(esc(resident_name(x["rid"])) if x["rid"] else "All residents in view")
        row += [what, esc(x.get("reason") or "–"), esc(x.get("comment") or "")]
        rows.append(row)
    table(headers, rows)


# ---------- filter bar ----------
FILTER_KEYS = {"f_set": "", "f_loc": "", "f_state": "", "f_sub": "", "f_council": "", "f_q": ""}


def _clear_filters():
    for k, v in FILTER_KEYS.items():
        st.session_state[k] = v


def filter_bar(scored):
    """The filters under the header. Returns the residents that match."""
    for k, v in FILTER_KEYS.items():
        st.session_state.setdefault(k, v)
    have_c = {r["council_pc"] for r in scored if r["council_pc"]}
    order = [f"{s['council']} · {s['postcode']}" for s in C.SITES]
    councils = [c for c in order if c in have_c] + sorted(c for c in have_c if c not in order)
    have_s = {r["sub_region"] for r in scored}
    subs = [s for s in C.SUB_REGIONS if s in have_s] + sorted(s for s in have_s if s not in C.SUB_REGIONS)
    state_names = dict(C.STATES)
    in_state = {r["state"] for r in scored}
    for key, opts in [("f_council", councils), ("f_sub", subs)]:
        if st.session_state[key] not in [""] + opts:
            st.session_state[key] = ""

    with card():
        c = st.columns([1.1, 1.1, 1.3, 1.25, 1.55, 1.2, 1.0], vertical_alignment="bottom")
        c[0].selectbox("Care setting", ["", *C.CARE_SETTINGS], key="f_set", format_func=lambda x: x or "All settings")
        c[1].selectbox("Location", ["", *C.LOCATIONS], key="f_loc", format_func=lambda x: x or "All locations")
        c[2].selectbox("State", ["", *state_names], key="f_state",
                       format_func=lambda x: "All states" if not x else f"{state_names[x]} ({x})" + ("" if x in in_state else " – no sites yet"))
        c[3].selectbox("Sub-region", ["", *subs], key="f_sub", format_func=lambda x: x or "All sub-regions")
        c[4].selectbox("Council / postcode", ["", *councils], key="f_council", format_func=lambda x: x or "All councils")
        c[5].text_input("Search", key="f_q", placeholder="Type a name or ID")
        c[6].button("Clear", on_click=_clear_filters, width="stretch", help="Clear all filters")

    ss = st.session_state
    q = ss["f_q"].strip().lower()
    return [r for r in scored
            if (not ss["f_set"] or r["care_setting"] == ss["f_set"]) and (not ss["f_loc"] or r["location_type"] == ss["f_loc"])
            and (not ss["f_state"] or r["state"] == ss["f_state"]) and (not ss["f_sub"] or r["sub_region"] == ss["f_sub"])
            and (not ss["f_council"] or r["council_pc"] == ss["f_council"])
            and (not q or q in f"{r['name']} {r['resident_id']}".lower())]
