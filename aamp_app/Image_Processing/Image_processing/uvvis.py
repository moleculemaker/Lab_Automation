from __future__ import annotations

from io import BytesIO
from typing import Dict, Tuple
import re

import pandas as pd


def _extract_round_sample_id(image_stem: str) -> str | None:
    match = re.search(r"(R\d+S\d+)", image_stem, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).upper()


def find_uvvis_file(image_name, fs, campaign_id):
    round_sample_id = _extract_round_sample_id(image_name)
    if round_sample_id is None:
        return None

    candidates = fs.find_one({"filename": {"$regex": f"^{round_sample_id}.*\\.csv$"}, "campaign_id": campaign_id})
    if candidates is None:
        return None
    return candidates


def _find_header_row(uvvis_data: bytes) -> int | None:
    text = uvvis_data.decode("utf-8", errors="ignore")
    for idx, line in enumerate(text.splitlines()):
        if "wavelength" in line.lower():
            return idx
    return None


def analyze_uvvis_data(
    image_name,
    fs,
    campaign_id,
    abs_threshold: float = 0.1,
    wavelength_min: float = 300.0,
    wavelength_max: float = 800.0,
) -> Tuple[bool, Dict[str, float | str]]:
    """Load UV-Vis CSV, compute simple statistics, and threshold check."""

    uvvis_file = find_uvvis_file(image_name, fs, campaign_id)
    if uvvis_file is None:
        return False, {
            "uvvis_reason": "file_not_found",
            "uvvis_abs_threshold": abs_threshold,
        }

    data = uvvis_file.read()
    header_row = _find_header_row(data)
    read_kwargs = {"encoding": "utf-8", "engine": "python"}
    try:
        if header_row is not None:
            df = pd.read_csv(BytesIO(data), header=header_row, **read_kwargs)
        else:
            df = pd.read_csv(BytesIO(data), **read_kwargs)
    except Exception:
        return False, {
            "uvvis_reason": "read_error",
            "uvvis_file": str(uvvis_file.filename),
            "uvvis_abs_threshold": abs_threshold,
        }

    df = df.dropna(axis=1, how="all")
    df = df.rename(columns=lambda c: str(c).strip())

    abs_col = None
    wavelength_col = None
    for col in df.columns:
        cname = str(col).lower()
        if abs_col is None and ("abs" in cname or "absorbance" in cname):
            abs_col = col
        if wavelength_col is None and ("wavelength" in cname or cname.startswith("wl")):
            wavelength_col = col

    if abs_col is None or wavelength_col is None:
        return False, {
            "uvvis_reason": "missing_columns",
            "uvvis_file": str(uvvis_file.filename),
            "uvvis_abs_threshold": abs_threshold,
        }

    df = df[[wavelength_col, abs_col]].copy()
    df[wavelength_col] = pd.to_numeric(df[wavelength_col], errors="coerce")
    df[abs_col] = pd.to_numeric(df[abs_col], errors="coerce")
    df = df.dropna()
    df = df[(df[wavelength_col] >= wavelength_min) & (df[wavelength_col] <= wavelength_max)]

    if df.empty:
        return False, {
            "uvvis_reason": "empty_data",
            "uvvis_file": str(uvvis_file.filename),
            "uvvis_abs_threshold": abs_threshold,
        }

    max_abs = float(df[abs_col].max())
    mean_abs = float(df[abs_col].mean())
    median_abs = float(df[abs_col].median())
    min_abs = float(df[abs_col].min())
    data_points = int(len(df))
    peak_idx = int(df[abs_col].idxmax())
    peak_wavelength = float(df.loc[peak_idx, wavelength_col])

    passed = max_abs >= abs_threshold

    stats: Dict[str, float | str] = {
        "uvvis_file": str(uvvis_file.filename),
        "uvvis_abs_threshold": abs_threshold,
        "uvvis_wavelength_min": wavelength_min,
        "uvvis_wavelength_max": wavelength_max,
        "uvvis_passed": passed,
        "uvvis_reason": "ok" if passed else "below_threshold",
        "uvvis_max_abs": max_abs,
        "uvvis_mean_abs": mean_abs,
        "uvvis_median_abs": median_abs,
        "uvvis_min_abs": min_abs,
        "uvvis_data_points": data_points,
        "uvvis_peak_wavelength": peak_wavelength,
    }

    return passed, stats
