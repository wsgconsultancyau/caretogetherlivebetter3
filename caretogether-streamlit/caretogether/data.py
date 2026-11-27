"""Loading the two CSV files (wearable readings and resident records) and adding site details.

The site list (data/sites.json) decides each resident's location group (Metro / Regional / Remote),
state, council, postcode, sub-region and Modified Monash Model (MMM) category.
"""
import pandas as pd

from . import config as C


class DataError(Exception):
    """Raised when a CSV file is missing columns or cannot be read."""


def _read_csv(source, needed_cols):
    """Read a CSV (a file path or an uploaded file) as text, check its columns and tidy the values."""
    try:
        df = pd.read_csv(source, dtype=str, keep_default_na=False)
    except Exception as e:  # a broken or empty file
        raise DataError(f"Could not read the file: {e}") from e
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = [c for c in needed_cols if c not in df.columns]
    if missing:
        raise DataError("Missing columns: " + ", ".join(missing))
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    return df[df["resident_id"] != ""].reset_index(drop=True)


def load_wearables(source):
    """Wearable readings: one row per resident per day. Numbers become numbers; bad dates are dropped."""
    df = _read_csv(source, C.WEAR_COLS)
    df = df[df["date"].str.match(r"^\d{4}-\d{2}-\d{2}$")].copy()
    for col in C.WEAR_COLS[2:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date", kind="stable").reset_index(drop=True)


def council_key(council, postcode):
    """Text used in the 'Council / postcode' filter, for example 'City of Ryde · 2112'."""
    if not council:
        return ""
    return f"{council} · {postcode}" if postcode else council


def load_residents(source):
    """Resident records, with site details added from the site list."""
    df = _read_csv(source, C.RES_COLS)
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df["falls_last_12m"] = pd.to_numeric(df["falls_last_12m"], errors="coerce").fillna(0)
    df["medication_count"] = pd.to_numeric(df["medication_count"], errors="coerce").fillna(0)
    rows = []
    for r in df.to_dict("records"):
        site = C.SITE_BY_NAME.get(r["site"])
        if site:
            r["location_type"] = site["group"]
        elif r.get("location_type", "").lower().startswith("rural"):
            r["location_type"] = "Remote"          # older files said "Rural"
        r["sub_region"] = site["subRegion"] if site else C.NOT_LISTED
        r["mmm"] = site["mmm"] if site else ""
        r["town"] = site["town"] if site else ""
        r["state"] = site["state"] if site else str(r.get("state", "")).upper()
        r["council"] = site["council"] if site else r.get("council", "")
        r["postcode"] = site["postcode"] if site else r.get("postcode", "")
        r["council_pc"] = council_key(r["council"], r["postcode"])
        rows.append(r)
    return pd.DataFrame(rows)


def load_sample_wearables():
    return load_wearables(C.WEARABLES_SAMPLE)


def load_sample_residents():
    return load_residents(C.RESIDENTS_SAMPLE)


def num_text(x):
    """Show 91 rather than 91.0, and keep decimals when there are some."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "–"
    return str(int(x)) if float(x).is_integer() else str(x)
