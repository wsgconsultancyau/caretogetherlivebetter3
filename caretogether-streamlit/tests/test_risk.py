"""Checks for the data loading and the falls and infection risk rules."""
import io

import pandas as pd
import pytest

from caretogether import data, risk
from caretogether.data import DataError

# The same results as the HTML dashboard: (falls points, infection points, falls level, infection level)
EXPECTED = {"R007": (8, 11, "Moderate", "High"), "R003": (16, 1, "High", "Low"), "R008": (11, 1, "High", "Low"),
            "R009": (12, 0, "High", "Low"), "R011": (8, 0, "Moderate", "Low"), "R001": (7, 0, "Moderate", "Low"),
            "R013": (6, 0, "Moderate", "Low"), "R005": (5, 0, "Moderate", "Low"), "R004": (4, 1, "Low", "Low"),
            "R010": (3, 0, "Low", "Low"), "R006": (2, 0, "Low", "Low"), "R002": (0, 0, "Low", "Low"), "R012": (0, 0, "Low", "Low")}


def test_sample_data_loads(sample):
    assert len(sample["wear"]) == 171
    assert sample["wear"]["resident_id"].nunique() == 13
    assert len(sample["res"]) == 13
    assert str(sample["as_of"]) == "2026-11-13"


def test_scores_match_the_dashboard(sample):
    got = {r["resident_id"]: (r["falls"], r["inf"], r["falls_lvl"], r["inf_lvl"]) for r in sample["scored"]}
    assert got == EXPECTED


def test_highest_risk_first(sample):
    assert [r["resident_id"] for r in sample["scored"]][:3] == ["R007", "R003", "R008"]


def test_site_list_sets_location(sample):
    margaret = next(r for r in sample["scored"] if r["resident_id"] == "R001")
    assert (margaret["location_type"], margaret["sub_region"], margaret["council_pc"]) == ("Metro", "Western Sydney", "City of Parramatta · 2150")
    beryl = next(r for r in sample["scored"] if r["resident_id"] == "R009")
    assert (beryl["location_type"], beryl["mmm"]) == ("Remote", "MM7")


@pytest.mark.parametrize("points,level", [(0, "Low"), (4, "Low"), (5, "Moderate"), (8, "Moderate"), (9, "High")])
def test_falls_levels(points, level):
    assert risk.falls_level(points) == level


@pytest.mark.parametrize("points,level", [(2, "Low"), (3, "Moderate"), (4, "Moderate"), (5, "High")])
def test_infection_levels(points, level):
    assert risk.infection_level(points) == level


def test_a_new_fall_raises_the_score(sample):
    before = next(r for r in sample["scored"] if r["resident_id"] == "R002")
    obs = pd.concat([sample["obs"], pd.DataFrame([{"id": "t1", "resident_id": "R002", "date": "2026-11-13", "type": "Fall",
                                                   "role": "Registered Nurse", "temp": "38.2", "note": "test"}])])
    after = next(r for r in risk.score_all(sample["res"], sample["wear"], obs) if r["resident_id"] == "R002")
    assert after["falls"] == before["falls"] + 2          # fall or near miss in the last 7 days
    assert after["inf"] == before["inf"] + 2              # measured temperature 37.8 °C or more


def test_missing_columns_are_reported():
    with pytest.raises(DataError, match="Missing columns"):
        data.load_wearables(io.StringIO("resident_id,date\nR001,2026-11-01\n"))
