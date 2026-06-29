from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


DEFAULT_SAMPLE_ID = "R0S39_Pg2TTT_CB_15mgml_7e-2mms_45C_100um_5ul"
ANGLES_DEG = list(range(0, 166, 5))
CURVE_SOURCES = ("sample_corr", "blank_corr")
MODES = ("PPL", "XPL")
CHANNELS = ("R", "G", "B")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


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
                fieldnames.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_angle_curve_rows(qc_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    qc_curves = qc_metrics["qc_curves"]
    for source in CURVE_SOURCES:
        for mode in MODES:
            curves = qc_curves[source][mode]
            for channel in CHANNELS:
                values = curves[channel]
                for angle_deg, value in zip(ANGLES_DEG, values, strict=True):
                    rows.append(
                        {
                            "sample_id": qc_metrics["sample_id"],
                            "source": source,
                            "mode": mode,
                            "channel": channel,
                            "angle_deg": angle_deg,
                            "value": value,
                        }
                    )
    return rows


def compact_fit_rows(roi_summary: list[dict[str, str]]) -> list[dict[str, Any]]:
    keep_fields = (
        "sample_id",
        "sample_type",
        "roi_size_fullres",
        "roi_label",
        "signal",
        "channel",
        "primary_metric_name",
        "primary_value",
        "primary_axis_deg",
        "mean_value",
        "p90_value",
        "valid_tile_fraction",
        "valid_tile_count",
        "total_tile_count",
        "median_rmse",
        "median_nrmse",
    )
    return [{field: row.get(field, "") for field in keep_fields} for row in roi_summary]


def compact_sample_summary(sample_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": sample_summary["sample_id"],
        "sample_type": sample_summary["sample_type"],
        "roi_size_fullres": sample_summary["roi_size_fullres"],
        "roi_labels": sample_summary["roi_labels"],
        "sample_summary_rows": sample_summary["sample_summary_rows"],
    }


def build_payload(bundle_root: Path, sample_id: str) -> dict[str, Any]:
    sample_root = bundle_root / "sample_data" / sample_id
    derived = sample_root / "derived"
    qc_metrics = load_json(derived / "qc_metrics.json")
    roi_summary = read_csv(derived / "roi_summary.csv")
    sample_summary = load_json(derived / "sample_summary.json")
    preset_summary = load_json(bundle_root / "config" / "derotation_preset" / "preset_values_summary.json")
    solved_correction = load_json(bundle_root / "config" / "derotation_preset" / "solved_correction.json")
    rotation_geometry = load_json(bundle_root / "config" / "derotation_preset" / "rotation_geometry.json")
    roi_preset = load_json(bundle_root / "config" / "roi_550_center.json")

    return {
        "schema": "pg2tt-webapp-rotation-payload-v1",
        "sample_id": sample_id,
        "sample_type": qc_metrics["sample_type"],
        "angle_degrees": ANGLES_DEG,
        "derotation_preset": {
            "summary": preset_summary,
            "center_xy_fullres": solved_correction["solved_center"],
            "translation_table": solved_correction["translation_table"],
            "rotation_geometry": {
                "center_xy_fullres": rotation_geometry["center_xy_fullres"],
                "mask_erosion_px": rotation_geometry["mask_erosion_px"],
                "full_mask_area_fraction": rotation_geometry["full_mask_area_fraction"],
                "full_mask_bbox": rotation_geometry["full_mask_bbox"],
                "largest_centered_square": rotation_geometry["largest_centered_square"],
            },
            "roi_preset": roi_preset,
        },
        "quality": {
            "blank_flatness_flag": qc_metrics["blank_flatness_flag"],
            "G1_G2_curve_diff": qc_metrics["G1_G2_curve_diff"],
            "registration_stability_flag": qc_metrics["registration_stability_flag"],
            "registration_stability_median_shift_px": qc_metrics["registration_stability_median_shift_px"],
        },
        "fits": {
            "sample_summary": compact_sample_summary(sample_summary),
            "roi_summary_compact": compact_fit_rows(roi_summary),
        },
        "files": {
            "angle_curve_long_csv": f"sample_data/{sample_id}/derived/angle_curve_long.csv",
            "angle_curve_fit_summary_csv": f"sample_data/{sample_id}/derived/angle_curve_fit_summary.csv",
            "qc_metrics_json": f"sample_data/{sample_id}/derived/qc_metrics.json",
            "roi_summary_csv": f"sample_data/{sample_id}/derived/roi_summary.csv",
            "tile_fits_csv": f"sample_data/{sample_id}/derived/tile_fits.csv",
            "extraction_bundle_npz": f"sample_data/{sample_id}/derived/extraction_bundle.npz",
            "qc_curves_png": f"sample_data/{sample_id}/figures/qc_curves.png",
            "fit_overlay_png": f"sample_data/{sample_id}/figures/fit_overlay.png",
            "representative_summary_png": f"sample_data/{sample_id}/figures/representative_summary_blank_corrected.png",
            "analysis_sample_images_dir": "sample_images/analysis_sample",
            "derotation_sample_images_dir": "sample_images/derotation_sample",
            "derotation_qc_dir": "derotation_qc_examples",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Pg2T-TT webapp-friendly rotation payload.")
    parser.add_argument("--bundle-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--sample-id", default=DEFAULT_SAMPLE_ID)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bundle_root = args.bundle_root.resolve()
    sample_root = bundle_root / "sample_data" / args.sample_id
    derived = sample_root / "derived"

    qc_metrics = load_json(derived / "qc_metrics.json")
    angle_rows = build_angle_curve_rows(qc_metrics)
    write_csv(derived / "angle_curve_long.csv", angle_rows)

    payload = build_payload(bundle_root, args.sample_id)
    write_json(derived / "webapp_payload.json", payload)
    print(f"Wrote {derived / 'angle_curve_long.csv'}")
    print(f"Wrote {derived / 'webapp_payload.json'}")


if __name__ == "__main__":
    main()
