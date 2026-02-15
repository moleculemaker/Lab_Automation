# PProDOT Demo Campaign

A project for optimizing PProDOT film manufacturing through image analysis and Bayesian optimization.

## Overview

This project provides tools for:
- **Image Analysis**: Analyzing film coverage and uniformity from sample images
- **UV-Vis Analysis**: Processing UV-Vis spectroscopy data
- **Bayesian Optimization**: Optimizing manufacturing parameters (Speed, Temperature, Gap, Volume) using constrained Bayesian optimization

## Project Structure

```
PProDOT_Demo_campaign/
├── Image_processing/          # Image analysis module
│   ├── __init__.py           # Module exports
│   ├── config.py             # Configuration dataclass (UniformityConfig)
│   ├── coverage.py           # HSV-based film coverage analysis
│   ├── pipeline.py           # Main image analysis pipeline
│   ├── scoring.py            # Uniformity score calculation
│   └── uvvis.py              # UV-Vis data analysis
├── constrained_bo_ver2.py    # Constrained Bayesian Optimizer
├── image_processing_changhyun.py  # Batch image processing script
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Module Descriptions

### Image_processing Module

A comprehensive image analysis module for evaluating film quality.

#### `config.py` - UniformityConfig
Configuration dataclass that holds all analysis parameters:
- ROI (Region of Interest) coordinates
- Reference image settings
- UV-Vis analysis thresholds
- Coverage and uniformity calculation parameters

**Usage:**
```python
from Image_processing import UniformityConfig

cfg = UniformityConfig(
    roi_x=580,
    roi_y=400,
    roi_width=913,
    roi_height=415,
    reference_dir="path/to/reference",
    uvvis_dir="path/to/uvvis",
    coverage_threshold=0.1,
    uniformity_std_sensitivity=15.0,
    uniformity_ent_sensitivity=2.0
)
```

#### `coverage.py` - Film Coverage Analysis
HSV-based film coverage analysis module. Instead of traditional reference subtraction, it uses:
- Dynamic thresholds based on reference image S-channel statistics
- Sample image HSV information
- Otsu thresholding on V channel for dark regions

**Key Functions:**
- `analyze_film_coverage()`: Main function that calculates coverage percentage and generates masks

**Returns:**
- Coverage percentage (0-1)
- Sample and reference ROI images
- Binary mask showing film regions
- Debug information dictionary

#### `pipeline.py` - Analysis Pipeline
Main pipeline that orchestrates the entire analysis process:
- Loads and processes images
- Analyzes coverage
- Calculates uniformity scores
- Processes UV-Vis data if available

**Key Functions:**
- `analyze_image()`: Complete analysis pipeline for a single image

#### `scoring.py` - Uniformity Scoring
Calculates uniformity scores using Reference-based Absolute Scoring (RAS):
- Compares sample statistics (std, entropy) with reference
- Uses ideal reference model when actual reference is unavailable
- Returns score between 0 and 1

**Key Functions:**
- `analyze_uniformity()`: Calculate uniformity score from statistics
- `compute_uniformity_score()`: High-level function to compute score from image path

#### `uvvis.py` - UV-Vis Analysis
Processes UV-Vis spectroscopy CSV files:
- Finds matching UV-Vis files based on sample ID
- Extracts absorbance data
- Checks against thresholds

**Key Functions:**
- `analyze_uvvis_data()`: Analyze UV-Vis file and return statistics
- `find_uvvis_file()`: Locate UV-Vis file for a given image

### constrained_bo_ver2.py

Constrained Bayesian Optimization system for parameter optimization.

**Purpose:** Optimizes manufacturing parameters (Speed, Temperature, Gap, Precursor Volume) to maximize uniformity score while satisfying constraints (UV-Vis ≥ 0.1 AND Coverage ≥ 0.9).

**Key Features:**
- **Objective Model**: Learns uniformity_score from valid samples only
- **Constraint Model**: Learns P(valid|x) from all samples
- **Acquisition Function**: EI(x) × P(valid|x)
- Handles discrete parameters (Temperature, Gap, Volume)
- Log-scale handling for Speed parameter
- Avoids duplicate parameter combinations

**Usage:**
```python
from constrained_bo_ver2 import ConstrainedBayesianOptimizer
import torch

# Define parameter bounds: [Speed, Temperature, gap, volume]
bounds = torch.tensor([
    [0.01, 20.0],      # Speed
    [25.0, 107.0],     # Temperature
    [50, 200],         # Gap
    [5, 15]            # Volume
]).T

# Initialize optimizer
optimizer = ConstrainedBayesianOptimizer(
    bounds=bounds,
    csv_path='data/Round0_3/PProDOT_CB_Campaign_parameters.csv',
    round_num=0,
    batch_size=8,
    discrete_or_not=[False, True, True, True],
    discrete_points=[...]  # Discrete values for each parameter
)

# Suggest candidates
candidates, metadata = optimizer.suggest()

# Save to CSV
optimizer.save_candidates_to_csv(candidates, metadata=metadata)
```

**Input CSV Format:**
The CSV should contain columns:
- `round#`, `Sample #`
- `Speed`, `Temperature`, `gap`, `Precursor Volume`
- `uvvis_max_abs`, `coverage_percentage`, `uniformity_score`

### image_processing_changhyun.py

Batch image processing script for analyzing multiple directories of images.

**Purpose:** Processes images from multiple directories, calculates metrics, and saves results to CSV files.

**Features:**
- Processes images from specified directories
- Matches images with reference and UV-Vis data
- Generates debug mask images with analysis results
- Saves comprehensive results to CSV

**Usage:**
```python
# Edit main() function to specify directories
main_dirs = [
    Path("data/Round0"),
    Path("data/Round0_1"),
    # Add more directories...
]

# Run the script
python image_processing_changhyun.py
```

**Directory Structure Expected:**
```
data/
└── Round0/
    ├── Raw/              # Sample images (e.g., R0S01.png)
    ├── blank/            # Reference images
    ├── UV-Vis/           # UV-Vis CSV files
    └── PProDOT_CB_Campaign_parameters.csv  # Parameter data
```

**Output:**
- `processing_results_simple.csv`: Analysis results with all metrics
- `Debug_Masks/`: Visual debug images showing analysis results

## Setup

### Virtual Environment Activation

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
.\venv\Scripts\activate.bat
```

### Package Installation

```powershell
pip install -r requirements.txt
```

## Dependencies

- **numpy**: Numerical computations
- **opencv-python**: Image processing
- **pandas**: Data manipulation
- **scikit-image**: Image analysis utilities
- **torch**: PyTorch for Bayesian optimization
- **botorch**: Bayesian optimization library
- **gpytorch**: Gaussian process models

## Workflow

### 1. Image Analysis Workflow

1. **Prepare Data Structure:**
   - Organize images in `Raw/` directory
   - Place reference images in `blank/` directory
   - Add UV-Vis CSV files to `UV-Vis/` directory

2. **Run Batch Processing:**
   ```python
   python image_processing_changhyun.py
   ```

3. **Review Results:**
   - Check `processing_results_simple.csv` for metrics
   - Review `Debug_Masks/` for visual analysis

### 2. Bayesian Optimization Workflow

1. **Prepare CSV with Initial Data:**
   - Include parameter values and corresponding metrics
   - Ensure columns: `round#`, `Sample #`, `Speed`, `Temperature`, `gap`, `Precursor Volume`, `uvvis_max_abs`, `coverage_percentage`, `uniformity_score`

2. **Run Optimization:**
   ```python
   python constrained_bo_ver2.py
   ```

3. **Review Suggestions:**
   - Check generated candidates
   - Check metadata (EI, P(valid), scores))
   - New candidates are saved to CSV

4. **Iterate:**
   - Run experiments with suggested parameters
   - Add results to CSV
   - Update `round_num` and run again

## Key Concepts

### Coverage Analysis
- Uses HSV color space for better film detection
- Dynamic threshold based on reference S-channel statistics
- Combines saturation and value channel analysis

### Uniformity Score
- Reference-based Absolute Scoring (RAS) method
- Compares sample roughness (std) and texture (entropy) with reference
- Score ranges from 0 (poor) to 1 (excellent)

### Validity Constraints
- **UV-Vis constraint**: `uvvis_max_abs >= 0.1`
- **Coverage constraint**: `coverage_percentage >= 0.9`
- Only valid samples are used for objective model training

### Bayesian Optimization
- Uses Gaussian Process (GP) models for both objective and constraints
- Acquisition function balances exploration and exploitation
- Handles discrete and continuous parameters appropriately

## Notes

- Speed parameter is handled in log scale for better optimization
- Reference images should be named with prefix matching `reference_name` (default: "background_normal_0deg")
- Image filenames should follow pattern: `R{round#}S{sample#}.{ext}` (e.g., R0S01.png)
- UV-Vis files should match pattern: `{round_sample_id}_*.csv` (e.g., R0S01_*.csv)

## Troubleshooting

**Issue: Reference images not found**
- Check `reference_dir` path in configuration
- Verify reference image naming matches `reference_name` pattern

**Issue: UV-Vis files not found**
- Ensure UV-Vis directory path is correct
- Check filename pattern matches sample ID extraction

**Issue: Low uniformity scores**
- Adjust `uniformity_std_sensitivity` and `uniformity_ent_sensitivity` parameters
- Review ROI coordinates to ensure correct region is analyzed

**Issue: BO not suggesting good candidates**
- Check if enough valid samples exist in CSV
- Verify constraint thresholds are appropriate
- Review objective model predictions in metadata
