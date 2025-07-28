"""
Common Objective Function Templates

This module provides common objective function templates for extracting
objective values from experiment results in the Lab Automation framework.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Callable, Optional
import os
import re
from datetime import datetime


def create_polyprint_objective_function() -> Callable:
    """
    Create an objective function for polyprint optimization.

    Returns:
        Function that extracts objective value from polyprint experiment results
    """
    def objective_function(parameters: Dict[str, Any], experiment_id: str) -> float:
        """
        Extract objective value from polyprint experiment results.

        Args:
            parameters: Dictionary containing experiment parameters
            experiment_id: Unique identifier for the experiment

        Returns:
            Objective value (higher is better)
        """
        temperature = parameters.get('temperature', 50.0)
        concentration = parameters.get('concentration', 1.0)
        speed = parameters.get('speed', 50.0)
        material_type = parameters.get('material_type', 'polymer')

        # Simulate a noisy objective function for polyprint
        np.random.seed(hash(experiment_id) % 2**32)

        # Optimal conditions for polyprint (example values)
        optimal_temp = 60.0
        optimal_concentration = 1.5
        optimal_speed = 80.0

        # Material type bonuses
        material_bonus = {
            'polymer': 0.0,
            'ceramic': -0.1,  # Slightly harder to print
            'metal': -0.2     # More challenging
        }

        # Calculate objective based on distance from optimal conditions
        temp_penalty = -((temperature - optimal_temp) ** 2) / 1000.0
        conc_penalty = -((concentration - optimal_concentration) ** 2) / 100.0
        speed_penalty = -((speed - optimal_speed) ** 2) / 1000.0
        material_penalty = material_bonus.get(material_type, 0.0)

        objective = temp_penalty + conc_penalty + speed_penalty + material_penalty
        noise = np.random.normal(0, 0.05)

        return objective + noise

    return objective_function


def create_polyprint_objective_function() -> Callable:
    """
    Create an objective function for polyprint optimization.

    Returns:
        Function that extracts objective value from polyprint experiment results
    """
    def objective_function(parameters: Dict[str, Any], experiment_id: str) -> float:
        """
        Extract objective value from polyprint experiment results.

        Args:
            parameters: Dictionary containing experiment parameters
            experiment_id: Unique identifier for the experiment

        Returns:
            Objective value (higher is better)
        """
        temperature = parameters.get('temperature', 50.0)
        concentration = parameters.get('concentration', 1.0)
        speed = parameters.get('speed', 50.0)
        material_type = parameters.get('material_type', 'PProDOT')

        # Simulate a noisy objective function for polyprint
        np.random.seed(hash(experiment_id) % 2**32)

        # Optimal conditions for polyprint (example values)
        optimal_temp = 60.0
        optimal_concentration = 1.5
        optimal_speed = 80.0

        # Material type bonuses
        material_bonus = {
            'PProDOT': 0.0,
            'P3MEEMT': -0.1,  # Slightly harder to print
            'P42gTTT': -0.2     # More challenging
        }

        # Calculate objective based on distance from optimal conditions
        temp_penalty = -((temperature - optimal_temp) ** 2) / 1000.0
        conc_penalty = -((concentration - optimal_concentration) ** 2) / 100.0
        speed_penalty = -((speed - optimal_speed) ** 2) / 1000.0
        material_penalty = material_bonus.get(material_type, 0.0)

        objective = temp_penalty + conc_penalty + speed_penalty + material_penalty
        noise = np.random.normal(0, 0.05)

        return objective + noise

    return objective_function


def create_model_based_polyprint_objective(model, scaler=None) -> Callable:
    """
    Create a model-based objective function for polyprint optimization.
    
    Args:
        model: Trained scikit-learn model (e.g., LogisticRegression)
        scaler: Fitted StandardScaler (optional)
        
    Returns:
        Function that extracts objective value using the trained model
    """
    def objective_function(parameters: Dict[str, Any], experiment_id: str) -> float:
        """
        Extract objective value using the trained model.
        
        Args:
            parameters: Dictionary containing experiment parameters
            experiment_id: Unique identifier for the experiment
            
        Returns:
            Objective value (success probability from model)
        """
        # Extract polyprint parameters
        concentration = parameters.get('concentration', 1.0)
        speed = parameters.get('speed', 50.0)
        temperature = parameters.get('temperature', 50.0)
        material_type = parameters.get('material_type', 'polymer')
        
        # Convert to tensor format expected by model
        # Note: The model expects [concentration, print_speed, gap_size, volume]
        # We'll map temperature to gap_size and material_type to volume for demonstration
        gap_size = temperature / 100.0  # Scale temperature to gap_size range
        volume = 15.0 if material_type == 'polymer' else (10.0 if material_type == 'ceramic' else 20.0)
        
        # Create input tensor for model
        input_tensor = torch.tensor([[concentration, speed, gap_size, volume]], dtype=torch.float32)
        
        # Use the model to predict success probability
        from .model_objective_factory import create_objective_from_model
        model_objective = create_objective_from_model(model, scaler)
        
        # Get prediction
        success_prob = model_objective(input_tensor).item()
        
        return success_prob
    
    return objective_function


def create_data_extraction_objective_function(data_directory: str = "data/dummy_meter") -> Callable:
    """
    Create an objective function that extracts values from data files.
    
    Args:
        data_directory: Directory containing experiment data files
        
    Returns:
        Function that extracts objective value from data files
    """
    def objective_function(parameters: Dict[str, float], experiment_id: str) -> float:
        """
        Extract objective value from data files.
        
        Args:
            parameters: Dictionary containing experiment parameters
            experiment_id: Unique identifier for the experiment
            
        Returns:
            Objective value extracted from data
        """
        try:
            # Look for data file with experiment_id
            data_file = os.path.join(data_directory, f"{experiment_id}.csv")
            
            if os.path.exists(data_file):
                # Read data file
                df = pd.read_csv(data_file)
                
                # Extract objective value (modify based on your data format)
                if 'value' in df.columns:
                    objective_value = df['value'].mean()  # or max, min, etc.
                elif 'measurement' in df.columns:
                    objective_value = df['measurement'].mean()
                else:
                    # Default to first numeric column
                    numeric_columns = df.select_dtypes(include=[np.number]).columns
                    if len(numeric_columns) > 0:
                        objective_value = df[numeric_columns[0]].mean()
                    else:
                        raise ValueError("No numeric columns found in data file")
                
                return float(objective_value)
            else:
                # If no data file found, return a penalty
                print(f"Warning: No data file found for experiment {experiment_id}")
                return -1000.0
                
        except Exception as e:
            print(f"Error extracting objective value for experiment {experiment_id}: {str(e)}")
            return -1000.0
    
    return objective_function


def create_log_extraction_objective_function(log_directory: str = "logs/optimization") -> Callable:
    """
    Create an objective function that extracts values from log files.
    
    Args:
        log_directory: Directory containing experiment log files
        
    Returns:
        Function that extracts objective value from log files
    """
    def objective_function(parameters: Dict[str, float], experiment_id: str) -> float:
        """
        Extract objective value from log files.
        
        Args:
            parameters: Dictionary containing experiment parameters
            experiment_id: Unique identifier for the experiment
            
        Returns:
            Objective value extracted from logs
        """
        try:
            # Look for log file with experiment_id
            log_file = os.path.join(log_directory, f"{experiment_id}.log")
            
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    log_content = f.read()
                
                # Look for objective value in log (modify pattern based on your logging format)
                # Example: look for "Objective: 0.1234" or "Score: 0.1234"
                objective_patterns = [
                    r"Objective:\s*([+-]?\d*\.?\d+)",
                    r"Score:\s*([+-]?\d*\.?\d+)",
                    r"Result:\s*([+-]?\d*\.?\d+)",
                    r"Value:\s*([+-]?\d*\.?\d+)"
                ]
                
                for pattern in objective_patterns:
                    match = re.search(pattern, log_content)
                    if match:
                        return float(match.group(1))
                
                # If no pattern found, return a default value
                print(f"Warning: No objective value pattern found in log for experiment {experiment_id}")
                return 0.0
            else:
                # If no log file found, return a penalty
                print(f"Warning: No log file found for experiment {experiment_id}")
                return -1000.0
                
        except Exception as e:
            print(f"Error extracting objective value from log for experiment {experiment_id}: {str(e)}")
            return -1000.0
    
    return objective_function


def create_custom_objective_function(extraction_func: Callable) -> Callable:
    """
    Create a custom objective function using provided extraction function.
    
    Args:
        extraction_func: Function that extracts objective value from experiment results
        
    Returns:
        Function that extracts objective value
    """
    def objective_function(parameters: Dict[str, float], experiment_id: str) -> float:
        """
        Extract objective value using custom extraction function.
        
        Args:
            parameters: Dictionary containing experiment parameters
            experiment_id: Unique identifier for the experiment
            
        Returns:
            Objective value
        """
        try:
            return extraction_func(parameters, experiment_id)
        except Exception as e:
            print(f"Error in custom objective function for experiment {experiment_id}: {str(e)}")
            return -1000.0
    
    return objective_function


def create_multi_objective_function(objective_functions: Dict[str, Callable], 
                                  weights: Optional[Dict[str, float]] = None) -> Callable:
    """
    Create a multi-objective function that combines multiple objectives.
    
    Args:
        objective_functions: Dictionary mapping objective names to functions
        weights: Dictionary mapping objective names to weights (optional)
        
    Returns:
        Function that returns weighted sum of objectives
    """
    if weights is None:
        # Equal weights if not specified
        weights = {name: 1.0 / len(objective_functions) for name in objective_functions.keys()}
    
    def multi_objective_function(parameters: Dict[str, float], experiment_id: str) -> float:
        """
        Calculate weighted sum of multiple objectives.
        
        Args:
            parameters: Dictionary containing experiment parameters
            experiment_id: Unique identifier for the experiment
            
        Returns:
            Weighted sum of objective values
        """
        total_objective = 0.0
        
        for name, func in objective_functions.items():
            weight = weights.get(name, 0.0)
            objective_value = func(parameters, experiment_id)
            total_objective += weight * objective_value
        
        return total_objective
    
    return multi_objective_function


def create_constraint_penalty_objective_function(base_objective: Callable,
                                               constraints: Dict[str, Callable],
                                               penalty_weight: float = 1000.0) -> Callable:
    """
    Create an objective function with constraint penalties.
    
    Args:
        base_objective: Base objective function
        constraints: Dictionary mapping constraint names to constraint functions
        penalty_weight: Weight for constraint violations
        
    Returns:
        Function that applies penalties for constraint violations
    """
    def constraint_objective_function(parameters: Dict[str, float], experiment_id: str) -> float:
        """
        Calculate objective with constraint penalties.
        
        Args:
            parameters: Dictionary containing experiment parameters
            experiment_id: Unique identifier for the experiment
            
        Returns:
            Objective value with constraint penalties
        """
        # Calculate base objective
        base_value = base_objective(parameters, experiment_id)
        
        # Calculate constraint violations
        total_penalty = 0.0
        for name, constraint_func in constraints.items():
            constraint_value = constraint_func(parameters, experiment_id)
            if constraint_value > 0:  # Constraint violated
                total_penalty += penalty_weight * constraint_value
        
        return base_value - total_penalty
    
    return constraint_objective_function 