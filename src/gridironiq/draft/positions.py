from __future__ import annotations

# Map combine / nflverse position strings to coarse roster buckets used for needs + snaps.
POS_BUCKET: dict[str, str] = {
    "QB": "QB",
    "RB": "RB",
    "FB": "RB",
    "WR": "WR",
    "TE": "TE",
    "OT": "OT",
    "G": "IOL",
    "C": "IOL",
    "IOL": "IOL",
    "EDGE": "EDGE",
    "DE": "EDGE",
    "DT": "IDL",
    "IDL": "IDL",
    "LB": "LB",
    "CB": "CB",
    "SAF": "SAF",
    "K": "ST",
    "P": "ST",
    "LS": "ST",
}

# Positional value multipliers (draft capital / replacement level prior).
POSITIONAL_VALUE: dict[str, float] = {
    "QB": 1.18,
    "OT": 1.10,
    "EDGE": 1.12,
    "CB": 1.06,
    "WR": 1.05,
    "TE": 1.02,
    "IOL": 1.04,
    "IDL": 1.03,
    "LB": 1.02,
    "SAF": 1.03,
    "RB": 0.93,
    "ST": 0.85,
}

# Snap-count position -> bucket (PFR-style labels in snap_counts).
SNAP_POS_BUCKET: dict[str, str] = {
    "QB": "QB",
    "RB": "RB",
    "FB": "RB",
    "WR": "WR",
    "TE": "TE",
    "T": "OT",
    "OT": "OT",
    "G": "IOL",
    "C": "IOL",
    "OL": "IOL",
    "DE": "EDGE",
    "DT": "IDL",
    "NT": "IDL",
    "LB": "LB",
    "ILB": "LB",
    "OLB": "EDGE",
    "MLB": "LB",
    "CB": "CB",
    "S": "SAF",
    "FS": "SAF",
    "SS": "SAF",
    "DB": "SAF",
}


def bucket_for_combine_pos(pos: str) -> str:
    p = (pos or "").strip().upper()
    return POS_BUCKET.get(p, p or "UNK")


def bucket_for_snap_pos(pos: str) -> str:
    p = (pos or "").strip().upper()
    return SNAP_POS_BUCKET.get(p, p)
