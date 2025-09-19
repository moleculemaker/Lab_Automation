#!/usr/bin/env python3
"""
Simple script to run the Bayesian Optimization demo.

This script can be run directly to see the complete optimization workflow.
It handles imports and provides a clean interface for users.
"""

import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Main function to run the demo."""
    try:
        # Import and run the demo
        from optimizer.demo.demo import run_optimization_demo
        
        print("Starting Bayesian Optimization Demo...")
        print("This may take a few minutes to complete.")
        print("Press Ctrl+C to interrupt if needed.\n")
        
        # Run the demo with default parameters
        best_params, best_score = run_optimization_demo(
            n_iterations=20,
            n_initial_points=10,
            batch_size=8,
            noise_std=0.1,
            visualize=True,
            seed=42
        )
        
        print(f"\nDemo completed successfully!")
        print(f"Best parameters found: {best_params}")
        print(f"Best score achieved: {best_score:.4f}")
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Please ensure all required packages are installed:")
        print("pip install -r requirements.txt")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
        sys.exit(0)
        
    except Exception as e:
        print(f"Error running demo: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 