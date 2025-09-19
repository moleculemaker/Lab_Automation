# Quick Start Guide

Get up and running with the Bayesian Optimization package in minutes!

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Verify installation:**
```bash
python -c "import torch, botorch, gpytorch; print('All dependencies installed successfully')"
```

## Run the Demo

### Option 1: Simple Demo
```bash
python run_demo.py
```

### Option 2: From Python
```python
from optimizer import run_optimization_demo

# Run with default settings
best_params, best_score = run_optimization_demo()
print(f"Best parameters: {best_params}")
print(f"Best score: {best_score:.4f}")
```

## Basic Usage

### Simple Optimization
```python
import torch
from optimizer import BayesianOptimizer, MockObjectiveFunction

# 1. Define parameter bounds
bounds = torch.tensor([
    [0.1, 1.0],      # concentration
    [10.0, 100.0],   # print_speed  
    [0.05, 0.5],     # gap_size
    [5.0, 25.0]      # volume
]).T

# 2. Create optimizer and objective
optimizer = BayesianOptimizer(bounds=bounds, batch_size=8)
objective = MockObjectiveFunction(noise_std=0.1)

# 3. Run optimization
best_params, best_score = optimizer.optimize(
    objective_function=objective,
    n_iterations=20,
    n_initial_points=10
)

print(f"Best found: {best_params} with score {best_score:.4f}")
```

### Custom Objective Function
```python
def my_objective(X):
    """Custom objective function"""
    # Your optimization logic here
    # X is a tensor of shape (batch_size, 4)
    # Return tensor of shape (batch_size, 1)
    
    # Example: simple quadratic function
    result = -(X - 0.5).pow(2).sum(dim=1, keepdim=True)
    return result

# Use with optimizer
optimizer = BayesianOptimizer(bounds=bounds, batch_size=8)
best_params, best_score = optimizer.optimize(
    objective_function=my_objective,
    n_iterations=15
)
```

## Key Parameters

| Parameter | Description | Default | Tips |
|-----------|-------------|---------|------|
| `bounds` | Parameter bounds tensor (2, n_dims) | Required | Define your search space |
| `batch_size` | Candidates per iteration | 8 | Larger = more parallel evaluation |
| `n_iterations` | Optimization iterations | 20 | More iterations = better results |
| `n_initial_points` | Initial random samples | 10 | Should be ≥ 2 * dimensions |
| `noise_std` | Objective function noise | 0.1 | Match your actual noise level |

## Common Patterns

### Pattern 1: Quick Optimization
```python
# For quick tests and experimentation
best_params, best_score = optimizer.optimize(
    objective_function=objective,
    n_iterations=10,
    n_initial_points=5,
    verbose=True
)
```

### Pattern 2: Production Optimization
```python
# For production use with more iterations
best_params, best_score = optimizer.optimize(
    objective_function=objective,
    n_iterations=50,
    n_initial_points=20,
    verbose=True
)
```

### Pattern 3: Manual Control
```python
# For custom control over the optimization loop
optimizer.generate_initial_data(10, objective)

for i in range(20):
    optimizer.fit_model()
    candidates = optimizer.optimize_acquisition()
    values = objective(candidates)
    optimizer.update_training_data(candidates, values)
    print(f"Iteration {i+1}: Best = {optimizer.best_observed_value:.4f}")
```

## Expected Output

The demo will show:
- Parameter space information
- Optimization progress for each iteration
- Best parameters found
- Comparison with true optimum
- Convergence analysis
- Visualization plots (if matplotlib available)

## Troubleshooting

### Import Errors
```bash
# Install missing packages
pip install torch botorch gpytorch numpy matplotlib
```

### Slow Performance
- Reduce `batch_size` (e.g., 4 instead of 8)
- Reduce `n_iterations` for testing
- Use smaller `n_initial_points`

### Memory Issues
- Reduce `batch_size`
- Use CPU instead of GPU: `torch.set_default_device('cpu')`

## Next Steps

1. **Read the full README.md** for detailed documentation
2. **Check example_usage.py** for advanced usage patterns
3. **Modify the objective function** for your specific problem
4. **Adjust bounds and parameters** for your optimization problem

## Need Help?

- Check the full documentation in `README.md`
- Look at examples in `example_usage.py`
- Review the source code for detailed comments
- The package is designed to be self-contained and well-documented 