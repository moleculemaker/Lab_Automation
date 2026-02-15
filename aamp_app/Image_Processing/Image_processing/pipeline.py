from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np

from .config import UniformityConfig
from .coverage import analyze_film_coverage
from .scoring import analyze_uniformity
from .uvvis import analyze_uvvis_data


def analyze_image(
    image_name,
    fs,
    image_bgr: np.ndarray,
    cfg: UniformityConfig,
    ref_bgr: np.ndarray | None = None,
) -> Tuple[
    Dict[str, Any],
    np.ndarray | None,
    np.ndarray | None,
    np.ndarray | None,
    Dict[str, Any] | None,
]:
    """Simplified coverage analysis pipeline."""

    sample_roi = None
    reference_roi = None
    coverage_mask = None
    coverage_debug: Dict[str, Any] | None = None

    metrics: Dict[str, Any] = {
        "coverage_percentage": None,
        "coverage_threshold_met": False,
        "sample_status": "reference_missing" if cfg.use_reference else "reference_not_required",
    }

    if image_bgr is None:
        metrics["sample_status"] = "image_not_loaded"
        return metrics, sample_roi, reference_roi, coverage_mask, coverage_debug

    if cfg.use_reference and ref_bgr is None:
        metrics["coverage_reason"] = "reference_not_found"
        return metrics, sample_roi, reference_roi, coverage_mask, coverage_debug

    uvvis_stats: Dict[str, Any] | None = None
    if image_name is not None:
        uvvis_passed, uvvis_stats = analyze_uvvis_data(
            image_name=image_name,
            fs=fs,
            campaign_id=cfg.campaign_id,
            abs_threshold=cfg.uvvis_abs_threshold,
            wavelength_min=cfg.uvvis_wavelength_min,
            wavelength_max=cfg.uvvis_wavelength_max,
        )
        metrics["uvvis_passed"] = uvvis_passed
        metrics["uvvis_reason"] = uvvis_stats.get("uvvis_reason") if uvvis_stats else None

    reference = ref_bgr if ref_bgr is not None else image_bgr

    coverage_pct, sample_roi, reference_roi, mask, debug_info = analyze_film_coverage(
        image=image_bgr,
        reference=reference,
        roi_x=cfg.roi_x,
        roi_y=cfg.roi_y,
        roi_width=cfg.roi_width,
        roi_height=cfg.roi_height,
        smoothing=cfg.coverage_smoothing,
        k=cfg.coverage_k,
        min_std=cfg.coverage_min_std,
    )

    coverage_mask = mask
    coverage_debug = debug_info

    threshold_met = coverage_pct >= cfg.coverage_threshold
    status = "coverage_pass" if threshold_met else "coverage_fail"
    comparator = ">=" if threshold_met else "<"

    metrics = {
        "coverage_percentage": coverage_pct,
        "coverage_threshold_met": threshold_met,
        "sample_status": status,
        "coverage_reason": f"coverage {coverage_pct:.3f} {comparator} threshold {cfg.coverage_threshold:.3f}",
    }

    for key, value in debug_info.items():
        metrics[f"coverage_{key}"] = value

    # Uniformity Score calculation (Reference-based Absolute Scoring)
    # ref_stats is already included in debug_info (calculated in coverage.py)
    # May return None if reference is not available
    ref_stats = {
        "ref_std": debug_info.get("ref_std"),  # May be None
        "ref_entropy": debug_info.get("ref_entropy"),  # May be None
        "sample_std": debug_info.get("sample_std", 0.0),
        "sample_entropy": debug_info.get("sample_entropy", 0.0),
    }
    
    # Use ideal reference if reference is not available
    use_model_ref = (ref_stats.get("ref_std") is None) or (not cfg.use_reference or ref_bgr is None)
    
    if sample_roi is not None:
        uniformity_score, uniformity_debug = analyze_uniformity(ref_stats, cfg, use_model_reference=use_model_ref)
        metrics["uniformity_score"] = uniformity_score
        for key, value in uniformity_debug.items():
            metrics[f"uniformity_{key}"] = value
        # Also add to coverage_debug
        if coverage_debug is not None:
            coverage_debug.update(uniformity_debug)
    else:
        # Set default value if sample ROI is not available
        metrics["uniformity_score"] = None
        if coverage_debug is not None:
            coverage_debug["uniformity_score"] = None

    if uvvis_stats:
        metrics.update(uvvis_stats)

    return metrics, sample_roi, reference_roi, coverage_mask, coverage_debug

