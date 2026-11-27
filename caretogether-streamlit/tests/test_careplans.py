"""Checks for care plan versions, review flags and RN approval."""
from datetime import date

from caretogether import careplans as cp
from caretogether import config as C

RN = {"name": "RN Claire Hughes", "role": "Registered Nurse"}
CARE_WORKER = {"name": "Grace Lee", "role": "AIN / Care worker"}


def resident(sample, rid):
    return next(r for r in sample["scored"] if r["resident_id"] == rid)


def test_plans_and_reviews(sample):
    db, as_of = cp.load_db(), sample["as_of"]
    with_plan = [r for r in sample["scored"] if cp.current(cp.snapshots(r["resident_id"], db))]
    assert len(with_plan) == 12                                        # Irene (R013) has no plan yet
    overdue = {r["resident_id"] for r in with_plan
               if cp.review_status(cp.plan(r["resident_id"], db), cp.current(cp.snapshots(r["resident_id"], db)), as_of)["k"] == "Overdue"}
    assert overdue == {"R009", "R010", "R006"}


def test_raymond_has_a_draft_waiting(sample):
    S = cp.snapshots("R008", cp.load_db())
    assert cp.current(S)["ver"]["v"] == 4
    assert cp.draft(S)["ver"]["v"] == 5


def test_rn_approval_makes_the_draft_current(sample):
    cp.decide("R008", 5, True, RN, "Checked with Teresa")
    S = cp.snapshots("R008", cp.load_db())
    assert cp.current(S)["ver"]["v"] == 5 and cp.draft(S) is None


def test_rejection_keeps_the_old_version(sample):
    cp.decide("R008", 5, False, RN, "Please check with the physio first")
    S = cp.snapshots("R008", cp.load_db())
    assert cp.current(S)["ver"]["v"] == 4
    assert S[-1]["st"]["status"] == "Rejected"


def test_care_worker_change_is_a_draft_and_rn_change_is_approved(sample):
    r = resident(sample, "R002")
    agreed = {"name": "George Tan", "rel": "Resident", "how": "In person", "date": date.today().isoformat()}
    patch = {"add": [cp.new_item("t1", "Safety when out", "Carry the watch when going out")], "change": [], "remove": []}
    v = cp.save_version("R002", r, patch, "Scheduled review", "", agreed, CARE_WORKER, cp.load_db())
    S = cp.snapshots("R002", cp.load_db())
    assert S[-1]["st"]["status"] == "Draft" and cp.current(S)["ver"]["v"] == v["v"] - 1
    cp.decide("R002", v["v"], False, RN, "Not needed")
    v2 = cp.save_version("R002", r, patch, "Scheduled review", "", agreed, RN, cp.load_db())
    S = cp.snapshots("R002", cp.load_db())
    assert cp.current(S)["ver"]["v"] == v2["v"]
    assert cp.diff(S[-1])[0]["kind"] == "add"


def test_review_prefill_after_an_alert(sample):
    p = cp.review_prefill(resident(sample, "R009"), cp.load_db(), sample["as_of"])
    assert p["reason"] == "After an emergency alert"
    assert "Left safe zone" in p["note"]


def test_dates():
    assert cp.add_months(date(2026, 1, 31), 1) == date(2026, 3, 3)     # rolls on, like the dashboard
    assert cp.add_months(date(2026, 5, 12), 6) == date(2026, 11, 12)
    assert cp.agreed_text({"name": "Teresa Silva", "rel": "Family member", "how": "Phone", "date": "2026-11-12"}) == \
        "Teresa Silva (Family member) · phone · 12/11/2026"
