# CareTogetherLiveBetter

Early warning of falls and infection for older people in Australian aged care (home care and residential care),
across metro, regional and remote sites. It combines wearable readings (steps, heart rate, gait speed, sleep,
skin temperature, SpO₂), resident records and care staff observations, and scores risk with transparent rules.

Built with **Python, Streamlit, pandas and Plotly** (like CareSignal). **All residents, staff and records are fictional demo data.**

---

## 1. Set it up on Windows (one time)

You need **Python 3.10 or newer**. To check, open **Command Prompt** and type `py --version`.
If Python is missing, install it from python.org and tick **"Add python.exe to PATH"**.

1. Unzip the project, for example to `C:\Projects\CareTogetherLiveBetter`.
2. In VS Code: **File → Open Folder…** and pick that folder.
3. Open a terminal in VS Code: **Terminal → New Terminal**.
4. Make a virtual environment (a private box for this project's packages):
   ```
   py -m venv .venv
   ```
5. Turn it on:
   ```
   .venv\Scripts\activate
   ```
   You should now see `(.venv)` at the start of the line.
   If PowerShell says scripts are disabled, run this once, then try again:
   ```
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   ```
6. Install the packages:
   ```
   pip install -r requirements.txt
   ```
7. In VS Code, press **Ctrl+Shift+P → Python: Select Interpreter** and pick the one in `.venv`.

## 2. Run the app

**Easiest:** double-click **`run.bat`** in the project folder. The first time it sets everything up for you
(steps 4 to 6 above), then it starts the app. Leave the black window open while you use the app.

**In VS Code:** press **F5** (or **Run → Start Debugging**) and pick **Run CareTogetherLiveBetter**.

**Or type it** in the VS Code terminal:
```
.venv\Scripts\activate
streamlit run app.py
```
Your browser opens at http://localhost:8501. To stop the app, click in the terminal and press **Ctrl+C**.

The street map on the Emergency page needs an internet connection.

**Colours:** the navy sidebar, white cards and teal buttons come from `.streamlit/config.toml` and the styles in
`caretogether/ui.py`. If the app ever looks plain, start it with `run.bat` (or from the folder that holds `app.py`)
and refresh the browser. The app shows a warning if the colour file did not load.

## 3. Run the tests

```
pytest
```
You should see `22 passed`. The tests use their own temporary database, so your demo data is not changed.

---

## What's in the app (pages on the left)

| Page | What it shows |
| --- | --- |
| Overview: all data | Summary tiles, falls risk and daily steps by location, who needs attention first, latest observations |
| Falls risk by location | Residents at each falls risk level, by Metro / Regional / Remote or by sub-region |
| Daily steps by location | Steps over time; residents whose activity dropped 30% or more |
| Residents ranked by risk | Every resident, highest risk first. Click a row to see the reasons, trends and observations |
| Medical History | Client overview, **Care plan**, Prescription changes, Visit history, Access log. Asks why you are opening a record first |
| Care plans | Review dates, reviews suggested by risk or alerts, drafts waiting for a registered nurse, change log |
| Risk details | Infection risk by location, most common reasons, how the points are scored |
| Data and sources | Add an observation, upload CSV files, site list, every record, download a risk summary, reset demo data |
| Emergency Location Tracking | Alerts for residents who may be lost while out (including couples), map with trail, consent, access log |

Use **Signed in as (demo)** on the left to switch person. Registered nurses can approve care plan changes;
anyone else saves a draft.

## Sample data (the `data` folder)

| File | What it holds |
| --- | --- |
| `wearables_sample.csv` | 171 daily wearable readings for 13 residents, 31 Oct – 13 Nov 2026 |
| `residents_sample.csv` | 13 resident records |
| `observations_sample.csv` | 3 staff observations to start with |
| `sites.json` | 7 sites with town, council, postcode, ABS SA4 region, remoteness, MMM category, sub-region and group |
| `medical_history.json` | Full medical records for R001 to R012 (R013 Irene has a basic record only, on purpose) |
| `care_plans.json` | Care plan versions for R001 to R012, including a draft waiting for RN approval (R008) |
| `emergency_alerts.json` | 10 alerts with trails, and location consent for each resident |
| `staff_and_access.json` | Demo staff, reasons for opening records, and sample access log entries |

To use your own data, upload CSV files on **Data and sources** with the same column names as the sample files.

## Where things you add are saved

Observations, care plan changes, RN approvals, alerts marked as found and the access log are saved in
`caretogether.db` (an SQLite database file in this folder, created the first time you run the app).
**Data and sources → Reset demo data** clears them, or close the app and delete `caretogether.db`.

## Project layout

```
CareTogetherLiveBetter/
├── app.py                  start here: loads data, scores risk, shows the pages
├── run.bat                 double-click to start (sets up the first time)
├── requirements.txt        packages to install
├── .streamlit/config.toml  colours (navy sidebar, teal buttons, warm grey page)
├── .vscode/launch.json     the F5 Run button in VS Code
├── data/                   sample data (never changed by the app)
├── caretogether/
│   ├── config.py           settings, colours and lists
│   ├── data.py             reads the CSV files and adds site details
│   ├── risk.py             the falls and infection rules   ← a machine learning model can replace score_resident() later
│   ├── store.py            the SQLite database
│   ├── access.py           signed-in person, "why are you opening this?", access log
│   ├── careplans.py        care plan versions, what changed, RN approval, review flags
│   ├── emergency.py        alert helpers (distance, times, consent)
│   ├── charts.py           Plotly charts and the map
│   ├── ui.py               shared look: header, filters, badges, tables
│   └── views/              one file per page
└── tests/                  pytest checks for the risk rules and care plans
```

## How risk is scored

Points add up. **Falls:** High = 9 or more, Moderate = 5 to 8. **Infection:** High = 5 or more, Moderate = 3 to 4.
"Recent" is the last 3 days of wearable readings; "baseline" is readings 7 or more days before the latest one.
The full list of rules is on the **Risk details** page and in `caretogether/risk.py`.

---

*Demo prototype for research. Not for clinical use. All names and details are fictional.*
