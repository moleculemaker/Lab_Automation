from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def axis_from_coeffs(cos_coeff: float, sin_coeff: float, harmonic_order: int) -> float:
    period = 180.0 / harmonic_order
    scale = 2.0 if harmonic_order == 2 else 4.0
    return float((math.degrees(math.atan2(sin_coeff, cos_coeff)) / scale) % period)


def harmonic_fit(angles_deg: np.ndarray, values: np.ndarray, min_valid: int = 10) -> dict[str, Any]:
    valid = np.isfinite(angles_deg) & np.isfinite(values)
    if int(valid.sum()) < min_valid:
        return {
            "fit_valid": False,
            "n_valid_angles": int(valid.sum()),
            "a0": float("nan"),
            "a2c": float("nan"),
            "a2s": float("nan"),
            "a4c": float("nan"),
            "a4s": float("nan"),
            "A2": float("nan"),
            "A4": float("nan"),
            "axis2_deg": float("nan"),
            "axis4_deg": float("nan"),
            "rmse": float("nan"),
            "nrmse": float("nan"),
        }

    theta = np.deg2rad(angles_deg[valid])
    design = np.column_stack(
        [
            np.ones(theta.shape[0], dtype=np.float64),
            np.cos(2.0 * theta),
            np.sin(2.0 * theta),
            np.cos(4.0 * theta),
            np.sin(4.0 * theta),
        ]
    )
    coeffs, *_ = np.linalg.lstsq(design, values[valid], rcond=None)
    predicted = design @ coeffs
    residual = values[valid] - predicted
    rmse = float(np.sqrt(np.mean(residual**2)))
    scale = float(np.nanmax(values[valid]) - np.nanmin(values[valid]))
    nrmse = rmse / max(scale, 1e-12)
    a0, a2c, a2s, a4c, a4s = [float(value) for value in coeffs]
    return {
        "fit_valid": True,
        "n_valid_angles": int(valid.sum()),
        "a0": a0,
        "a2c": a2c,
        "a2s": a2s,
        "a4c": a4c,
        "a4s": a4s,
        "A2": float(math.hypot(a2c, a2s)),
        "A4": float(math.hypot(a4c, a4s)),
        "axis2_deg": axis_from_coeffs(a2c, a2s, 2),
        "axis4_deg": axis_from_coeffs(a4c, a4s, 4),
        "rmse": rmse,
        "nrmse": nrmse,
    }


def fit_long_table(input_csv: Path) -> list[dict[str, Any]]:
    rows = read_csv(input_csv)
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (row["sample_id"], row["source"], row["mode"], row["channel"])
        grouped[key].append(row)

    fit_rows: list[dict[str, Any]] = []
    for (sample_id, source, mode, channel), group_rows in sorted(grouped.items()):
        group_rows = sorted(group_rows, key=lambda row: float(row["angle_deg"]))
        angles = np.array([float(row["angle_deg"]) for row in group_rows], dtype=np.float64)
        values = np.array([float(row["value"]) for row in group_rows], dtype=np.float64)
        fit = harmonic_fit(angles, values)
        fit_rows.append(
            {
                "sample_id": sample_id,
                "source": source,
                "mode": mode,
                "channel": channel,
                **fit,
            }
        )
    return fit_rows


def parse_args() -> argparse.Namespace:
    bundle_root = Path(__file__).resolve().parents[1]
    sample_id = "R0S39_Pg2TTT_CB_15mgml_7e-2mms_45C_100um_5ul"
    default_input = bundle_root / "sample_data" / sample_id / "derived" / "angle_curve_long.csv"
    default_output = bundle_root / "sample_data" / sample_id / "derived" / "angle_curve_fit_summary.csv"
    parser = argparse.ArgumentParser(description="Fit A2/A4 harmonic terms from angle_curve_long.csv.")
    parser.add_argument("--input-csv", type=Path, default=default_input)
    parser.add_argument("--output-csv", type=Path, default=default_output)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fit_rows = fit_long_table(args.input_csv)
    write_csv(args.output_csv, fit_rows)
    print(f"Wrote {args.output_csv}")


if __name__ == "__main__":
    main()
