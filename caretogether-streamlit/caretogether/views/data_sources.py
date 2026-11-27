"""Data and sources: add observations, upload CSV files, and see every record behind the dashboard."""
import io

import pandas as pd
import streamlit as st

from .. import access, config as C, data, store, ui
from ..data import DataError, num_text
from ..risk import top_reasons


def _risk_csv(rows):
    df = pd.DataFrame([{"resident_id": r["resident_id"], "name": r["name"], "site": r["site"], "council": r["council"], "postcode": r["postcode"],
                        "state": r["state"], "location": r["location_type"], "sub_region": r["sub_region"], "mmm": r["mmm"],
                        "falls_points": r["falls"], "falls_level": r["falls_lvl"], "infection_points": r["inf"], "infection_level": r["inf_lvl"],
                        "main_reasons": "; ".join(top_reasons(r))} for r in rows])
    return df.to_csv(index=False)


def _upload(kind, loader):
    """Read an uploaded CSV and keep it for this browser session (until 'Use sample data')."""
    f = st.session_state.get(f"up_{kind}_{st.session_state.get(f'up_{kind}_n', 0)}")
    if f is None:
        return
    try:
        st.session_state[f"{kind}_upload"] = loader(io.BytesIO(f.getvalue()))
        st.session_state[f"{kind}_label"] = f.name
        st.session_state.pop(f"{kind}_error", None)
    except DataError as e:
        st.session_state[f"{kind}_error"] = str(e)


def _use_sample(kind):
    for k in [f"{kind}_upload", f"{kind}_label", f"{kind}_error"]:
        st.session_state.pop(k, None)
    st.session_state[f"up_{kind}_n"] = st.session_state.get(f"up_{kind}_n", 0) + 1   # empties the upload box


def upload_box(kind, title, lead, loader, status):
    with ui.card():
        st.markdown(f"**{title}**  \n{lead}")
        n = st.session_state.get(f"up_{kind}_n", 0)
        st.file_uploader(f"Upload {title.lower()} (CSV)", type=["csv"], key=f"up_{kind}_{n}", on_change=_upload, args=(kind, loader))
        if st.session_state.get(f"{kind}_error"):
            st.error("⚠ " + st.session_state[f"{kind}_error"])
        st.success("✓ " + status)
        st.button("Use sample data", key=f"sample_{kind}", on_click=_use_sample, args=(kind,))


def render(ctx):
    rows = ctx.rows
    ui.page_title("Data and sources", "Add observations, upload new data, and see every record behind the dashboard.")
    st.download_button("Download risk summary (CSV)", _risk_csv(rows), file_name="risk_summary.csv", mime="text/csv")

    c1, c2, c3 = st.columns([1.3, 1, 1])
    with c1, ui.card():
        st.markdown("**Clinical observations**  \nAdded by care staff. Risk scores update straight away.")
        ids = list(ctx.res["resident_id"])
        pre = st.session_state.pop("obs_for", None)      # set by "+ Add observation" on a resident
        if pre in ids:
            st.session_state["obs_res"] = pre
        elif st.session_state.get("obs_res") not in ids:
            st.session_state["obs_res"] = ids[0]
        if st.session_state.pop("obs_clear", False):    # empty the note after an observation is saved
            st.session_state["obs_note"], st.session_state["obs_temp"] = "", ""
        with st.form("obs_form", clear_on_submit=False):
            a, b = st.columns(2)
            rid = a.selectbox("Resident", ids, key="obs_res", format_func=lambda i: f"{ctx.name(i)} ({i})")
            when = b.date_input("Date", value=ctx.as_of_date, format="DD/MM/YYYY")
            obs_type = a.selectbox("What happened", C.OBS_TYPES)
            role = b.selectbox("Recorded by (role)", C.OBS_ROLES)
            temp = a.text_input("Temperature °C (optional)", placeholder="e.g. 37.9", key="obs_temp")
            note = st.text_area("Note", placeholder="What did you observe?", key="obs_note")
            if st.form_submit_button("Add observation", type="primary"):
                t = temp.strip()
                ok = True
                if t:
                    try:
                        ok = 34 <= float(t) <= 42
                    except ValueError:
                        ok = False
                if not ok:
                    st.error("Temperature must be a number between 34 and 42 °C, or left blank.")
                else:
                    store.add_observation(rid, when.isoformat(), obs_type, role, t, note.strip(), access.current_user()["name"])
                    st.session_state["obs_clear"] = True
                    st.toast(f"Observation added for {ctx.name(rid)}. Risk scores updated.")
                    st.rerun()
        st.caption(f"{len(ctx.obs)} observations on record.")
    with c2:
        w = ctx.wear
        span = f"{w['date'].min().day} {w['date'].min():%b} – {w['date'].max().day} {w['date'].max():%b}" if not w.empty else ""
        upload_box("wear", "Wearable readings", "Daily summaries per resident from a smartwatch or wearable sensor.", data.load_wearables,
                   f"{ctx.wear_label}: {len(w)} readings · {w['resident_id'].nunique()} residents · {span}")
    with c3:
        upload_box("res", "Resident clinical records", "Profile and history, for example exported from the provider's care system.",
                   data.load_residents, f"{ctx.res_label}: {len(ctx.res)} residents across {ctx.res['site'].nunique()} sites")

    with ui.card():
        st.markdown("**Site list**  \nEach site's town, council, ABS region and remoteness, Modified Monash (MMM) category and sub-region. "
                    "The site list sets every resident's location group and sub-region.")
        counts = ctx.res["site"].value_counts()
        sites = pd.DataFrame([{"Site": s["site"], "Type": s["type"], "Council · postcode": f"{s['council']} · {s['postcode']}", "Town": s["town"],
                               "State": s["state"], "ABS SA4 region": s["sa4"], "Remoteness": s["ra"], "MMM": s["mmm"], "Sub-region": s["subRegion"],
                               "Group": s["group"], "Residents": int(counts.get(s["site"], 0))} for s in C.SITES])
        st.dataframe(sites, hide_index=True)
        unlisted = [s for s in ctx.res["site"].unique() if s not in C.SITE_BY_NAME]
        if unlisted:
            st.warning(f"{C.NOT_LISTED}: {', '.join(unlisted)}. Add them to data/sites.json to give them a sub-region.")

    with ui.card():
        st.markdown("**Residents and scores**  \nEvery resident in the current filter, with both scores.")
        st.dataframe(pd.DataFrame([{"ID": r["resident_id"], "Name": r["name"], "Age": num_text(r["age"]), "Setting": r["care_setting"],
                                    "Location": r["location_type"], "State": r["state"] or "–", "Sub-region": r["sub_region"], "MMM": r["mmm"] or "–",
                                    "Council / postcode": r["council_pc"] or "–", "Site": r["site"],
                                    "Falls": f"{ui.ICON[r['falls_lvl']]} {r['falls_lvl']} · {r['falls']}",
                                    "Infection": f"{ui.ICON[r['inf_lvl']]} {r['inf_lvl']} · {r['inf']}", "Walking aid": r["walking_aid"],
                                    "Cognition": r["cognitive_impairment"], "Meds": num_text(r["medication_count"]), "Conditions": r["conditions"]}
                                   for r in rows]), hide_index=True)

    ids = {r["resident_id"] for r in rows}
    c4, c5 = st.columns([1.4, 1])
    with c4, ui.card():
        w = ctx.wear[ctx.wear["resident_id"].isin(ids)].iloc[::-1]
        st.markdown(f"**Wearable readings**  \n{len(w)} readings for the residents in the current filter, newest first.")
        st.dataframe(pd.DataFrame({"Resident": w["resident_id"].map(ctx.name), "Date": w["date"].dt.strftime("%d %b"), "Steps": w["steps"],
                                   "Resting HR": w["resting_heart_rate"], "Gait (m/s)": w["gait_speed_mps"], "Sleep (h)": w["sleep_hours"],
                                   "Skin temp (°C)": w["skin_temp_c"], "SpO₂ (%)": w["spo2_pct"]}), hide_index=True, height=420)
    with c5, ui.card():
        o = ctx.obs[ctx.obs["resident_id"].isin(ids)].sort_values("date", ascending=False, kind="stable")
        st.markdown(f"**All staff observations**  \n{len(o)} observations, newest first.")
        for x in o.to_dict("records"):
            ui.html_block(ui.obs_html(x, ctx.name(x["resident_id"])))

    with st.expander("Reset demo data"):
        st.write("Removes every observation, care plan change, approval, alert update and access log entry added in the app, "
                 "and goes back to the sample data. The files in the data folder are not changed.")
        if st.checkbox("Yes, I want to reset the demo data") and st.button("Reset demo data"):
            store.reset_demo()
            st.session_state.clear()
            st.toast("Demo data reset")
            st.rerun()
