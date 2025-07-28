import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from typing import Callable, Tuple
import warnings
warnings.filterwarnings('ignore')

def create_objective_from_model(model: LogisticRegression, scaler: StandardScaler = None) -> Callable:
    """
    Factory function that creates a BoTorch-compatible objective function from a trained scikit-learn model.
    
    Parameters:
    -----------
    model : LogisticRegression
        A trained scikit-learn LogisticRegression model
    scaler : StandardScaler, optional
        A fitted StandardScaler to normalize features. If None, no scaling is applied.
    
    Returns:
    --------
    Callable
        An objective function that accepts (batch_size, 4) tensor of base parameters
        and returns (batch_size, 1) tensor of success probabilities
    """
    
    # Determine expected number of features from the model or scaler
    if scaler is not None:
        n_features_expected = scaler.n_features_in_
    else:
        n_features_expected = model.coef_.shape[1]
    
    print(f"Model expects {n_features_expected} features")
    
    def objective_function(X: torch.Tensor) -> torch.Tensor:
        """
        Objective function that evaluates parameter combinations using the trained model.
        
        Parameters:
        -----------
        X : torch.Tensor
            Input tensor of shape (batch_size, 4) containing base parameters:
            [concentration, print_speed, gap_size, volume]
        
        Returns:
        --------
        torch.Tensor
            Output tensor of shape (batch_size, 1) containing success probabilities
        """
        
        # Convert to numpy for feature engineering
        X_np = X.detach().cpu().numpy()
        batch_size = X_np.shape[0]
        
        # Extract base parameters
        concentration = X_np[:, 0]  # Column 0: concentration
        print_speed = X_np[:, 1]    # Column 1: print_speed
        gap_size = X_np[:, 2]       # Column 2: gap_size
        volume = X_np[:, 3]         # Column 3: volume
        
        # Create comprehensive feature matrix based on typical polymer printing feature engineering
        features = create_feature_matrix(concentration, print_speed, gap_size, volume, n_features_expected)
        
        # Apply feature scaling if provided
        if scaler is not None:
            features = scaler.transform(features)
        
        # Get success probabilities using the trained model
        # predict_proba returns [P(class=0), P(class=1)], we want P(class=1)
        success_probabilities = model.predict_proba(features)[:, 1]
        
        # Convert back to PyTorch tensor and reshape for BoTorch
        result = torch.tensor(success_probabilities, dtype=torch.float32, device=X.device)
        result = result.unsqueeze(-1)  # Shape: (batch_size, 1)
        
        return result
    
    return objective_function

def create_feature_matrix(concentration, print_speed, gap_size, volume, n_features_expected):
    """
    Create feature matrix with comprehensive feature engineering to match trained model.
    """
    batch_size = len(concentration)
    
    if n_features_expected == 11:
        # Original 11-feature structure
        features = np.zeros((batch_size, 11))
        features[:, 0] = gap_size ** 2                    # gap_size_squared
        features[:, 1] = 0.5                              # solvent_CF (fixed constant)
        features[:, 2] = print_speed ** 2                 # print_speed_squared
        features[:, 3] = concentration ** 2               # concentration_squared
        features[:, 4] = concentration                    # concentration
        features[:, 5] = gap_size                         # gap_size
        features[:, 6] = print_speed * gap_size           # print_speed_gap_size
        features[:, 7] = print_speed                      # print_speed
        features[:, 8] = concentration * print_speed      # concentration_print_speed
        features[:, 9] = print_speed * volume             # print_speed_volume
        features[:, 10] = volume                          # volume
        
    else:
        # Extended feature structure for larger models
        features = np.zeros((batch_size, n_features_expected))
        
        # Base parameters
        features[:, 0] = concentration
        features[:, 1] = print_speed  
        features[:, 2] = gap_size
        features[:, 3] = volume
        
        # Interaction terms
        features[:, 4] = concentration * print_speed
        features[:, 5] = concentration * gap_size
        features[:, 6] = concentration * volume
        features[:, 7] = print_speed * gap_size
        features[:, 8] = print_speed * volume
        features[:, 9] = gap_size * volume
        
        # Squared terms
        features[:, 10] = concentration ** 2
        features[:, 11] = print_speed ** 2
        features[:, 12] = gap_size ** 2
        features[:, 13] = volume ** 2
        
        # Solvent features (assuming multiple solvents were used in training)
        if n_features_expected >= 18:
            # Add solvent dummy variables
            features[:, 14] = 0.5  # solvent_CB (fixed)
            features[:, 15] = 0.0  # solvent_CF 
            features[:, 16] = 0.0  # solvent_anisole
            features[:, 17] = 0.0  # solvent_p-xylene
            
            # If even more features, add higher-order interactions
            if n_features_expected > 18:
                for i in range(18, min(n_features_expected, 25)):
                    # Add more complex interactions or polynomial terms
                    if i == 18:
                        features[:, i] = concentration * print_speed * gap_size
                    elif i == 19:
                        features[:, i] = concentration * print_speed * volume
                    elif i == 20:
                        features[:, i] = concentration * gap_size * volume
                    elif i == 21:
                        features[:, i] = print_speed * gap_size * volume
                    elif i == 22:
                        features[:, i] = concentration ** 3
                    elif i == 23:
                        features[:, i] = print_speed ** 3
                    elif i == 24:
                        features[:, i] = gap_size ** 3
                    else:
                        features[:, i] = 1.0  # constant term
    
    return features

def create_mock_model_and_scaler() -> Tuple[LogisticRegression, StandardScaler]:
    """
    Create a mock LogisticRegression model and StandardScaler for demonstration purposes.
    
    Returns:
    --------
    Tuple[LogisticRegression, StandardScaler]
        A tuple containing the trained model and fitted scaler
    """
    
    # Set random seed for reproducibility
    np.random.seed(42)
    
    # Create dummy training data
    n_samples = 1000
    n_features = 11
    
    # Generate realistic parameter ranges for the dummy data
    # These approximate the ranges from the actual polymer printing experiments
    X_dummy = np.random.rand(n_samples, n_features)
    
    # Scale features to realistic ranges based on the feature definitions
    X_dummy[:, 0] = X_dummy[:, 0] * 0.25        # gap_size_squared (0 to 0.25)
    X_dummy[:, 1] = 0.5                         # solvent_CF (constant)
    X_dummy[:, 2] = X_dummy[:, 2] * 10000       # print_speed_squared (0 to 10000)
    X_dummy[:, 3] = X_dummy[:, 3] * 1.0         # concentration_squared (0 to 1.0)
    X_dummy[:, 4] = X_dummy[:, 4] * 1.0         # concentration (0 to 1.0)
    X_dummy[:, 5] = X_dummy[:, 5] * 0.5         # gap_size (0 to 0.5)
    X_dummy[:, 6] = X_dummy[:, 6] * 50          # print_speed_gap_size (0 to 50)
    X_dummy[:, 7] = X_dummy[:, 7] * 100         # print_speed (0 to 100)
    X_dummy[:, 8] = X_dummy[:, 8] * 100         # concentration_print_speed (0 to 100)
    X_dummy[:, 9] = X_dummy[:, 9] * 2500        # print_speed_volume (0 to 2500)
    X_dummy[:, 10] = X_dummy[:, 10] * 25        # volume (0 to 25)
    
    # Create synthetic target variable with some realistic patterns
    # Higher success probability for moderate concentration, speed, and gap_size
    concentration = X_dummy[:, 4]
    print_speed = X_dummy[:, 7]
    gap_size = X_dummy[:, 5]
    volume = X_dummy[:, 10]
    
    # Create a synthetic success probability based on realistic patterns
    # Success is higher for moderate values of key parameters
    success_prob = (
        0.3 +  # Base probability
        0.4 * np.exp(-((concentration - 0.6) ** 2) / 0.2) +  # Optimal concentration around 0.6
        0.2 * np.exp(-((print_speed - 45) ** 2) / 800) +     # Optimal print_speed around 45
        0.1 * np.exp(-((gap_size - 0.2) ** 2) / 0.08)        # Optimal gap_size around 0.2
    )
    
    # Add some noise
    success_prob += np.random.normal(0, 0.1, n_samples)
    success_prob = np.clip(success_prob, 0, 1)
    
    # Convert to binary outcomes
    y_dummy = (success_prob > 0.5).astype(int)
    
    # Fit the scaler
    scaler = StandardScaler()
    X_dummy_scaled = scaler.fit_transform(X_dummy)
    
    # Train the logistic regression model
    model = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(X_dummy_scaled, y_dummy)
    
    # Print model performance for verification
    accuracy = model.score(X_dummy_scaled, y_dummy)
    print(f"Mock model training accuracy: {accuracy:.3f}")
    
    return model, scaler

def test_objective_function():
    """
    Test the objective function with sample inputs to verify correct operation.
    """
    
    # Create mock model and scaler
    model, scaler = create_mock_model_and_scaler()
    
    # Create objective function
    objective_fn = create_objective_from_model(model, scaler)
    
    # Test with a batch of parameter combinations
    # Parameters: [concentration, print_speed, gap_size, volume]
    test_params = torch.tensor([
        [0.5, 50.0, 0.2, 15.0],  # Near optimal values
        [0.1, 10.0, 0.05, 5.0],  # Lower values
        [0.9, 90.0, 0.45, 25.0], # Higher values
        [0.6, 45.0, 0.2, 15.0]   # Optimal values
    ], dtype=torch.float32)
    
    print(f"Input tensor shape: {test_params.shape}")
    print(f"Input parameters:\n{test_params}")
    
    # Call objective function
    results = objective_fn(test_params)
    
    print(f"Output tensor shape: {results.shape}")
    print(f"Success probabilities:\n{results}")
    
    # Verify that results are valid probabilities
    assert torch.all(results >= 0), "All probabilities should be non-negative"
    assert torch.all(results <= 1), "All probabilities should be <= 1"
    assert results.shape == (4, 1), f"Expected shape (4, 1), got {results.shape}"
    
    print("All tests passed!")
    
    return objective_fn, test_params, results

if __name__ == "__main__":
    print("=" * 60)
    print("Model Objective Factory Demonstration")
    print("=" * 60)
    
    print("\n1. Creating and training mock LogisticRegression model...")
    model, scaler = create_mock_model_and_scaler()
    
    print(f"\nModel coefficients shape: {model.coef_.shape}")
    print(f"Model intercept: {model.intercept_[0]:.3f}")
    print(f"Number of features expected: {model.coef_.shape[1]}")
    
    print("\n2. Creating objective function from model...")
    objective_fn = create_objective_from_model(model, scaler)
    print("Objective function created successfully!")
    
    print("\n3. Testing objective function with sample parameter combinations...")
    
    # Create sample input tensor (batch_size=2, 4 parameters)
    sample_params = torch.tensor([
        [0.6, 45.0, 0.2, 15.0],  # Near optimal combination
        [0.2, 80.0, 0.4, 10.0]   # Suboptimal combination
    ], dtype=torch.float32)
    
    print(f"Sample input tensor shape: {sample_params.shape}")
    print(f"Sample parameters:")
    print(f"  Batch 1: concentration={sample_params[0,0]:.1f}, print_speed={sample_params[0,1]:.1f}, gap_size={sample_params[0,2]:.1f}, volume={sample_params[0,3]:.1f}")
    print(f"  Batch 2: concentration={sample_params[1,0]:.1f}, print_speed={sample_params[1,1]:.1f}, gap_size={sample_params[1,2]:.1f}, volume={sample_params[1,3]:.1f}")
    
    # Call objective function
    results = objective_fn(sample_params)
    
    print(f"\nResults tensor shape: {results.shape}")
    print(f"Success probabilities:")
    print(f"  Batch 1: {results[0,0]:.4f}")
    print(f"  Batch 2: {results[1,0]:.4f}")
    
    print("\n4. Running comprehensive test...")
    test_objective_function()
    
    print("\n" + "=" * 60)
    print("Demonstration completed successfully!")
    print("=" * 60)
    
    print("\nUsage Summary:")
    print("- Use create_objective_from_model(model, scaler) to create an objective function")
    print("- The returned function accepts (batch_size, 4) tensors of [concentration, print_speed, gap_size, volume]")
    print("- It returns (batch_size, 1) tensors of success probabilities")
    print("- The function handles all necessary feature engineering and scaling internally") 