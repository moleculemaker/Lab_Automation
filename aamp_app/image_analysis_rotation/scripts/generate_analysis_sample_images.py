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

from rotation_adapter import derotate_array, load_derotation_preset, normalize_to_uint8


DEFAULT_SAMPLE_ID = "R0S39_Pg2TTT_CB_15mgml_7e-2mms_45C_100um_5ul"
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
    return np.stack([normalize_to_uint8(rgb[..., index]) for index in range(3)], axis=-1)


def label_image(image: Image.Image, text: str) -> Image.Image:
    labeled = image.copy()
    draw = ImageDraw.Draw(labeled)
    draw.rectangle((0, 0, labeled.width, 28), fill=(0, 0, 0))
    draw.text((8, 8), text, fill=(255, 255, 255))
    return labeled


def find_metadata(sample_raw_dir: Path) -> Path:
    candidates = sorted(sample_raw_dir.glob("*_metadata.json"))
    if len(candidates) != 1:
        raise FileNotFoundError(f"Expected one metadata JSON in {sample_raw_dir}, found {len(candidates)}")
    return candidates[0]


def build_frame_index(sample_raw_dir: Path) -> dict[tuple[str, int], Path]:
    metadata = load_json(find_metadata(sample_raw_dir))
    frames: dict[tuple[str, int], Path] = {}
    for image in metadata["images"]:
        mode = str(image["mode"]).lower()
        angle = int(image["sample_angle_deg"])
        frames[(mode, angle)] = sample_raw_dir / mode / image["filename"]
    return frames


def make_contact_sheet(paths: list[Path], output_path: Path, columns: int = 4) -> None:
    images = [Image.open(path).convert("RGB") for path in paths]
    thumb_width = 260
    thumbs = []
    for image in images:
        ratio = thumb_width / image.width
        thumbs.append(image.resize((thumb_width, int(image.height * ratio)), Image.Resampling.LANCZOS))
    rows = int(np.ceil(len(thumbs) / columns))
    cell_height = max(image.height for image in thumbs)
    sheet = Image.new("RGB", (columns * thumb_width, rows * cell_height), "white")
    for index, image in enumerate(thumbs):
        x = (index % columns) * thumb_width
        y = (index // columns) * cell_height
        sheet.paste(image, (x, y))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def generate_images(
    sample_raw_dir: Path,
    sample_id: str,
    preset_dir: Path,
    output_dir: Path,
    angles: tuple[int, ...],
) -> None:
    preset = load_derotation_preset(preset_dir)
    frames = build_frame_index(sample_raw_dir)
    for mode in ("ppl", "xpl"):
        original_paths: list[Path] = []
        derotated_paths: list[Path] = []
        original_dir = output_dir / "all_angles" / mode / "original"
        derotated_dir = output_dir / "all_angles" / mode / "derotated"
        original_dir.mkdir(parents=True, exist_ok=True)
        derotated_dir.mkdir(parents=True, exist_ok=True)

        for angle in angles:
            frame_path = frames.get((mode, angle))
            if frame_path is None:
                raise FileNotFoundError(f"Missing {mode} angle {angle} in {sample_raw_dir}")
            raw = np.asarray(Image.open(frame_path), dtype=np.float32)
            rgb = split_gbrg_to_rgb(raw)
            derotated = derotate_array(rgb, float(angle), preset, coordinate_space="half", apply_translation=True)

            original = label_image(Image.fromarray(normalize_rgb_to_uint8(rgb)), f"{sample_id} {mode.upper()} original {angle} deg")
            corrected = label_image(
                Image.fromarray(normalize_rgb_to_uint8(derotated)),
                f"{sample_id} {mode.upper()} derotated {angle} deg",
            )
            original_path = original_dir / f"{sample_id}_{mode}_{angle:03d}_original.png"
            derotated_path = derotated_dir / f"{sample_id}_{mode}_{angle:03d}_derotated.png"
            original.save(original_path)
            corrected.save(derotated_path)
            original_paths.append(original_path)
            derotated_paths.append(derotated_path)

        make_contact_sheet(original_paths, output_dir / "all_angles" / mode / f"{mode}_original_contact_sheet.png")
        make_contact_sheet(derotated_paths, output_dir / "all_angles" / mode / f"{mode}_derotated_contact_sheet.png")


def parse_args() -> argparse.Namespace:
    bundle_root = Path(__file__).resolve().parents[1]
    repo_root = bundle_root.parents[2]
    parser = argparse.ArgumentParser(description="Generate all-angle sample preview images for this bundle.")
    parser.add_argument("--sample-id", default=DEFAULT_SAMPLE_ID)
    parser.add_argument(
        "--sample-raw-dir",
        type=Path,
        default=repo_root / "pg2T-TT" / "data" / "imaging" / "RAW" / DEFAULT_SAMPLE_ID,
    )
    parser.add_argument("--preset-dir", type=Path, default=bundle_root / "config" / "derotation_preset")
    parser.add_argument("--output-dir", type=Path, default=bundle_root / "sample_images" / "analysis_sample")
    parser.add_argument("--angles", type=int, nargs="*", default=list(DEFAULT_ANGLES))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_images(args.sample_raw_dir, args.sample_id, args.preset_dir, args.output_dir, tuple(args.angles))
    print(f"Wrote all-angle sample images to {args.output_dir}")


if __name__ == "__main__":
    main()
