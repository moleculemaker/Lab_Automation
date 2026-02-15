"""Custom image processing pipeline for coverage analysis."""

from .config import UniformityConfig
from .coverage import analyze_film_coverage
from .pipeline import analyze_image
from .scoring import compute_uniformity_score, _match_reference_for
from .uvvis import analyze_uvvis_data, find_uvvis_file

__all__ = [
    "UniformityConfig",
    "analyze_film_coverage",
    "analyze_image",
    "compute_uniformity_score",
    "_match_reference_for",
    "analyze_uvvis_data",
    "find_uvvis_file",
]

