"""The falls and infection risk rules.

These are the same transparent, point-based rules as the HTML dashboard. Each rule adds points and
a reason you can read. Later, a machine learning model can replace score_resident() and keep the
same output, so the pages do not need to change.

Time windows (counted back from the latest wearable reading):
  recent   = the last 3 days (0 to 2 days back)
  baseline = readings 7 or more days back (if there are none, every reading that is not recent)
  last 7 days for observations = 0 to 6 days back (and 1 day ahead, in case of time zones)
"""
import math
import re
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

from . import config as C
from .data import num_text

FALLS_RULES = [
    ("Age 85 or over", "+1"), ("1 fall in last 12 months", "+2"), ("2 or more falls in last 12 months", "+3"),
    ("Uses a walking aid", "+1"), ("Mild / moderate cognitive impairment", "+1 / +2"),
    ("5–8 / 9 or more medications", "+1 / +2"), ("Gait under 0.8 / under 0.6 m/s (last 3 days)", "+2 / +3"),
    ("Gait down 0.1 m/s or more from baseline", "+1"), ("Daily steps down 30% or more", "+2"),
    ("Fall or near miss recorded in last 7 days", "+2"), ("Reduced mobility recorded", "+1"),
]
INFECTION_RULES = [
    ("Skin temperature up 0.3 / 0.5 °C or more", "+1 / +2"), ("Resting heart rate up 6 / 10 bpm or more", "+1 / +2"),
    ("SpO₂ under 94% (last 3 days)", "+2"), ("SpO₂ down 3 points from baseline", "+1"),
    ("Daily steps down 30% or more", "+1"), ("Condition that raises infection risk (UTI, COPD, CKD)", "+1"),
    ("Fever, unwell or confusion recorded in last 7 days", "+2"), ("Measured temperature 37.8 °C or higher", "+2"),
]


def falls_level(points):
    return "High" if points >= 9 else "Moderate" if points >= 5 else "Low"


def infection_level(points):
    return "High" if points >= 5 else "Moderate" if points >= 3 else "Low"


def _round(x):
    """Round halves up (2.5 -> 3), like the dashboard. Python's round() would give 2."""
    return math.floor(x + 0.5)


def _fixed(x, places):
    """Format a number with a fixed number of decimals, rounding halves up."""
    return str(Decimal(x).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


def _avg(values):
    vals = [float(v) for v in values if v is not None and not pd.isna(v)]
    return sum(vals) / len(vals) if vals else None


def _num(v):
    try:
        x = float(v)
        return None if math.isnan(x) else x
    except (TypeError, ValueError):
        return None


def latest_date(wear):
    """The date of the newest wearable reading (risk scores are worked out as of this day)."""
    if wear is None or wear.empty:
        return pd.Timestamp.today().normalize()
    return wear["date"].max()


def score_resident(res, wear, obs, as_of):
    """Work out the falls and infection points for one resident.

    res  = one resident (a dict)
    wear = all wearable readings (DataFrame)
    obs  = all observations (DataFrame with resident_id, date, type, temp, ...)
    """
    rid = res["resident_id"]
    mine = wear[wear["resident_id"] == rid]
    days_back = (as_of - mine["date"]).dt.days
    recent = mine[days_back <= 2]
    base = mine[days_back >= 7]
    if base.empty:
        base = mine[days_back > 2]

    def means(df):
        return {"steps": _avg(df["steps"]), "gait": _avg(df["gait_speed_mps"]), "rhr": _avg(df["resting_heart_rate"]),
                "temp": _avg(df["skin_temp_c"]), "spo2": _avg(df["spo2_pct"])}
    R, B = means(recent), means(base)

    my_obs = obs[obs["resident_id"] == rid].copy() if not obs.empty else obs
    if not my_obs.empty:
        my_obs["_back"] = (as_of - pd.to_datetime(my_obs["date"], errors="coerce")).dt.days
        obs7 = my_obs[(my_obs["_back"] <= 6) & (my_obs["_back"] >= -1)]
    else:
        obs7 = my_obs
    obs7_types = set(obs7["type"]) if not obs7.empty else set()

    F, I = [], []
    def add_f(p, text, key): F.append({"p": p, "t": text, "k": key})
    def add_i(p, text, key): I.append({"p": p, "t": text, "k": key})

    age = _num(res.get("age"))
    if age is not None and age >= 85:
        add_f(1, f"Age {num_text(age)}", "Age 85+")
    falls12 = _num(res.get("falls_last_12m")) or 0
    if falls12 >= 2:
        add_f(3, f"{num_text(falls12)} falls in last 12 months", "Past falls")
    elif falls12 == 1:
        add_f(2, "1 fall in last 12 months", "Past falls")
    if str(res.get("walking_aid", "")).lower().startswith("y"):
        add_f(1, "Uses walking aid", "Walking aid")
    cog = str(res.get("cognitive_impairment", "")).lower()
    if cog.startswith("mod") or cog.startswith("sev"):
        add_f(2, "Moderate cognitive impairment", "Cognitive impairment")
    elif cog.startswith("mild"):
        add_f(1, "Mild cognitive impairment", "Cognitive impairment")
    meds = _num(res.get("medication_count")) or 0
    if meds >= 9:
        add_f(2, f"Polypharmacy ({num_text(meds)} medications)", "5+ medications")
    elif meds >= 5:
        add_f(1, f"{num_text(meds)} medications", "5+ medications")
    if R["gait"] is not None:
        if R["gait"] < 0.6:
            add_f(3, f"Very slow gait ({_fixed(R['gait'], 2)} m/s)", "Slow gait")
        elif R["gait"] < 0.8:
            add_f(2, f"Slow gait ({_fixed(R['gait'], 2)} m/s)", "Slow gait")
    if R["gait"] is not None and B["gait"] is not None and B["gait"] - R["gait"] >= 0.1:
        add_f(1, f"Gait slowed by {_fixed(B['gait'] - R['gait'], 2)} m/s", "Gait slowing")
    step_drop = 1 - R["steps"] / B["steps"] if R["steps"] is not None and B["steps"] else None
    if step_drop is not None and step_drop >= 0.3:
        pct = _round(step_drop * 100)
        add_f(2, f"Activity down {pct}%", "Activity down 30%+")
        add_i(1, f"Activity down {pct}%", "Activity down 30%+")
    if obs7_types & {"Fall", "Near miss"}:
        add_f(2, "Fall or near miss in last 7 days", "Recent fall or near miss")
    if "Reduced mobility" in obs7_types:
        add_f(1, "Reduced mobility recorded", "Reduced mobility noted")
    if R["temp"] is not None and B["temp"] is not None:
        d = R["temp"] - B["temp"]
        if d >= 0.5:
            add_i(2, f"Skin temp up {_fixed(d, 1)} °C", "Skin temp up")
        elif d >= 0.3:
            add_i(1, f"Skin temp up {_fixed(d, 1)} °C", "Skin temp up")
    if R["rhr"] is not None and B["rhr"] is not None:
        d = R["rhr"] - B["rhr"]
        if d >= 10:
            add_i(2, f"Resting HR up {_round(d)} bpm", "Resting HR up")
        elif d >= 6:
            add_i(1, f"Resting HR up {_round(d)} bpm", "Resting HR up")
    if R["spo2"] is not None:
        if R["spo2"] < 94:
            add_i(2, f"Low SpO₂ ({_fixed(R['spo2'], 0)}%)", "Low or falling SpO₂")
        elif B["spo2"] is not None and B["spo2"] - R["spo2"] >= 3:
            add_i(1, f"SpO₂ down {_round(B['spo2'] - R['spo2'])} points", "Low or falling SpO₂")
    if re.search(r"uti|copd|ckd|pneumonia", str(res.get("conditions", "")), re.IGNORECASE):
        add_i(1, "Condition that raises infection risk", "Infection-prone condition")
    if obs7_types & {"Fever / unwell", "Confusion / behaviour change"}:
        add_i(2, "Fever, unwell or confusion recorded", "Fever or confusion noted")
    max_t = max([_num(t) or 0 for t in obs7["temp"]] + [0]) if not obs7.empty else 0
    if max_t >= 37.8:
        add_i(2, f"Measured temperature {_fixed(max_t, 1)} °C", "Temperature 37.8 °C+")

    f_pts, i_pts = sum(x["p"] for x in F), sum(x["p"] for x in I)
    last7_days = mine[days_back <= 6]["date"].nunique()
    obs_list = my_obs.drop(columns=["_back"], errors="ignore").sort_values("date", ascending=False, kind="stable").to_dict("records") if not my_obs.empty else []
    return {
        **res,
        "falls": f_pts, "inf": i_pts,
        "falls_lvl": falls_level(f_pts), "inf_lvl": infection_level(i_pts),
        "f_reasons": sorted(F, key=lambda x: -x["p"]), "i_reasons": sorted(I, key=lambda x: -x["p"]),
        "completeness": last7_days / 7,
        "last_reading": mine["date"].max() if not mine.empty else None,
        "readings": mine.reset_index(drop=True), "obs": obs_list, "obs7": len(obs7),
        "R": R, "B": B, "step_drop": step_drop,
    }


def score_all(residents, wear, obs):
    """Score every resident, highest risk first (then most points first)."""
    as_of = latest_date(wear)
    scored = [score_resident(r, wear, obs, as_of) for r in residents.to_dict("records")]
    return sorted(scored, key=lambda r: (-max(C.RANK[r["falls_lvl"]], C.RANK[r["inf_lvl"]]), -(r["falls"] + r["inf"])))


def worst_level(r):
    return r["falls_lvl"] if C.RANK[r["falls_lvl"]] >= C.RANK[r["inf_lvl"]] else r["inf_lvl"]


def top_reasons(r, n=3):
    """The main reasons, led by whichever risk is higher."""
    if C.RANK[r["inf_lvl"]] > C.RANK[r["falls_lvl"]]:
        picks = r["i_reasons"][:2] + r["f_reasons"][:1]
    else:
        picks = r["f_reasons"][:2] + r["i_reasons"][:1]
    return [x["t"] for x in picks[:n]]
