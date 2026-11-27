"""Settings shared by the whole app: file paths, colours, risk levels and fixed lists.

Change values here (not inside the pages) so every page stays consistent.
"""
import json
import os
from pathlib import Path

# ---------- folders and files ----------
ROOT = Path(__file__).resolve().parent.parent          # the CareTogetherLiveBetter folder
DATA_DIR = ROOT / "data"
# created automatically the first time you run the app (tests use their own file through CARETOGETHER_DB)
DB_PATH = Path(os.environ.get("CARETOGETHER_DB", ROOT / "caretogether.db"))

WEARABLES_SAMPLE = DATA_DIR / "wearables_sample.csv"
RESIDENTS_SAMPLE = DATA_DIR / "residents_sample.csv"
OBSERVATIONS_SAMPLE = DATA_DIR / "observations_sample.csv"

APP_NAME = "CareTogetherLiveBetter"
TAGLINE = "Care Together for Our Seniors · early warning of falls and infection"

# ---------- risk levels and locations ----------
LEVELS = ["High", "Moderate", "Low"]
RANK = {"High": 3, "Moderate": 2, "Low": 1}
LOCATIONS = ["Metro", "Regional", "Remote"]
CARE_SETTINGS = ["Home care", "Residential"]

# ---------- colours (the same as the HTML dashboard, checked for colour-blind safety) ----------
COLOURS = {
    "navy": "#13233A", "teal": "#0F6E61", "teal_bg": "#E6F2EF", "page": "#F4F3EE",
    "line": "#E2E1DA", "ink": "#13233A", "ink_2": "#3E4C5E", "muted": "#6B7787",
    "hi": "#C8412F", "hi_bg": "#FCE7E3", "hi_ink": "#9C2416",
    "mo": "#E3A02F", "mo_bg": "#FDF1D8", "mo_ink": "#7A4E00",
    "lo": "#2F8F5B", "lo_bg": "#E2F3E8", "lo_ink": "#1F6B42",
}
LEVEL_COLOURS = {"High": COLOURS["hi"], "Moderate": COLOURS["mo"], "Low": COLOURS["lo"]}
LOCATION_COLOURS = {"Metro": "#1F6FD6", "Regional": "#D9480F", "Remote": "#0F8F7A"}

# ---------- columns the two CSV uploads must have ----------
WEAR_COLS = ["resident_id", "date", "steps", "avg_heart_rate", "resting_heart_rate",
             "gait_speed_mps", "sleep_hours", "skin_temp_c", "spo2_pct"]
RES_COLS = ["resident_id", "name", "age", "sex", "care_setting", "location_type", "site",
            "falls_last_12m", "walking_aid", "cognitive_impairment", "medication_count", "conditions"]

# ---------- observation form ----------
OBS_TYPES = ["Fall", "Near miss", "Reduced mobility", "Fever / unwell", "Confusion / behaviour change",
             "Poor food or fluid intake", "General note"]
OBS_ROLES = ["Registered Nurse", "Enrolled Nurse", "AIN / Care worker", "GP", "Physiotherapist", "Family member"]


def _load(name):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


# ---------- reference data (fictional demo data in the data folder) ----------
_sites = _load("sites.json")
SITES = _sites["sites"]                      # one dict per site: town, postcode, council, SA4, remoteness, MMM, sub-region, group
SITE_BY_NAME = {s["site"]: s for s in SITES}
STATES = _sites["states"]                    # [["NSW", "New South Wales"], ...]
SUB_REGIONS = list(dict.fromkeys(s["subRegion"] for s in SITES))
SUB_REGION_DASH = _sites["sub_region_dash"]  # line styles so the Sydney sub-regions differ by more than colour
NOT_LISTED = "Not in site list"

_mh = _load("medical_history.json")
MED_HISTORY = _mh["records"]                 # full records for R001 to R012 (R013 has none on purpose)
VISIT_TONE = _mh["visit_tone"]

_cp = _load("care_plans.json")
CP_SECTIONS = _cp["sections"]
CP_REASONS = _cp["reasons"]
CP_REL = _cp["relationships"]
CP_HOW = _cp["how_agreed"]
CARE_PLANS = _cp["plans"]                    # seeded versions for R001 to R012

_emg = _load("emergency_alerts.json")
EMG_NOW = _emg["demo_now"]                   # the demo clock for the emergency page
EMG_LOST = _emg["lost_types"]
EMG_ALERTS = _emg["alerts"]
EMG_CONSENT = _emg["consent"]

_acc = _load("staff_and_access.json")
STAFF = _acc["staff"]
REASONS = _acc["reasons"]                    # reasons to open a medical history or a location
GRANT_MINUTES = _acc["grant_minutes"]        # how long a reason lasts before you are asked again
MH_ACTION = _acc["actions"]
ACCESS_SEED = _acc["access_log_seed"]

MH = "Medical history"
EL = "Emergency location"
