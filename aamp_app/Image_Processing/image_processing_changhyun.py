#!/usr/bin/env python3
"""Simple image processing script using compute_uniformity_score.

Processes images from 'data/Round0/Raw' directory.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from typing import Dict, Any

import pandas as pd
import cv2
import numpy as np
from .Image_processing.scoring import compute_uniformity_score, _match_reference_for
from .Image_processing.pipeline import analyze_image
from .Image_processing.config import UniformityConfig


def _save_mask_with_footer(
    mask: np.ndarray,
    sample_roi: np.ndarray | None,
    source_image: np.ndarray | None,
    roi_coords: tuple[int, int, int, int],
    image_name: str,
    coverage_pct: float | None,
    uniformity_value: float | None,
    uvvis_max: float | None,
    debug_info: dict | None,
    output_path: Path,
):
    if mask is None:
        return

    def _prepare_panel(
        img: np.ndarray,
        label: str | None = None,
        draw_rect: bool = False,
        rect: tuple[int, int, int, int] | None = None,
    ) -> np.ndarray:
        if img.dtype != np.uint8:
            img_disp = np.clip(img, 0, 255).astype(np.uint8)
        else:
            img_disp = img.copy()
        if len(img_disp.shape) == 2:
            img_disp = cv2.cvtColor(img_disp, cv2.COLOR_GRAY2BGR)

        if draw_rect and rect is not None:
            x, y, w, h = rect
            cv2.rectangle(img_disp, (x, y), (x + w, y + h), (0, 0, 255), 2)

        if label:
            label_strip = np.full((30, img_disp.shape[1], 3), 255, dtype=np.uint8)
            cv2.putText(
                label_strip,
                label,
                (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )
            panel = cv2.vconcat([label_strip, img_disp])
        else:
            panel = img_disp
        panel = cv2.copyMakeBorder(panel, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=(0, 0, 0))
        return panel

    def _pad_to_width(img: np.ndarray, width: int) -> np.ndarray:
        if img.shape[1] >= width:
            if img.shape[1] == width:
                return img
            scale = width / img.shape[1]
            new_h = int(img.shape[0] * scale)
            return cv2.resize(img, (width, new_h), interpolation=cv2.INTER_AREA)
        pad_total = width - img.shape[1]
        left = pad_total // 2
        right = pad_total - left
        return cv2.copyMakeBorder(img, 0, 0, left, right, cv2.BORDER_CONSTANT, value=(255, 255, 255))

    def _resize_to_height(img: np.ndarray, height: int) -> np.ndarray:
        if img.shape[0] == height:
            return img
        scale = height / img.shape[0]
        new_w = max(1, int(round(img.shape[1] * scale)))
        interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
        return cv2.resize(img, (new_w, height), interpolation=interpolation)

    if len(mask.shape) == 2:
        mask_binary = mask
    else:
        mask_binary = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

    if sample_roi is None:
        sample_roi_color = np.zeros((mask_binary.shape[0], mask_binary.shape[1], 3), dtype=np.uint8)
    else:
        sample_roi_color = sample_roi
        if sample_roi_color.dtype != np.uint8:
            sample_roi_color = np.clip(sample_roi_color, 0, 255).astype(np.uint8)
        if len(sample_roi_color.shape) == 2:
            sample_roi_color = cv2.cvtColor(sample_roi_color, cv2.COLOR_GRAY2BGR)

    masked_roi = cv2.bitwise_and(sample_roi_color, sample_roi_color, mask=mask_binary)
    mask_color = cv2.cvtColor(mask_binary, cv2.COLOR_GRAY2BGR)

    roi_x, roi_y, roi_w, roi_h = roi_coords
    if source_image is None:
        full_panel_img = np.zeros_like(sample_roi_color)
    else:
        if source_image.dtype != np.uint8:
            full_panel_img = np.clip(source_image, 0, 255).astype(np.uint8)
        else:
            full_panel_img = source_image.copy()

    panel_full = _prepare_panel(full_panel_img, None, True, (roi_x, roi_y, roi_w, roi_h))
    panel_original = _prepare_panel(sample_roi_color, "Original ROI")
    panel_masked = _prepare_panel(masked_roi, "Masked ROI (film=color, no film=black)")
    panel_binary = _prepare_panel(mask_color, "Binary Mask (film=white, no film=black)")

    # Unify all panels to maximum height (panel 1 may have different height since it has no title)
    max_height = max(panel_full.shape[0], panel_original.shape[0], panel_masked.shape[0], panel_binary.shape[0])
    panel_full = _resize_to_height(panel_full, max_height)
    panel_original = _resize_to_height(panel_original, max_height)
    panel_masked = _resize_to_height(panel_masked, max_height)
    panel_binary = _resize_to_height(panel_binary, max_height)

    col1_width = max(panel_full.shape[1], panel_original.shape[1])
    col2_width = max(panel_masked.shape[1], panel_binary.shape[1])

    panel_full = _pad_to_width(panel_full, col1_width)
    panel_original = _pad_to_width(panel_original, col1_width)
    panel_masked = _pad_to_width(panel_masked, col2_width)
    panel_binary = _pad_to_width(panel_binary, col2_width)

    spacer_col = np.full((max_height, 10, 3), 255, dtype=np.uint8)

    top_row = cv2.hconcat([panel_full, spacer_col, panel_masked])
    bottom_row = cv2.hconcat([panel_original, spacer_col.copy(), panel_binary])

    spacer_row = np.full((10, top_row.shape[1], 3), 255, dtype=np.uint8)
    stacked = cv2.vconcat([top_row, spacer_row, bottom_row])

    # Add title (from filename up to _mask)
    title_text = output_path.stem.replace("_mask", "")
    title_height = 50
    title_bar = np.full((title_height, stacked.shape[1], 3), 255, dtype=np.uint8)
    cv2.putText(
        title_bar,
        title_text,
        (10, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 0),
        2,
        cv2.LINE_AA,
    )

    # Create footer (divided into multiple columns)
    debug_info = debug_info or {}
    cov_display = (coverage_pct or 0.0) * 100
    uniformity_score = debug_info.get("uniformity_score", uniformity_value if uniformity_value is not None else 0.0)
    
    # Reference-based Uniformity statistics
    ref_std = debug_info.get("ref_std", 0.0)
    ref_entropy = debug_info.get("ref_entropy", 0.0)
    sample_std = debug_info.get("sample_std", 0.0)
    sample_entropy = debug_info.get("sample_entropy", 0.0)
    delta_std = debug_info.get("delta_std", 0.0)
    delta_entropy = debug_info.get("delta_entropy", 0.0)
    std_sensitivity = debug_info.get("uniformity_std_sensitivity", 15.0)
    ent_sensitivity = debug_info.get("uniformity_ent_sensitivity", 2.0)
    use_model_ref = debug_info.get("use_model_reference", 0.0) > 0.5  # Convert float to bool
    
    uvvis_display = uvvis_max if uvvis_max is not None else 0.0
    threshold_val = debug_info.get("saturation_threshold", 0.0)
    ref_mean = debug_info.get("ref_s_mean", 0.0)

    footer_height = 200
    footer = np.full((footer_height, stacked.shape[1], 3), 255, dtype=np.uint8)
    
    # Two-column layout
    col_width = stacked.shape[1] // 2
    left_col_x = 15
    right_col_x = col_width + 15
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    color = (0, 0, 0)
    thickness = 1
    line_height = 28
    y_start = 25

    # Reference notation (whether Model Reference is used)
    ref_label = "Ref" if not use_model_ref else "Model Ref"
    
    # Left column
    left_lines = [
        f"File: {image_name}",
        f"Coverage: {cov_display:.1f}%",
        f"Uniformity: {uniformity_score:.3f}",
        f"  ({ref_label} Std: {ref_std:.2f}, Sample: {sample_std:.2f})",
        f"  ({ref_label} Ent: {ref_entropy:.2f}, Sample: {sample_entropy:.2f})",
        f"UV-Vis max (300-800nm): {uvvis_display:.3f}",
    ]
    for idx, text in enumerate(left_lines):
        y = y_start + idx * line_height
        cv2.putText(footer, text, (left_col_x, y), font, font_scale, color, thickness, cv2.LINE_AA)

    # Right column
    right_lines = [
        f"Threshold: {threshold_val:.1f}",
        f"Ref Mean: {ref_mean:.1f}",
        f"Delta Std: {delta_std:.2f} (K1: {std_sensitivity:.1f})",
        f"Delta Ent: {delta_entropy:.2f} (K2: {ent_sensitivity:.1f})",
    ]
    if use_model_ref:
        right_lines.append("Note: Model Reference used")
    for idx, text in enumerate(right_lines):
        y = y_start + idx * line_height
        cv2.putText(footer, text, (right_col_x, y), font, font_scale, color, thickness, cv2.LINE_AA)

    combined = cv2.vconcat([title_bar, stacked, footer])
    cv2.imwrite(str(output_path), combined)


def process_single_directory(
    main_dir: Path,
    roi_x: int,
    roi_y: int,
    roi_width: int,
    roi_height: int,
    uvvis_abs_threshold: float,
    coverage_threshold: float,
    metadata_base: Dict[str, Any],
) -> None:
    """Process images for a single directory."""
    
    raw_dir = main_dir / "Raw"
    reference_dir = main_dir / "blank"
    uvvis_dir = main_dir / "UV-Vis"
    initial_parameters_csv = main_dir / "PProDOT_CB_Campaign_parameters.csv"
    output_csv = main_dir / "processing_results_simple.csv"
    
    print(f"\n{'='*60}")
    print(f"Processing directory: {main_dir}")
    print(f"{'='*60}")
    
    # Load initial parameters CSV if available
    parameters_df = None
    if initial_parameters_csv.exists():
        parameters_df = pd.read_csv(initial_parameters_csv)
        if parameters_df.columns[0] == '' or parameters_df.columns[0].startswith('Unnamed'):
            parameters_df = parameters_df.iloc[:, 1:]
        parameters_df.columns = parameters_df.columns.str.strip()
    
    # Prepare metadata for compute_uniformity_score
    metadata = metadata_base.copy()
    metadata.update({
        "reference_dir": str(reference_dir.resolve()),
        "uvvis_dir": str(uvvis_dir.resolve()),
    })
    
    # Find all image files
    if not raw_dir.exists():
        print(f"  Warning: Raw directory not found: {raw_dir}")
        return
    
    image_exts = {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'}
    image_files = [f for f in raw_dir.iterdir() if f.is_file() and f.suffix.lower() in image_exts]
    
    if len(image_files) == 0:
        print(f"  Warning: No image files found in {raw_dir}")
        return
    
    print(f"Found {len(image_files)} image files")

    debug_mask_dir = main_dir / "Debug_Masks"
    debug_mask_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each image
    results = []
    for i, image_path in enumerate(sorted(image_files), 1):
        print(f"[{i}/{len(image_files)}] Processing {image_path.name}...")
        sample_roi = None
        final_mask = None
        debug_info = None
        
        # Extract round# and Sample # from filename (R0S01 -> round=0, sample=1)
        import re
        match = re.match(r'R(\d+)S(\d+)', image_path.stem, re.IGNORECASE)
        round_num = int(match.group(1)) if match else None
        sample_num = int(match.group(2)) if match else None
        
        # Compute uniformity score and full metrics
        try:
            # Use verbose=True for first image to diagnose issues
            verbose = (i == 1)
            uniformity_score = compute_uniformity_score(
                image_path=str(image_path),
                metadata=metadata,
                verbose=verbose
            )
            
            # Also get full metrics for CSV
            img = cv2.imread(str(image_path))
            if img is not None:
                cfg = UniformityConfig(
                    input_dir=str(image_path.parent),
                    use_reference=True,
                    reference_dir=str(reference_dir.resolve()),
                    reference_name="background_normal_0deg",
                    roi_x=roi_x,
                    roi_y=roi_y,
                    roi_width=roi_width,
                    roi_height=roi_height,
                    uvvis_dir=str(uvvis_dir.resolve()),
                    uvvis_abs_threshold=uvvis_abs_threshold,
                    coverage_threshold=coverage_threshold,
                    coverage_k=metadata.get("coverage_k", 3.0),
                    uniformity_std_sensitivity=metadata.get("uniformity_std_sensitivity", 15.0),
                    uniformity_ent_sensitivity=metadata.get("uniformity_ent_sensitivity", 2.0),
                    compute_learning_features=True,
                )
                
                # Load reference image (required for ROI feature computation)
                ref_path = _match_reference_for(image_path, cfg.reference_dir, cfg.reference_name)
                ref_bgr = None
                if ref_path is not None and ref_path.exists():
                    ref_bgr = cv2.imread(str(ref_path))
                
                (
                    metrics,
                    sample_roi,
                    reference_roi,
                    final_mask,
                    debug_info,
                ) = analyze_image(img, cfg, ref_bgr=ref_bgr, image_path=image_path)
                
                # Get uniformity score from metrics or debug_info (new CV-based calculation)
                uniformity_score_from_metrics = metrics.get("uniformity_score")
                uniformity_score_from_debug = debug_info.get("uniformity_score") if isinstance(debug_info, dict) else None
                if uniformity_score_from_metrics is not None:
                    uniformity_score = uniformity_score_from_metrics
                elif uniformity_score_from_debug is not None:
                    uniformity_score = uniformity_score_from_debug
                
                # Start with basic info
                result = {
                    "round#": round_num,
                    "Sample #": sample_num,
                    "image_name": image_path.name,
                    "image_path": str(image_path),
                    "uniformity_score": uniformity_score,
                }
                
                # Add all metrics
                result.update(metrics)
            else:
                result = {
                    "round#": round_num,
                    "Sample #": sample_num,
                    "image_name": image_path.name,
                    "image_path": str(image_path),
                    "uniformity_score": uniformity_score,
                }
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            uniformity_score = None
            result = {
                "round#": round_num,
                "Sample #": sample_num,
                "image_name": image_path.name,
                "image_path": str(image_path),
                "uniformity_score": None,
            }
        
        # Add parameters from CSV if available
        if parameters_df is not None and round_num is not None and sample_num is not None:
            param_row = parameters_df[
                (parameters_df["round#"] == round_num) & 
                (parameters_df["Sample #"] == sample_num)
            ]
            if not param_row.empty:
                row = param_row.iloc[0]
                result["Temperature"] = row.get("Temperature", None)
                result["Speed"] = row.get("Speed", None)
                result["gap"] = row.get("gap", None)
                result["Solvent"] = row.get("Solvent", None)
                result["Concentration"] = row.get("Concentration", None)
                result["Precursor Volume"] = row.get("Precursor Volume", None)
        
        if isinstance(debug_info, dict):
            result.update(debug_info)

        if final_mask is not None:
            coverage_pct = result.get("coverage_percentage")
            uvvis_max = result.get("uvvis_max_abs")
            uniformity_val = uniformity_score if uniformity_score is not None else coverage_pct
            threshold_val = (debug_info or {}).get("saturation_threshold", metadata.get("coverage_k", 0.0))
            mask_path = debug_mask_dir / f"{image_path.stem}_mask_th{threshold_val:.1f}.png"
            _save_mask_with_footer(
                final_mask,
                sample_roi,
                img,
                (roi_x, roi_y, roi_width, roi_height),
                image_path.name,
                coverage_pct,
                uniformity_val,
                uvvis_max,
                debug_info,
                mask_path,
            )

        results.append(result)
    
    # Save to CSV with preferred column order
    df = pd.DataFrame(results)
    preferred_order = [
        "round#",
        "Sample #",
        "image_name",
        "image_path",
        "coverage_percentage",
        "uvvis_max_abs",
        "uniformity_score",
    ]
    remaining_cols = [col for col in df.columns if col not in preferred_order]
    df = df[[col for col in preferred_order if col in df.columns] + remaining_cols]
    df.to_csv(output_csv, index=False)
    print(f"\nResults saved to {output_csv}")
    return results


def main():
    """Main entry point."""
    
    # ============================================
    # Configuration: Choose method for processing multiple directories
    # ============================================
    
    # Method 1: Specify directly as a list
    main_dirs = [
        Path("Round0"),
        # Path("data/Round0_1"),
        # Path("data/Round0_2"),
        # Path("data/Round0_3"),
        # Path("data/Round1"),
        # Path("data/Round2"),
        # Path("data/Round3"),
        # Path("data/Round4"),
        # Path("data/Round5"),
        # Path("data/PProDOT_2nd_dataset")
        # Add desired directories
    ]
    
    # Method 2: Automatically discover all Round* directories under data/ (comment out Method 1 first)
    # data_base = Path("data")
    # if data_base.exists():
    #     main_dirs = [d for d in data_base.iterdir() if d.is_dir() and d.name.startswith("Round")]
    # else:
    #     main_dirs = []
    
    # Common settings
    roi_x = 580
    roi_y = 400
    roi_width = 913
    roi_height = 415
    
    # Thresholds
    uvvis_abs_threshold = 0.1
    coverage_threshold = 0.1
    
    # Common metadata (reference_dir and uvvis_dir are automatically set for each directory)
    metadata_base = {
        "roi_x": roi_x,
        "roi_y": roi_y,
        "roi_width": roi_width,
        "roi_height": roi_height,
        "uvvis_abs_threshold": uvvis_abs_threshold,
        "coverage_threshold": coverage_threshold,
        "coverage_k": 1.0,
        "uniformity_std_sensitivity": 15.0,  # K1: Sensitivity to Std difference
        "uniformity_ent_sensitivity": 2.0,   # K2: Sensitivity to Entropy difference
    }
    
    # Process each directory
    for main_dir in main_dirs:
        if not main_dir.exists():
            print(f"Warning: Directory not found: {main_dir}, skipping...")
            continue
        
        try:
            process_single_directory(
                main_dir=main_dir,
                roi_x=roi_x,
                roi_y=roi_y,
                roi_width=roi_width,
                roi_height=roi_height,
                uvvis_abs_threshold=uvvis_abs_threshold,
                coverage_threshold=coverage_threshold,
                metadata_base=metadata_base,
            )
        except Exception as e:
            print(f"Error processing {main_dir}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n{'='*60}")
    print("All directories processed!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
