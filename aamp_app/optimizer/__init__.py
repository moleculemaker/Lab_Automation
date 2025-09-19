"""
Bayesian Optimization Package

A complete, self-contained Python package for batch Bayesian Optimization
using BoTorch and GPyTorch libraries.
"""

__version__ = "1.0.0"
__author__ = "Polyprint Project"

from .bayesian_optimizer import BayesianOptimizer
from .objective_function import MockObjectiveFunction
from .demo.demo import run_optimization_demo

__all__ = ["BayesianOptimizer", "MockObjectiveFunction", "run_optimization_demo"] 