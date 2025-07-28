"""
Example: Restructured Optimization Framework

This example demonstrates how to use the restructured optimization framework
with the new modular organization.
"""

import torch
import numpy as np
from typing import Dict, List

# Import the restructured optimization components
from optimization import (
    # Main classes
    BayesianOptimizer, OptimizationRunner,
    
    # Parameter spaces
    ParameterSpace, Parameter, ParameterType,
    create_polyprint_space,
    
    # Objective functions
    create_polyprint_objective_function,
    create_model_based_polyprint_objective,
    create_multi_objective_function,
    
    # Model-based objectives
    create_objective_from_model,
    create_mock_model_and_scaler,
    
    # Recipe templates
    create_polyprint_template
)


def example_basic_polyprint_optimization():
    """
    Basic polyprint optimization example using the restructured framework.
    """
    print("=" * 60)
    print("BASIC POLYPRINT OPTIMIZATION EXAMPLE")
    print("=" * 60)
    
    # Use the polyprint parameter space
    param_space = create_polyprint_space()
    parameter_bounds = param_space.get_bounds_tensor().T.numpy().tolist()
    parameter_names = param_space.parameter_names
    
    print(f"Parameter space: {parameter_names}")
    print(f"Parameter bounds: {parameter_bounds}")
    
    # Create recipe template and objective function
    recipe_template = create_polyprint_template()
    objective_function = create_polyprint_objective_function()
    
    # Initialize optimization runner
    runner = OptimizationRunner(
        parameter_bounds=parameter_bounds,
        parameter_names=parameter_names,
        recipe_template=recipe_template,
        objective_function=objective_function,
        batch_size=3,
        experiment_name="basic_polyprint_optimization"
    )
    
    # Run optimization
    best_parameters, best_score = runner.run_optimization(
        n_iterations=2,
        n_initial_points=4,
        verbose=True
    )
    
    print(f"\nBest polyprint score: {best_score:.4f}")
    print(f"Optimal polyprint parameters: {runner.get_best_parameters_dict()}")
    
    # Save optimization plot
    runner.save_optimization_plot()


def example_model_based_polyprint_optimization():
    """
    Model-based polyprint optimization example using a trained ML model.
    """
    print("\n" + "=" * 60)
    print("MODEL-BASED POLYPRINT OPTIMIZATION EXAMPLE")
    print("=" * 60)
    
    # Create a mock trained model and scaler
    print("Creating mock trained model...")
    model, scaler = create_mock_model_and_scaler()
    
    # Use the polyprint parameter space
    param_space = create_polyprint_space()
    parameter_bounds = param_space.get_bounds_tensor().T.numpy().tolist()
    parameter_names = param_space.parameter_names
    
    print(f"Parameter space: {parameter_names}")
    print(f"Parameter bounds: {parameter_bounds}")
    
    # Create recipe template and model-based objective function
    recipe_template = create_polyprint_template()
    objective_function = create_model_based_polyprint_objective(model, scaler)
    
    # Initialize optimization runner
    runner = OptimizationRunner(
        parameter_bounds=parameter_bounds,
        parameter_names=parameter_names,
        recipe_template=recipe_template,
        objective_function=objective_function,
        batch_size=2,
        experiment_name="model_based_polyprint_optimization"
    )
    
    # Run optimization
    best_parameters, best_score = runner.run_optimization(
        n_iterations=2,
        n_initial_points=3,
        verbose=True
    )
    
    print(f"\nBest model-based polyprint score: {best_score:.4f}")
    print(f"Optimal polyprint parameters: {runner.get_best_parameters_dict()}")
    
    # Save optimization plot
    runner.save_optimization_plot()


def example_polyprint_optimization():
    """
    Polyprint optimization example using the new polyprint parameter space.
    """
    print("\n" + "=" * 60)
    print("POLYPRINT OPTIMIZATION EXAMPLE")
    print("=" * 60)
    
    # Use the polyprint parameter space
    param_space = create_polyprint_space()
    parameter_bounds = param_space.get_bounds_tensor().T.numpy().tolist()
    parameter_names = param_space.parameter_names
    
    print(f"Parameter space: {parameter_names}")
    print(f"Parameter bounds: {parameter_bounds}")
    
    # Create recipe template and objective function
    recipe_template = create_polyprint_template()
    objective_function = create_polyprint_objective_function()
    
    # Initialize optimization runner
    runner = OptimizationRunner(
        parameter_bounds=parameter_bounds,
        parameter_names=parameter_names,
        recipe_template=recipe_template,
        objective_function=objective_function,
        batch_size=3,
        experiment_name="polyprint_optimization_example"
    )
    
    # Run optimization
    best_parameters, best_score = runner.run_optimization(
        n_iterations=2,
        n_initial_points=4,
        verbose=True
    )
    
    print(f"\nBest polyprint score: {best_score:.4f}")
    print(f"Optimal polyprint parameters: {runner.get_best_parameters_dict()}")
    
    # Save optimization plot
    runner.save_optimization_plot()


def example_custom_parameter_space():
    """
    Example using a custom parameter space.
    """
    print("\n" + "=" * 60)
    print("CUSTOM PARAMETER SPACE EXAMPLE")
    print("=" * 60)
    
    # Create custom parameter space
    parameters = [
        Parameter(
            name="temperature",
            param_type=ParameterType.CONTINUOUS,
            bounds=(20.0, 80.0),
            description="Reaction temperature"
        ),
        Parameter(
            name="concentration",
            param_type=ParameterType.CONTINUOUS,
            bounds=(0.1, 2.0),
            description="Reactant concentration"
        ),
        Parameter(
            name="reaction_time",
            param_type=ParameterType.CONTINUOUS,
            bounds=(10.0, 120.0),
            description="Reaction time in minutes"
        )
    ]
    
    param_space = ParameterSpace(parameters)
    
    # Get bounds and names for optimizer
    parameter_bounds = param_space.get_continuous_bounds()
    parameter_names = param_space.get_continuous_names()
    
    # Create recipe template and objective function
    recipe_template = create_chemical_reaction_template()
    
    def custom_objective(parameters: Dict[str, float], experiment_id: str) -> float:
        """Custom objective function for chemical reaction."""
        temperature = parameters.get('temperature', 25.0)
        concentration = parameters.get('concentration', 1.0)
        reaction_time = parameters.get('reaction_time', 60.0)
        
        # Simulate chemical reaction yield
        np.random.seed(hash(experiment_id) % 2**32)
        
        # Optimal conditions: T=60°C, C=1.5 mol/L, t=90 min
        yield_factor = -((temperature - 60.0)**2 + (concentration - 1.5)**2 + (reaction_time - 90.0)**2) / 1000.0
        noise = np.random.normal(0, 0.05)
        
        return yield_factor + noise
    
    # Initialize optimization runner
    runner = OptimizationRunner(
        parameter_bounds=parameter_bounds,
        parameter_names=parameter_names,
        recipe_template=recipe_template,
        objective_function=custom_objective,
        batch_size=3,
        experiment_name="chemical_reaction_optimization"
    )
    
    # Run optimization
    best_parameters, best_score = runner.run_optimization(
        n_iterations=2,
        n_initial_points=4,
        verbose=True
    )
    
    print(f"\nBest yield: {best_score:.4f}")
    print(f"Optimal conditions: {runner.get_best_parameters_dict()}")


def example_multi_objective_optimization():
    """
    Example of multi-objective optimization.
    """
    print("\n" + "=" * 60)
    print("MULTI-OBJECTIVE OPTIMIZATION EXAMPLE")
    print("=" * 60)
    
    # Define multiple objective functions
    def yield_objective(parameters: Dict[str, float], experiment_id: str) -> float:
        """Maximize yield."""
        temperature = parameters.get('temperature', 25.0)
        speed = parameters.get('speed', 5.0)
        return -((temperature - 70.0)**2 + (speed - 30.0)**2) / 1000.0
    
    def cost_objective(parameters: Dict[str, float], experiment_id: str) -> float:
        """Minimize cost (negative because we maximize)."""
        temperature = parameters.get('temperature', 25.0)
        speed = parameters.get('speed', 5.0)
        # Cost increases with temperature and speed
        return -(temperature * 0.1 + speed * 0.05)
    
    # Create multi-objective function
    objective_functions = {
        'yield': yield_objective,
        'cost': cost_objective
    }
    
    weights = {
        'yield': 0.7,  # 70% weight on yield
        'cost': 0.3    # 30% weight on cost
    }
    
    multi_objective = create_multi_objective_function(objective_functions, weights)
    
    # Setup optimization
    parameter_bounds = [(25.0, 100.0), (5.0, 50.0)]
    parameter_names = ['temperature', 'speed']
    
    recipe_template = create_dummy_experiment_template()
    
    # Initialize optimization runner
    runner = OptimizationRunner(
        parameter_bounds=parameter_bounds,
        parameter_names=parameter_names,
        recipe_template=recipe_template,
        objective_function=multi_objective,
        batch_size=2,
        experiment_name="multi_objective_optimization"
    )
    
    # Run optimization
    best_parameters, best_score = runner.run_optimization(
        n_iterations=2,
        n_initial_points=4,
        verbose=True
    )
    
    print(f"\nBest combined score: {best_score:.4f}")
    print(f"Optimal parameters: {runner.get_best_parameters_dict()}")


def example_direct_bayesian_optimizer():
    """
    Example using the Bayesian optimizer directly.
    """
    print("\n" + "=" * 60)
    print("DIRECT BAYESIAN OPTIMIZER EXAMPLE")
    print("=" * 60)
    
    # Define parameters
    parameter_bounds = [(25.0, 100.0), (5.0, 50.0)]
    parameter_names = ['temperature', 'speed']
    
    # Create recipe template and objective function
    recipe_template = create_dummy_experiment_template()
    objective_function = create_dummy_objective_function()
    
    # Initialize Bayesian optimizer directly
    optimizer = BayesianOptimizer(
        parameter_bounds=parameter_bounds,
        parameter_names=parameter_names,
        batch_size=3,
        seed=42
    )
    
    # Run optimization
    best_parameters, best_score = optimizer.optimize(
        recipe_template=recipe_template,
        objective_function=objective_function,
        n_iterations=2,
        n_initial_points=4,
        verbose=True
    )
    
    print(f"\nBest score: {best_score:.4f}")
    print(f"Best parameters: {optimizer.get_best_parameters_dict()}")
    
    # Get optimization summary
    summary = optimizer.get_optimization_summary()
    print(f"Total experiments: {summary['total_experiments']}")


if __name__ == "__main__":
    # Run all examples
    example_basic_polyprint_optimization()
    example_model_based_polyprint_optimization()
    example_polyprint_optimization()
    example_custom_parameter_space()
    example_multi_objective_optimization()
    example_direct_bayesian_optimizer()
    
    print("\n" + "=" * 60)
    print("ALL EXAMPLES COMPLETED")
    print("=" * 60)
    print("Check the logs/optimization directory for detailed results and plots.") 