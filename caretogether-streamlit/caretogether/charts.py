"""Plotly charts and the emergency map.

Colours: the risk levels and the three location groups use the dashboard's colour-blind-safe colours.
Sydney sub-regions share one colour, so they also get different line styles (solid, dashed, dotted).
"""
import math

import pandas as pd
import plotly.graph_objects as go

from . import config as C
from .emergency import initials, last_point

CONFIG = {"displayModeBar": False, "responsive": True}   # pass to st.plotly_chart(config=...)
DASH = {(): "solid", (8, 5): "dash", (2, 4): "dot"}


def _style(fig, height=340, legend=True):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=10, r=10, t=10, b=10),
                      font=dict(family="Helvetica Neue, Arial, Helvetica, sans-serif", size=13, color=C.COLOURS["ink_2"]),
                      showlegend=legend, legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="left", x=0),
                      hoverlabel=dict(bgcolor=C.COLOURS["navy"], font_color="white"),
                      paper_bgcolor="white", plot_bgcolor="white")
    fig.update_xaxes(showgrid=False, linecolor="#CFCEC5")
    fig.update_yaxes(gridcolor=C.COLOURS["line"], zeroline=False)
    return fig


def groups_for(rows, by):
    """The groups for the location charts: Metro / Regional / Remote, or each sub-region."""
    if by != "subregion":
        return [{"name": L, "key": "location_type", "col": C.LOCATION_COLOURS[L], "dash": "solid",
                 "note": ", ".join(dict.fromkeys(s["subRegion"] for s in C.SITES if s["group"] == L))} for L in C.LOCATIONS]
    extra = [x for x in dict.fromkeys(r["sub_region"] for r in rows) if x not in C.SUB_REGIONS]
    out = []
    for name in C.SUB_REGIONS + extra:
        sites = [s for s in C.SITES if s["subRegion"] == name]
        group = sites[0]["group"] if sites else ""
        note = (f"{group} · {', '.join(dict.fromkeys(s['town'] for s in sites))} · {sites[0]['mmm']}" if sites
                else "Site not in the site list")
        out.append({"name": name, "key": "sub_region", "col": C.LOCATION_COLOURS.get(group, C.COLOURS["muted"]),
                    "dash": DASH.get(tuple(C.SUB_REGION_DASH.get(name, [])), "solid"), "note": note})
    return out


def risk_bar(rows, field, by="location"):
    """Stacked bars: how many residents are at each risk level in each group."""
    G = groups_for(rows, by)
    fig = go.Figure()
    for lvl in C.LEVELS:
        counts = [sum(1 for r in rows if r[g["key"]] == g["name"] and r[field] == lvl) for g in G]
        fig.add_bar(name=f"{lvl} risk", x=[g["name"] for g in G], y=counts, marker_color=C.LEVEL_COLOURS[lvl],
                    marker_line=dict(color="white", width=2), hovertemplate="%{x}: %{y}<extra>" + lvl + " risk</extra>")
    fig.update_layout(barmode="stack", bargap=0.45)
    fig.update_yaxes(title_text="Residents", dtick=1, rangemode="tozero")
    return _style(fig)


def steps_line(rows, wear, by="location"):
    """Average daily steps per resident in each group, day by day."""
    G = groups_for(rows, by)
    if not rows or wear.empty:
        return _style(go.Figure())
    group_of = {r["resident_id"]: r[G[0]["key"]] for r in rows}
    w = wear[wear["resident_id"].isin(group_of)].copy()
    w["group"] = w["resident_id"].map(group_of)
    dates = sorted(w["date"].unique())
    fig = go.Figure()
    for g in G:
        means = w[w["group"] == g["name"]].groupby("date")["steps"].mean()
        ys = [round(means[d]) if d in means.index and pd.notna(means[d]) else None for d in dates]
        if all(v is None for v in ys):
            continue
        fig.add_scatter(name=g["name"], x=[pd.Timestamp(d) for d in dates], y=ys, mode="lines", connectgaps=True,
                        line=dict(color=g["col"], width=3, dash=g["dash"], shape="spline", smoothing=0.6),
                        hovertemplate="%{x|%-d %b}: %{y:,} steps<extra>" + g["name"] + "</extra>")
    fig.update_xaxes(tickformat="%-d %b")
    fig.update_yaxes(title_text="Steps per day")
    fig.update_layout(hovermode="x unified")
    return _style(fig)


def reasons_bar(rows):
    """How many residents each risk reason applies to."""
    counts = {}
    for r in rows:
        for k in dict.fromkeys(x["k"] for x in r["f_reasons"] + r["i_reasons"]):
            counts[k] = counts.get(k, 0) + 1
    items = sorted(counts.items(), key=lambda kv: -kv[1])
    fig = go.Figure(go.Bar(x=[v for _, v in items][::-1], y=[k for k, _ in items][::-1], orientation="h",
                           marker_color=C.COLOURS["teal"], hovertemplate="%{y}: %{x} residents<extra></extra>"))
    fig.update_xaxes(title_text="Residents", dtick=1, gridcolor=C.COLOURS["line"], showgrid=True)
    fig.update_yaxes(showgrid=False)
    return _style(fig, height=max(320, len(items) * 30 + 60), legend=False)


def mini(r, col, base, lo=None):
    """A small trend chart for one resident, with the baseline average as a dashed line."""
    d = r["readings"]
    fig = go.Figure(go.Scatter(x=d["date"], y=d[col], mode="lines+markers", line=dict(color=C.COLOURS["teal"], width=2.5),
                               marker=dict(size=5), name="Value", hovertemplate="%{x|%-d %b}: %{y}<extra></extra>"))
    if base is not None:
        fig.add_scatter(x=[d["date"].min(), d["date"].max()], y=[base, base], mode="lines", name="Baseline",
                        line=dict(color=C.COLOURS["muted"], dash="dash", width=1.5), hoverinfo="skip")
    fig.update_xaxes(tickformat="%-d %b", nticks=5)
    fig.update_yaxes(nticks=4)
    if lo is not None:
        fig.update_yaxes(rangemode="tozero")
    return _style(fig, height=190, legend=False)


# ---------- emergency map ----------
STATUS_COLOURS = {"Open": C.COLOURS["hi"], "Acknowledged": C.COLOURS["mo"], "Resolved": "#7A8594"}
NSW_CENTRE = {"lat": -32.5, "lon": 147.5}


def _circle(lat, lon, radius_m, n=72):
    """Points around a circle of radius_m metres, to draw safe zones and position accuracy."""
    dlat = radius_m / 111320
    dlon = radius_m / (111320 * math.cos(math.radians(lat)))
    ts = [2 * math.pi * i / n for i in range(n + 1)]
    return [lat + dlat * math.cos(t) for t in ts], [lon + dlon * math.sin(t) for t in ts]


def _view(points):
    """Centre and zoom that fit all the points."""
    if not points:
        return NSW_CENTRE, 5
    lats, lons = [p[0] for p in points], [p[1] for p in points]
    centre = {"lat": (min(lats) + max(lats)) / 2, "lon": (min(lons) + max(lons)) / 2}
    span = max(max(lats) - min(lats), (max(lons) - min(lons)) * 0.8, 0.002)
    return centre, max(3, min(16.5, math.log2(360 / span) - 1.2))


def alert_map(alerts, a, hidden, resident_name):
    """The emergency map: every alert's last position, or one alert with its trail, home and safe zone."""
    fig, pts = go.Figure(), []
    metro, remote = C.LOCATION_COLOURS["Metro"], C.LOCATION_COLOURS["Remote"]
    if hidden:
        fig.add_scattermap(lat=[NSW_CENTRE["lat"]], lon=[NSW_CENTRE["lon"]], mode="markers", marker=dict(size=1, opacity=0),
                           hoverinfo="skip", showlegend=False)
    elif not a:
        for x in alerts:
            lp = last_point(x.get("trail"))
            if not lp:
                continue
            pts.append((lp[1], lp[2]))
            fig.add_scattermap(lat=[lp[1]], lon=[lp[2]], mode="markers+text", text=[initials(resident_name(x["rid"]))],
                               marker=dict(size=26, color=STATUS_COLOURS.get(x["status"], "#7A8594")),
                               textfont=dict(color="white", size=11), name=f"{x['id']} · {x['status']}",
                               hovertemplate=f"{resident_name(x['rid'])} · {x['type']} · {x['status']}<extra></extra>", showlegend=False)
    else:
        h = a.get("home")
        if h:
            pts.append((h["lat"], h["lon"]))
            if a.get("zone"):
                la, lo = _circle(h["lat"], h["lon"], a["zone"])
                fig.add_scattermap(lat=la, lon=lo, mode="lines", line=dict(color=remote, width=2), name=f"Safe zone ({a['zone']} m)",
                                   hoverinfo="skip")
            fig.add_scattermap(lat=[h["lat"]], lon=[h["lon"]], mode="markers+text", text=["⌂"], marker=dict(size=24, color=C.COLOURS["navy"]),
                               textfont=dict(color="white", size=14), name="Home or site", hovertemplate=f"{h['label']}<extra></extra>")
        for lm in a.get("landmarks", []):
            pts.append((lm["lat"], lm["lon"]))
            fig.add_scattermap(lat=[lm["lat"]], lon=[lm["lon"]], mode="markers+text", text=[lm["label"]], textposition="middle right",
                               marker=dict(size=9, color="#3E4C5E"), textfont=dict(size=12, color=C.COLOURS["ink"]),
                               showlegend=False, hovertemplate=f"{lm['label']}<extra></extra>")
        names = [str(resident_name(a["rid"])).split(" ")[0], str(a.get("companion", "")).split(" ")[0]]
        for trail, colour, who in [(a.get("trail"), metro, names[0]), (a.get("trail2"), remote, names[1])]:
            if not trail:
                continue
            pts += [(p[1], p[2]) for p in trail]
            fig.add_scattermap(lat=[p[1] for p in trail], lon=[p[2] for p in trail], mode="lines+markers",
                               line=dict(color=colour, width=4), marker=dict(size=8, color=colour), name=f"{who}'s trail",
                               text=[f"{who} · {p[0]}" + (f" · {p[3]}" if len(p) > 3 and p[3] else "") for p in trail],
                               hovertemplate="%{text}<extra></extra>")
        lp, lp2 = last_point(a.get("trail")), last_point(a.get("trail2"))
        if lp and a.get("last", {}).get("acc"):
            la, lo = _circle(lp[1], lp[2], a["last"]["acc"])
            fig.add_scattermap(lat=la, lon=lo, mode="lines", fill="toself", fillcolor="rgba(200,65,47,0.12)",
                               line=dict(color=STATUS_COLOURS.get(a["status"], "#7A8594"), width=1), name="Position accuracy", hoverinfo="skip")
        if lp:
            fig.add_scattermap(lat=[lp[1]], lon=[lp[2]], mode="markers+text", text=[initials(resident_name(a["rid"]))],
                               marker=dict(size=30, color=C.COLOURS["hi"] if a["status"] == "Open" else metro),
                               textfont=dict(color="white", size=12), name=f"{names[0]}: last known position",
                               hovertemplate=f"{names[0]}: last known position at {lp[0]}<extra></extra>")
        if lp2:
            fig.add_scattermap(lat=[lp2[1] - 0.00012], lon=[lp2[2] + 0.00018], mode="markers+text", text=[initials(a["companion"])],
                               marker=dict(size=22, color=remote), textfont=dict(color="white", size=10),
                               name=f"{names[1]}: last known position", hovertemplate=f"{names[1]}: last known position at {lp2[0]}<extra></extra>")
    centre, zoom = _view(pts)
    fig.update_layout(map=dict(style="carto-voyager", center=centre, zoom=zoom), height=460, margin=dict(l=0, r=0, t=0, b=0),
                      showlegend=bool(a) and not hidden, legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.9)"),
                      hoverlabel=dict(bgcolor=C.COLOURS["navy"], font_color="white"))
    return fig, len(pts)
