"""
Parameter Space Definitions and Management

This module provides utilities for defining and managing parameter spaces
for Bayesian optimization in the Lab Automation framework.
"""

import torch
import numpy as np
from typing import List, Tuple, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum


class ParameterType(Enum):
    """Enumeration of parameter types."""
    CONTINUOUS = "continuous"
    DISCRETE = "discrete"
    CATEGORICAL = "categorical"


@dataclass
class Parameter:
    """Represents a single parameter in the optimization space."""
    name: str
    param_type: ParameterType
    bounds: Tuple[float, float]  # For continuous/discrete
    categories: Optional[List[str]] = None  # For categorical
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate parameter definition."""
        if self.param_type == ParameterType.CATEGORICAL:
            if self.categories is None:
                raise ValueError("Categories must be provided for categorical parameters")
        else:
            if len(self.bounds) != 2:
                raise ValueError("Bounds must be a tuple of (min, max)")
            if self.bounds[0] >= self.bounds[1]:
                raise ValueError("Lower bound must be less than upper bound")


class ParameterSpace:
    """
    Manages a collection of parameters for Bayesian optimization.
    
    This class provides utilities for:
    - Defining parameter spaces with different types
    - Converting between different representations
    - Validating parameter values
    - Sampling from the parameter space
    """
    
    def __init__(self, parameters: List[Parameter]):
        """
        Initialize parameter space with a list of parameters.
        
        Args:
            parameters: List of Parameter objects defining the space
        """
        self.parameters = parameters
        self.parameter_names = [p.name for p in parameters]
        self._validate_parameters()
        
    def _validate_parameters(self):
        """Validate that all parameters have unique names."""
        if len(self.parameter_names) != len(set(self.parameter_names)):
            raise ValueError("All parameters must have unique names")
    
    def get_continuous_bounds(self) -> List[Tuple[float, float]]:
        """
        Get bounds for continuous parameters only.
        
        Returns:
            List of (min, max) tuples for continuous parameters
        """
        bounds = []
        for param in self.parameters:
            if param.param_type == ParameterType.CONTINUOUS:
                bounds.append(param.bounds)
        return bounds
    
    def get_continuous_names(self) -> List[str]:
        """
        Get names of continuous parameters only.
        
        Returns:
            List of parameter names for continuous parameters
        """
        names = []
        for param in self.parameters:
            if param.param_type == ParameterType.CONTINUOUS:
                names.append(param.name)
        return names
    
    def get_bounds_tensor(self) -> torch.Tensor:
        """
        Get bounds as a torch tensor for the Bayesian optimizer.
        
        Returns:
            Bounds tensor of shape (2, n_dims)
        """
        bounds = []
        for param in self.parameters:
            if param.param_type == ParameterType.CONTINUOUS:
                bounds.append(param.bounds)
            elif param.param_type == ParameterType.DISCRETE:
                bounds.append(param.bounds)
            else:
                # For categorical, use integer encoding
                bounds.append((0, len(param.categories) - 1))
        
        return torch.tensor(bounds).T
    
    def sample_random_points(self, n_points: int, seed: Optional[int] = None) -> torch.Tensor:
        """
        Sample random points from the parameter space.
        
        Args:
            n_points: Number of points to sample
            seed: Random seed for reproducibility
            
        Returns:
            Tensor of sampled points of shape (n_points, n_dims)
        """
        if seed is not None:
            torch.manual_seed(seed)
            np.random.seed(seed)
        
        points = []
        for _ in range(n_points):
            point = []
            for param in self.parameters:
                if param.param_type == ParameterType.CONTINUOUS:
                    value = np.random.uniform(param.bounds[0], param.bounds[1])
                elif param.param_type == ParameterType.DISCRETE:
                    value = np.random.randint(param.bounds[0], param.bounds[1] + 1)
                else:  # Categorical
                    value = np.random.randint(0, len(param.categories))
                point.append(value)
            points.append(point)
        
        return torch.tensor(points, dtype=torch.float64)
    
    def tensor_to_dict(self, tensor: torch.Tensor) -> Dict[str, Union[float, str]]:
        """
        Convert parameter tensor to dictionary.
        
        Args:
            tensor: Parameter tensor of shape (n_dims,) or (batch_size, n_dims)
            
        Returns:
            Dictionary mapping parameter names to values
        """
        if tensor.dim() == 1:
            # Single point
            result = {}
            for i, param in enumerate(self.parameters):
                value = float(tensor[i])
                if param.param_type == ParameterType.CATEGORICAL:
                    value = param.categories[int(value)]
                result[param.name] = value
            return result
        else:
            # Batch of points
            results = []
            for j in range(tensor.shape[0]):
                point_dict = {}
                for i, param in enumerate(self.parameters):
                    value = float(tensor[j, i])
                    if param.param_type == ParameterType.CATEGORICAL:
                        value = param.categories[int(value)]
                    point_dict[param.name] = value
                results.append(point_dict)
            return results
    
    def dict_to_tensor(self, param_dict: Dict[str, Union[float, str]]) -> torch.Tensor:
        """
        Convert parameter dictionary to tensor.
        
        Args:
            param_dict: Dictionary mapping parameter names to values
            
        Returns:
            Parameter tensor of shape (n_dims,)
        """
        tensor_values = []
        for param in self.parameters:
            value = param_dict[param.name]
            if param.param_type == ParameterType.CATEGORICAL:
                # Convert categorical value to index
                try:
                    value = param.categories.index(value)
                except ValueError:
                    raise ValueError(f"Invalid categorical value '{value}' for parameter '{param.name}'")
            tensor_values.append(float(value))
        
        return torch.tensor(tensor_values, dtype=torch.float64)
    
    def validate_point(self, point: Union[torch.Tensor, Dict[str, Union[float, str]]]) -> bool:
        """
        Validate that a point is within the parameter space bounds.
        
        Args:
            point: Parameter point as tensor or dictionary
            
        Returns:
            True if point is valid, False otherwise
        """
        try:
            if isinstance(point, dict):
                tensor = self.dict_to_tensor(point)
            else:
                tensor = point
            
            for i, param in enumerate(self.parameters):
                value = float(tensor[i])
                if param.param_type == ParameterType.CONTINUOUS:
                    if value < param.bounds[0] or value > param.bounds[1]:
                        return False
                elif param.param_type == ParameterType.DISCRETE:
                    if value < param.bounds[0] or value > param.bounds[1] or value != int(value):
                        return False
                else:  # Categorical
                    if value < 0 or value >= len(param.categories) or value != int(value):
                        return False
            
            return True
        except Exception:
            return False
    
    def get_parameter_info(self) -> Dict[str, Any]:
        """
        Get information about all parameters.
        
        Returns:
            Dictionary containing parameter information
        """
        info = {}
        for param in self.parameters:
            info[param.name] = {
                'type': param.param_type.value,
                'bounds': param.bounds if param.param_type != ParameterType.CATEGORICAL else None,
                'categories': param.categories if param.param_type == ParameterType.CATEGORICAL else None,
                'description': param.description
            }
        return info


# Predefined parameter spaces for polyprint experiments
def create_polyprint_space() -> ParameterSpace:
    """
    Create a parameter space for polyprint optimization.
    
    Returns:    
        ParameterSpace with temperature, concentration, and speed parameters
    """
    parameters = [
        Parameter(
            name="temperature",
            param_type=ParameterType.CONTINUOUS,
            bounds=(20.0, 80.0),
            description="temperature in degrees Celsius"
        ),
        Parameter(
            name="concentration",
            param_type=ParameterType.CONTINUOUS,
            bounds=(0.1, 2.0),
            description="Polymer concentration in wt%"
        ),
        Parameter(
            name="speed",
            param_type=ParameterType.CONTINUOUS,
            bounds=(10.0, 120.0),
            description="speed in m/s"
        ),
        Parameter(
            name="material_type",
            param_type=ParameterType.CATEGORICAL,
            bounds=(0, 2),  # Not used for categorical
            categories=["PProDOT", "P3MEEMT", "P42gTTT"],
            description="Type of material being processed"
        )
    ]
    return ParameterSpace(parameters)

