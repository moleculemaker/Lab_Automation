from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from bson import ObjectId


@dataclass
class UniformityConfig:
    """Lightweight configuration object.

    Maintains compatibility with the existing imageproc.uniformity.config interface
    by keeping the same field names.
    """

    campaign_id: Optional[ObjectId] = None
    use_reference: bool = True
    reference_name: str = "background_normal_0deg"

    roi_x: int = 0
    roi_y: int = 0
    roi_width: int = 100
    roi_height: int = 100

    uvvis_abs_threshold: float = 0.1
    uvvis_wavelength_min: float = 300.0
    uvvis_wavelength_max: float = 800.0
    uvvis_required: bool = False

    coverage_threshold: float = 0.1
    coverage_smoothing: float = 1.5
    # Sigma multiplier (K value) used in HSV S channel threshold calculation. Adjust default value here if needed.
    coverage_k: float = 3.0
    coverage_min_std: float = 10.0

    # Uniformity calculation sensitivity parameters (for Reference-based Absolute Scoring)
    uniformity_std_sensitivity: float = 15.0  # K1: Sensitivity to Std difference
    uniformity_ent_sensitivity: float = 2.0   # K2: Sensitivity to Entropy difference

    compute_learning_features: bool = False

    extra: dict = field(default_factory=dict)

    @property
    def roi_bbox(self) -> tuple[int, int, int, int]:
        return (self.roi_x, self.roi_y, self.roi_width, self.roi_height)

