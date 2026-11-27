"""Everything a page needs, worked out once per page load and passed to the page as ctx."""
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Ctx:
    wear: pd.DataFrame            # wearable readings
    res: pd.DataFrame             # resident records (with site details)
    obs: pd.DataFrame             # staff observations (from the database)
    scored: list                  # every resident with risk scores, highest risk first
    rows: list = field(default_factory=list)   # the residents that match the filters
    as_of: pd.Timestamp = None    # date of the latest wearable reading
    db: dict = None               # care plan versions and RN decisions saved in the app
    alerts: list = None           # emergency alerts with saved updates
    wear_label: str = ""
    res_label: str = ""

    @property
    def as_of_date(self):
        return self.as_of.date()

    def name(self, rid):
        hit = self.res[self.res["resident_id"] == rid]
        return hit.iloc[0]["name"] if not hit.empty else rid

    def resident(self, rid):
        return next((r for r in self.scored if r["resident_id"] == rid), None)
