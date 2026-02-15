#!/usr/bin/env python3
"""
Constrained Bayesian Optimization for PProDOT Film Optimization.

This implements a constrained BO system with:
- Objective Model: Learns uniformity_score from valid samples only
- Constraint Model: Learns P(valid|x) from all samples
- Acquisition: EI(x) × P(valid|x)
"""
from io import BytesIO
import torch
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, List, Tuple

# BoTorch imports
from botorch.models import SingleTaskGP
from botorch.fit import fit_gpytorch_mll
from botorch.acquisition import qLogNoisyExpectedImprovement
from botorch.optim import optimize_acqf
from botorch.utils.transforms import normalize, unnormalize
from botorch.utils.sampling import draw_sobol_samples

# GPyTorch imports
from gpytorch.mlls import ExactMarginalLogLikelihood
from gpytorch.kernels import ScaleKernel, RBFKernel
from gpytorch.priors import GammaPrior


class ConstrainedBayesianOptimizer:
    """
    Constrained Bayesian Optimizer with separate objective and constraint models.
    
    Objective Model: Learns uniformity_score from valid samples (uvvis>=0.1 AND coverage>=0.9)
    Constraint Model: Learns P(valid|x) from all samples
    Acquisition: EI(x) × P(valid|x)
    """
    
    def __init__(
        self,
        bounds: torch.Tensor,
        csv_data: bytes,
        round_num: int = 0,
        batch_size: int = 8,
        seed: int = 42,
        discrete_or_not: List[bool] = [False, True, True, True],
        discrete_points: Optional[List[torch.Tensor]] = None,
        verbose: bool = True,
        log_scale_params: List[bool] = [True, False, False, False],  # Speed is log scale
        uvvis_threshold: float = 0.1,
        coverage_threshold: float = 0.9
    ):
        """
        Initialize Constrained Bayesian Optimizer.
        
        Args:
            bounds: Parameter bounds tensor of shape (2, n_dims) [original scale]
            csv_data: Path to CSV file containing training data
            round_num: Current round number (uses data from rounds <= round_num)
            batch_size: Number of candidates to suggest per iteration
            seed: Random seed
            discrete_or_not: List indicating which parameters are discrete
            discrete_points: List of discrete values for each parameter
            verbose: Whether to print progress messages
            log_scale_params: List indicating which parameters are in log scale
            uvvis_threshold: UV-Vis absorbance threshold for validity
            coverage_threshold: Coverage percentage threshold for validity
        """
        # Set device (default CPU)
        self.device = torch.device("cpu")
        
        # Convert bounds to log scale for log-scale parameters
        self.log_scale_params = log_scale_params
        bounds_log = bounds.clone()
        for i, is_log in enumerate(log_scale_params):
            if is_log:
                bounds_log[0, i] = np.log10(bounds[0, i].item())
                bounds_log[1, i] = np.log10(bounds[1, i].item())
        self.bounds = bounds_log.double()
        self.bounds_original = bounds.double()
        
        self.batch_size = batch_size
        self.seed = seed
        self.discrete_or_not = discrete_or_not
        self.discrete_points = discrete_points if discrete_points is not None else []
        self.csv_data = csv_data
        self.round_num = round_num
        self.verbose = verbose
        self.uvvis_threshold = uvvis_threshold
        self.coverage_threshold = coverage_threshold

        torch.manual_seed(seed)
        np.random.seed(seed)

        assert bounds.shape[0] == 2, "Bounds must have shape (2, n_dims)"
        assert (bounds[1] > bounds[0]).all(), "Upper bounds must be greater than lower bounds"

        self.n_dims = bounds.shape[1]
        self.objective_model = None
        self.constraint_model = None
        self.train_X_all = None  # All samples (normalized)
        self.train_Y_obj = None  # Objective values (valid samples only)
        self.train_X_obj = None  # Valid samples only (normalized)
        self.train_Y_valid = None  # Validity flags (all samples)
        self.train_Y_mean = None  # For denormalization
        self.train_Y_std = None
        
        # Set to track already-seen parameter combinations
        self.seen_param_keys = set()

        # Load initial data from CSV
        self._load_data()

    def _load_data(self) -> None:
        """Load and preprocess training data from CSV file."""
        df = pd.read_csv(BytesIO(self.csv_data))
        
        # Filter by round number: use all rounds up to and including round_num
        if 'round#' in df.columns:
            df_all_rounds = df[df['round#'] <= self.round_num].copy()
            if self.verbose:
                rounds_used = sorted(df_all_rounds['round#'].unique().tolist())
                print(f"  Using data from rounds: {rounds_used}")
        else:
            df_all_rounds = df.copy()
        
        # Build seen_param_keys from all rows (including NaN uniformity_score)
        self.seen_param_keys.clear()
        for _, row in df_all_rounds.iterrows():
            try:
                sp = round(float(row['Speed']), 2)
                T = int(round(float(row['Temperature'])))
                g = int(round(float(row['gap'])))
                v = int(round(float(row['Precursor Volume'])))
                self.seen_param_keys.add((sp, T, g, v))
            except (KeyError, ValueError, TypeError):
                # Skip rows with missing or invalid parameter values
                continue
        
        if self.verbose:
            print(f"  Seen parameter combinations: {len(self.seen_param_keys)}")
        
        # Filter rows with valid uniformity_score for training
        df = df_all_rounds.dropna(subset=['uniformity_score']).copy()
        
        if len(df) == 0:
            raise ValueError(f"No valid data found for round {self.round_num} in {self.csv_data}")

        # Extract parameters: [Speed, Temperature, gap, Precursor Volume]
        speed = df['Speed'].values
        temperature = df['Temperature'].values
        gap = df['gap'].values
        volume = df['Precursor Volume'].values

        # Convert Speed to log scale
        speed_log = np.log10(speed)

        # Stack in order: [Speed (log), Temperature, gap, volume]
        train_X_all = np.column_stack([speed_log, temperature, gap, volume])
        train_Y_all = df['uniformity_score'].values.reshape(-1, 1)

        # Compute validity flags
        uvvis_values = df['uvvis_max_abs'].values if 'uvvis_max_abs' in df.columns else np.zeros(len(df))
        coverage_values = df['coverage_percentage'].values if 'coverage_percentage' in df.columns else np.zeros(len(df))
        
        valid_mask = (uvvis_values >= self.uvvis_threshold) & (coverage_values >= self.coverage_threshold)
        valid_flags = valid_mask.astype(float).reshape(-1, 1)

        if self.verbose:
            n_valid = valid_mask.sum()
            print(f"  Total samples: {len(df)}")
            print(f"  Valid samples (uvvis>={self.uvvis_threshold} AND coverage>={self.coverage_threshold}): {n_valid}/{len(df)} ({100*n_valid/len(df):.1f}%)")

        # Store data
        self.train_X_all = torch.tensor(train_X_all, dtype=torch.float64)
        self.train_Y_valid = torch.tensor(valid_flags, dtype=torch.float64)
        
        # Objective model uses only valid samples
        if valid_mask.sum() > 0:
            self.train_X_obj = torch.tensor(train_X_all[valid_mask], dtype=torch.float64)
            self.train_Y_obj = torch.tensor(train_Y_all[valid_mask], dtype=torch.float64)
            
            # Store normalization parameters for objective
            self.train_Y_mean = self.train_Y_obj.mean().item()
            self.train_Y_std = max(self.train_Y_obj.std().item(), 1e-6)  # Numerical stability
            
            if self.verbose:
                print(f"  Objective model: {len(self.train_X_obj)} valid samples")
                print(f"  Best observed score: {self.train_Y_obj.max().item():.6f}")
        else:
            raise ValueError("No valid samples found for objective model!")

        if self.verbose:
            print(f"  Constraint model: {len(self.train_X_all)} total samples")
            print(f"  Validity rate: {valid_flags.mean().item():.2%}")

    def _build_models(self) -> None:
        """Build objective and constraint GP models."""
        if self.train_X_obj is None or self.train_Y_obj is None:
            raise ValueError("No objective training data available.")
        if self.train_X_all is None or self.train_Y_valid is None:
            raise ValueError("No constraint training data available.")

        # Normalize all data
        train_X_all_normalized = normalize(self.train_X_all.double(), self.bounds.double())
        train_X_obj_normalized = normalize(self.train_X_obj.double(), self.bounds.double())
        
        # Normalize objective values
        train_Y_obj_normalized = (self.train_Y_obj.double() - self.train_Y_mean) / self.train_Y_std
        
        # Constraint values are already 0/1, no normalization needed

        # Build Objective Model (valid samples only)
        self.objective_model = SingleTaskGP(
            train_X_obj_normalized,
            train_Y_obj_normalized,
            covar_module=ScaleKernel(
                RBFKernel(
                    lengthscale_prior=GammaPrior(3.0, 1.0),
                    ard_num_dims=self.n_dims
                ),
                outputscale_prior=GammaPrior(2.0, 0.5)
            )
        )

        self.objective_model.train()
        mll_obj = ExactMarginalLogLikelihood(self.objective_model.likelihood, self.objective_model)
        fit_gpytorch_mll(mll_obj)
        self.objective_model.eval()

        # Build Constraint Model (all samples)
        self.constraint_model = SingleTaskGP(
            train_X_all_normalized,
            self.train_Y_valid.double(),
            covar_module=ScaleKernel(
                RBFKernel(
                    lengthscale_prior=GammaPrior(3.0, 1.0),
                    ard_num_dims=self.n_dims
                ),
                outputscale_prior=GammaPrior(2.0, 0.5)
            )
        )

        self.constraint_model.train()
        mll_const = ExactMarginalLogLikelihood(self.constraint_model.likelihood, self.constraint_model)
        fit_gpytorch_mll(mll_const)
        self.constraint_model.eval()

        if self.verbose:
            print("  Models fitted successfully")

    def _decode_and_snap(self, candidates_normalized: torch.Tensor) -> torch.Tensor:
        """
        Decode normalized candidates to original scale with discrete snapping.
        
        Args:
            candidates_normalized: Tensor of shape (n, n_dims) in normalized [0,1] space
            
        Returns:
            Tensor of shape (n, n_dims) in original scale with discrete snapping applied
        """
        # Inverse transform
        candidates_unnormalized = unnormalize(candidates_normalized, self.bounds.double())
        
        # Convert log-scale parameters back to original scale
        candidates_original = candidates_unnormalized.clone()
        for i, is_log in enumerate(self.log_scale_params):
            if is_log:
                candidates_original[:, i] = 10 ** candidates_unnormalized[:, i]
        
        # Apply discrete constraints
        for i in range(candidates_original.shape[0]):
            for j in range(candidates_original.shape[1]):
                if self.discrete_or_not[j] and j < len(self.discrete_points):
                    column_values = self.discrete_points[j]
                    closest_value = torch.abs(column_values - candidates_original[i, j])
                    candidates_original[i, j] = column_values[torch.argmin(closest_value)]
        
        # Round Speed (continuous variable) to 2 decimal places
        candidates_original[:, 0] = torch.round(candidates_original[:, 0] * 100.0) / 100.0
        
        return candidates_original
    
    def _compute_metadata(self, candidates_normalized: torch.Tensor, acquisition_function) -> dict:
        """
        Compute all metadata for candidates.
        
        Args:
            candidates_normalized: Tensor of shape (n, n_dims) in normalized space
            acquisition_function: qLogNoisyExpectedImprovement instance
            
        Returns:
            Dictionary with all metadata arrays
        """
        with torch.no_grad():
            # EI log and raw
            ei_log = acquisition_function(candidates_normalized.unsqueeze(1)).squeeze(-1)  # (n,)
            ei_raw = torch.clamp(torch.exp(ei_log), min=0.0)
            
            # Constraint GP posterior
            constraint_posterior = self.constraint_model.posterior(candidates_normalized)
            mu_valid_raw = constraint_posterior.mean.squeeze(-1)  # (n,)
            p_valid = torch.sigmoid(mu_valid_raw)
            
            # Objective GP posterior
            objective_posterior = self.objective_model.posterior(candidates_normalized)
            mu_obj = objective_posterior.mean.squeeze(-1)  # (n,)
            sigma_obj = objective_posterior.stddev.squeeze(-1)  # (n,)
            
            # Denormalize objective predictions
            mu_obj_denorm = mu_obj * self.train_Y_std + self.train_Y_mean
            
            # Constrained score
            score_constrained = ei_raw * p_valid
            
            return {
                'ei_log': ei_log.cpu().numpy(),
                'ei_raw': ei_raw.cpu().numpy(),
                'p_valid': p_valid.cpu().numpy(),
                'score_constrained': score_constrained.cpu().numpy(),
                'mu_obj': mu_obj_denorm.cpu().numpy(),
                'sigma_obj': sigma_obj.cpu().numpy(),
                'mu_valid_raw': mu_valid_raw.cpu().numpy()
            }
    
    def suggest(self, verbose: bool = None) -> Tuple[torch.Tensor, dict]:
        """
        Suggest next batch of candidates using constrained acquisition.
        
        Acquisition: EI_raw(x) × P(valid|x)
        
        Returns:
            candidates: Tensor of shape (batch_size, n_dims) containing suggested candidates
            metadata: Dictionary with all metadata for each candidate
        """
        if verbose is None:
            verbose = self.verbose

        if verbose:
            print("=" * 60)
            print("GENERATING CONSTRAINED BO CANDIDATES")
            print("=" * 60)
            print(f"Objective samples: {len(self.train_X_obj)}")
            print(f"Constraint samples: {len(self.train_X_all)}")
            print(f"Batch size: {self.batch_size}")
            print(f"Seen parameter combinations: {len(self.seen_param_keys)}")
            print("=" * 60)

        # Build models
        if verbose:
            print("Building GP models...")
        self._build_models()

        # Normalize training data
        train_X_all_normalized = normalize(self.train_X_all.double(), self.bounds.double())
        train_X_obj_normalized = normalize(self.train_X_obj.double(), self.bounds.double())

        # Unit bounds for normalized space
        unit_bounds = torch.stack([
            torch.zeros(self.n_dims, dtype=torch.float64, device=self.device),
            torch.ones(self.n_dims, dtype=torch.float64, device=self.device),
        ])
        
        # Acquisition function
        acquisition_function = qLogNoisyExpectedImprovement(
            model=self.objective_model,
            X_baseline=train_X_obj_normalized,
            prune_baseline=True,
            cache_root=True
        )

        # Step 1: Generate main EI candidate pool (larger than batch_size)
        pool_q = self.batch_size * 5  # 40 candidates for batch_size=8
        if verbose:
            print(f"Step 1: Generating main EI candidate pool (q={pool_q})...")
        
        candidates_pool, _ = optimize_acqf(
            acq_function=acquisition_function,
            bounds=unit_bounds,
            q=pool_q,
            num_restarts=40,
            raw_samples=500,
            options={"batch_limit": 5, "maxiter": 200}
        )

        if verbose:
            print(f"  Generated {pool_q} candidate pool")

        # Step 2: Compute metadata for all candidates
        if verbose:
            print("Step 2: Computing metadata (EI, P(valid), scores)...")
        
        metadata_pool = self._compute_metadata(candidates_pool, acquisition_function)
        score_constrained = torch.tensor(metadata_pool['score_constrained'], dtype=torch.float64)
        
        if verbose:
            print(f"  EI_log range: [{metadata_pool['ei_log'].min():.4f}, {metadata_pool['ei_log'].max():.4f}]")
            print(f"  EI_raw range: [{metadata_pool['ei_raw'].min():.4f}, {metadata_pool['ei_raw'].max():.4f}]")
            print(f"  P(valid) range: [{metadata_pool['p_valid'].min():.4f}, {metadata_pool['p_valid'].max():.4f}]")
            print(f"  Score_constrained range: [{score_constrained.min():.4f}, {score_constrained.max():.4f}]")

        # Step 3: Filter by uniqueness and select top candidates
        if verbose:
            print("Step 3: Filtering duplicates and selecting candidates...")
        
        sorted_indices = torch.argsort(score_constrained, descending=True)
        selected_indices = []  # Store indices in candidates_pool
        selected_original = []
        selected_metadata = {
            'ei_log': [], 'ei_raw': [], 'p_valid': [], 'score_constrained': [],
            'mu_obj': [], 'sigma_obj': [], 'mu_valid_raw': [],
            'candidate_rank': [], 'source': []
        }
        
        rank = 1
        for idx in sorted_indices:
            if len(selected_indices) >= self.batch_size:
                break
            
            # Decode and snap
            candidate_norm = candidates_pool[idx:idx+1]
            candidate_orig = self._decode_and_snap(candidate_norm)
            
            # Create parameter tuple
            sp = round(float(candidate_orig[0, 0]), 2)
            T = int(round(float(candidate_orig[0, 1])))
            g = int(round(float(candidate_orig[0, 2])))
            v = int(round(float(candidate_orig[0, 3])))
            param_key = (sp, T, g, v)
            
            # Check if already seen
            if param_key in self.seen_param_keys:
                continue
            
            # Add to selected
            self.seen_param_keys.add(param_key)
            selected_indices.append(idx.item())  # Store as int for indexing
            selected_original.append(candidate_orig)
            
            # Store metadata
            selected_metadata['ei_log'].append(metadata_pool['ei_log'][idx])
            selected_metadata['ei_raw'].append(metadata_pool['ei_raw'][idx])
            selected_metadata['p_valid'].append(metadata_pool['p_valid'][idx])
            selected_metadata['score_constrained'].append(metadata_pool['score_constrained'][idx])
            selected_metadata['mu_obj'].append(metadata_pool['mu_obj'][idx])
            selected_metadata['sigma_obj'].append(metadata_pool['sigma_obj'][idx])
            selected_metadata['mu_valid_raw'].append(metadata_pool['mu_valid_raw'][idx])
            selected_metadata['candidate_rank'].append(rank)
            selected_metadata['source'].append('main_ei')
            rank += 1
        
        n_selected_main = len(selected_indices)
        if verbose:
            print(f"  Selected {n_selected_main} unique candidates from main pool")

        # Step 4: Sobol fallback with max-min distance exploration
        if len(selected_indices) < self.batch_size:
            if verbose:
                print(f"Step 4: Sobol fallback with max-min distance exploration to fill remaining {self.batch_size - len(selected_indices)} slots...")
            
            k = self.batch_size - len(selected_indices)
            
            # Construct X_seen: previous data + this round's main EI selections
            X_prev = train_X_all_normalized  # (N_prev, d) - already normalized
            if n_selected_main > 0:
                X_round = candidates_pool[torch.tensor(selected_indices, dtype=torch.long, device=candidates_pool.device)]  # (n_selected_main, d) - already normalized
                X_seen = torch.cat([X_prev, X_round], dim=0)  # (N_prev + n_selected_main, d)
            else:
                X_seen = X_prev  # No main EI selections yet
            
            if verbose:
                if n_selected_main > 0:
                    print(f"  X_seen: {X_seen.shape[0]} points (previous: {X_prev.shape[0]}, this round: {X_round.shape[0]})")
                else:
                    print(f"  X_seen: {X_seen.shape[0]} points (previous: {X_prev.shape[0]}, this round: 0)")
            
            # Generate and filter Sobol pool
            fallback_pool_size = self.batch_size * 20  # 160 for batch_size=8
            max_pool_retries = 5
            valid_sobol_pool_norm = []
            valid_sobol_param_keys = []
            
            n_sobol = fallback_pool_size
            pool_retry = 0
            
            while len(valid_sobol_pool_norm) < k and pool_retry < max_pool_retries:
                # Generate Sobol samples
                sobol_raw = draw_sobol_samples(
                    bounds=unit_bounds,
                    n=1,
                    q=n_sobol
                ).squeeze(0).double()  # (n_sobol, d)
                
                # Filter duplicates
                for i in range(sobol_raw.shape[0]):
                    candidate_norm = sobol_raw[i:i+1]  # (1, d)
                    candidate_orig = self._decode_and_snap(candidate_norm)
                    
                    # Create parameter tuple
                    sp = round(float(candidate_orig[0, 0]), 2)
                    T = int(round(float(candidate_orig[0, 1])))
                    g = int(round(float(candidate_orig[0, 2])))
                    v = int(round(float(candidate_orig[0, 3])))
                    param_key = (sp, T, g, v)
                    
                    # Check if already seen
                    if param_key not in self.seen_param_keys:
                        valid_sobol_pool_norm.append(candidate_norm)
                        valid_sobol_param_keys.append(param_key)
                
                if len(valid_sobol_pool_norm) < k:
                    n_sobol *= 2
                    pool_retry += 1
                    if verbose:
                        print(f"  Pool retry {pool_retry}: Found {len(valid_sobol_pool_norm)}/{k} valid candidates, expanding pool to {n_sobol}")
            
            if len(valid_sobol_pool_norm) < k:
                raise RuntimeError(
                    f"ConstrainedBO: could not generate {k} unique Sobol candidates "
                    f"after {max_pool_retries} pool expansion retries. "
                    f"Consider relaxing the uniqueness constraint or adjusting the search space."
                )
            
            # Stack valid pool
            sobol_pool_norm = torch.cat(valid_sobol_pool_norm, dim=0)  # (M, d) where M >= k
            
            if verbose:
                print(f"  Valid Sobol pool: {sobol_pool_norm.shape[0]} candidates")
            
            # Greedy max-min distance selection
            selected_fallback_norm = []
            selected_fallback_param_keys = []
            remaining_pool = sobol_pool_norm.clone()
            remaining_param_keys = valid_sobol_param_keys.copy()
            X_seen_current = X_seen.clone()
            
            for i in range(k):
                # Compute minimum distances to X_seen
                distances = torch.cdist(remaining_pool, X_seen_current)  # (M_remaining, N_seen)
                dist_min, _ = distances.min(dim=1)  # (M_remaining,)
                
                # Select candidate with maximum min-distance
                best_idx = dist_min.argmax().item()
                x_best = remaining_pool[best_idx:best_idx+1]  # (1, d)
                param_key_best = remaining_param_keys[best_idx]
                
                # Add to selected
                selected_fallback_norm.append(x_best)
                selected_fallback_param_keys.append(param_key_best)
                X_seen_current = torch.cat([X_seen_current, x_best], dim=0)
                
                # Remove from remaining pool
                mask = torch.ones(remaining_pool.shape[0], dtype=torch.bool, device=remaining_pool.device)
                mask[best_idx] = False
                remaining_pool = remaining_pool[mask]
                remaining_param_keys = [rk for j, rk in enumerate(remaining_param_keys) if j != best_idx]
                
                if verbose and (i + 1) % max(1, k // 4) == 0:
                    print(f"  Selected {i+1}/{k} fallback candidates (min distance: {dist_min[best_idx]:.4f})")
            
            # Stack selected fallback candidates
            selected_fallback_norm = torch.cat(selected_fallback_norm, dim=0)  # (k, d)
            
            # Compute metadata for selected fallback candidates
            if verbose:
                print(f"  Computing metadata for {k} fallback candidates...")
            
            with torch.no_grad():
                # Objective GP posterior
                objective_posterior = self.objective_model.posterior(selected_fallback_norm)
                mu_obj_fallback = objective_posterior.mean.squeeze(-1)  # (k,)
                sigma_obj_fallback = objective_posterior.stddev.squeeze(-1)  # (k,)
                mu_obj_fallback_denorm = mu_obj_fallback * self.train_Y_std + self.train_Y_mean
                
                # EI
                ei_log_fallback = acquisition_function(selected_fallback_norm.unsqueeze(1)).squeeze(-1)  # (k,)
                ei_raw_fallback = torch.clamp(torch.exp(ei_log_fallback), min=0.0)
                
                # Constraint GP posterior
                constraint_posterior = self.constraint_model.posterior(selected_fallback_norm)
                mu_valid_raw_fallback = constraint_posterior.mean.squeeze(-1)  # (k,)
                p_valid_fallback = torch.sigmoid(mu_valid_raw_fallback)
                
                # Constrained score
                score_constrained_fallback = ei_raw_fallback * p_valid_fallback
            
            # Decode and snap for final output
            selected_fallback_original = self._decode_and_snap(selected_fallback_norm)
            
            # Add to selected lists
            for i in range(k):
                param_key = selected_fallback_param_keys[i]
                self.seen_param_keys.add(param_key)
                selected_indices.append(len(selected_indices))  # Dummy index for Sobol
                selected_original.append(selected_fallback_original[i:i+1])
                
                # Store metadata
                selected_metadata['ei_log'].append(ei_log_fallback[i].item())
                selected_metadata['ei_raw'].append(ei_raw_fallback[i].item())
                selected_metadata['p_valid'].append(p_valid_fallback[i].item())
                selected_metadata['score_constrained'].append(score_constrained_fallback[i].item())
                selected_metadata['mu_obj'].append(mu_obj_fallback_denorm[i].item())
                selected_metadata['sigma_obj'].append(sigma_obj_fallback[i].item())
                selected_metadata['mu_valid_raw'].append(mu_valid_raw_fallback[i].item())
                selected_metadata['candidate_rank'].append(rank)
                selected_metadata['source'].append('sobol_fallback')
                rank += 1
            
            if verbose:
                print(f"  Selected {k} fallback candidates using max-min distance exploration")
        
        # Stack selected candidates
        candidates_final = torch.cat(selected_original, dim=0).float()
        
        # Re-rank all selected candidates by score_constrained
        final_scores = torch.tensor(selected_metadata['score_constrained'], dtype=torch.float64)
        final_rank_order = torch.argsort(final_scores, descending=True)
        
        # Reorder candidates and metadata
        candidates_final = candidates_final[final_rank_order]
        for key in selected_metadata:
            if key == 'candidate_rank':
                # Re-assign ranks 1 to batch_size
                selected_metadata[key] = list(range(1, self.batch_size + 1))
            else:
                # Reorder by final_rank_order
                arr = np.array(selected_metadata[key])
                selected_metadata[key] = arr[final_rank_order.cpu().numpy()].tolist()
        
        if verbose:
            print(f"\nFinal {self.batch_size} candidates (ranked by score_constrained):")
            for i in range(self.batch_size):
                print(f"  [{selected_metadata['candidate_rank'][i]}] [{selected_metadata['source'][i]}] "
                      f"Speed={candidates_final[i, 0]:.2f}, "
                      f"Temp={candidates_final[i, 1]:.1f}, "
                      f"Gap={candidates_final[i, 2]:.1f}, "
                      f"Volume={candidates_final[i, 3]:.1f}")
                print(f"      EI_log={selected_metadata['ei_log'][i]:.4f}, "
                      f"EI_raw={selected_metadata['ei_raw'][i]:.4f}, "
                      f"P(valid)={selected_metadata['p_valid'][i]:.4f}, "
                      f"Score={selected_metadata['score_constrained'][i]:.4f}")

        return candidates_final, selected_metadata

    def save_candidates_to_csv(
        self, 
        candidates: torch.Tensor,
        metadata: Optional[dict] = None,
        next_round_num: Optional[int] = None,
        solvent: str = "CB",
        concentration: int = 40
    ) -> None:
        """
        Save suggested candidates to CSV file.
        
        Args:
            candidates: Tensor of shape (batch_size, n_dims) containing suggested candidates
            metadata: Optional dictionary with EI, P_valid, Score values for each candidate
            next_round_num: Round number for new candidates (default: round_num + 1)
            solvent: Solvent value for new rows (default: "CB")
            concentration: Concentration value for new rows (default: 40)
        """
        df = pd.read_csv(BytesIO(self.csv_data))
        
        # Determine next round number
        if next_round_num is None:
            next_round_num = self.round_num + 1
        
        # Determine starting sample number
        if 'Sample #' in df.columns and 'round#' in df.columns and len(df) > 0:
            round_df = df[df['round#'] == next_round_num]
            if len(round_df) > 0:
                start_sample = int(round_df['Sample #'].max()) + 1
            else:
                start_sample = 1  # New round, start from 1
        else:
            start_sample = 1
        
        # Convert candidates to numpy
        candidates_np = candidates.cpu().numpy()
        batch_size = candidates_np.shape[0]
        
        # Create new rows
        new_rows = []
        for i in range(batch_size):
            speed = float(candidates_np[i, 0])
            temperature = float(candidates_np[i, 1])
            gap = float(candidates_np[i, 2])
            volume = float(candidates_np[i, 3])
            
            new_row = {
                'Unnamed: 0': 'PProDOT',
                'round#': next_round_num,
                'Sample #': start_sample + i,
                'Temperature': int(round(temperature)),
                'Speed': round(speed, 2),  # Round to 2 decimal places to avoid float precision issues
                'gap': int(round(gap)),
                'Solvent': solvent,
                'Concentration': concentration,
                'Precursor Volume': int(round(volume)),
                'uvvis_max_abs': np.nan,
                'uniformity_score': np.nan,
            }
            
            # Add metadata if provided
            if metadata is not None:
                # Required metadata
                if 'ei_log' in metadata and i < len(metadata['ei_log']):
                    new_row['ei_log'] = metadata['ei_log'][i]
                if 'ei_raw' in metadata and i < len(metadata['ei_raw']):
                    new_row['ei_raw'] = metadata['ei_raw'][i]
                if 'p_valid' in metadata and i < len(metadata['p_valid']):
                    new_row['p_valid'] = metadata['p_valid'][i]
                if 'score_constrained' in metadata and i < len(metadata['score_constrained']):
                    new_row['score_constrained'] = metadata['score_constrained'][i]
                if 'candidate_rank' in metadata and i < len(metadata['candidate_rank']):
                    new_row['candidate_rank'] = int(metadata['candidate_rank'][i])
                if 'source' in metadata and i < len(metadata['source']):
                    new_row['source'] = metadata['source'][i]
                
                # Additional analysis metadata
                if 'mu_obj' in metadata and i < len(metadata['mu_obj']):
                    new_row['mu_obj'] = metadata['mu_obj'][i]
                if 'sigma_obj' in metadata and i < len(metadata['sigma_obj']):
                    new_row['sigma_obj'] = metadata['sigma_obj'][i]
                if 'mu_valid_raw' in metadata and i < len(metadata['mu_valid_raw']):
                    new_row['mu_valid_raw'] = metadata['mu_valid_raw'][i]
            
            # Update seen_param_keys immediately
            param_key = (round(speed, 2), int(round(temperature)), int(round(gap)), int(round(volume)))
            self.seen_param_keys.add(param_key)
            
            for col in df.columns:
                if col not in new_row:
                    new_row[col] = np.nan
            
            new_rows.append(new_row)
        
        new_df = pd.DataFrame(new_rows)
        
        # Ensure all columns from new_df are included (especially metadata columns)
        # If metadata columns don't exist in df, add them with NaN
        for col in new_df.columns:
            if col not in df.columns:
                df[col] = np.nan
        
        # Reorder new_df to match df columns (including newly added ones)
        new_df = new_df[df.columns]
        combined_df = pd.concat([df, new_df], ignore_index=True)
        
        if self.verbose:
            print(f"\nSaved {batch_size} candidates")
            print(f"  Round: {next_round_num}, Samples: {start_sample} to {start_sample + batch_size - 1}")
            if metadata is not None:
                print(f"  Metadata (EI, P_valid, Score) also saved")

        return combined_df

    def reload_data(self) -> None:
        """Reload data from CSV file (useful after CSV is updated)."""
        if self.verbose:
            print(f"Reloading data from {self.csv_data}...")
        self._load_data()
        # Reset models to force refitting
        self.objective_model = None
        self.constraint_model = None
