"""
Recipe Templates and Parameter Substitution

This module provides utilities for creating recipe templates and handling
parameter substitution in the Lab Automation framework.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Callable, Optional, List
import os
import re
from datetime import datetime

# Lab Automation imports
from command_sequence import CommandSequence
from devices.dummy_heater import DummyHeater
from devices.dummy_motor import DummyMotor
from devices.dummy_meter import DummyMeter
from commands.dummy_heater_commands import (
    DummyHeaterInitialize, DummyHeaterSetTemp, DummyHeaterDeinitialize
)
from commands.dummy_motor_commands import (
    DummyMotorInitialize, DummyMotorSetSpeed, DummyMotorMoveRelative, DummyMotorDeinitialize,
    DummyMotorMoveSpeedAbsolute
)
from commands.dummy_meter_commands import (
    DummyMeterInitialize, DummyMeterMeasure, DummyMeterDeinitialize
)


def create_polyprint_template() -> Callable:
    """
    Create a recipe template for polyprint optimization.
    
    Returns:
        Function that creates CommandSequence from parameters
    """
    def recipe_template(parameters: Dict[str, Any]) -> CommandSequence:
        """
        Create a command sequence for polyprint experiment.
        
        Args:
            parameters: Dictionary containing 'temperature', 'concentration', 'speed', 'material_type'
            
        Returns:
            CommandSequence for the experiment
        """
        # Extract parameters
        temperature = parameters.get('temperature', 50.0)
        concentration = parameters.get('concentration', 1.0)
        speed = parameters.get('speed', 50.0)
        material_type = parameters.get('material_type', 'polymer')
        
        # Generate coefficients for emulating the objective function (from example6)
        n_fourier = 3
        a1 = np.random.uniform(-1, 1, size=(n_fourier,1))
        b1 = np.random.uniform(-1, 1, size=(n_fourier,1))
        a2 = np.random.uniform(-1, 1, size=(n_fourier,1))
        b2 = np.random.uniform(-1, 1, size=(n_fourier,1))
        noise_width = 0.1
        
        # Create command sequence
        seq = CommandSequence()
        
        # Create devices (using example6-style setup)
        heater = DummyHeater('print_heater', heat_rate=40.0)
        motor = DummyMotor('print_motor')
        meter = DummyMeter('print_meter', heater, motor, a1, b1, a2, b2, noise_width)
        
        # Add devices to sequence
        seq.add_device(heater)
        seq.add_device(motor)
        seq.add_device(meter)
        
        # Add commands to sequence
        seq.add_command(DummyHeaterInitialize(heater))
        seq.add_command(DummyMotorInitialize(motor))
        seq.add_command(DummyMeterInitialize(meter))
        
        # Move to start position
        seq.add_command(DummyMotorMoveSpeedAbsolute(motor, 50.0, 5.0))
        
        # Set print parameters
        seq.add_command(DummyHeaterSetTemp(heater, temperature))
        seq.add_command(DummyMotorSetSpeed(motor, speed))
        
        # Simulate printing process
        seq.add_command(DummyMotorMoveRelative(motor, distance=5.0))  # Print material
        seq.add_command(DummyMotorMoveRelative(motor, distance=-5.0))  # Return to start
        
        # Measure printed material
        seq.add_command(DummyMeterMeasure(meter, filename=None))
        
        # Deinitialize devices
        seq.add_command(DummyHeaterDeinitialize(heater))
        seq.add_command(DummyMotorDeinitialize(motor))
        seq.add_command(DummyMeterDeinitialize(meter))
        
        return seq
    
    return recipe_template


def create_polyprint_template() -> Callable:
    """
    Create a recipe template for polyprint optimization.
    
    Returns:
        Function that creates CommandSequence from parameters
    """
    def recipe_template(parameters: Dict[str, Any]) -> CommandSequence:
        """
        Create a command sequence for polyprint experiment.
        
        Args:
            parameters: Dictionary containing 'temperature', 'concentration', 'speed', 'material_type'
            
        Returns:
            CommandSequence for the experiment
        """
        # Extract parameters
        temperature = parameters.get('temperature', 50.0)
        concentration = parameters.get('concentration', 1.0)
        speed = parameters.get('speed', 50.0)
        material_type = parameters.get('material_type', 'PProDOT')
        
        # Generate coefficients for emulating the objective function (from example6)
        n_fourier = 3
        a1 = np.random.uniform(-1, 1, size=(n_fourier,1))
        b1 = np.random.uniform(-1, 1, size=(n_fourier,1))
        a2 = np.random.uniform(-1, 1, size=(n_fourier,1))
        b2 = np.random.uniform(-1, 1, size=(n_fourier,1))
        noise_width = 0.1
        
        # Create command sequence
        seq = CommandSequence()
        
        # Create devices (using example6-style setup)
        heater = DummyHeater('print_heater', heat_rate=40.0)
        motor = DummyMotor('print_motor')
        meter = DummyMeter('print_meter', heater, motor, a1, b1, a2, b2, noise_width)
        
        # Add devices to sequence
        seq.add_device(heater)
        seq.add_device(motor)
        seq.add_device(meter)
        
        # Add commands to sequence
        seq.add_command(DummyHeaterInitialize(heater))
        seq.add_command(DummyMotorInitialize(motor))
        seq.add_command(DummyMeterInitialize(meter))
        
        # Move to start position
        seq.add_command(DummyMotorMoveSpeedAbsolute(motor, 50.0, 5.0))
        
        # Set print parameters
        seq.add_command(DummyHeaterSetTemp(heater, temperature))
        seq.add_command(DummyMotorSetSpeed(motor, speed))
        
        # Simulate printing process
        seq.add_command(DummyMotorMoveRelative(motor, distance=5.0))  # Print material
        seq.add_command(DummyMotorMoveRelative(motor, distance=-5.0))  # Return to start
        
        # Measure printed material
        seq.add_command(DummyMeterMeasure(meter, filename=None))
        
        # Deinitialize devices
        seq.add_command(DummyHeaterDeinitialize(heater))
        seq.add_command(DummyMotorDeinitialize(motor))
        seq.add_command(DummyMeterDeinitialize(meter))
        
        return seq
    
    return recipe_template


def create_custom_recipe_template(device_setup_func: Callable, command_setup_func: Callable) -> Callable:
    """
    Create a custom recipe template using provided setup functions.
    
    Args:
        device_setup_func: Function that creates and returns devices
        command_setup_func: Function that creates commands from parameters and devices
        
    Returns:
        Function that creates CommandSequence from parameters
    """
    def recipe_template(parameters: Dict[str, float]) -> CommandSequence:
        """
        Create a command sequence using custom setup functions.
        
        Args:
            parameters: Dictionary containing experiment parameters
            
        Returns:
            CommandSequence for the experiment
        """
        # Create command sequence
        seq = CommandSequence()
        
        # Setup devices
        devices = device_setup_func(parameters)
        
        # Add devices to sequence
        for device in devices:
            seq.add_device(device)
        
        # Setup commands
        commands = command_setup_func(parameters, devices)
        
        # Add commands to sequence
        for command in commands:
            seq.add_command(command)
        
        return seq
    
    return recipe_template
