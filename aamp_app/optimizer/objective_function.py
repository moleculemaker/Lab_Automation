"""
Mock Objective Function for Bayesian Optimization Demo

This module contains a realistic simulation of a black-box objective function
for a printing process optimization problem. The function has a single maximum
and includes realistic noise levels.
"""

import torch
import numpy as np
from typing import Tuple


class MockObjectiveFunction:
    """
    Mock objective function simulating a printing process optimization.
    
    This function represents a realistic black-box optimization scenario where:
    - The objective is to maximize print quality (score)
    - The function has a single global maximum
    - Realistic noise is added to simulate measurement uncertainty
    - The function depends on 4 continuous parameters
    
    Parameters:
        concentration: [0.1, 1.0] - Material concentration
        print_speed: [10.0, 100.0] - Printing speed (mm/s)
        gap_size: [0.05, 0.5] - Gap size between layers (mm)
        volume: [5.0, 25.0] - Volume per drop (μL)
    """
    
    def __init__(self, noise_std: float = 0.1, seed: int = 42):
        """
        Initialize the mock objective function.
        
        Args:
            noise_std: Standard deviation of Gaussian noise added to observations
            seed: Random seed for reproducible results
        """
        self.noise_std = noise_std
        self.seed = seed
        
        # Set random seed for reproducible results
        torch.manual_seed(seed)
        np.random.seed(seed)
        
        # Define the optimal parameters (global maximum)
        # These represent the "true" best settings for our simulated process
        self.optimal_params = torch.tensor([
            0.6,    # concentration: medium-high concentration
            45.0,   # print_speed: moderate speed
            0.2,    # gap_size: medium gap
            15.0    # volume: medium volume
        ])
        
        # Parameter bounds for normalization
        self.bounds = torch.tensor([
            [0.1, 1.0],      # concentration
            [10.0, 100.0],   # print_speed
            [0.05, 0.5],     # gap_size
            [5.0, 25.0]      # volume
        ])
        
        # Maximum possible score (achieved at optimal parameters)
        self.max_score = 1.0
        
    def __call__(self, X: torch.Tensor) -> torch.Tensor:
        """
        Evaluate the objective function on a batch of parameter sets.
        
        Args:
            X: Input tensor of shape (batch_size, 4) containing parameter values
            
        Returns:
            Tensor of shape (batch_size, 1) containing noisy objective values
        """
        # Ensure input is the correct shape
        if X.dim() == 1:
            X = X.unsqueeze(0)
        
        batch_size = X.shape[0]
        
        # Normalize parameters to [0, 1] range for easier computation
        X_normalized = self._normalize_parameters(X)
        optimal_normalized = self._normalize_parameters(self.optimal_params.unsqueeze(0))
        
        # Calculate base score using a combination of Gaussian and polynomial terms
        scores = self._calculate_base_score(X_normalized, optimal_normalized.squeeze(0))
        
        # Add realistic noise to simulate measurement uncertainty
        noise = torch.randn(batch_size, 1) * self.noise_std
        noisy_scores = scores + noise
        
        # Ensure scores are non-negative (realistic for quality metrics)
        noisy_scores = torch.clamp(noisy_scores, min=0.0)
        
        return noisy_scores
    
    def _normalize_parameters(self, X: torch.Tensor) -> torch.Tensor:
        """
        Normalize parameters to [0, 1] range based on their bounds.
        
        Args:
            X: Parameter tensor of shape (batch_size, 4)
            
        Returns:
            Normalized parameter tensor
        """
        lower_bounds = self.bounds[:, 0]
        upper_bounds = self.bounds[:, 1]
        
        # Normalize to [0, 1]
        X_normalized = (X - lower_bounds) / (upper_bounds - lower_bounds)
        
        return X_normalized
    
    def _calculate_base_score(self, X_norm: torch.Tensor, optimal_norm: torch.Tensor) -> torch.Tensor:
        """
        Calculate the base (noise-free) objective score.
        
        This function creates a realistic objective landscape with:
        - A single global maximum at the optimal parameters
        - Smooth transitions between parameter regions
        - Realistic parameter interactions
        
        Args:
            X_norm: Normalized parameter tensor (batch_size, 4)
            optimal_norm: Normalized optimal parameters (4,)
            
        Returns:
            Base scores tensor (batch_size, 1)
        """
        batch_size = X_norm.shape[0]
        
        # Calculate distance from optimal parameters
        distances = torch.norm(X_norm - optimal_norm, dim=1)
        
        # Primary Gaussian component centered at optimal parameters
        gaussian_scores = torch.exp(-8 * distances**2)
        
        # Add parameter-specific effects to create more realistic landscape
        
        # Concentration effect: too low or too high concentration reduces quality
        conc_effect = 1.0 - 2.0 * (X_norm[:, 0] - 0.5)**2
        
        # Print speed effect: very slow or very fast reduces quality
        speed_effect = 1.0 - 1.5 * (X_norm[:, 1] - 0.4)**2
        
        # Gap size effect: optimal gap size is critical
        gap_effect = 1.0 - 3.0 * (X_norm[:, 2] - 0.3)**2
        
        # Volume effect: moderate volume is best
        volume_effect = 1.0 - 1.2 * (X_norm[:, 3] - 0.5)**2
        
        # Combine all effects
        combined_effects = (conc_effect + speed_effect + gap_effect + volume_effect) / 4.0
        
        # Final score combines Gaussian and parameter effects
        base_scores = 0.7 * gaussian_scores + 0.3 * combined_effects
        
        # Scale to reasonable range and ensure maximum is achievable
        base_scores = self.max_score * torch.clamp(base_scores, min=0.0, max=1.0)
        
        return base_scores.unsqueeze(1)
    
    def get_optimal_parameters(self) -> Tuple[torch.Tensor, float]:
        """
        Get the true optimal parameters and maximum score.
        
        Returns:
            Tuple of (optimal_parameters, max_score)
        """
        return self.optimal_params, self.max_score
    
    def evaluate_at_optimal(self) -> float:
        """
        Evaluate the function at the optimal parameters (useful for comparison).
        
        Returns:
            Score at optimal parameters (without noise)
        """
        optimal_normalized = self._normalize_parameters(self.optimal_params.unsqueeze(0))
        base_score = self._calculate_base_score(optimal_normalized, optimal_normalized.squeeze(0))
        return base_score.item()


# Convenience function for backward compatibility
def mock_objective(X: torch.Tensor, noise_std: float = 0.1) -> torch.Tensor:
    """
    Convenience function to evaluate the mock objective function.
    
    Args:
        X: Input tensor of shape (batch_size, 4)
        noise_std: Standard deviation of noise to add
        
    Returns:
        Noisy objective values of shape (batch_size, 1)
    """
    objective = MockObjectiveFunction(noise_std=noise_std)
    return objective(X) 