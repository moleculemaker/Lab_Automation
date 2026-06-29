from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy import ndimage


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_derotation_preset(preset_dir: Path) -> dict[str, Any]:
    correction = load_json(preset_dir / "solved_correction.json")
    geometry = load_json(preset_dir / "rotation_geometry.json")
    solved_center = correction["solved_center"]
    center_full = (float(solved_center["x"]), float(solved_center["y"]))
    center_half = ((center_full[0] - 0.5) / 2.0, (center_full[1] - 0.5) / 2.0)
    shifts_full: dict[int, tuple[float, float]] = {}
    shifts_half: dict[int, tuple[float, float]] = {}
    for row in correction.get("translation_table", []):
        angle = int(round(float(row["angle_deg"])))
        dx = float(row.get("shift_x_px", 0.0))
        dy = float(row.get("shift_y_px", 0.0))
        shifts_full[angle] = (dx, dy)
        shifts_half[angle] = (dx / 2.0, dy / 2.0)
    return {
        "center_full": center_full,
        "center_half": center_half,
        "shifts_full": shifts_full,
        "shifts_half": shifts_half,
        "geometry": geometry,
    }


def rotate_plane(arr: np.ndarray, angle_deg: float, center_xy: tuple[float, float]) -> np.ndarray:
    if abs(angle_deg) < 1e-9:
        return arr.astype(np.float32, copy=True)
    image = Image.fromarray(arr.astype(np.float32))
    rotated = image.rotate(
        angle_deg,
        resample=Image.Resampling.BILINEAR,
        expand=False,
        center=center_xy,
        fillcolor=0.0,
    )
    return np.asarray(rotated, dtype=np.float32)


def derotate_plane(
    arr: np.ndarray,
    angle_deg: float,
    preset: dict[str, Any],
    coordinate_space: str = "half",
    apply_translation: bool = True,
) -> np.ndarray:
    if coordinate_space == "full":
        center = preset["center_full"]
        shifts = preset["shifts_full"]
    elif coordinate_space == "half":
        center = preset["center_half"]
        shifts = preset["shifts_half"]
    else:
        raise ValueError("coordinate_space must be 'full' or 'half'")

    rotated = rotate_plane(arr, angle_deg, center)
    if not apply_translation:
        return rotated
    dx, dy = shifts.get(int(round(angle_deg)), (0.0, 0.0))
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return rotated
    return ndimage.shift(rotated, (dy, dx), order=1, mode="constant", cval=0.0).astype(np.float32)


def derotate_array(
    arr: np.ndarray,
    angle_deg: float,
    preset: dict[str, Any],
    coordinate_space: str = "half",
    apply_translation: bool = True,
) -> np.ndarray:
    arr = np.asarray(arr)
    if arr.ndim == 2:
        return derotate_plane(arr.astype(np.float32), angle_deg, preset, coordinate_space, apply_translation)
    if arr.ndim == 3:
        channels = [
            derotate_plane(arr[..., index].astype(np.float32), angle_deg, preset, coordinate_space, apply_translation)
            for index in range(arr.shape[2])
        ]
        return np.stack(channels, axis=-1)
    raise ValueError("Expected a 2D grayscale image or a 3D channel-last image")


def load_halfres_valid_mask(mask_path: Path) -> np.ndarray:
    full_mask = np.asarray(Image.open(mask_path).convert("L"), dtype=np.uint8) > 0
    height2 = full_mask.shape[0] // 2
    width2 = full_mask.shape[1] // 2
    trimmed = full_mask[: height2 * 2, : width2 * 2]
    return trimmed.reshape(height2, 2, width2, 2).all(axis=(1, 3))


def normalize_to_uint8(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return np.zeros(arr.shape, dtype=np.uint8)
    low, high = np.percentile(finite, [1, 99.7])
    if high <= low:
        high = low + 1.0
    scaled = np.clip((arr - low) / (high - low), 0.0, 1.0)
    return (scaled * 255.0 + 0.5).astype(np.uint8)


def derotate_image_file(
    input_path: Path,
    output_path: Path,
    angle_deg: float,
    preset_dir: Path,
    coordinate_space: str,
) -> None:
    preset = load_derotation_preset(preset_dir)
    image = Image.open(input_path)
    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")
    arr = np.asarray(image, dtype=np.float32)
    corrected = derotate_array(arr, angle_deg, preset, coordinate_space=coordinate_space, apply_translation=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if corrected.ndim == 2:
        out = normalize_to_uint8(corrected)
    else:
        out = np.stack([normalize_to_uint8(corrected[..., index]) for index in range(corrected.shape[2])], axis=-1)
    Image.fromarray(out).save(output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply the distributed Pg2T-TT derotation preset to one grayscale image.")
    parser.add_argument("--input-image", type=Path, required=True)
    parser.add_argument("--output-image", type=Path, required=True)
    parser.add_argument("--angle-deg", type=float, required=True)
    parser.add_argument("--coordinate-space", choices=("full", "half"), default="full")
    parser.add_argument(
        "--preset-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "config" / "derotation_preset",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    derotate_image_file(args.input_image, args.output_image, args.angle_deg, args.preset_dir, args.coordinate_space)


if __name__ == "__main__":
    main()
