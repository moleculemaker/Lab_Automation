# Bayesian Optimization Package

A complete, self-contained Python package for batch Bayesian Optimization using BoTorch and GPyTorch libraries. This package demonstrates how to optimize a noisy, black-box objective function with 4 continuous parameters using batch optimization.

## Features

- **Batch Optimization**: Suggests 8 new candidates per iteration for parallel evaluation
- **Noisy Objective Handling**: Uses qLogNoisyExpectedImprovement acquisition function (numerically stable)
- **Gaussian Process Surrogate**: SingleTaskGP model for function approximation
- **Real-world Simulation**: Mock objective function with realistic noise and single maximum
- **Well-documented**: Comprehensive comments and easy-to-understand code

## Problem Definition

### Objective
Maximize a noisy, black-box objective function representing a printing process optimization.

### Parameters
- `concentration`: [0.1, 1.0] - Material concentration
- `print_speed`: [10.0, 100.0] - Printing speed (mm/s)
- `gap_size`: [0.05, 0.5] - Gap size between layers (mm)
- `volume`: [5.0, 25.0] - Volume per drop (μL)

### Configuration
- **Batch Size**: 8 candidates per iteration
- **Iterations**: 20 optimization rounds
- **Initial Points**: 10 random samples

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Import and use the package:
```python
from optimizer import run_optimization_demo

# Run the complete optimization workflow
best_params, best_score = run_optimization_demo()
```

## Usage Example

```python
import torch
from optimizer import BayesianOptimizer, MockObjectiveFunction

# Define search space bounds
bounds = torch.tensor([
    [0.1, 1.0],      # concentration
    [10.0, 100.0],   # print_speed
    [0.05, 0.5],     # gap_size
    [5.0, 25.0]      # volume
]).T

# Create optimizer and objective function
optimizer = BayesianOptimizer(bounds=bounds, batch_size=8)
objective = MockObjectiveFunction()

# Run optimization
best_params, best_score = optimizer.optimize(
    objective_function=objective,
    n_iterations=20,
    n_initial_points=10
)

print(f"Best parameters: {best_params}")
print(f"Best score: {best_score:.4f}")
```

## 📓 Jupyter Notebooks

The package includes three interactive Jupyter notebooks:

### 1. **Tutorial Notebook** (`tutorial_notebook.ipynb`)
- **Perfect for beginners** - step-by-step explanation of Bayesian optimization
- Covers theory, implementation, and best practices
- Interactive examples and visualizations

### 2. **Demo Notebook** (`demo_notebook.ipynb`)
- **Complete demonstration** of the optimization workflow
- Comprehensive analysis and visualization
- Real-world manufacturing example

### 3. **Interactive Notebook** (`interactive_notebook.ipynb`)
- **Experimentation platform** with easy parameter adjustment
- Compare different optimization settings
- Real-time visualization of results

To use the notebooks:
```bash
# Install Jupyter if not already installed
pip install jupyter

# Launch Jupyter
jupyter notebook

# Open any of the .ipynb files
```

## Architecture

### Core Components

1. **BayesianOptimizer**: Main optimization class handling the GP model and acquisition function
2. **MockObjectiveFunction**: Simulates a realistic black-box objective with noise
3. **Demo Script**: Complete workflow demonstration

### Workflow

1. **Initialization**: Generate initial training dataset (10 random points)
2. **Optimization Loop** (20 iterations):
   - Fit SingleTaskGP model to current data
   - Define qLogNoisyExpectedImprovement acquisition function
   - Optimize acquisition function to find 8 new candidates
   - Evaluate candidates and update training data
3. **Results**: Report best parameters and score

## Key Libraries Used

- **BoTorch**: State-of-the-art Bayesian optimization library
- **GPyTorch**: Gaussian process library for surrogate modeling
- **PyTorch**: Tensor operations and automatic differentiation

## Files Structure

```
optimizer/
├── __init__.py              # Package initialization
├── bayesian_optimizer.py    # Core optimization class
├── objective_function.py    # Mock objective function
├── demo.py                  # Complete demo script
├── run_demo.py              # Simple executable script
├── example_usage.py         # Advanced usage examples
├── setup.py                 # Package setup
├── requirements.txt         # Dependencies
├── README.md               # This file
├── QUICKSTART.md           # Quick start guide
├── demo_notebook.ipynb      # Complete demonstration notebook
├── interactive_notebook.ipynb # Interactive experimentation
└── tutorial_notebook.ipynb # Step-by-step tutorial
```

## Performance Notes

- The mock objective function simulates realistic noise levels
- qLogNEI acquisition function is optimized for noisy objectives with improved numerical stability
- Batch optimization allows for parallel evaluation of candidates
- GPU acceleration available through PyTorch/BoTorch

## License

This package is part of the Polyprint project and serves as an educational example for Bayesian optimization in manufacturing processes. 

## Model Integration with Scikit-Learn

The optimizer now supports direct integration with trained scikit-learn models through the `model_objective_factory` module. This allows you to use your trained models as objective functions for Bayesian optimization.

### Using Your Trained Model

#### 1. Create Objective Function from Model

```python
from model_objective_factory import create_objective_from_model
import joblib

# Load your trained model and scaler
model = joblib.load('your_trained_model.pkl')
scaler = joblib.load('your_trained_scaler.pkl')

# Create BoTorch-compatible objective function
objective_fn = create_objective_from_model(model, scaler)
```

#### 2. Run Optimization

```python
from bayesian_optimizer import BayesianOptimizer
import torch

# Define parameter bounds
bounds = torch.tensor([
    [0.1, 10.0, 0.05, 5.0],   # Lower bounds: [concentration, print_speed, gap_size, volume]
    [1.0, 100.0, 0.5, 25.0]  # Upper bounds: [concentration, print_speed, gap_size, volume]
], dtype=torch.float64)

# Initialize optimizer
optimizer = BayesianOptimizer(bounds=bounds, batch_size=8, seed=42)

# Run optimization
best_params, best_score = optimizer.optimize(
    objective_function=objective_fn,
    n_iterations=20,
    n_initial_points=10,
    verbose=True
)

print(f"Best parameters: {best_params}")
print(f"Best success probability: {best_score:.4f}")
```

### How It Works

The `create_objective_from_model` function creates a wrapper that:

1. **Accepts BoTorch tensors**: Input shape `(batch_size, 4)` with parameters `[concentration, print_speed, gap_size, volume]`

2. **Performs feature engineering**: Automatically creates the 11 features your model expects:
   - `gap_size_squared`
   - `solvent_CF` (fixed at 0.5)
   - `print_speed_squared`
   - `concentration_squared`
   - `concentration`
   - `gap_size`
   - `print_speed_gap_size`
   - `print_speed`
   - `concentration_print_speed`
   - `print_speed_volume`
   - `volume`

3. **Applies scaling**: Uses your trained `StandardScaler` to normalize features

4. **Returns probabilities**: Uses `model.predict_proba()` to get success probabilities

5. **Outputs BoTorch tensors**: Returns shape `(batch_size, 1)` tensor of success probabilities

### Running the Demo

```bash
# Test the model factory
python model_objective_factory.py

# Test full integration with Bayesian optimization
python model_integration_example.py
```

### Key Benefits

- **Seamless Integration**: Direct compatibility between scikit-learn models and BoTorch
- **Automatic Feature Engineering**: No need to manually recreate feature transformations
- **Batch Evaluation**: Efficient evaluation of multiple parameter combinations
- **Clean Architecture**: Factory pattern separates model logic from optimization logic
- **Robust**: Handles tensor conversions, scaling, and error checking automatically

### Requirements

Your scikit-learn model must:
- Be a trained `LogisticRegression` or similar classifier
- Have a `predict_proba()` method
- Expect exactly 11 features in the specified order
- Be paired with a fitted `StandardScaler`

The factory pattern makes it easy to extend support for other model types in the future. 