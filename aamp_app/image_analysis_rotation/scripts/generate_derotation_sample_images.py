from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rotation_adapter import derotate_plane, load_derotation_preset, normalize_to_uint8


DEFAULT_ANGLES = tuple(range(0, 166, 5))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def split_gbrg_to_rgb(raw: np.ndarray) -> np.ndarray:
    height = (raw.shape[0] // 2) * 2
    width = (raw.shape[1] // 2) * 2
    trimmed = raw[:height, :width].astype(np.float32, copy=False)
    g1 = trimmed[0::2, 0::2]
    b = trimmed[0::2, 1::2]
    r = trimmed[1::2, 0::2]
    g2 = trimmed[1::2, 1::2]
    g = 0.5 * (g1 + g2)
    return np.stack([r, g, b], axis=-1)


def normalize_rgb_to_uint8(rgb: np.ndarray) -> np.ndarray:
    rgb = np.asarray(rgb, dtype=np.float32)
    output = np.zeros(rgb.shape, dtype=np.uint8)
    for channel in range(3):
        output[..., channel] = normalize_to_uint8(rgb[..., channel])
    return output


def read_frame_path(raw_dir: Path, angle: int) -> Path:
    candidates = sorted(raw_dir.glob(f"*_{angle:03d}.tif"))
    if len(candidates) != 1:
        raise FileNotFoundError(f"Expected one TIFF for angle {angle} in {raw_dir}, found {len(candidates)}")
    return candidates[0]


def derotate_rgb(rgb_halfres: np.ndarray, angle: int, preset: dict) -> np.ndarray:
    corrected_channels = []
    for channel in range(3):
        corrected_channels.append(
            derotate_plane(
                rgb_halfres[..., channel],
                float(angle),
                preset,
                coordinate_space="half",
                apply_translation=True,
            )
        )
    return np.stack(corrected_channels, axis=-1)


def label_image(image: Image.Image, text: str) -> Image.Image:
    labeled = image.copy()
    draw = ImageDraw.Draw(labeled)
    draw.rectangle((0, 0, labeled.width, 28), fill=(0, 0, 0))
    draw.text((8, 8), text, fill=(255, 255, 255))
    return labeled


def make_contact_sheet(paths: list[Path], output_path: Path, columns: int = 4) -> None:
    images = [Image.open(path).convert("RGB") for path in paths]
    thumb_width = 260
    thumbs = []
    for image in images:
        ratio = thumb_width / image.width
        thumb = image.resize((thumb_width, int(image.height * ratio)), Image.Resampling.LANCZOS)
        thumbs.append(thumb)
    rows = int(np.ceil(len(thumbs) / columns))
    cell_height = max(image.height for image in thumbs)
    sheet = Image.new("RGB", (columns * thumb_width, rows * cell_height), "white")
    for index, image in enumerate(thumbs):
        x = (index % columns) * thumb_width
        y = (index // columns) * cell_height
        sheet.paste(image, (x, y))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def generate_images(source_raw_dir: Path, preset_dir: Path, output_dir: Path, angles: tuple[int, ...]) -> None:
    preset = load_derotation_preset(preset_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    contact_paths: list[Path] = []
    for angle in angles:
        frame_path = read_frame_path(source_raw_dir, angle)
        raw = np.asarray(Image.open(frame_path), dtype=np.float32)
        rgb = split_gbrg_to_rgb(raw)
        corrected = derotate_rgb(rgb, angle, preset)

        before = label_image(Image.fromarray(normalize_rgb_to_uint8(rgb)), f"before derotation, {angle} deg")
        after = label_image(Image.fromarray(normalize_rgb_to_uint8(corrected)), f"after derotation, {angle} deg")
        before_path = output_dir / f"rotation_calibration_3_{angle:03d}_before.png"
        after_path = output_dir / f"rotation_calibration_3_{angle:03d}_after.png"
        before.save(before_path)
        after.save(after_path)
        contact_paths.extend([before_path, after_path])

    make_contact_sheet(contact_paths, output_dir / "rotation_calibration_3_before_after_contact_sheet.png")


def parse_args() -> argparse.Namespace:
    bundle_root = Path(__file__).resolve().parents[1]
    repo_root = bundle_root.parents[2]
    parser = argparse.ArgumentParser(description="Generate derotation before/after PNG examples for this bundle.")
    parser.add_argument(
        "--source-raw-dir",
        type=Path,
        default=repo_root / "pg2T-TT" / "data" / "imaging" / "RAW" / "rotation_calibration_3" / "ppl",
    )
    parser.add_argument("--preset-dir", type=Path, default=bundle_root / "config" / "derotation_preset")
    parser.add_argument("--output-dir", type=Path, default=bundle_root / "sample_images" / "derotation_sample")
    parser.add_argument("--angles", type=int, nargs="*", default=list(DEFAULT_ANGLES))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_images(args.source_raw_dir, args.preset_dir, args.output_dir, tuple(args.angles))
    print(f"Wrote derotation sample images to {args.output_dir}")


if __name__ == "__main__":
    main()
