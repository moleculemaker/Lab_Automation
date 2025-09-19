"""
Bayesian Optimization Demo Script

This script demonstrates a complete Bayesian optimization workflow for
optimizing a printing process with 4 continuous parameters.

The script includes:
- Parameter space definition
- Mock objective function evaluation
- Bayesian optimization with batch candidates
- Results visualization and analysis
"""

import torch
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, List
import time

# Import our custom modules
from ..bayesian_optimizer import BayesianOptimizer
from ..objective_function import MockObjectiveFunction


def print_header(title: str, width: int = 80) -> None:
    """Print a formatted header for console output."""
    print("\n" + "=" * width)
    print(f"{title:^{width}}")
    print("=" * width)


def print_parameter_info() -> None:
    """Print information about the optimization parameters."""
    print("\nPARAMETER SPACE:")
    print("-" * 50)
    print("Parameter        | Range          | Description")
    print("-" * 50)
    print("concentration    | [0.1, 1.0]     | Material concentration")
    print("print_speed      | [10.0, 100.0]  | Printing speed (mm/s)")
    print("gap_size         | [0.05, 0.5]    | Gap size between layers (mm)")
    print("volume           | [5.0, 25.0]    | Volume per drop (μL)")
    print("-" * 50)


def format_parameters(params: torch.Tensor) -> str:
    """Format parameters for display."""
    if params.dim() == 1:
        concentration, print_speed, gap_size, volume = params
        return (f"concentration={concentration:.3f}, "
                f"print_speed={print_speed:.1f}, "
                f"gap_size={gap_size:.3f}, "
                f"volume={volume:.1f}")
    else:
        return f"Tensor of shape {params.shape}"


def visualize_optimization_progress(
    iteration_history: List[dict],
    true_optimum: float,
    save_plot: bool = False
) -> None:
    """
    Visualize the optimization progress over iterations.
    
    Args:
        iteration_history: List of iteration information
        true_optimum: True optimal value for comparison
        save_plot: Whether to save the plot to file
    """
    try:
        iterations = [info['iteration'] for info in iteration_history]
        best_values = [info['best_value'] for info in iteration_history]
        
        plt.figure(figsize=(12, 8))
        
        # Plot best observed value over iterations
        plt.subplot(2, 1, 1)
        plt.plot(iterations, best_values, 'b-o', linewidth=2, markersize=6)
        plt.axhline(y=true_optimum, color='r', linestyle='--', 
                   label=f'True optimum: {true_optimum:.3f}')
        plt.xlabel('Iteration')
        plt.ylabel('Best Observed Value')
        plt.title('Optimization Progress: Best Value vs Iteration')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Plot improvement over iterations
        plt.subplot(2, 1, 2)
        improvements = [best_values[i] - best_values[0] for i in range(len(best_values))]
        plt.plot(iterations, improvements, 'g-o', linewidth=2, markersize=6)
        plt.xlabel('Iteration')
        plt.ylabel('Improvement from Initial Best')
        plt.title('Cumulative Improvement Over Iterations')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_plot:
            plt.savefig('optimization_progress.png', dpi=300, bbox_inches='tight')
            print("Plot saved as 'optimization_progress.png'")
        
        plt.show()
        
    except ImportError:
        print("Matplotlib not available. Skipping visualization.")
    except Exception as e:
        print(f"Error creating visualization: {e}")


def compare_with_true_optimum(
    best_params: torch.Tensor,
    best_score: float,
    objective_function: MockObjectiveFunction
) -> None:
    """
    Compare the optimization results with the true optimum.
    
    Args:
        best_params: Best parameters found by optimization
        best_score: Best score achieved
        objective_function: The objective function to get true optimum
    """
    print_header("COMPARISON WITH TRUE OPTIMUM")
    
    # Get true optimal parameters and score
    true_params, true_max_score = objective_function.get_optimal_parameters()
    true_score_noiseless = objective_function.evaluate_at_optimal()
    
    print(f"\nTRUE OPTIMUM:")
    print(f"Parameters: {format_parameters(true_params)}")
    print(f"Score (noiseless): {true_score_noiseless:.4f}")
    print(f"Max possible score: {true_max_score:.4f}")
    
    print(f"\nOPTIMIZED RESULT:")
    print(f"Parameters: {format_parameters(best_params)}")
    print(f"Score (noisy): {best_score:.4f}")
    
    # Calculate parameter differences
    param_diff = torch.norm(best_params - true_params).item()
    score_diff = abs(best_score - true_score_noiseless)
    
    print(f"\nCOMPARISON:")
    print(f"Parameter L2 distance: {param_diff:.4f}")
    print(f"Score difference: {score_diff:.4f}")
    print(f"Score gap from true optimum: {(true_score_noiseless - best_score):.4f}")
    
    # Performance assessment
    if param_diff < 5.0:  # Reasonable threshold for parameter space
        print("✓ Parameters are close to true optimum")
    else:
        print("⚠ Parameters are far from true optimum")
    
    if score_diff < 0.2:  # Reasonable threshold considering noise
        print("✓ Score is close to true optimum")
    else:
        print("⚠ Score is far from true optimum")


def analyze_convergence(iteration_history: List[dict]) -> None:
    """
    Analyze convergence properties of the optimization.
    
    Args:
        iteration_history: List of iteration information
    """
    print_header("CONVERGENCE ANALYSIS")
    
    best_values = [info['best_value'] for info in iteration_history]
    
    # Find when best improvements occurred
    improvements = []
    for i in range(1, len(best_values)):
        improvement = best_values[i] - best_values[i-1]
        if improvement > 0.01:  # Significant improvement threshold
            improvements.append((i+1, improvement))
    
    print(f"\nSIGNIFICANT IMPROVEMENTS (> 0.01):")
    if improvements:
        for iteration, improvement in improvements:
            print(f"Iteration {iteration}: +{improvement:.4f}")
    else:
        print("No significant improvements found")
    
    # Calculate convergence metrics
    final_best = best_values[-1]
    initial_best = best_values[0]
    total_improvement = final_best - initial_best
    
    print(f"\nCONVERGENCE METRICS:")
    print(f"Initial best: {initial_best:.4f}")
    print(f"Final best: {final_best:.4f}")
    print(f"Total improvement: {total_improvement:.4f}")
    
    # Check for convergence in last 5 iterations
    if len(best_values) >= 5:
        last_5_values = best_values[-5:]
        convergence_variance = np.var(last_5_values)
        print(f"Variance in last 5 iterations: {convergence_variance:.6f}")
        
        if convergence_variance < 0.001:
            print("✓ Optimization appears to have converged")
        else:
            print("⚠ Optimization may not have fully converged")


def run_optimization_demo(
    n_iterations: int = 20,
    n_initial_points: int = 10,
    batch_size: int = 8,
    noise_std: float = 0.1,
    visualize: bool = True,
    seed: int = 42
) -> Tuple[torch.Tensor, float]:
    """
    Run a complete Bayesian optimization demonstration.
    
    Args:
        n_iterations: Number of optimization iterations
        n_initial_points: Number of initial random points
        batch_size: Batch size for candidate generation
        noise_std: Standard deviation of noise in objective function
        visualize: Whether to create visualization plots
        seed: Random seed for reproducibility
        
    Returns:
        Tuple of (best_parameters, best_score)
    """
    print_header("BAYESIAN OPTIMIZATION DEMO")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print_parameter_info()
    
    # Define parameter bounds (using float32 for consistency)
    bounds = torch.tensor([
        [0.1, 1.0],      # concentration
        [10.0, 100.0],   # print_speed
        [0.05, 0.5],     # gap_size
        [5.0, 25.0]      # volume
    ], dtype=torch.float32).T  # Transpose to get shape (2, 4)
    
    print(f"\nOPTIMIZATION CONFIGURATION:")
    print(f"Dimensions: {bounds.shape[1]}")
    print(f"Batch size: {batch_size}")
    print(f"Iterations: {n_iterations}")
    print(f"Initial points: {n_initial_points}")
    print(f"Noise std: {noise_std}")
    print(f"Random seed: {seed}")
    
    # Create objective function and optimizer
    objective_function = MockObjectiveFunction(noise_std=noise_std, seed=seed)
    optimizer = BayesianOptimizer(
        bounds=bounds,
        batch_size=batch_size,
        seed=seed
    )
    
    # Run optimization
    print_header("RUNNING OPTIMIZATION")
    start_time = time.time()
    
    best_params, best_score = optimizer.optimize(
        objective_function=objective_function,
        n_iterations=n_iterations,
        n_initial_points=n_initial_points,
        verbose=True
    )
    
    end_time = time.time()
    optimization_time = end_time - start_time
    
    print_header("OPTIMIZATION RESULTS")
    print(f"Optimization completed in {optimization_time:.2f} seconds")
    print(f"Total function evaluations: {len(optimizer.train_X)}")
    print(f"Best score: {best_score:.4f}")
    print(f"Best parameters: {format_parameters(best_params)}")
    
    # Detailed analysis
    compare_with_true_optimum(best_params, best_score, objective_function)
    analyze_convergence(optimizer.get_optimization_history())
    
    # Visualization
    if visualize:
        print_header("VISUALIZATION")
        true_optimum = objective_function.evaluate_at_optimal()
        visualize_optimization_progress(
            optimizer.get_optimization_history(),
            true_optimum,
            save_plot=True
        )
    
    print_header("DEMO COMPLETED")
    return best_params, best_score


def main():
    """Main function to run the demo."""
    # Example 1: Standard optimization
    print("Running standard optimization demo...")
    best_params, best_score = run_optimization_demo()
    
    # Example 2: Quick optimization with fewer iterations
    print("\n" + "="*80)
    print("Running quick optimization demo (10 iterations)...")
    run_optimization_demo(
        n_iterations=10,
        n_initial_points=5,
        batch_size=4,
        visualize=False
    )


if __name__ == "__main__":
    main() 