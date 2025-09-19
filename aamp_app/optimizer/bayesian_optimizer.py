import torch
import numpy as np
from typing import Callable, Tuple, Optional, List

# BoTorch imports for Bayesian optimization
from botorch.models import SingleTaskGP
from botorch.fit import fit_gpytorch_mll
from botorch.acquisition import qLogNoisyExpectedImprovement
from botorch.optim import optimize_acqf
from botorch.utils.transforms import normalize, unnormalize

# GPyTorch imports for Gaussian process components
from gpytorch.mlls import ExactMarginalLogLikelihood
from gpytorch.kernels import ScaleKernel, RBFKernel
from gpytorch.priors import GammaPrior

def plot_optimization_results(optimizer, objective):
    """Create selective plots of the optimization results (1, 3, and 4 only)."""

    import matplotlib.pyplot as plt
    import numpy as np
    import base64
    import io

    history = optimizer.get_optimization_history()
    train_X, train_Y = optimizer.get_training_data()
    true_params, _ = objective.get_optimal_parameters()
    true_score = objective.evaluate_at_optimal()

    # Create a 1x3 subplot layout for the three selected plots
    fig, axes = plt.subplots(1, 3, figsize=(21, 6))  # Wider layout

    ### 1. Optimization Progress (axes[0])
    iterations = [h['iteration'] for h in history]
    best_values = [h['best_value'] for h in history]

    axes[0].plot(iterations, best_values, 'b-o', linewidth=2, markersize=6)
    axes[0].axhline(y=true_score, color='r', linestyle='--', alpha=0.7, 
                    label=f'True optimum: {true_score:.3f}')
    axes[0].set_xlabel('Iteration')
    axes[0].set_ylabel('Best Observed Value')
    axes[0].set_title('Optimization Progress')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    ### 3. Parameter Space Exploration (axes[1])
    scatter = axes[1].scatter(train_X[:, 0], train_X[:, 1], c=train_Y.squeeze(), 
                              cmap='viridis', alpha=0.6, s=50)
    axes[1].scatter(optimizer.best_parameters[0], optimizer.best_parameters[1], 
                    c='red', s=200, marker='*', label='Best found', 
                    edgecolor='black', linewidth=2)
    axes[1].scatter(true_params[0], true_params[1], c='orange', s=200, marker='*', 
                    label='True optimum', edgecolor='black', linewidth=2)
    axes[1].set_xlabel('Concentration')
    axes[1].set_ylabel('Print Speed (mm/s)')
    axes[1].set_title('Parameter Space Exploration')
    axes[1].legend()
    plt.colorbar(scatter, ax=axes[1], label='Objective Value')

    ### 4. Gap Size vs Volume (axes[2])
    scatter2 = axes[2].scatter(train_X[:, 2], train_X[:, 3], c=train_Y.squeeze(), 
                               cmap='viridis', alpha=0.6, s=50)
    axes[2].scatter(optimizer.best_parameters[2], optimizer.best_parameters[3], 
                    c='red', s=200, marker='*', label='Best found', 
                    edgecolor='black', linewidth=2)
    axes[2].scatter(true_params[2], true_params[3], c='orange', s=200, marker='*', 
                    label='True optimum', edgecolor='black', linewidth=2)
    axes[2].set_xlabel('Gap Size (mm)')
    axes[2].set_ylabel('Volume (μL)')
    axes[2].set_title('🔍 Gap Size vs Volume')
    axes[2].legend()
    plt.colorbar(scatter2, ax=axes[2], label='Objective Value')

    plt.tight_layout()
    plt.show()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight')
    buf.seek(0)
    encoded_image = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.close(fig)

    return encoded_image

class BayesianOptimizer:
    
    def __init__(
        self,
        bounds: torch.Tensor,
        batch_size: int = 8,
        noise_variance: float = 0.01,
        seed: int = 42
    ):
        self.bounds = bounds.double()
        self.batch_size = batch_size
        self.noise_variance = noise_variance
        self.seed = seed

        torch.manual_seed(seed)
        np.random.seed(seed)

        assert bounds.shape[0] == 2, "Bounds must have shape (2, n_dims)"
        assert (bounds[1] > bounds[0]).all(), "Upper bounds must be greater than lower bounds"

        self.n_dims = bounds.shape[1]

        self.train_X = None
        self.train_Y = None
        self.model = None

        self.iteration_history = []
        self.best_observed_value = -float('inf')
        self.best_parameters = None

    def generate_initial_data(self, n_points: int, objective_function: Callable) -> None:
        print(f"Generating {n_points} initial training points...")

        initial_X = self._generate_random_points(n_points)
        initial_Y = objective_function(initial_X)

        self.train_X = initial_X
        self.train_Y = initial_Y

        # Print all initial parameter sets and their scores
        # print("Initial parameter sets and scores:")  # <-- ADDED PRINT
        # for i in range(n_points):
        #     print(f"  [{i+1}] Params: {initial_X[i].tolist()}, Score: {initial_Y[i].item():.4f}")  # <-- ADDED PRINT

        best_idx = torch.argmax(initial_Y)
        self.best_observed_value = initial_Y[best_idx].item()
        self.best_parameters = initial_X[best_idx]

        print(f"Initial best score: {self.best_observed_value:.4f}")
        print(f"Initial best parameters: {self.best_parameters}")

    def _generate_random_points(self, n_points: int) -> torch.Tensor:
        unit_points = torch.rand(n_points, self.n_dims, dtype=torch.float64)
        lower_bounds = self.bounds[0]
        upper_bounds = self.bounds[1]
        scaled_points = lower_bounds + (upper_bounds - lower_bounds) * unit_points
        return scaled_points

    def fit_model(self) -> None:
        if self.train_X is None or self.train_Y is None:
            raise ValueError("No training data available. Call generate_initial_data first.")

        train_X_double = self.train_X.double()
        train_Y_double = self.train_Y.double()

        train_X_normalized = normalize(train_X_double, self.bounds.double())
        train_Y_normalized = (train_Y_double - train_Y_double.mean()) / train_Y_double.std()

        self.model = SingleTaskGP(
            train_X_normalized,
            train_Y_normalized,
            covar_module=ScaleKernel(
                RBFKernel(
                    lengthscale_prior=GammaPrior(2.0, 0.5),
                    ard_num_dims=self.n_dims
                ),
                outputscale_prior=GammaPrior(2.0, 0.5)
            )
        )

        self.model.train()
        mll = ExactMarginalLogLikelihood(self.model.likelihood, self.model)
        fit_gpytorch_mll(mll)
        self.model.eval()

    def optimize_acquisition(self) -> torch.Tensor:
        if self.model is None:
            raise ValueError("Model not fitted. Call fit_model first.")

        train_X_double = self.train_X.double()
        train_X_normalized = normalize(train_X_double, self.bounds.double())

        acquisition_function = qLogNoisyExpectedImprovement(
            model=self.model,
            X_baseline=train_X_normalized,
            prune_baseline=True,
            cache_root=True
        )

        unit_bounds = torch.stack([torch.zeros(self.n_dims), torch.ones(self.n_dims)]).double()
        candidates, _ = optimize_acqf(
            acq_function=acquisition_function,
            bounds=unit_bounds,
            q=self.batch_size,
            num_restarts=20,
            raw_samples=200,
            options={"batch_limit": 5, "maxiter": 200}
        )

        candidates_unnormalized = unnormalize(candidates, self.bounds.double())
        return candidates_unnormalized.float()

    def update_training_data(self, new_X: torch.Tensor, new_Y: torch.Tensor) -> None:
        self.train_X = torch.cat([self.train_X, new_X], dim=0)
        self.train_Y = torch.cat([self.train_Y, new_Y], dim=0)

        current_best_idx = torch.argmax(new_Y)
        current_best_value = new_Y[current_best_idx].item()

        if current_best_value > self.best_observed_value:
            self.best_observed_value = current_best_value
            self.best_parameters = new_X[current_best_idx]

    def optimize(
        self,
        objective_function: Callable,
        n_iterations: int = 20,
        n_initial_points: int = 10,
        verbose: bool = True,
        target: float = 0.95
    ) -> Tuple[torch.Tensor, float]:

        img = []

        if verbose:
            print("=" * 60)
            print("BAYESIAN OPTIMIZATION STARTING")
            print("=" * 60)
            print(f"Parameters: {self.n_dims} dimensions")
            print(f"Batch size: {self.batch_size}")
            print(f"Iterations: {n_iterations}")
            print(f"Initial points: {n_initial_points}")
            print("=" * 60)

        self.generate_initial_data(n_initial_points, objective_function)

        for iteration in range(n_iterations):
            if verbose:
                print(f"\nIteration {iteration + 1}/{n_iterations}")
                print("-" * 40)
                print("Fitting GP model...")

            self.fit_model()

            if verbose:
                print("Optimizing acquisition function...")
            candidates = self.optimize_acquisition()

            if verbose:
                print(f"Evaluating {self.batch_size} candidates...")
            candidate_values = objective_function(candidates)

            # Print all evaluated candidates and their scores
            print("New candidate parameter sets and scores:")  # <-- ADDED PRINT
            for i in range(self.batch_size):
                print(f"  [{i+1}] Params: {candidates[i].tolist()}, Score: {candidate_values[i].item():.4f}")  # <-- ADDED PRINT

            self.update_training_data(candidates, candidate_values)

            iteration_info = {
                'iteration': iteration + 1,
                'best_value': self.best_observed_value,
                'best_params': self.best_parameters.clone()
            }
            self.iteration_history.append(iteration_info)

            if verbose:
                print(f"Current best score: {self.best_observed_value:.4f}")
                print(f"Current best parameters: {self.best_parameters}")
            img.append(plot_optimization_results(self, objective_function))

            if self.best_observed_value >= target:
                if verbose:
                    print(f"Target objective {target} reached. Stopping optimization.")
                break

        if verbose:
            print("\n" + "=" * 60)
            print("OPTIMIZATION COMPLETED")
            print("=" * 60)
            print(f"Final best score: {self.best_observed_value:.4f}")
            print(f"Final best parameters: {self.best_parameters}")
            print(f"Total evaluations: {len(self.train_X)}")

        return self.best_parameters, self.best_observed_value, img

    def get_optimization_history(self) -> List[dict]:
        return self.iteration_history

    def get_training_data(self) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.train_X, self.train_Y
