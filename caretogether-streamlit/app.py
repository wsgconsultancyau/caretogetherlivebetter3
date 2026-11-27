"""CareTogetherLiveBetter: start here.

Run it from this folder with:
    streamlit run app.py

Every time you click something, Streamlit runs this file from the top. It:
  1. loads the data (sample files, or files you uploaded on "Data and sources"),
  2. works out every resident's falls and infection risk,
  3. shows the header, the filters and the page you picked on the left.
"""
import streamlit as st

from caretogether import access, careplans, config as C, data, emergency, risk, store, ui
from caretogether.context import Ctx
from caretogether.views import (data_sources, emergency_page, falls, history, overview, plans, residents,
                                risk_details, steps)

st.set_page_config(page_title=C.APP_NAME, page_icon=":material/monitor_heart:", layout="wide")
store.init_db()
ui.inject_css()
if st.get_option("theme.primaryColor") != "#0F6E61":   # the colour file (.streamlit/config.toml) was not loaded
    st.warning("The app's colours did not load. Close the app, then start it with run.bat, or open the CareTogetherLiveBetter "
               "folder (the one with app.py) in VS Code and run:  streamlit run app.py", icon=":material/palette:")


@st.cache_data
def sample_wearables():
    return data.load_sample_wearables()


@st.cache_data
def sample_residents():
    return data.load_sample_residents()


# ---------- 1. data ----------
ss = st.session_state
wear = ss["wear_upload"] if "wear_upload" in ss else sample_wearables()
res = ss["res_upload"] if "res_upload" in ss else sample_residents()
obs = store.get_observations()

# ---------- 2. risk scores ----------
scored = risk.score_all(res, wear, obs)
ctx = Ctx(wear=wear, res=res, obs=obs, scored=scored, as_of=risk.latest_date(wear), db=careplans.load_db(),
          alerts=emergency.alerts_with_updates(), wear_label=ss.get("wear_label", "Sample data"), res_label=ss.get("res_label", "Sample data"))

# ---------- 3. header, signed-in person (demo) and filters ----------
ui.header(ctx.as_of)
with st.sidebar:
    st.selectbox("Signed in as (demo)", [s["name"] for s in C.STAFF], key="user",
                 format_func=lambda n: f"{n} · {next(s['role'] for s in C.STAFF if s['name'] == n)}")
    st.caption("Pick who you are to try the access log and care plan approval. Registered nurses can approve care plan changes.")
ctx.rows = ui.filter_bar(scored)

# counts shown beside page names on the left
ids = {r["resident_id"] for r in ctx.rows}
n_high = sum(1 for r in ctx.rows if "High" in (r["falls_lvl"], r["inf_lvl"]))
n_plans = sum(1 for r in ctx.rows if careplans.flags(r, ctx.db, ctx.as_of_date))
n_open = sum(1 for a in ctx.alerts if a["status"] == "Open" and a["rid"] in ids)
count = lambda n: f"  ({n})" if n else ""

pages = {
    "overview": st.Page(lambda: overview.render(ctx), title="Overview: all data", icon=":material/dashboard:", url_path="overview", default=True),
    "falls": st.Page(lambda: falls.render(ctx), title="Falls risk by location", icon=":material/bar_chart:", url_path="falls"),
    "steps": st.Page(lambda: steps.render(ctx), title="Daily steps by location", icon=":material/show_chart:", url_path="steps"),
    "residents": st.Page(lambda: residents.render(ctx), title="Residents ranked by risk" + count(n_high), icon=":material/group:", url_path="residents"),
    "history": st.Page(lambda: history.render(ctx), title="Medical History", icon=":material/clinical_notes:", url_path="history"),
    "plans": st.Page(lambda: plans.render(ctx), title="Care plans" + count(n_plans), icon=":material/assignment:", url_path="plans"),
    "risk": st.Page(lambda: risk_details.render(ctx), title="Risk details", icon=":material/info:", url_path="risk"),
    "data": st.Page(lambda: data_sources.render(ctx), title="Data and sources", icon=":material/database:", url_path="data"),
    "emg": st.Page(lambda: emergency_page.render(ctx), title="Emergency Location Tracking" + count(n_open), icon=":material/location_on:", url_path="emergency"),
}
ui.PAGES.clear()
ui.PAGES.update(pages)
st.navigation(list(pages.values())).run()
