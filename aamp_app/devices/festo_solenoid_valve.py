"""Requires Festo Solenoid Valve flashed to Arduino Board"""
"""Valve 1: Pin 12, Valve 2: Pin 8, Valve 3: Pin 4"""
from typing import Tuple, Optional
import time
import serial

from .device import ArduinoSerialDevice, check_initialized, check_serial


class FestoSolenoidValve(ArduinoSerialDevice):
    def __init__(
        self, name: str, port: str, baudrate: int = 9600, timeout: float = 0.1
    ):
        super().__init__(name, port, baudrate, timeout)

    def get_init_args(self) -> dict:
        args_dict = {
            "name": self._name,
            "port": self._port,
            "baudrate": self._baudrate,
            "timeout": self._timeout
        }
        return args_dict

    def update_init_args(self, args_dict: dict):
        self._name = args_dict["name"]
        self._port = args_dict["port"]
        self._baudrate = args_dict["baudrate"]
        self._timeout = args_dict["timeout"]

    def initialize(self) -> Tuple[bool, str]:
        self._is_initialized = True
        return (True, "Solenoid valve initialized")

    def deinitialize(self) -> Tuple[bool, str]:
        self.ser.close()
        self._is_initialized = False
        return (True, "Solenoid valve deinitialized")

    @check_serial
    @check_initialized
    def valve_open(self, valve_num: int) -> Tuple[bool, str]:
        if valve_num == 1:
            self.ser.write(b"A")
        elif valve_num == 2:
            self.ser.write(b"B")
        elif valve_num == 3:
            self.ser.write(b"C")
        else:
            return (False, "Incorrect solenoid valve number")
        return (True, "Solenoid valve is open")

    @check_serial
    def valve_closed(self, valve_num: int) -> Tuple[bool, str]:
        if valve_num == 1:
            self.ser.write(b"D")
        elif valve_num == 2:
            self.ser.write(b"E")
        elif valve_num == 3:
            self.ser.write(b"F")
        else:
            return (False, "Incorrect solenoid valve number")
        return (True, "Solenoid valve is closed")

    @check_serial
    def close_all(self) -> Tuple[bool, str]:
        self.ser.write(b"D")
        time.sleep(0.25)
        self.ser.write(b"E")
        time.sleep(0.25)
        self.ser.write(b"F")
        time.sleep(0.25)
        return (True, "Closed all solenoid valves")
