#!/usr/bin/env python3
"""
Active Learning Script for PProDOT Film Optimization (v4).

Phase 3: Active Learning & Mapping
- Step 1: Repeated Stratified 5-Fold CV for model validation
- Step 2: Uncertainty-based active learning suggestion

v3 Changes:
- CV predictions are now clipped to match training data clipping
  (pred_abs clipped to [0, 2.0], pred_cov clipped to [0, 1.0])
  This ensures consistency between training data and predictions for R² calculation.

v4 Changes:
- Added predicted values (pred_abs, pred_cov, pred_uni) to suggestions CSV
- Added uncertainty values (sigma_abs, sigma_cov, sigma_uni) to suggestions CSV
- Column order: score, p_valid, score_raw, predictions, uncertainties, weights, contributions, etc.
"""

import torch
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Tuple, Dict, List, Optional
from scipy.stats import norm
import random
import warnings
warnings.filterwarnings('ignore')

# BoTorch imports
from botorch.models import SingleTaskGP
from botorch.fit import fit_gpytorch_mll
from botorch.optim import optimize_acqf
from botorch.utils.transforms import normalize, unnormalize
from botorch.utils.sampling import draw_sobol_samples

# GPyTorch imports
from gpytorch.mlls import ExactMarginalLogLikelihood
from gpytorch.kernels import ScaleKernel, RBFKernel
from gpytorch.priors import GammaPrior

# Scikit-learn imports
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.metrics import r2_score, mean_squared_error, accuracy_score


# ============================================================================
# Configuration
# ============================================================================

# Parameter bounds (original scale) - Same as constrained_bo_ver2.py
BOUNDS_ORIGINAL = torch.tensor([
    [0.01, 20.0],      # Speed
    [25.0, 107.0],     # Temperature
    [50.0, 200.0],     # Gap
    [5.0, 15.0]        # Volume
]).T

# Log scale parameters
LOG_SCALE_PARAMS = [True, False, False, False]  # Only Speed is log scale

# UV-Vis clipping threshold
UVVIS_CLIP_THRESHOLD = 2.0

# Valid thresholds (Phase 3: Mapping focus - lower threshold for coverage)
VALID_ABS_THRESHOLD = 0.1
VALID_COV_THRESHOLD = 0.1  # Phase 3: Any film formation is considered valid for mapping
UVVIS_THRESHOLD = VALID_ABS_THRESHOLD  # Alias for backward compatibility
COVERAGE_THRESHOLD = VALID_COV_THRESHOLD  # Alias for backward compatibility

# Hard cutoff for P(valid) in active learning
HARD_CUTOFF_P_VALID = 0.05

# CV settings
N_SPLITS = 5
N_REPEATS = 5

# Active Learning settings
SOBOL_GRID_SIZE = 3000
BATCH_SIZE = 8

UNI_CLIP_PERCENTILE = 95  # Clip σ_Uni at 95th percentile

# Output Settings
SOLVENT = "CB"
CONCENTRATION = 40

# Random Seed
SEED = 42


# ============================================================================
# Data Loading & Preprocessing
# ============================================================================

def load_and_preprocess_data(csv_path: Path, round_num: Optional[int] = None) -> Tuple[pd.DataFrame, int, torch.Tensor]:
    """
    Load CSV and preprocess data.
    Also loads previous round suggestions for round-level diversity.
    
    Args:
        csv_path: Path to CSV file
        round_num: Round number to use (uses data from rounds <= round_num). 
                   If None, uses maximum round in CSV.
    
    Returns:
        df: Preprocessed DataFrame with Valid column (filtered by round_num if specified)
        current_round: Round number used (round_num if specified, else max round in data)
        X_prev_suggestions: Previous round suggestions as tensor (n_prev, 4) or None
    """
    print("=" * 60)
    print("[Data] Loading and preprocessing...")
    print("=" * 60)
    
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"  Loaded {len(df)} rows from {csv_path}")
    
    # Filter by round number if specified (similar to constrained_bo_ver2.py)
    if round_num is not None and 'round#' in df.columns:
        df = df[df['round#'] <= round_num].copy()
        if len(df) == 0:
            raise ValueError(f"No data found for round {round_num} in {csv_path}")
        rounds_used = sorted(df['round#'].unique().tolist())
        print(f"  Using data from rounds: {rounds_used} (round_num={round_num})")
        if -1 in rounds_used:
            print(f"  (Includes historical data from round -1)")
        current_round = round_num
    elif 'round#' in df.columns:
        current_round = int(df['round#'].max())
        print(f"  Current round (auto-detected): {current_round}")
    else:
        current_round = 0
        print(f"  Warning: No 'round#' column found, assuming round 0")
    
    # Clip uvvis_max_abs to 2.0
    if 'uvvis_max_abs' in df.columns:
        # Drop NaNs in uvvis_max_abs
        n_nans = df['uvvis_max_abs'].isna().sum()
        if n_nans > 0:
            print(f"  Dropping {n_nans} rows with NaN uvvis_max_abs")
            df = df.dropna(subset=['uvvis_max_abs'])
            
        n_clipped = (df['uvvis_max_abs'] > UVVIS_CLIP_THRESHOLD).sum()
        if n_clipped > 0:
            print(f"  Clipping {n_clipped} uvvis_max_abs values > {UVVIS_CLIP_THRESHOLD} to {UVVIS_CLIP_THRESHOLD}")
            df['uvvis_max_abs'] = df['uvvis_max_abs'].clip(upper=UVVIS_CLIP_THRESHOLD)
            
    if 'coverage_percentage' in df.columns:
        n_nans = df['coverage_percentage'].isna().sum()
        if n_nans > 0:
            print(f"  Dropping {n_nans} rows with NaN coverage_percentage")
            df = df.dropna(subset=['coverage_percentage'])
    
    # Calculate Valid column
    if 'Valid' not in df.columns:
        df['Valid'] = (df['uvvis_max_abs'] >= UVVIS_THRESHOLD) & (df['coverage_percentage'] >= COVERAGE_THRESHOLD)
        print(f"  Calculated Valid column: {df['Valid'].sum()}/{len(df)} valid samples ({100*df['Valid'].mean():.1f}%)")
    
    # Load previous round suggestions for round-level diversity
    # Get data directory from CSV path
    csv_dir = csv_path.parent
    # Check both data_dir and results directory for previous suggestions
    results_dir_check = csv_dir / "results"
    X_prev_suggestions = None
    if current_round > 0:
        # Try results directory first, then fall back to data_dir
        prev_suggestions_path = results_dir_check / f"round{current_round}_suggestions.csv"
        if not prev_suggestions_path.exists():
            prev_suggestions_path = csv_dir / f"round{current_round}_suggestions.csv"
        if prev_suggestions_path.exists():
            print(f"  Loading previous round suggestions from {prev_suggestions_path}")
            prev_df = pd.read_csv(prev_suggestions_path)
            
            # Extract inputs from previous suggestions (same format as main data)
            if all(col in prev_df.columns for col in ['Speed', 'Temperature', 'gap', 'Precursor Volume']):
                speed_prev = prev_df['Speed'].values
                temp_prev = prev_df['Temperature'].values
                gap_prev = prev_df['gap'].values
                vol_prev = prev_df['Precursor Volume'].values
                
                # Convert Speed to log scale
                speed_prev_log = np.log10(speed_prev)
                
                # Stack inputs: [Speed_log, Temperature, gap, Volume]
                X_prev_suggestions = torch.tensor(
                    np.column_stack([speed_prev_log, temp_prev, gap_prev, vol_prev]),
                    dtype=torch.float64
                )
                print(f"  Loaded {len(X_prev_suggestions)} previous round suggestions")
            else:
                print(f"  Warning: Previous suggestions file missing required columns, skipping")
        else:
            print(f"  No previous round suggestions found (expected: {prev_suggestions_path})")
    
    # Check required columns
    required_cols = ['Speed', 'Temperature', 'gap', 'Precursor Volume', 
                     'uvvis_max_abs', 'coverage_percentage', 'uniformity_score']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    return df, current_round, X_prev_suggestions


def prepare_inputs_outputs(df: pd.DataFrame) -> Tuple[torch.Tensor, Dict[str, torch.Tensor], torch.Tensor]:
    """
    Prepare inputs (X) and outputs (Y) for model training.
    
    Returns:
        X: Input tensor (n_samples, 4) [Speed_log, Temperature, gap, Volume]
        Y_dict: Dictionary with Y_abs, Y_cov, Y_uni, Y_valid
        valid_mask: Boolean mask for valid samples (for uniformity model)
    """
    # Extract inputs
    speed = df['Speed'].values
    temperature = df['Temperature'].values
    gap = df['gap'].values
    volume = df['Precursor Volume'].values
    
    # Convert Speed to log scale
    speed_log = np.log10(speed)
    
    # Stack inputs: [Speed_log, Temperature, gap, Volume]
    X = torch.tensor(np.column_stack([speed_log, temperature, gap, volume]), dtype=torch.float64)
    
    # Extract outputs
    Y_abs = torch.tensor(df['uvvis_max_abs'].values, dtype=torch.float64).reshape(-1, 1)
    Y_cov = torch.tensor(df['coverage_percentage'].values, dtype=torch.float64).reshape(-1, 1)
    
    # Uniformity: only valid samples with non-NaN uniformity_score
    uniformity_values = df['uniformity_score'].values
    valid_mask = (df['Valid'].values) & (~pd.isna(uniformity_values))
    # Ensure valid_mask is 1D boolean array for proper indexing
    valid_mask = valid_mask.astype(bool)
    
    Y_uni = torch.tensor(uniformity_values, dtype=torch.float64).reshape(-1, 1)
    Y_valid = torch.tensor(df['Valid'].values, dtype=torch.float64).reshape(-1, 1)
    
    Y_dict = {
        'abs': Y_abs,
        'cov': Y_cov,
        'uni': Y_uni,
        'valid': Y_valid
    }
    
    return X, Y_dict, valid_mask


def create_strata(df: pd.DataFrame) -> np.ndarray:
    """
    Create stratification labels (3 groups).
    
    Groups:
        0: Valid (Abs >= 0.1 & Cov >= 0.1) - successful film
        1: Invalid & Abs >= 0.1 (thick but low coverage/fragmented)
        2: Invalid & Abs < 0.1 (thin film failure)
    """
    valid = df['Valid'].values
    abs_high = (df['uvvis_max_abs'] >= UVVIS_THRESHOLD).values
    
    strata = np.zeros(len(df), dtype=int)
    strata[valid] = 0  # Valid samples
    strata[(~valid) & (abs_high)] = 1  # Invalid but thick
    strata[(~valid) & (~abs_high)] = 2  # Invalid and thin
    
    return strata


# ============================================================================
# GP Model Building
# ============================================================================

def build_gp_model(X_normalized: torch.Tensor, Y: torch.Tensor) -> SingleTaskGP:
    """
    Build and fit a GP model.
    
    Args:
        X_normalized: Normalized input tensor (n_samples, n_dims)
        Y: Output tensor (n_samples, 1)
    
    Returns:
        Fitted GP model
    """
    model = SingleTaskGP(
        X_normalized,
        Y,
        covar_module=ScaleKernel(
            RBFKernel(
                lengthscale_prior=GammaPrior(3.0, 1.0),
                ard_num_dims=4
            ),
            outputscale_prior=GammaPrior(2.0, 0.5)
        )
    )
    
    model.train()
    mll = ExactMarginalLogLikelihood(model.likelihood, model)
    fit_gpytorch_mll(mll)
    model.eval()
    
    return model


# ============================================================================
# Step 1: Cross-Validation
# ============================================================================

def run_cross_validation(
    X: torch.Tensor,
    Y_dict: Dict[str, torch.Tensor],
    valid_mask: np.ndarray,
    strata: np.ndarray,
    bounds: torch.Tensor
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Run Repeated Stratified K-Fold Cross-Validation.
    
    Returns:
        results_df: DataFrame with CV results for all folds
        mean_r2_dict: Dictionary with mean R² scores for weighting calculation
    """
    print("\n" + "=" * 60)
    print("[CV] Running Repeated Stratified 5-Fold CV...")
    print("=" * 60)
    
    # Normalize bounds for log-scale Speed
    bounds_normalized = bounds.clone()
    for i, is_log in enumerate(LOG_SCALE_PARAMS):
        if is_log:
            bounds_normalized[0, i] = np.log10(bounds[0, i].item())
            bounds_normalized[1, i] = np.log10(bounds[1, i].item())
    
    # Check if we have enough samples per stratum
    unique_strata, counts = np.unique(strata, return_counts=True)
    min_samples_per_stratum = counts.min()
    
    if min_samples_per_stratum < N_SPLITS:
        print(f"  Warning: Minimum samples per stratum ({min_samples_per_stratum}) < n_splits ({N_SPLITS})")
        print(f"  Falling back to 2-group stratification (Valid/Invalid)")
        strata = (strata < 2).astype(int)  # Valid=True -> 0, Valid=False -> 1
    
    # Initialize CV
    rskf = RepeatedStratifiedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=42)
    
    # Store results
    results = []
    
    fold_idx = 0
    for train_idx, test_idx in rskf.split(X, strata):
        fold_idx += 1
        
        # Split data
        X_train = X[train_idx]
        X_test = X[test_idx]
        
        Y_abs_train = Y_dict['abs'][train_idx]
        Y_abs_test = Y_dict['abs'][test_idx]
        
        Y_cov_train = Y_dict['cov'][train_idx]
        Y_cov_test = Y_dict['cov'][test_idx]
        
        # Uniformity: only valid samples
        valid_train_mask = valid_mask[train_idx]
        Y_uni_test = Y_dict['uni'][test_idx]
        valid_test_mask = valid_mask[test_idx]
        
        # Normalize inputs
        X_train_norm = normalize(X_train.double(), bounds_normalized.double())
        X_test_norm = normalize(X_test.double(), bounds_normalized.double())
        
        # Build and train models
        model_abs = build_gp_model(X_train_norm, Y_abs_train)
        model_cov = build_gp_model(X_train_norm, Y_cov_train)
        
        # Uniformity model: only if we have enough valid samples (>= 2)
        if valid_train_mask.sum() >= 2:
            # Fix: First slice Y_uni by train_idx, then apply valid_train_mask
            Y_uni_train_full = Y_dict['uni'][train_idx]  # First slice by train_idx
            valid_train_mask_tensor = torch.tensor(valid_train_mask, dtype=torch.bool)
            X_uni_train = X_train[valid_train_mask_tensor]
            Y_uni_train = Y_uni_train_full[valid_train_mask_tensor]  # Then apply mask
            X_uni_train_norm = normalize(X_uni_train.double(), bounds_normalized.double())
            model_uni = build_gp_model(X_uni_train_norm, Y_uni_train)
        else:
            model_uni = None
        
        # Predictions
        with torch.no_grad():
            # Absorbance
            posterior_abs = model_abs.posterior(X_test_norm)
            pred_abs = posterior_abs.mean.squeeze(-1).cpu().numpy()
            # Clip predictions to match data clipping (consistency with training data)
            pred_abs = np.clip(pred_abs, 0.0, UVVIS_CLIP_THRESHOLD)
            
            # Coverage
            posterior_cov = model_cov.posterior(X_test_norm)
            pred_cov = posterior_cov.mean.squeeze(-1).cpu().numpy()
            # Clip coverage to [0, 1] for physical consistency
            pred_cov = np.clip(pred_cov, 0.0, 1.0)
            
            # Uniformity (only for valid test samples)
            if model_uni is not None and valid_test_mask.sum() > 0:
                valid_test_mask_tensor = torch.tensor(valid_test_mask, dtype=torch.bool)
                X_uni_test_norm = normalize(X_test[valid_test_mask_tensor].double(), bounds_normalized.double())
                posterior_uni = model_uni.posterior(X_uni_test_norm)
                pred_uni = posterior_uni.mean.squeeze(-1).cpu().numpy()
            else:
                pred_uni = np.full(valid_test_mask.sum(), np.nan) if valid_test_mask.sum() > 0 else np.array([])
        
        # Ground truth
        true_abs = Y_abs_test.squeeze().cpu().numpy()
        true_cov = Y_cov_test.squeeze().cpu().numpy()
        if valid_test_mask.sum() > 0:
            valid_test_mask_tensor = torch.tensor(valid_test_mask, dtype=torch.bool)
            true_uni = Y_uni_test[valid_test_mask_tensor].squeeze().cpu().numpy()
        else:
            true_uni = np.array([])
        
        # Metrics
        r2_abs = r2_score(true_abs, pred_abs)
        rmse_abs = np.sqrt(mean_squared_error(true_abs, pred_abs))
        
        r2_cov = r2_score(true_cov, pred_cov)
        rmse_cov = np.sqrt(mean_squared_error(true_cov, pred_cov))
        
        if len(true_uni) > 0 and not np.isnan(pred_uni).all():
            r2_uni = r2_score(true_uni, pred_uni)
            rmse_uni = np.sqrt(mean_squared_error(true_uni, pred_uni))
        else:
            r2_uni = np.nan
            rmse_uni = np.nan
        
        # Classification accuracy (Physics-informed)
        pred_valid = (pred_abs >= UVVIS_THRESHOLD) & (pred_cov >= COVERAGE_THRESHOLD)
        true_valid = valid_test_mask
        accuracy = accuracy_score(true_valid, pred_valid)
        
        results.append({
            'fold': fold_idx,
            'repeat': (fold_idx - 1) // N_SPLITS + 1,
            'split': ((fold_idx - 1) % N_SPLITS) + 1,
            'r2_abs': r2_abs,
            'rmse_abs': rmse_abs,
            'r2_cov': r2_cov,
            'rmse_cov': rmse_cov,
            'r2_uni': r2_uni,
            'rmse_uni': rmse_uni,
            'accuracy': accuracy
        })
        
        if fold_idx % 10 == 0:
            print(f"  Completed {fold_idx}/{N_SPLITS * N_REPEATS} folds...")
    
    results_df = pd.DataFrame(results)
    
    # Summary statistics
    print("\n[CV] Summary Statistics:")
    print("-" * 60)
    for metric in ['r2_abs', 'rmse_abs', 'r2_cov', 'rmse_cov', 'r2_uni', 'rmse_uni', 'accuracy']:
        mean_val = results_df[metric].mean()
        std_val = results_df[metric].std()
        print(f"  {metric:12s}: {mean_val:8.4f} ± {std_val:8.4f}")
    
    # Compute mean R² scores for adaptive weighting
    # Handle NaN values in r2_uni (when valid samples are insufficient)
    mean_r2_abs = float(results_df['r2_abs'].mean())
    mean_r2_cov = float(results_df['r2_cov'].mean())
    mean_r2_uni = float(results_df['r2_uni'].dropna().mean()) if results_df['r2_uni'].notna().any() else 0.0
    
    mean_r2_dict = {
        'abs_r2': mean_r2_abs,
        'cov_r2': mean_r2_cov,
        'uni_r2': mean_r2_uni
    }
    
    print(f"\n[CV] Mean R² Scores (for weighting):")
    print(f"  Abs: {mean_r2_abs:.4f}, Cov: {mean_r2_cov:.4f}, Uni: {mean_r2_uni:.4f}")
    
    return results_df, mean_r2_dict


# ============================================================================
# Step 2: Active Learning Suggestion
# ============================================================================

def compute_active_learning_scores(
    models: Dict[str, SingleTaskGP],
    X_train_normalized: torch.Tensor,
    bounds_normalized: torch.Tensor,
    X_train_all: torch.Tensor,
    mean_r2_dict: Dict[str, float],
    X_prev_suggestions: torch.Tensor = None
) -> Tuple[torch.Tensor, torch.Tensor, Dict]:
    """
    Compute active learning scores using Adaptive Weighting based on CV R² scores.
    
    Args:
        models: Dictionary with 'abs', 'cov', 'uni' GP models
        X_train_normalized: Normalized training data [0, 1]
        bounds_normalized: Normalized bounds
        X_train_all: Original scale training data (for diversity calculation)
        mean_r2_dict: Dictionary with mean R² scores from CV
        X_prev_suggestions: Previous round suggestions (optional)
    
    Returns:
        candidates_normalized: Suggested candidates (in [0, 1] normalized space)
        scores: Final scores for each candidate
        metadata: Dictionary with intermediate values including weights and contributions
    """
    print("\n" + "=" * 60)
    print("[Optimization] Active Learning Suggestion...")
    print("=" * 60)
    
    # Step 0: Compute adaptive weights from CV R² scores
    print("Step 0: Computing adaptive weights from CV R² scores...")
    r2_abs = mean_r2_dict['abs_r2']
    r2_cov = mean_r2_dict['cov_r2']
    r2_uni = mean_r2_dict['uni_r2']
    
    # Raw weights: max(0.1, 1.0 - R²)
    raw_w_abs = max(0.1, 1.0 - r2_abs)
    raw_w_cov = max(0.1, 1.0 - r2_cov)
    raw_w_uni = max(0.1, 1.0 - r2_uni)
    
    # Normalize to sum to 1.0
    total_raw = raw_w_abs + raw_w_cov + raw_w_uni
    w_abs = raw_w_abs / total_raw
    w_cov = raw_w_cov / total_raw
    w_uni = raw_w_uni / total_raw
    
    print(f"  R² scores: Abs={r2_abs:.4f}, Cov={r2_cov:.4f}, Uni={r2_uni:.4f}")
    print(f"  Adaptive weights: W_Abs={w_abs:.4f}, W_Cov={w_cov:.4f}, W_Uni={w_uni:.4f}")
    
    # Step 1: Generate Sobol grid for normalization
    print(f"Step 1: Generating {SOBOL_GRID_SIZE} Sobol samples for normalization...")
    unit_bounds = torch.stack([
        torch.zeros(4, dtype=torch.float64),
        torch.ones(4, dtype=torch.float64)
    ])
    
    sobol_grid_unit = draw_sobol_samples(
        bounds=unit_bounds,
        n=1,
        q=SOBOL_GRID_SIZE
    ).squeeze(0).double()  # (SOBOL_GRID_SIZE, 4) in [0, 1]
    
    # Model expects inputs in [0, 1] normalized space (no transformation needed)
    # Use unit hypercube samples directly as model input
    sobol_grid_norm = sobol_grid_unit
    
    # Predict uncertainties on Sobol grid (all in [0, 1] normalized space)
    with torch.no_grad():
        posterior_abs = models['abs'].posterior(sobol_grid_norm)
        sigma_abs_pool = posterior_abs.stddev.squeeze(-1).cpu().numpy()
        
        posterior_cov = models['cov'].posterior(sobol_grid_norm)
        sigma_cov_pool = posterior_cov.stddev.squeeze(-1).cpu().numpy()
        
        posterior_uni = models['uni'].posterior(sobol_grid_norm)
        sigma_uni_pool = posterior_uni.stddev.squeeze(-1).cpu().numpy()
    
    # Compute normalization statistics for Abs and Cov (no clipping)
    mean_abs = sigma_abs_pool.mean()
    std_abs = sigma_abs_pool.std()
    mean_cov = sigma_cov_pool.mean()
    std_cov = sigma_cov_pool.std()
    
    # For σ_Uni: Clip first, then recompute statistics on clipped values
    # This prevents invalid region's explosive σ from making valid region's σ look too small
    uni_clip_threshold = np.percentile(sigma_uni_pool, UNI_CLIP_PERCENTILE)
    sigma_uni_pool_clipped = np.clip(sigma_uni_pool, None, uni_clip_threshold)
    mean_uni = sigma_uni_pool_clipped.mean()  # Recompute mean on clipped values
    std_uni = sigma_uni_pool_clipped.std()    # Recompute std on clipped values
    
    print(f"  Sigma statistics (Abs): mean={mean_abs:.4f}, std={std_abs:.4f}")
    print(f"  Sigma statistics (Cov): mean={mean_cov:.4f}, std={std_cov:.4f}")
    print(f"  Sigma statistics (Uni): mean={mean_uni:.4f}, std={std_uni:.4f} (after clipping at {uni_clip_threshold:.4f})")
    
    # Step 2: Generate candidate pool using Sobol sampling
    print(f"\nStep 2: Generating candidate pool (batch_size={BATCH_SIZE})...")
    
    # Generate large candidate pool using Sobol sampling
    pool_size = BATCH_SIZE * 20  # 160 candidates
    candidates_pool_unit = draw_sobol_samples(
        bounds=unit_bounds,
        n=1,
        q=pool_size * 2  # Larger pool for better diversity
    ).squeeze(0).double()  # (pool_size*2, 4) in [0, 1]
    
    # Model expects inputs in [0, 1] normalized space (no transformation needed)
    # Use unit hypercube samples directly as model input
    candidates_pool_norm = candidates_pool_unit
    
    # Compute scores for all candidates
    print(f"  Computing scores for {len(candidates_pool_norm)} candidates...")
    
    with torch.no_grad():
        # Predict uncertainties
        posterior_abs = models['abs'].posterior(candidates_pool_norm)
        mu_abs = posterior_abs.mean.squeeze(-1)
        sigma_abs = posterior_abs.stddev.squeeze(-1)
        
        posterior_cov = models['cov'].posterior(candidates_pool_norm)
        mu_cov = posterior_cov.mean.squeeze(-1)
        sigma_cov = posterior_cov.stddev.squeeze(-1)
        
        posterior_uni = models['uni'].posterior(candidates_pool_norm)
        mu_uni = posterior_uni.mean.squeeze(-1)
        sigma_uni = posterior_uni.stddev.squeeze(-1)
    
    # Apply physical constraints to predictions
    # Absorbance: Data is clipped at 2.0 during loading, so clamp predictions to [0, 2.0] for safety
    mu_abs = torch.clamp(mu_abs, 0.0, 2.0)
    
    # Coverage: Must be in [0, 1] (0% to 100%)
    # This prevents probability calculation distortion from unrealistic predictions (e.g., 1.2 or -0.1)
    mu_cov = torch.clamp(mu_cov, 0.0, 1.0)
    
    # Clip σ_Uni BEFORE normalization (clip raw sigma_uni values)
    sigma_uni_np = sigma_uni.cpu().numpy()
    sigma_uni_clipped = np.clip(sigma_uni_np, None, uni_clip_threshold)
    
    # Normalize uncertainties (after clipping for σ_Uni)
    # Convert to torch tensors for consistent type handling
    norm_sigma_abs = torch.tensor((sigma_abs.cpu().numpy() - mean_abs) / (std_abs + 1e-8), dtype=torch.float64)
    norm_sigma_cov = torch.tensor((sigma_cov.cpu().numpy() - mean_cov) / (std_cov + 1e-8), dtype=torch.float64)
    norm_sigma_uni = torch.tensor((sigma_uni_clipped - mean_uni) / (std_uni + 1e-8), dtype=torch.float64)
    
    # Compute P(valid)
    # P(valid) = P(Abs >= 0.1) * P(Cov >= 0.1)
    # Using normal approximation
    mu_abs_np = mu_abs.cpu().numpy()
    sigma_abs_np = sigma_abs.cpu().numpy()
    mu_cov_np = mu_cov.cpu().numpy()  # mu_cov is already clamped to [0, 1]
    sigma_cov_np = sigma_cov.cpu().numpy()
    
    # Calculate probabilities using clamped mu_cov (physical constraint applied)
    p_abs_high = 1 - norm.cdf((VALID_ABS_THRESHOLD - mu_abs_np) / (sigma_abs_np + 1e-8))
    p_cov_high = 1 - norm.cdf((VALID_COV_THRESHOLD - mu_cov_np) / (sigma_cov_np + 1e-8))
    
    # Combine probabilities
    p_valid = p_abs_high * p_cov_high
    
    # Clip final probability to [0, 1] range (after calculation)
    p_valid = np.clip(p_valid, 0.0, 1.0)
    
    # Convert p_valid to torch tensor to avoid type conflicts
    p_valid_tensor = torch.tensor(p_valid, dtype=torch.float64)
    
    # Compute individual terms (contributions) for each component
    term_abs = torch.tensor(w_abs, dtype=torch.float64) * norm_sigma_abs
    term_cov = torch.tensor(w_cov, dtype=torch.float64) * norm_sigma_cov
    term_uni = torch.tensor(w_uni, dtype=torch.float64) * norm_sigma_uni * (p_valid_tensor ** 2)
    
    # Compute raw score using adaptive weighting
    # Score = W_Abs * Norm(σ_Abs) + W_Cov * Norm(σ_Cov) + W_Uni * Norm(σ_Uni) * P_valid^2
    score_raw = term_abs + term_cov + term_uni
    
    # Hard cutoff: P(valid) < HARD_CUTOFF_P_VALID 이면 Score를 0으로
    score_raw[p_valid_tensor < HARD_CUTOFF_P_VALID] = 0.0
    
    # Diversity bonus (멀리 있을수록 좋음)
    print(f"  Applying diversity bonus...")
    
    # Combine current training data with previous round suggestions for round-level diversity
    if X_prev_suggestions is not None:
        X_train_all_with_prev = torch.cat([X_train_all, X_prev_suggestions], dim=0)
        print(f"  Including {len(X_prev_suggestions)} previous round suggestions in diversity calculation")
    else:
        X_train_all_with_prev = X_train_all
    
    X_train_norm = normalize(X_train_all_with_prev.double(), bounds_normalized.double())
    
    # Compute all distances at once (more efficient)
    distances = torch.cdist(candidates_pool_norm, X_train_norm)  # (n_candidates, n_train)
    min_dists = distances.min(dim=1).values  # (n_candidates,)
    
    # Diversity weight: Tanh 방식 (부드러운 변환)
    # 거리가 가까우면(0에 가까움) weight가 0에 가까워지고,
    # 거리가 멀면 weight가 1에 가까워져서 score를 보존함
    # Scale factor 0.2는 정규화된 공간(0~1)에서의 거리 감도 조절용
    diversity_weight = torch.tanh(min_dists / 0.2)
    
    # Apply diversity weight to raw scores
    scores_final = torch.tensor(score_raw, dtype=torch.float64) * diversity_weight
    
    # Compute density median (nearest neighbor distance median)
    print(f"  Computing density median...")
    # Combine all existing data points
    if X_prev_suggestions is not None:
        X_all_existing = torch.cat([X_train_normalized, normalize(X_prev_suggestions.double(), bounds_normalized.double())], dim=0)
    else:
        X_all_existing = X_train_normalized
    
    # Compute distance matrix (excluding self-distances)
    distances_all = torch.cdist(X_all_existing, X_all_existing)
    # Fill diagonal with inf to exclude self-distances
    distances_all.fill_diagonal_(float('inf'))
    # Get minimum distance for each point (nearest neighbor)
    min_dists_all = distances_all.min(dim=1).values
    # Compute median
    density_median = float(torch.median(min_dists_all).item())
    print(f"  Density median (nearest neighbor distance): {density_median:.6f}")
    
    # Select top candidates
    top_indices = torch.argsort(scores_final, descending=True)[:BATCH_SIZE]
    candidates_selected = candidates_pool_norm[top_indices]
    scores_selected = scores_final[top_indices]
    
    print(f"\n  Selected {BATCH_SIZE} candidates:")
    for i, idx in enumerate(top_indices):
        p_valid_val = p_valid_tensor[idx].item()
        print(f"    [{i+1}] Score: {scores_final[idx]:.4f}, P(valid): {p_valid_val:.4f}")
    
    # Compute contributions and primary reasons for selected candidates
    contrib_abs_selected = term_abs[top_indices].cpu().numpy()
    contrib_cov_selected = term_cov[top_indices].cpu().numpy()
    contrib_uni_selected = term_uni[top_indices].cpu().numpy()
    
    # Primary reason: which term has the maximum contribution
    primary_reasons = []
    for i in range(len(top_indices)):
        contribs = {
            'Uncertainty (Abs)': contrib_abs_selected[i],
            'Uncertainty (Cov)': contrib_cov_selected[i],
            'Uncertainty (Uni)': contrib_uni_selected[i]
        }
        primary_reason = max(contribs, key=contribs.get)
        primary_reasons.append(primary_reason)
    
    # Extract predictions and uncertainties for selected candidates
    pred_abs_selected = mu_abs[top_indices].cpu().numpy()
    pred_cov_selected = mu_cov[top_indices].cpu().numpy()
    pred_uni_selected = mu_uni[top_indices].cpu().numpy()
    sigma_abs_selected = sigma_abs[top_indices].cpu().numpy()
    sigma_cov_selected = sigma_cov[top_indices].cpu().numpy()
    sigma_uni_selected = sigma_uni[top_indices].cpu().numpy()
    
    metadata = {
        'sigma_abs_pool_mean': mean_abs,
        'sigma_abs_pool_std': std_abs,
        'sigma_cov_pool_mean': mean_cov,
        'sigma_cov_pool_std': std_cov,
        'sigma_uni_pool_mean': mean_uni,
        'sigma_uni_pool_std': std_uni,
        'uni_clip_threshold': uni_clip_threshold,
        'p_valid': p_valid_tensor[top_indices].cpu().numpy(),
        'scores_raw': score_raw[top_indices].cpu().numpy() if isinstance(score_raw, torch.Tensor) else score_raw[top_indices],
        'scores_final': scores_selected.cpu().numpy(),
        # Predictions
        'pred_abs': pred_abs_selected,
        'pred_cov': pred_cov_selected,
        'pred_uni': pred_uni_selected,
        # Uncertainties
        'sigma_abs': sigma_abs_selected,
        'sigma_cov': sigma_cov_selected,
        'sigma_uni': sigma_uni_selected,
        # Adaptive weighting
        'weight_abs': w_abs,
        'weight_cov': w_cov,
        'weight_uni': w_uni,
        'contrib_abs': contrib_abs_selected,
        'contrib_cov': contrib_cov_selected,
        'contrib_uni': contrib_uni_selected,
        'primary_reason': primary_reasons,
        'density_median': density_median
    }
    
    return candidates_selected, scores_selected, metadata


def train_all_models(df: pd.DataFrame) -> Tuple[Dict[str, SingleTaskGP], Dict[str, float], torch.Tensor, torch.Tensor]:
    """
    Train all GP models and compute normalization statistics.
    
    Args:
        df: DataFrame with accumulated data
        
    Returns:
        models: Dictionary of fitted models
        normalization_stats: Dictionary of normalization statistics
        X: Original input tensor
        bounds_normalized: Normalized bounds tensor
    """
    print("\n" + "=" * 60)
    print("[Model] Training all models...")
    print("=" * 60)
    
    # Prepare inputs and outputs
    X, Y_dict, valid_mask = prepare_inputs_outputs(df)
    
    # Prepare bounds (with log scale conversion)
    bounds_normalized = BOUNDS_ORIGINAL.clone()
    for i, is_log in enumerate(LOG_SCALE_PARAMS):
        if is_log:
            bounds_normalized[0, i] = np.log10(BOUNDS_ORIGINAL[0, i].item())
            bounds_normalized[1, i] = np.log10(BOUNDS_ORIGINAL[1, i].item())
            
    X_normalized = normalize(X.double(), bounds_normalized.double())
    
    # Build models
    model_abs = build_gp_model(X_normalized, Y_dict['abs'])
    model_cov = build_gp_model(X_normalized, Y_dict['cov'])
    
    # Uniformity model: only valid samples
    valid_mask_tensor = torch.tensor(valid_mask, dtype=torch.bool)
    if valid_mask_tensor.sum() >= 2:
        X_uni = X[valid_mask_tensor]
        Y_uni = Y_dict['uni'][valid_mask_tensor]
        X_uni_normalized = normalize(X_uni.double(), bounds_normalized.double())
        model_uni = build_gp_model(X_uni_normalized, Y_uni)
    else:
        model_uni = None
        print("  Warning: Not enough valid samples for Uniformity model")
        
    models = {
        'abs': model_abs,
        'cov': model_cov,
        'uni': model_uni
    }
    
    # Normalization statistics will be computed in compute_active_learning_scores()
    # to ensure consistency with run_active_learning.py (ver1)
    # Return empty dict here; it will be populated from metadata in main()
    # This avoids generating Sobol samples here, which would change the random state
    # and cause different suggestions than ver1
    normalization_stats = {}
    
    return models, normalization_stats, X, bounds_normalized


def calculate_model_predictions_on_grid(
    models: Dict[str, SingleTaskGP],
    stats: Dict[str, float],
    grid_tensor: torch.Tensor,
    weights: Dict[str, float]
) -> Dict[str, np.ndarray]:
    """
    Calculate model predictions and acquisition scores on a grid.
    
    Args:
        models: Dictionary of trained models
        stats: Normalization statistics
        grid_tensor: Normalized grid points (n_points, 4)
        weights: Adaptive weights {'abs': w_abs, 'cov': w_cov, 'uni': w_uni}
        
    Returns:
        Dictionary with keys:
            'mean_abs', 'mean_cov', 'mean_uni', 'p_valid',
            'std_abs', 'std_cov', 'std_uni',
            'score'
    """
    # Unpack stats
    mean_abs = stats['sigma_abs_mean']
    std_abs = stats['sigma_abs_std']
    mean_cov = stats['sigma_cov_mean']
    std_cov = stats['sigma_cov_std']
    mean_uni = stats['sigma_uni_mean']
    std_uni = stats['sigma_uni_std']
    uni_clip_threshold = stats['uni_clip_threshold']
    
    # Unpack weights
    w_abs = weights['abs']
    w_cov = weights['cov']
    w_uni = weights['uni']
    
    with torch.no_grad():
        # Predict
        posterior_abs = models['abs'].posterior(grid_tensor)
        mu_abs = posterior_abs.mean.squeeze(-1)
        sigma_abs = posterior_abs.stddev.squeeze(-1)
        
        posterior_cov = models['cov'].posterior(grid_tensor)
        mu_cov = posterior_cov.mean.squeeze(-1)
        sigma_cov = posterior_cov.stddev.squeeze(-1)
        
        if models['uni'] is not None:
            posterior_uni = models['uni'].posterior(grid_tensor)
            mu_uni = posterior_uni.mean.squeeze(-1)
            sigma_uni = posterior_uni.stddev.squeeze(-1)
        else:
            mu_uni = torch.zeros_like(mu_abs)
            sigma_uni = torch.zeros_like(sigma_abs)
            
    # Apply constraints
    mu_abs = torch.clamp(mu_abs, 0.0, 2.0)
    mu_cov = torch.clamp(mu_cov, 0.0, 1.0)
    
    # Clip sigma_uni
    sigma_uni_np = sigma_uni.cpu().numpy()
    sigma_uni_clipped = np.clip(sigma_uni_np, None, uni_clip_threshold)
    
    # Normalize uncertainties
    norm_sigma_abs = (sigma_abs.cpu().numpy() - mean_abs) / (std_abs + 1e-8)
    norm_sigma_cov = (sigma_cov.cpu().numpy() - mean_cov) / (std_cov + 1e-8)
    norm_sigma_uni = (sigma_uni_clipped - mean_uni) / (std_uni + 1e-8)
    
    # Compute P(valid)
    mu_abs_np = mu_abs.cpu().numpy()
    sigma_abs_np = sigma_abs.cpu().numpy()
    mu_cov_np = mu_cov.cpu().numpy()
    sigma_cov_np = sigma_cov.cpu().numpy()
    
    p_abs_high = 1 - norm.cdf((VALID_ABS_THRESHOLD - mu_abs_np) / (sigma_abs_np + 1e-8))
    p_cov_high = 1 - norm.cdf((VALID_COV_THRESHOLD - mu_cov_np) / (sigma_cov_np + 1e-8))
    p_valid = p_abs_high * p_cov_high
    p_valid = np.clip(p_valid, 0.0, 1.0)
    
    # Compute Score
    term_abs = w_abs * norm_sigma_abs
    term_cov = w_cov * norm_sigma_cov
    term_uni = w_uni * norm_sigma_uni * (p_valid ** 2)
    
    score = term_abs + term_cov + term_uni
    
    # Hard cutoff
    score[p_valid < HARD_CUTOFF_P_VALID] = 0.0
    
    return {
        'mean_abs': mu_abs_np,
        'mean_cov': mu_cov_np,
        'mean_uni': mu_uni.cpu().numpy(),
        'p_valid': p_valid,
        'std_abs': sigma_abs_np,
        'std_cov': sigma_cov_np,
        'std_uni': sigma_uni_np,
        'score': score
    }


# ============================================================================
# Task 1: Evaluation & Logging (New)
# ============================================================================

def get_data_density_metrics(X_norm: torch.Tensor) -> Dict[str, float]:
    """
    Compute data density metrics based on nearest neighbor distances in normalized space.
    
    Args:
        X_norm: Normalized input tensor (n_samples, n_dims)
        
    Returns:
        Dictionary with Density_Median, Density_P25, Density_P75
    """
    if len(X_norm) < 2:
        return {
            'Density_Median': 0.0, 
            'Density_P25': 0.0, 
            'Density_P75': 0.0
        }
        
    # Compute distance matrix (excluding self-distances)
    distances = torch.cdist(X_norm, X_norm)
    # Fill diagonal with inf to exclude self-distances
    distances.fill_diagonal_(float('inf'))
    
    # Get minimum distance for each point (nearest neighbor)
    min_dists = distances.min(dim=1).values
    min_dists_np = min_dists.cpu().numpy()
    
    # Compute stats
    median = float(np.median(min_dists_np))
    p25 = float(np.percentile(min_dists_np, 25))
    p75 = float(np.percentile(min_dists_np, 75))
    
    return {
        'Density_Median': median,
        'Density_P25': p25,
        'Density_P75': p75
    }


def evaluate_current_state(df: pd.DataFrame, save_cv_path: Optional[Path] = None) -> Dict[str, float]:
    """
    Evaluate current state of the campaign.
    
    Args:
        df: DataFrame with accumulated data
        save_cv_path: Optional path to save CV results CSV
        
    Returns:
        Dictionary containing all metrics (CV performance, Density, Weights)
    """
    print("\n" + "=" * 60)
    print("[Evaluation] Evaluating current state...")
    print("=" * 60)
    
    # Prepare inputs and outputs
    X, Y_dict, valid_mask = prepare_inputs_outputs(df)
    
    # Create strata
    strata = create_strata(df)
    
    # Prepare bounds (with log scale conversion)
    bounds_normalized = BOUNDS_ORIGINAL.clone()
    for i, is_log in enumerate(LOG_SCALE_PARAMS):
        if is_log:
            bounds_normalized[0, i] = np.log10(BOUNDS_ORIGINAL[0, i].item())
            bounds_normalized[1, i] = np.log10(BOUNDS_ORIGINAL[1, i].item())
            
    # 1. Density Metrics
    X_normalized = normalize(X.double(), bounds_normalized.double())
    density_metrics = get_data_density_metrics(X_normalized)
    print(f"  Density Median: {density_metrics['Density_Median']:.4f}")
    
    # 2. Cross-Validation
    cv_results, mean_r2_dict = run_cross_validation(X, Y_dict, valid_mask, strata, BOUNDS_ORIGINAL)
    
    if save_cv_path:
        cv_results.to_csv(save_cv_path, index=False)
        print(f"  CV results saved to {save_cv_path}")
        
    # 3. Adaptive Weights
    r2_abs = mean_r2_dict['abs_r2']
    r2_cov = mean_r2_dict['cov_r2']
    r2_uni = mean_r2_dict['uni_r2']
    
    raw_w_abs = max(0.1, 1.0 - r2_abs)
    raw_w_cov = max(0.1, 1.0 - r2_cov)
    raw_w_uni = max(0.1, 1.0 - r2_uni)
    
    total_raw = raw_w_abs + raw_w_cov + raw_w_uni
    w_abs = raw_w_abs / total_raw
    w_cov = raw_w_cov / total_raw
    w_uni = raw_w_uni / total_raw
    
    # Assemble Metrics
    metrics = {
        # Basic
        'Total_Samples': len(df),
        'Valid_Samples': int(df['Valid'].sum()),
        'Valid_Rate': float(df['Valid'].mean()),
        
        # CV Performance (Abs)
        'CV_Abs_R2_Mean': cv_results['r2_abs'].mean(),
        'CV_Abs_R2_Std': cv_results['r2_abs'].std(),
        'CV_Abs_RMSE_Mean': cv_results['rmse_abs'].mean(),
        
        # CV Performance (Cov)
        'CV_Cov_R2_Mean': cv_results['r2_cov'].mean(),
        'CV_Cov_R2_Std': cv_results['r2_cov'].std(),
        'CV_Cov_RMSE_Mean': cv_results['rmse_cov'].mean(),
        
        # CV Performance (Uni)
        'CV_Uni_R2_Mean': cv_results['r2_uni'].mean(),
        'CV_Uni_R2_Std': cv_results['r2_uni'].std(),
        'CV_Uni_RMSE_Mean': cv_results['rmse_uni'].mean(),
        
        # CV Performance (Accuracy)
        'CV_Valid_Acc_Mean': cv_results['accuracy'].mean(),
        'CV_Valid_Acc_Std': cv_results['accuracy'].std(),
        
        # Strategy Weights
        'W_Abs': w_abs,
        'W_Cov': w_cov,
        'W_Uni': w_uni
    }
    
    # Add Density Metrics
    metrics.update(density_metrics)
    
    return metrics


def append_progress_log(round_num: int, metrics_dict: Dict[str, float], log_path: Path):
    """
    Append metrics to the campaign progress log CSV.
    """
    # Create row dictionary
    row = {'Round': round_num}
    row.update(metrics_dict)
    
    # Create DataFrame
    df_row = pd.DataFrame([row])
    
    # Define column order (optional, but good for readability)
    cols_order = [
        'Round', 'Total_Samples', 'Valid_Samples', 'Valid_Rate',
        'CV_Abs_R2_Mean', 'CV_Abs_R2_Std', 'CV_Abs_RMSE_Mean',
        'CV_Cov_R2_Mean', 'CV_Cov_R2_Std', 'CV_Cov_RMSE_Mean',
        'CV_Uni_R2_Mean', 'CV_Uni_R2_Std', 'CV_Uni_RMSE_Mean',
        'CV_Valid_Acc_Mean', 'CV_Valid_Acc_Std',
        'Density_Median', 'Density_P25', 'Density_P75',
        'W_Abs', 'W_Cov', 'W_Uni'
    ]
    
    # Reorder columns if they exist in the row
    existing_cols = [c for c in cols_order if c in df_row.columns]
    remaining_cols = [c for c in df_row.columns if c not in cols_order]
    df_row = df_row[existing_cols + remaining_cols]
    
    # Append to file
    if not log_path.exists():
        df_row.to_csv(log_path, index=False)
        print(f"[Log] Created new progress log at {log_path}")
    else:
        df_row.to_csv(log_path, mode='a', header=False, index=False)
        print(f"[Log] Appended Round {round_num} stats to {log_path}")


# ============================================================================
# Main Function
# ============================================================================

def main():
    """Main execution function."""
    # Set random seeds for reproducibility
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    random.seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(SEED)

    # Data directory - specify directory path here
    # All files (input CSV and output files) will be in this directory
    data_dir = Path("/home/weiqizhang/Lab_Automation/aamp_app/Image_Processing/Round5")
    
    # Round number - specify which round to use (uses data from rounds <= round_num)
    # Suggestions will be generated for round_num + 1
    # round_num = 8  # Removed hardcoded value to use auto-detection or CLI if needed
    
    # Construct CSV path from directory
    csv_path = data_dir / "PProDOT_CB_Campaign_parameters.csv"
    
    # Load and preprocess data (including previous round suggestions)
    # If round_num is None, it will use the max round in the CSV
    df, current_round, X_prev_suggestions = load_and_preprocess_data(csv_path, round_num=None)
    
    # ========================================================================
    # Step 1: Evaluate Current State & Log Progress
    # ========================================================================
    
    # Create results directory if it doesn't exist
    results_dir = data_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Define paths (all output files go to results directory)
    cv_output_path = results_dir / f"cv_results_round{current_round}_v4.csv"
    progress_log_path = results_dir / "campaign_progress_v4.csv"
    
    # Evaluate
    metrics = evaluate_current_state(df, save_cv_path=cv_output_path)
    
    # Log progress
    append_progress_log(current_round, metrics, progress_log_path)
    
    # Extract mean R2 scores for adaptive weighting
    mean_r2_dict = {
        'abs_r2': metrics['CV_Abs_R2_Mean'],
        'cov_r2': metrics['CV_Cov_R2_Mean'],
        'uni_r2': metrics['CV_Uni_R2_Mean']
    }
    
    # ========================================================================
    # Step 2: Active Learning Suggestion
    # ========================================================================
    
    # Train all models
    models, normalization_stats, X, bounds_normalized = train_all_models(df)
    
    X_normalized = normalize(X.double(), bounds_normalized.double())
    
    # Compute active learning scores (with previous round suggestions for diversity)
    candidates_normalized, scores, metadata = compute_active_learning_scores(
        models, X_normalized, bounds_normalized, X, mean_r2_dict, X_prev_suggestions
    )
    
    # Update normalization_stats from metadata (for visualization)
    normalization_stats = {
        'sigma_abs_mean': metadata['sigma_abs_pool_mean'],
        'sigma_abs_std': metadata['sigma_abs_pool_std'],
        'sigma_cov_mean': metadata['sigma_cov_pool_mean'],
        'sigma_cov_std': metadata['sigma_cov_pool_std'],
        'sigma_uni_mean': metadata['sigma_uni_pool_mean'],
        'sigma_uni_std': metadata['sigma_uni_pool_std'],
        'uni_clip_threshold': metadata['uni_clip_threshold']
    }
    
    # Decode candidates to original scale
    candidates_unnorm = unnormalize(candidates_normalized, bounds_normalized.double())
    candidates_original = candidates_unnorm.clone()
    for i, is_log in enumerate(LOG_SCALE_PARAMS):
        if is_log:
            candidates_original[:, i] = 10 ** candidates_unnorm[:, i]
    
    # Round discrete parameters
    candidates_original[:, 1] = torch.round(candidates_original[:, 1])  # Temperature
    candidates_original[:, 2] = torch.round(candidates_original[:, 2])  # Gap
    candidates_original[:, 3] = torch.round(candidates_original[:, 3])  # Volume
    candidates_original[:, 0] = torch.round(candidates_original[:, 0] * 100.0) / 100.0  # Speed (2 decimals)
    
    # Save suggestions to results directory
    next_round = current_round + 1
    suggestions_path = results_dir / f"round{next_round}_suggestions_v4.csv"
    
    # Determine starting sample number
    # If we have previous data for this round (unlikely for new suggestions, but good for consistency), continue numbering
    # Otherwise start from 1
    start_sample = 1
    
    # Construct DataFrame with requested column order
    # Header: round#, Sample #, Temperature, Speed, gap, Solvent, Concentration, Precursor Volume
    
    suggestions_df = pd.DataFrame({
        'round#': [next_round] * BATCH_SIZE,
        'Sample #': range(start_sample, start_sample + BATCH_SIZE),
        'Temperature': candidates_original[:, 1].cpu().numpy().astype(int),
        'Speed': candidates_original[:, 0].cpu().numpy(),
        'gap': candidates_original[:, 2].cpu().numpy().astype(int),
        'Solvent': [SOLVENT] * BATCH_SIZE,
        'Concentration': [CONCENTRATION] * BATCH_SIZE,
        'Precursor Volume': candidates_original[:, 3].cpu().numpy().astype(int),
        
        # Metadata follows
        'score': scores.cpu().numpy(),
        'p_valid': metadata['p_valid'],
        'score_raw': metadata['scores_raw'],
        # Predictions
        'pred_abs': metadata['pred_abs'],
        'pred_cov': metadata['pred_cov'],
        'pred_uni': metadata['pred_uni'],
        # Uncertainties
        'sigma_abs': metadata['sigma_abs'],
        'sigma_cov': metadata['sigma_cov'],
        'sigma_uni': metadata['sigma_uni'],
        # Adaptive weighting information
        'Weight_Abs': [metadata['weight_abs']] * len(candidates_original),
        'Weight_Cov': [metadata['weight_cov']] * len(candidates_original),
        'Weight_Uni': [metadata['weight_uni']] * len(candidates_original),
        # Contributions
        'Contrib_Abs': metadata['contrib_abs'],
        'Contrib_Cov': metadata['contrib_cov'],
        'Contrib_Uni': metadata['contrib_uni'],
        # Primary reason and density
        'Primary_Reason': metadata['primary_reason'],
        'Density_Median': [metadata['density_median']] * len(candidates_original)
    })
    
    suggestions_df.to_csv(suggestions_path, index=False)
    print(f"\n[Optimization] Suggestions saved to {suggestions_path}")
    
    print("\n" + "=" * 60)
    print("Active Learning Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

