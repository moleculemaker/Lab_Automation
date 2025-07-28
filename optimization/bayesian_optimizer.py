"""
Main Bayesian Optimizer Class

This module contains the main Bayesian optimizer class that integrates the polyprint
Bayesian optimizer with the Lab Automation framework.
"""

import torch
import numpy as np
from typing import Callable, Tuple, Optional, List, Dict, Any
import logging
from datetime import datetime
import os

# Lab Automation imports
from command_sequence import CommandSequence
from command_invoker import CommandInvoker

# Import the polyprint Bayesian optimizer
from .optimizer.bayesian_optimizer import BayesianOptimizer as PolyprintOptimizer


class BayesianOptimizer:
    """
    Main Bayesian optimizer class for Lab Automation.
    
    This class wraps the polyprint Bayesian optimizer and provides integration
    with the Lab Automation framework for experiment execution and result processing.
    """
    
    def __init__(
        self,
        parameter_bounds: List[Tuple[float, float]],
        parameter_names: List[str],
        batch_size: int = 8,
        noise_variance: float = 0.01,
        seed: int = 42
    ):
        """
        Initialize the Bayesian optimizer.
        
        Args:
            parameter_bounds: List of (min, max) tuples for each parameter
            parameter_names: Names of the parameters for recipe substitution
            batch_size: Number of experiments to run per optimization iteration
            noise_variance: Expected noise variance in observations
            seed: Random seed for reproducible results
        """
        self.parameter_bounds = parameter_bounds
        self.parameter_names = parameter_names
        self.batch_size = batch_size
        self.noise_variance = noise_variance
        self.seed = seed
        
        # Validate inputs
        assert len(parameter_bounds) == len(parameter_names), "Parameter bounds and names must have same length"
        
        # Convert bounds to torch tensor for polyprint optimizer
        bounds_tensor = torch.tensor(parameter_bounds).T  # Shape: (2, n_dims)
        
        # Initialize the polyprint Bayesian optimizer
        self.polyprint_optimizer = PolyprintOptimizer(
            bounds=bounds_tensor,
            batch_size=batch_size,
            noise_variance=noise_variance,
            seed=seed
        )
        
        # Track optimization progress
        self.optimization_history = []
        self.experiment_results = []
        
    def _create_parameter_dict(self, parameters: torch.Tensor) -> Dict[str, float]:
        """
        Convert parameter tensor to dictionary for recipe substitution.
        
        Args:
            parameters: Parameter tensor of shape (n_dims,)
            
        Returns:
            Dictionary mapping parameter names to values
        """
        return {name: float(value) for name, value in zip(self.parameter_names, parameters)}
    
    def _execute_experiment(self, parameters: torch.Tensor, experiment_id: str, 
                          recipe_template: Callable, objective_function: Callable,
                          logger: logging.Logger) -> float:
        """
        Execute a single experiment with given parameters.
        
        Args:
            parameters: Parameter tensor for this experiment
            experiment_id: Unique identifier for this experiment
            recipe_template: Function that creates CommandSequence from parameters
            objective_function: Function that extracts objective value from experiment results
            logger: Logger instance for experiment logging
            
        Returns:
            Objective value from the experiment
        """
        logger.info(f"Executing experiment {experiment_id}")
        logger.info(f"Parameters: {self._create_parameter_dict(parameters)}")
        
        try:
            # Create recipe with current parameters
            parameter_dict = self._create_parameter_dict(parameters)
            command_sequence = recipe_template(parameter_dict)
            
            # Execute experiment
            invoker = CommandInvoker(
                command_sequence,
                log_to_file=True,
                log_filename=f"logs/optimization/{experiment_id}.log",
                alert_slack=False
            )
            
            success = invoker.invoke_commands()
            
            if not success:
                logger.error(f"Experiment {experiment_id} failed")
                # Return a penalty value for failed experiments
                return -1000.0
            
            # Extract objective value from experiment results
            objective_value = objective_function(parameter_dict, experiment_id)
            
            logger.info(f"Experiment {experiment_id} completed. Objective: {objective_value:.4f}")
            
            return objective_value
            
        except Exception as e:
            logger.error(f"Error in experiment {experiment_id}: {str(e)}")
            return -1000.0  # Penalty for failed experiments
    
    def _execute_batch(self, parameters_batch: torch.Tensor, recipe_template: Callable,
                      objective_function: Callable, logger: logging.Logger) -> torch.Tensor:
        """
        Execute a batch of experiments.
        
        Args:
            parameters_batch: Batch of parameter tensors of shape (batch_size, n_dims)
            recipe_template: Function that creates CommandSequence from parameters
            objective_function: Function that extracts objective value from experiment results
            logger: Logger instance for experiment logging
            
        Returns:
            Batch of objective values of shape (batch_size, 1)
        """
        batch_size = parameters_batch.shape[0]
        objective_values = []
        
        logger.info(f"Executing batch of {batch_size} experiments")
        
        for i in range(batch_size):
            # Create unique experiment ID
            experiment_id = f"batch_{len(self.optimization_history)}_{i}"
            
            # Execute experiment
            objective_value = self._execute_experiment(
                parameters_batch[i], experiment_id, recipe_template, objective_function, logger
            )
            objective_values.append(objective_value)
            
            # Store experiment result
            experiment_result = {
                'experiment_id': experiment_id,
                'parameters': parameters_batch[i].clone(),
                'objective_value': objective_value,
                'timestamp': datetime.now().isoformat()
            }
            self.experiment_results.append(experiment_result)
        
        return torch.tensor(objective_values).unsqueeze(1)  # Shape: (batch_size, 1)
    
    def optimize(
        self,
        recipe_template: Callable,
        objective_function: Callable,
        n_iterations: int = 20,
        n_initial_points: int = 10,
        verbose: bool = True,
        logger: Optional[logging.Logger] = None
    ) -> Tuple[torch.Tensor, float]:
        """
        Run the complete Bayesian optimization loop.
        
        Args:
            recipe_template: Function that creates CommandSequence from parameters
            objective_function: Function that extracts objective value from experiment results
            n_iterations: Number of optimization iterations
            n_initial_points: Number of initial random experiments
            verbose: Whether to print progress information
            logger: Logger instance for optimization logging
            
        Returns:
            Tuple of (best_parameters, best_score)
        """
        if logger is None:
            logger = logging.getLogger(__name__)
        
        logger.info("=" * 60)
        logger.info("BAYESIAN OPTIMIZATION STARTING")
        logger.info("=" * 60)
        logger.info(f"Parameters: {self.parameter_names}")
        logger.info(f"Parameter bounds: {self.parameter_bounds}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Iterations: {n_iterations}")
        logger.info(f"Initial points: {n_initial_points}")
        logger.info("=" * 60)
        
        # Define objective function for polyprint optimizer
        def lab_objective_function(parameters_batch: torch.Tensor) -> torch.Tensor:
            """Wrapper function that executes experiments and returns objective values."""
            return self._execute_batch(parameters_batch, recipe_template, objective_function, logger)
        
        # Run polyprint Bayesian optimization
        best_parameters, best_score = self.polyprint_optimizer.optimize(
            objective_function=lab_objective_function,
            n_iterations=n_iterations,
            n_initial_points=n_initial_points,
            verbose=verbose
        )
        
        # Update optimization history
        self.optimization_history = self.polyprint_optimizer.get_optimization_history()
        
        logger.info("=" * 60)
        logger.info("OPTIMIZATION COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Final best score: {best_score:.4f}")
        logger.info(f"Final best parameters: {best_parameters}")
        logger.info(f"Total experiments: {len(self.experiment_results)}")
        
        return best_parameters, best_score
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the optimization results.
        
        Returns:
            Dictionary containing optimization summary
        """
        return {
            'parameter_names': self.parameter_names,
            'parameter_bounds': self.parameter_bounds,
            'best_parameters': self.polyprint_optimizer.best_parameters,
            'best_score': self.polyprint_optimizer.best_observed_value,
            'total_experiments': len(self.experiment_results),
            'optimization_history': self.optimization_history,
            'experiment_results': self.experiment_results
        }
    
    def get_best_parameters_dict(self) -> Dict[str, float]:
        """
        Get the best parameters as a dictionary.
        
        Returns:
            Dictionary mapping parameter names to best values
        """
        return self._create_parameter_dict(self.polyprint_optimizer.best_parameters)
    
    def get_training_data(self) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Get the current training data from the polyprint optimizer.
        
        Returns:
            Tuple of (train_X, train_Y)
        """
        return self.polyprint_optimizer.get_training_data() 