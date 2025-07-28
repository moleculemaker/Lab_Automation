"""
Optimization Runner

This module contains the OptimizationRunner class that orchestrates the complete
optimization workflow, including logging, result saving, and progress tracking.
"""

import torch
import numpy as np
from typing import Callable, Tuple, Optional, List, Dict, Any
import logging
from datetime import datetime
import os
import json

# Import the main Bayesian optimizer
from .bayesian_optimizer import BayesianOptimizer


class OptimizationRunner:
    """
    Orchestrates the complete optimization workflow.
    
    This class provides a high-level interface for running Bayesian optimization
    experiments with comprehensive logging, result saving, and progress tracking.
    """
    
    def __init__(
        self,
        parameter_bounds: List[Tuple[float, float]],
        parameter_names: List[str],
        recipe_template: Callable,
        objective_function: Callable,
        batch_size: int = 8,
        noise_variance: float = 0.01,
        seed: int = 42,
        log_directory: str = "logs/optimization",
        save_results: bool = True,
        experiment_name: Optional[str] = None
    ):
        """
        Initialize the optimization runner.
        
        Args:
            parameter_bounds: List of (min, max) tuples for each parameter
            parameter_names: Names of the parameters for recipe substitution
            recipe_template: Function that creates CommandSequence from parameters
            objective_function: Function that extracts objective value from experiment results
            batch_size: Number of experiments to run per optimization iteration
            noise_variance: Expected noise variance in observations
            seed: Random seed for reproducible results
            log_directory: Directory to save optimization logs and results
            save_results: Whether to save optimization results to files
            experiment_name: Name for this optimization experiment
        """
        self.parameter_bounds = parameter_bounds
        self.parameter_names = parameter_names
        self.recipe_template = recipe_template
        self.objective_function = objective_function
        self.batch_size = batch_size
        self.noise_variance = noise_variance
        self.seed = seed
        self.log_directory = log_directory
        self.save_results = save_results
        self.experiment_name = experiment_name or f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Setup logging
        self._setup_logging()
        
        # Initialize Bayesian optimizer
        self.optimizer = BayesianOptimizer(
            parameter_bounds=parameter_bounds,
            parameter_names=parameter_names,
            batch_size=batch_size,
            noise_variance=noise_variance,
            seed=seed
        )
        
        # Track optimization progress
        self.optimization_history = []
        self.experiment_results = []
        
    def _setup_logging(self):
        """Setup logging for optimization process."""
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)
            
        # Create experiment-specific log file
        log_file = os.path.join(self.log_directory, f"{self.experiment_name}.log")
        self.logger = logging.getLogger(f"OptimizationRunner_{self.experiment_name}")
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)-5s]: %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
    def _save_optimization_state(self, iteration: int):
        """Save current optimization state to files."""
        if not self.save_results:
            return
            
        # Save optimization history
        history_file = os.path.join(self.log_directory, f"{self.experiment_name}_history.npz")
        np.savez(
            history_file,
            iteration=iteration,
            best_parameters=self.optimizer.get_best_parameters_dict(),
            best_value=self.optimizer.get_optimization_summary()['best_score'],
            train_X=self.optimizer.get_training_data()[0].numpy(),
            train_Y=self.optimizer.get_training_data()[1].numpy()
        )
        
        # Save experiment results as JSON
        results_file = os.path.join(self.log_directory, f"{self.experiment_name}_results.json")
        results_data = []
        for result in self.optimizer.experiment_results:
            results_data.append({
                'experiment_id': result['experiment_id'],
                'parameters': result['parameters'].numpy().tolist(),
                'objective_value': float(result['objective_value']),
                'timestamp': result['timestamp']
            })
        
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        # Save optimization summary
        summary_file = os.path.join(self.log_directory, f"{self.experiment_name}_summary.json")
        summary = self.get_optimization_summary()
        # Convert torch tensors to lists for JSON serialization
        summary['best_parameters'] = summary['best_parameters'].numpy().tolist()
        summary['optimization_history'] = [
            {
                'iteration': h['iteration'],
                'best_value': float(h['best_value']),
                'best_params': h['best_params'].numpy().tolist()
            }
            for h in summary['optimization_history']
        ]
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
    
    def run_optimization(
        self,
        n_iterations: int = 20,
        n_initial_points: int = 10,
        verbose: bool = True,
        save_frequency: int = 5
    ) -> Tuple[torch.Tensor, float]:
        """
        Run the complete optimization process.
        
        Args:
            n_iterations: Number of optimization iterations
            n_initial_points: Number of initial random experiments
            verbose: Whether to print progress information
            save_frequency: How often to save optimization state (every N iterations)
            
        Returns:
            Tuple of (best_parameters, best_score)
        """
        self.logger.info("=" * 60)
        self.logger.info(f"OPTIMIZATION RUNNER STARTING: {self.experiment_name}")
        self.logger.info("=" * 60)
        self.logger.info(f"Parameters: {self.parameter_names}")
        self.logger.info(f"Parameter bounds: {self.parameter_bounds}")
        self.logger.info(f"Batch size: {self.batch_size}")
        self.logger.info(f"Iterations: {n_iterations}")
        self.logger.info(f"Initial points: {n_initial_points}")
        self.logger.info(f"Log directory: {self.log_directory}")
        self.logger.info("=" * 60)
        
        try:
            # Run Bayesian optimization
            best_parameters, best_score = self.optimizer.optimize(
                recipe_template=self.recipe_template,
                objective_function=self.objective_function,
                n_iterations=n_iterations,
                n_initial_points=n_initial_points,
                verbose=verbose,
                logger=self.logger
            )
            
            # Save final state
            self._save_optimization_state(n_iterations)
            
            # Update local tracking
            self.optimization_history = self.optimizer.optimization_history
            self.experiment_results = self.optimizer.experiment_results
            
            self.logger.info("=" * 60)
            self.logger.info("OPTIMIZATION COMPLETED SUCCESSFULLY")
            self.logger.info("=" * 60)
            self.logger.info(f"Final best score: {best_score:.4f}")
            self.logger.info(f"Final best parameters: {best_parameters}")
            self.logger.info(f"Total experiments: {len(self.experiment_results)}")
            self.logger.info(f"Results saved to: {self.log_directory}")
            
            return best_parameters, best_score
            
        except Exception as e:
            self.logger.error(f"Optimization failed: {str(e)}")
            raise
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of the optimization results.
        
        Returns:
            Dictionary containing optimization summary
        """
        return self.optimizer.get_optimization_summary()
    
    def get_best_parameters_dict(self) -> Dict[str, float]:
        """
        Get the best parameters as a dictionary.
        
        Returns:
            Dictionary mapping parameter names to best values
        """
        return self.optimizer.get_best_parameters_dict()
    
    def get_progress_report(self) -> Dict[str, Any]:
        """
        Get a progress report of the current optimization state.
        
        Returns:
            Dictionary containing progress information
        """
        summary = self.get_optimization_summary()
        
        return {
            'experiment_name': self.experiment_name,
            'total_experiments': summary['total_experiments'],
            'best_score': summary['best_score'],
            'best_parameters': summary['best_parameters'],
            'optimization_history_length': len(summary['optimization_history']),
            'parameter_names': self.parameter_names,
            'parameter_bounds': self.parameter_bounds,
            'batch_size': self.batch_size
        }
    
    def save_optimization_plot(self, save_path: Optional[str] = None):
        """
        Save optimization progress plots.
        
        Args:
            save_path: Path to save the plot (optional)
        """
        try:
            import matplotlib.pyplot as plt
            
            summary = self.get_optimization_summary()
            history = summary['optimization_history']
            
            if len(history) < 2:
                self.logger.warning("Not enough data to create optimization plot")
                return
            
            # Create figure with subplots
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            
            # Plot 1: Best value over iterations
            iterations = [h['iteration'] for h in history]
            best_values = [h['best_value'] for h in history]
            
            ax1.plot(iterations, best_values, 'b-o', linewidth=2, markersize=6)
            ax1.set_xlabel('Iteration')
            ax1.set_ylabel('Best Objective Value')
            ax1.set_title('Optimization Progress')
            ax1.grid(True, alpha=0.3)
            
            # Plot 2: Parameter evolution
            if len(history) > 1:
                param_data = np.array([h['best_params'] for h in history])
                for i, param_name in enumerate(self.parameter_names):
                    ax2.plot(iterations, param_data[:, i], 'o-', label=param_name, linewidth=2, markersize=6)
                
                ax2.set_xlabel('Iteration')
                ax2.set_ylabel('Parameter Value')
                ax2.set_title('Best Parameters Evolution')
                ax2.legend()
                ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Save plot
            if save_path is None:
                save_path = os.path.join(self.log_directory, f"{self.experiment_name}_progress.png")
            
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Optimization plot saved to: {save_path}")
            
        except ImportError:
            self.logger.warning("Matplotlib not available, skipping plot generation")
        except Exception as e:
            self.logger.error(f"Error creating optimization plot: {str(e)}")
    
    def load_previous_results(self, results_file: str) -> bool:
        """
        Load results from a previous optimization run.
        
        Args:
            results_file: Path to the results JSON file
            
        Returns:
            True if loading was successful, False otherwise
        """
        try:
            with open(results_file, 'r') as f:
                results_data = json.load(f)
            
            # Convert results back to the expected format
            for result in results_data:
                self.experiment_results.append({
                    'experiment_id': result['experiment_id'],
                    'parameters': torch.tensor(result['parameters']),
                    'objective_value': result['objective_value'],
                    'timestamp': result['timestamp']
                })
            
            self.logger.info(f"Loaded {len(results_data)} previous results from {results_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading previous results: {str(e)}")
            return False 