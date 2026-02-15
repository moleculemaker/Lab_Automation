from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import cv2
import numpy as np

from .config import UniformityConfig
# analyze_image is only used inside compute_uniformity_score function, so use lazy import


# Ideal (Perfect) Reference statistics (used when reference is not available)
MODEL_REF_STD = 2.3
MODEL_REF_ENTROPY = 2.9


def analyze_uniformity(
    ref_stats: Dict[str, float],
    cfg: UniformityConfig,
    use_model_reference: bool = False,
) -> Tuple[float, Dict[str, float]]:
    """Calculate Uniformity Score using Reference-based Absolute Scoring (RAS) method.
    
    Args:
        ref_stats: Dictionary containing Reference and Sample statistics
            - ref_std: Reference S channel standard deviation (None if not available)
            - ref_entropy: Reference S channel entropy (None if not available)
            - sample_std: Sample S channel standard deviation
            - sample_entropy: Sample S channel entropy
        cfg: UniformityConfig object (includes sensitivity parameters)
        use_model_reference: If True, use ideal reference (default: False)
        
    Returns:
        (uniformity_score, debug_info)
        - uniformity_score: float value between 0 and 1
        - debug_info: Contains all intermediate calculation values (including use_model_reference flag)
    """
    sample_std = ref_stats.get("sample_std", 0.0)
    sample_entropy = ref_stats.get("sample_entropy", 0.0)
    
    # Reference statistics: use actual reference if available, otherwise use ideal reference
    if use_model_reference or ref_stats.get("ref_std") is None:
        ref_std = MODEL_REF_STD
        ref_entropy = MODEL_REF_ENTROPY
        use_model_reference = True
    else:
        ref_std = ref_stats.get("ref_std", 0.0)
        ref_entropy = ref_stats.get("ref_entropy", 0.0)
    
    # Step 1: Roughness Score (Std)
    delta_std = max(0.0, sample_std - ref_std)
    score_std = np.exp(-delta_std / cfg.uniformity_std_sensitivity)
    
    # Step 2: Texture Score (Entropy)
    delta_ent = max(0.0, sample_entropy - ref_entropy)
    score_ent = np.exp(-delta_ent / cfg.uniformity_ent_sensitivity)
    
    # Step 3: Final Score
    final_score = (score_std * 0.5) + (score_ent * 0.5)
    
    debug_info: Dict[str, float] = {
        "ref_std": ref_std,
        "ref_entropy": ref_entropy,
        "sample_std": sample_std,
        "sample_entropy": sample_entropy,
        "delta_std": delta_std,
        "delta_entropy": delta_ent,
        "score_std": float(score_std),
        "score_entropy": float(score_ent),
        "uniformity_std_sensitivity": cfg.uniformity_std_sensitivity,
        "uniformity_ent_sensitivity": cfg.uniformity_ent_sensitivity,
        "use_model_reference": 1.0 if use_model_reference else 0.0,  # Convert bool to float
        "uniformity_score": float(final_score),
    }
    
    return float(final_score), debug_info


def compute_uniformity_score(
    image_path: str,
    metadata: Dict[str, Any] | None = None,
    verbose: bool = False,
) -> float:
    """Calculate temporary Uniformity score based on coverage."""
    # Lazy import to avoid circular dependency
    from .pipeline import analyze_image

    image_path_obj = Path(image_path)
    if not image_path_obj.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image_bgr = cv2.imread(str(image_path_obj))
    if image_bgr is None:
        raise ValueError(f"Could not load image: {image_path}")

    metadata = metadata or {}
    cfg = _create_config_from_metadata(metadata, image_path_obj)

    reference_bgr = None
    if cfg.use_reference:
        ref_path = _match_reference_for(image_path_obj, cfg.reference_dir, cfg.reference_name)
        if ref_path is not None and ref_path.exists():
            reference_bgr = cv2.imread(str(ref_path))
        elif verbose:
            print(f"[WARN] Reference not found for {image_path_obj.name}")

    metrics, *_ = analyze_image(
        image_bgr=image_bgr,
        cfg=cfg,
        ref_bgr=reference_bgr,
        image_path=image_path_obj,
    )

    # Use new CV-based uniformity score (full ROI based)
    uniformity_score = metrics.get("uniformity_score")
    if uniformity_score is not None:
        return float(uniformity_score)
    
    # Fallback: coverage percentage (previous method)
    coverage_pct = metrics.get("coverage_percentage")
    if coverage_pct is None:
        return 0.0
    return float(coverage_pct)


def _create_config_from_metadata(metadata: Dict[str, Any], image_path: Path) -> UniformityConfig:
    return UniformityConfig(
        input_dir=str(image_path.parent),
        use_reference=metadata.get("reference_dir") is not None,
        reference_dir=metadata.get("reference_dir"),
        reference_name=metadata.get("reference_name", "background_normal_0deg"),
        roi_x=metadata.get("roi_x", 0),
        roi_y=metadata.get("roi_y", 0),
        roi_width=metadata.get("roi_width", 100),
        roi_height=metadata.get("roi_height", 100),
        uvvis_dir=metadata.get("uvvis_dir"),
        uvvis_abs_threshold=metadata.get("uvvis_abs_threshold", 0.1),
        uvvis_wavelength_min=metadata.get("uvvis_wavelength_min", 300.0),
        uvvis_wavelength_max=metadata.get("uvvis_wavelength_max", 800.0),
        coverage_threshold=metadata.get("coverage_threshold", 0.1),
        coverage_smoothing=metadata.get("coverage_smoothing", 1.5),
        coverage_k=metadata.get("coverage_k", 3.0),
        coverage_min_std=metadata.get("coverage_min_std", 10.0),
        uniformity_std_sensitivity=metadata.get("uniformity_std_sensitivity", 20.0),
        uniformity_ent_sensitivity=metadata.get("uniformity_ent_sensitivity", 3.0),
        compute_learning_features=metadata.get("compute_learning_features", False),
    )


def _match_reference_for(
    image_path: Path,
    reference_dir: str | None,
    reference_name: str | None,
) -> Path | None:
    """Find image matching reference_name pattern within reference_dir."""

    search_dir = Path(reference_dir) if reference_dir else image_path.parent
    if reference_name:
        for candidate in sorted(search_dir.iterdir()):
            if candidate.is_file() and candidate.stem.startswith(reference_name):
                return candidate

    if reference_dir:
        same_name = Path(reference_dir) / image_path.name
        try:
            if same_name.exists() and same_name.resolve() != image_path.resolve():
                return same_name
        except Exception:
            if same_name.exists() and str(same_name) != str(image_path):
                return same_name

    return None

