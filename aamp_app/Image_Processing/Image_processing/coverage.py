"""HSV-based film coverage analysis module.

Instead of the traditional reference subtraction approach,
this module calculates coverage by combining dynamic thresholds
based on reference image S-channel statistics with sample image HSV information.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Dict

import cv2
import numpy as np
from skimage.measure import shannon_entropy


@dataclass
class ROIParams:
    x: int
    y: int
    width: int
    height: int


def _clamp_roi(image: np.ndarray, roi: ROIParams) -> ROIParams:
    """Clamp ROI to ensure it stays within image boundaries."""
    h, w = image.shape[:2]
    x = max(0, min(roi.x, w - 1))
    y = max(0, min(roi.y, h - 1))
    width = max(1, min(roi.width, w - x))
    height = max(1, min(roi.height, h - y))
    return ROIParams(x, y, width, height)


def _extract_roi(image: np.ndarray, roi: ROIParams) -> np.ndarray:
    """Extract the image region corresponding to the clamped ROI."""
    roi = _clamp_roi(image, roi)
    return image[roi.y:roi.y + roi.height, roi.x:roi.x + roi.width]


def _ensure_same_shape(sample_roi: np.ndarray, reference_roi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Resize reference ROI if sample and reference ROI sizes differ."""
    if sample_roi.shape[:2] == reference_roi.shape[:2]:
        return sample_roi, reference_roi
    resized_ref = cv2.resize(reference_roi, (sample_roi.shape[1], sample_roi.shape[0]))
    return sample_roi, resized_ref


def _apply_mask_smoothing(mask: np.ndarray, sigma: float) -> np.ndarray:
    """Apply Gaussian blur to reduce noise."""
    if sigma <= 0:
        return mask
    blurred = cv2.GaussianBlur(mask, (0, 0), sigma)
    return (blurred > 127).astype(np.uint8) * 255


def analyze_film_coverage(
    image: np.ndarray,
    reference: np.ndarray,
    roi_x: int,
    roi_y: int,
    roi_width: int,
    roi_height: int,
    smoothing: float = 1.5,
    k: float = 3.0,
    min_std: float = 10.0,
) -> Tuple[float, np.ndarray, np.ndarray, np.ndarray, Dict[str, float]]:
    """HSV-based film coverage analysis.

    Args:
        image: Sample BGR image
        reference: Reference BGR image
        roi_x, roi_y, roi_width, roi_height: ROI coordinates
        smoothing: Gaussian sigma for mask post-processing
        k: Standard deviation multiplier for dynamic threshold
        min_std: Minimum value to use when standard deviation is 0

    Returns:
        (coverage_pct, sample_roi_bgr, reference_roi_bgr, final_mask, debug_info)
    """
    roi = ROIParams(roi_x, roi_y, roi_width, roi_height)
    sample_roi = _extract_roi(image, roi)
    reference_roi = _extract_roi(reference, roi)
    sample_roi, reference_roi = _ensure_same_shape(sample_roi, reference_roi)

    # Convert to HSV
    sample_hsv = cv2.cvtColor(sample_roi, cv2.COLOR_BGR2HSV)
    reference_hsv = cv2.cvtColor(reference_roi, cv2.COLOR_BGR2HSV)

    # Reference S channel statistics
    ref_s = reference_hsv[:, :, 1].astype(np.float32)
    ref_s_mean = float(np.mean(ref_s))
    ref_s_std = float(np.std(ref_s))
    effective_std = ref_s_std if ref_s_std > 0 else float(min_std)
    saturation_threshold = float(np.clip(ref_s_mean + k * effective_std, 0, 255))

    # Condition A: S channel dynamic threshold
    sample_s = sample_hsv[:, :, 1].astype(np.float32)
    condition_a = sample_s > saturation_threshold

    # Condition B: V channel Otsu (dark regions)
    sample_v = sample_hsv[:, :, 2].astype(np.uint8)
    otsu_threshold, otsu_mask = cv2.threshold(
        sample_v, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    condition_b = otsu_mask > 0

    # Final mask
    final_mask = np.logical_or(condition_a, condition_b).astype(np.uint8) * 255
    final_mask = _apply_mask_smoothing(final_mask, smoothing)

    total_pixels = final_mask.size
    film_pixels = int(np.sum(final_mask > 0))
    coverage_percentage = float(film_pixels) / float(total_pixels) if total_pixels else 0.0

    # Reference statistics (for Uniformity calculation)
    ref_s_uint8 = reference_hsv[:, :, 1].astype(np.uint8)
    ref_entropy = float(shannon_entropy(ref_s_uint8))
    
    # Sample statistics (for Uniformity calculation)
    sample_s_uint8 = sample_hsv[:, :, 1].astype(np.uint8)
    sample_std = float(np.std(sample_s_uint8.astype(np.float32)))
    sample_entropy = float(shannon_entropy(sample_s_uint8))
    
    debug_info: Dict[str, float] = {
        "coverage_percentage": coverage_percentage,
        "roi_width": float(sample_roi.shape[1]),
        "roi_height": float(sample_roi.shape[0]),
        "ref_s_mean": ref_s_mean,
        "ref_s_std": ref_s_std,
        "effective_std": effective_std,
        "saturation_threshold": saturation_threshold,
        "k_value": k,
        "min_std_floor": min_std,
        "otsu_threshold": float(otsu_threshold),
        "condition_a_pixels": int(np.sum(condition_a)),
        "condition_b_pixels": int(np.sum(condition_b)),
        "film_pixels": film_pixels,
        "total_pixels": int(total_pixels),
        # Reference statistics (for Uniformity calculation)
        "ref_std": ref_s_std,
        "ref_entropy": ref_entropy,
        "sample_std": sample_std,
        "sample_entropy": sample_entropy,
    }

    return coverage_percentage, sample_roi, reference_roi, final_mask, debug_info

