# Optimization Package

This package contains Bayesian optimization tools and workflow orchestration for polyprint experiments.

## Structure

- `bayesian_optimizer.py` - Main Bayesian optimizer class that integrates the polyprint optimizer with Lab Automation
- `objective_functions.py` - Polyprint objective function templates and model-based objectives
- `parameter_spaces.py` - Polyprint parameter space definitions and management
- `optimization_runner.py` - Orchestrates the complete optimization workflow with logging and result saving
- `recipe_templates.py` - Polyprint recipe templating and parameter substitution utilities
- `model_objective_factory.py` - Factory for creating objective functions from trained ML models
- `example_restructured.py` - Examples demonstrating polyprint optimization with both simulated and model-based objectives

## Integration with Lab Automation

This package integrates with the existing Lab Automation framework:
- Uses `CommandSequence` for recipe generation
- Leverages `CommandInvoker` for experiment execution
- Integrates with existing logging and error handling systems
- Supports the existing device and command architecture

## Quick Start

### Basic Usage with OptimizationRunner

```python
from optimization import (
    OptimizationRunner, 
    create_dummy_experiment_template, 
    create_dummy_objective_function
)

# Initialize optimization runner
runner = OptimizationRunner(
    parameter_bounds=[(25.0, 100.0), (5.0, 50.0)],
    parameter_names=['temperature', 'speed'],
    recipe_template=create_dummy_experiment_template(),
    objective_function=create_dummy_objective_function(),
    batch_size=4
)

# Run optimization
best_parameters, best_score = runner.run_optimization(
    n_iterations=10,
    n_initial_points=8
)
```

### Using Parameter Spaces

```python
from optimization import (
    ParameterSpace, Parameter, ParameterType,
    create_temperature_speed_space
)

# Use predefined parameter space
param_space = create_temperature_speed_space()
parameter_bounds = param_space.get_continuous_bounds()
parameter_names = param_space.get_continuous_names()

# Or create custom parameter space
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
    )
]
param_space = ParameterSpace(parameters)
```

### Direct Bayesian Optimizer Usage

```python
from optimization import BayesianOptimizer

# Initialize optimizer directly
optimizer = BayesianOptimizer(
    parameter_bounds=[(25.0, 100.0), (5.0, 50.0)],
    parameter_names=['temperature', 'speed'],
    batch_size=4
)

# Run optimization
best_parameters, best_score = optimizer.optimize(
    recipe_template=recipe_template,
    objective_function=objective_function,
    n_iterations=10,
    n_initial_points=8
)
```

## Key Features

### BayesianOptimizer Class
- **Direct Integration**: Wraps the polyprint Bayesian optimizer
- **Lab Automation Integration**: Seamless integration with CommandSequence and CommandInvoker
- **Batch Optimization**: Run multiple experiments per iteration
- **Flexible Interface**: Works with any recipe template and objective function

### Parameter Spaces
- **Polyprint Parameter Space**: Specialized for polyprint optimization with:
  - **Temperature**: 20.0-80.0°C (continuous)
  - **Concentration**: 0.1-2.0 wt% (continuous)
  - **Speed**: 10.0-120.0 m/s (continuous)
  - **Material Type**: PProDOT/P3MEEMT/P42gTTT (categorical)
- **Validation**: Automatic validation of parameter bounds and values
- **Conversion Utilities**: Easy conversion between different parameter representations

### Objective Functions
- **Polyprint Objective**: Specialized objective function for polyprint optimization with material-specific bonuses
- **Model-Based Objectives**: Create objective functions from trained ML models (LogisticRegression, etc.)


### Recipe Templates
- **Polyprint Template**: Specialized template for polyprint experiments with temperature, concentration, speed, and material type parameters
- **Parameter Substitution**: Automatic parameter injection into recipes
- **Custom Templates**: Create custom recipe templates for specific experiments

## Example Usage

See `example_restructured.py` for complete examples including:
- Basic polyprint optimization with OptimizationRunner
- Model-based polyprint optimization using trained ML models
- Custom parameter spaces
- Multi-objective optimization
- Direct Bayesian optimizer usage
- Result analysis and visualization

## Dependencies

The optimization package requires:
- Your existing Lab Automation framework
- PyTorch (for the Bayesian optimizer)
- BoTorch (for Gaussian Process optimization)
- NumPy and Pandas (for data handling)
- Matplotlib (for plotting, optional)

## Implementation Details

The optimizer is adapted from the polyprint repository (https://github.com/v-palacio/polyprint/tree/main/optimizer) to work seamlessly with the Lab Automation command pattern and device architecture.
