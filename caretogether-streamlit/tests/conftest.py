"""Test set-up: the tests use their own temporary database, so your caretogether.db is never touched."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["CARETOGETHER_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from caretogether import config as C, data, risk, store  # noqa: E402


@pytest.fixture
def sample():
    """Fresh demo database plus the sample data, scored."""
    store.reset_demo()
    wear, res = data.load_sample_wearables(), data.load_sample_residents()
    obs = store.get_observations()
    return {"wear": wear, "res": res, "obs": obs, "scored": risk.score_all(res, wear, obs), "as_of": risk.latest_date(wear).date()}
