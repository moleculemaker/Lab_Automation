import torch
import numpy as np
from model_objective_factory import create_objective_from_model, create_mock_model_and_scaler
from bayesian_optimizer import BayesianOptimizer

def demonstrate_model_integration():
    """
    Demonstrate how to integrate a scikit-learn model with the Bayesian optimization framework.
    """
    
    print("=" * 60)
    print("Model Integration with Bayesian Optimization")
    print("=" * 60)
    
    # Step 1: Create or load a trained scikit-learn model
    print("\n1. Creating trained scikit-learn model...")
    model, scaler = create_mock_model_and_scaler()
    print(f"Model created with {model.coef_.shape[1]} features")
    
    # Step 2: Create objective function from the model
    print("\n2. Creating objective function from model...")
    objective_fn = create_objective_from_model(model, scaler)
    print("Objective function created successfully!")
    
    # Step 3: Set up Bayesian optimization
    print("\n3. Setting up Bayesian optimization...")
    
    # Define parameter bounds (same as in the demo)
    # BayesianOptimizer expects bounds in shape (2, n_dims) where first row is lower bounds
    bounds = torch.tensor([
        [0.1, 10.0, 0.05, 5.0],   # Lower bounds: [concentration, print_speed, gap_size, volume]
        [1.0, 100.0, 0.5, 25.0]  # Upper bounds: [concentration, print_speed, gap_size, volume]
    ], dtype=torch.float64)
    
    # Initialize optimizer
    optimizer = BayesianOptimizer(
        bounds=bounds,
        batch_size=4,  # Smaller batch for demonstration
        seed=42
    )
    
    print(f"Optimizer initialized with bounds:")
    print(f"  Concentration: [{bounds[0,0]:.1f}, {bounds[1,0]:.1f}]")
    print(f"  Print Speed: [{bounds[0,1]:.1f}, {bounds[1,1]:.1f}]")
    print(f"  Gap Size: [{bounds[0,2]:.3f}, {bounds[1,2]:.3f}]")
    print(f"  Volume: [{bounds[0,3]:.1f}, {bounds[1,3]:.1f}]")
    
    # Step 4: Run optimization
    print("\n4. Running Bayesian optimization...")
    
    # Run optimization
    best_params, best_score = optimizer.optimize(
        objective_function=objective_fn,
        n_iterations=5,  # Fewer iterations for demonstration
        n_initial_points=6,
        verbose=True
    )
    
    # Display results
    print(f"\nOptimization completed!")
    print(f"Best parameters found:")
    print(f"  Concentration: {best_params[0]:.3f}")
    print(f"  Print Speed: {best_params[1]:.1f}")
    print(f"  Gap Size: {best_params[2]:.3f}")
    print(f"  Volume: {best_params[3]:.1f}")
    print(f"Best success probability: {best_score:.4f}")
    
    # Step 5: Analyze results
    print("\n5. Analyzing optimization results...")
    
    # Get training data (all evaluated points)
    train_X, train_Y = optimizer.get_training_data()
    
    print(f"Total evaluations: {len(train_Y)}")
    print(f"Best score: {train_Y.max().item():.4f}")
    print(f"Mean score: {train_Y.mean().item():.4f}")
    print(f"Score improvement: {(train_Y.max() - train_Y.min()).item():.4f}")
    
    # Show top 3 parameter combinations
    print("\nTop 3 parameter combinations:")
    sorted_indices = torch.argsort(train_Y.flatten(), descending=True)
    
    for i, idx in enumerate(sorted_indices[:3]):
        params = train_X[idx]
        score = train_Y[idx].item()
        print(f"  {i+1}. Score: {score:.4f} | "
              f"Conc: {params[0]:.3f}, Speed: {params[1]:.1f}, "
              f"Gap: {params[2]:.3f}, Vol: {params[3]:.1f}")
    
    return optimizer, best_params, best_score

def test_with_real_model_workflow():
    """
    Example of how to use this with a real trained model.
    This shows the workflow you would follow with your actual model.
    """
    
    print("\n" + "=" * 60)
    print("Real Model Integration Workflow")
    print("=" * 60)
    
    print("\nExample workflow for using your trained model:")
    print("1. Load your trained model:")
    print("   import joblib")
    print("   model = joblib.load('your_trained_model.pkl')")
    print("   scaler = joblib.load('your_trained_scaler.pkl')")
    
    print("\n2. Create objective function:")
    print("   from model_objective_factory import create_objective_from_model")
    print("   objective_fn = create_objective_from_model(model, scaler)")
    
    print("\n3. Set up and run optimization:")
    print("   from bayesian_optimizer import BayesianOptimizer")
    print("   optimizer = BayesianOptimizer(objective_function=objective_fn, ...)")
    print("   best_params, best_score, results = optimizer.optimize()")
    
    print("\n4. The optimization will:")
    print("   - Handle batch evaluation of parameter combinations")
    print("   - Automatically perform feature engineering for each combination")
    print("   - Use your model's predict_proba to get success probabilities")
    print("   - Find optimal parameters that maximize success probability")
    
    print("\nFeature Engineering Details:")
    print("- Input: [concentration, print_speed, gap_size, volume]")
    print("- Automatically creates 11 features in the correct order:")
    print("  1. gap_size_squared")
    print("  2. solvent_CF (fixed at 0.5)")
    print("  3. print_speed_squared")
    print("  4. concentration_squared")
    print("  5. concentration")
    print("  6. gap_size")
    print("  7. print_speed_gap_size")
    print("  8. print_speed")
    print("  9. concentration_print_speed")
    print("  10. print_speed_volume")
    print("  11. volume")
    print("- Applies scaling using your trained StandardScaler")
    print("- Returns success probabilities from your model")

if __name__ == "__main__":
    # Run the demonstration
    optimizer, best_params, best_score = demonstrate_model_integration()
    
    # Show the real model workflow
    test_with_real_model_workflow()
    
    print("\n" + "=" * 60)
    print("Integration demonstration completed!")
    print("=" * 60)
    
    print("\nKey Benefits:")
    print("- Seamless integration between scikit-learn models and BoTorch")
    print("- Automatic feature engineering and scaling")
    print("- Batch evaluation for efficient optimization")
    print("- Clean separation of concerns using factory pattern")
    print("- Compatible with existing Bayesian optimization framework") 