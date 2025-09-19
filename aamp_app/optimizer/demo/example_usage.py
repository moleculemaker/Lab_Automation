"""
Example Usage Scripts for Bayesian Optimization Package

This script demonstrates various ways to use the Bayesian optimization package
for different optimization scenarios.
"""

import torch
import numpy as np
from optimizer import BayesianOptimizer, MockObjectiveFunction


def example_1_basic_usage():
    """
    Example 1: Basic usage with default parameters
    """
    print("="*60)
    print("EXAMPLE 1: Basic Usage")
    print("="*60)
    
    # Define parameter bounds
    bounds = torch.tensor([
        [0.1, 1.0],      # concentration
        [10.0, 100.0],   # print_speed
        [0.05, 0.5],     # gap_size
        [5.0, 25.0]      # volume
    ]).T
    
    # Create optimizer and objective function
    optimizer = BayesianOptimizer(bounds=bounds, batch_size=8)
    objective = MockObjectiveFunction(noise_std=0.1)
    
    # Run optimization
    best_params, best_score = optimizer.optimize(
        objective_function=objective,
        n_iterations=10,
        n_initial_points=5,
        verbose=True
    )
    
    print(f"Best parameters: {best_params}")
    print(f"Best score: {best_score:.4f}")
    return best_params, best_score


def example_2_custom_parameters():
    """
    Example 2: Custom optimization parameters
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: Custom Parameters")
    print("="*60)
    
    # Define parameter bounds
    bounds = torch.tensor([
        [0.1, 1.0],      # concentration
        [10.0, 100.0],   # print_speed
        [0.05, 0.5],     # gap_size
        [5.0, 25.0]      # volume
    ]).T
    
    # Create optimizer with custom parameters
    optimizer = BayesianOptimizer(
        bounds=bounds,
        batch_size=4,           # Smaller batch size
        noise_variance=0.05,    # Lower noise assumption
        seed=123                # Different random seed
    )
    
    # Create objective with different noise level
    objective = MockObjectiveFunction(noise_std=0.05, seed=123)
    
    # Run optimization with custom settings
    best_params, best_score = optimizer.optimize(
        objective_function=objective,
        n_iterations=15,
        n_initial_points=8,
        verbose=True
    )
    
    print(f"Best parameters: {best_params}")
    print(f"Best score: {best_score:.4f}")
    return best_params, best_score


def example_3_step_by_step():
    """
    Example 3: Step-by-step optimization (manual control)
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: Step-by-Step Optimization")
    print("="*60)
    
    # Define parameter bounds
    bounds = torch.tensor([
        [0.1, 1.0],      # concentration
        [10.0, 100.0],   # print_speed
        [0.05, 0.5],     # gap_size
        [5.0, 25.0]      # volume
    ]).T
    
    # Create optimizer and objective function
    optimizer = BayesianOptimizer(bounds=bounds, batch_size=6)
    objective = MockObjectiveFunction(noise_std=0.1)
    
    # Step 1: Generate initial data
    print("Step 1: Generating initial data...")
    optimizer.generate_initial_data(8, objective)
    
    # Step 2: Manual optimization loop
    n_iterations = 5
    for i in range(n_iterations):
        print(f"\nIteration {i+1}/{n_iterations}")
        
        # Fit model
        print("  Fitting GP model...")
        optimizer.fit_model()
        
        # Get next candidates
        print("  Getting next candidates...")
        candidates = optimizer.optimize_acquisition()
        
        # Evaluate candidates
        print("  Evaluating candidates...")
        values = objective(candidates)
        
        # Update training data
        optimizer.update_training_data(candidates, values)
        
        print(f"  Current best: {optimizer.best_observed_value:.4f}")
    
    print(f"\nFinal best parameters: {optimizer.best_parameters}")
    print(f"Final best score: {optimizer.best_observed_value:.4f}")
    
    return optimizer.best_parameters, optimizer.best_observed_value


def example_4_analysis():
    """
    Example 4: Detailed analysis of optimization results
    """
    print("\n" + "="*60)
    print("EXAMPLE 4: Detailed Analysis")
    print("="*60)
    
    # Define parameter bounds
    bounds = torch.tensor([
        [0.1, 1.0],      # concentration
        [10.0, 100.0],   # print_speed
        [0.05, 0.5],     # gap_size
        [5.0, 25.0]      # volume
    ]).T
    
    # Create optimizer and objective function
    optimizer = BayesianOptimizer(bounds=bounds, batch_size=8)
    objective = MockObjectiveFunction(noise_std=0.1)
    
    # Run optimization
    best_params, best_score = optimizer.optimize(
        objective_function=objective,
        n_iterations=8,
        n_initial_points=6,
        verbose=False
    )
    
    # Get optimization history
    history = optimizer.get_optimization_history()
    train_X, train_Y = optimizer.get_training_data()
    
    print(f"Optimization Summary:")
    print(f"- Total evaluations: {len(train_X)}")
    print(f"- Best score: {best_score:.4f}")
    print(f"- Best parameters: {best_params}")
    
    # Analyze convergence
    print(f"\nConvergence Analysis:")
    best_values = [h['best_value'] for h in history]
    improvements = [best_values[i] - best_values[i-1] for i in range(1, len(best_values))]
    
    print(f"- Initial best: {best_values[0]:.4f}")
    print(f"- Final best: {best_values[-1]:.4f}")
    print(f"- Total improvement: {best_values[-1] - best_values[0]:.4f}")
    print(f"- Average improvement per iteration: {np.mean(improvements):.4f}")
    
    # Compare with true optimum
    true_params, _ = objective.get_optimal_parameters()
    true_score = objective.evaluate_at_optimal()
    
    param_distance = torch.norm(best_params - true_params).item()
    score_gap = true_score - best_score
    
    print(f"\nComparison with True Optimum:")
    print(f"- True optimal score: {true_score:.4f}")
    print(f"- Found score: {best_score:.4f}")
    print(f"- Score gap: {score_gap:.4f}")
    print(f"- Parameter distance: {param_distance:.4f}")
    
    return best_params, best_score


def example_5_custom_objective():
    """
    Example 5: Using a custom objective function
    """
    print("\n" + "="*60)
    print("EXAMPLE 5: Custom Objective Function")
    print("="*60)
    
    def custom_objective(X):
        """
        Custom objective function example.
        This function has a different optimal point than the mock function.
        """
        # Ensure X is 2D
        if X.dim() == 1:
            X = X.unsqueeze(0)
        
        # Extract parameters
        concentration = X[:, 0]
        print_speed = X[:, 1]
        gap_size = X[:, 2]
        volume = X[:, 3]
        
        # Custom objective: minimize print time while maintaining quality
        # Quality decreases if parameters are too far from optimal ranges
        quality = 1.0 - 0.5 * ((concentration - 0.8)**2 + 
                               (print_speed - 60.0)**2 / 1000.0 + 
                               (gap_size - 0.3)**2 * 4.0 + 
                               (volume - 12.0)**2 / 100.0)
        
        # Add noise
        noise = torch.randn(X.shape[0], 1) * 0.05
        
        return quality.unsqueeze(1) + noise
    
    # Define parameter bounds
    bounds = torch.tensor([
        [0.1, 1.0],      # concentration
        [10.0, 100.0],   # print_speed
        [0.05, 0.5],     # gap_size
        [5.0, 25.0]      # volume
    ]).T
    
    # Create optimizer
    optimizer = BayesianOptimizer(bounds=bounds, batch_size=6)
    
    # Run optimization with custom objective
    best_params, best_score = optimizer.optimize(
        objective_function=custom_objective,
        n_iterations=10,
        n_initial_points=6,
        verbose=True
    )
    
    print(f"Best parameters: {best_params}")
    print(f"Best score: {best_score:.4f}")
    
    return best_params, best_score


def main():
    """
    Run all examples
    """
    print("BAYESIAN OPTIMIZATION EXAMPLES")
    print("These examples demonstrate different ways to use the package.")
    print("Each example shows a different aspect of the optimization workflow.")
    
    # Run examples
    example_1_basic_usage()
    example_2_custom_parameters()
    example_3_step_by_step()
    example_4_analysis()
    example_5_custom_objective()
    
    print("\n" + "="*60)
    print("ALL EXAMPLES COMPLETED")
    print("="*60)


if __name__ == "__main__":
    main() 