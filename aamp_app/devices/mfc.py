from typing import Tuple
import time
from mfc import FlowController
import asyncio
from .device import Device, check_initialized


# Default ip address is 192.168.2.155
# Secondary mfc ip address should be set to 192.168.2.156 and so on
# Must pip install the correct edited version of mfc python library
# +24 VDC is pin 7, ground is pin 5


class MassFlowController(Device):
    def __init__(self, name: str, ip: str):
        super().__init__(name)
        self._ip = ip

    def get_init_args(self) -> dict:
        args_dict = {
            "name": self._name,
            "ip": self._ip,
        }
        return args_dict

    def update_init_args(self, args_dict: dict):
        self._name = args_dict["name"]
        self._ip = args_dict["ip"]

    def initialize(self) -> Tuple[bool, str]:
        self._is_initialized = True
        return (True, "Initialized mass flow controller")

    async def deinitialize(self) -> Tuple[bool, str]:
        async with FlowController(self._ip) as fc:
            await fc.disconnect()
            self._is_initialized = False
        return (True, "Deinitialized mass flow controller")

    @check_initialized
    async def get(self) -> Tuple[bool, dict]:
        async with FlowController(self._ip) as fc:
            info = await fc.get()
            return (True, info)

    @check_initialized
    async def set_gas(self, gas: str) -> Tuple[bool, str]:
        """Gas instance must first be created within web browser interface"""
        async with FlowController(self._ip) as fc:
            await fc.set_gas(gas)
        return (True, f"Set MFC gas to {gas}")

    @check_initialized
    async def set(self, setpoint) -> Tuple[bool, str]:
        async with FlowController(self._ip) as fc:
            await fc.set(setpoint)
        return (True, f"Set MFC flowrate to {setpoint} sccm")

    async def open(self) -> Tuple[bool, str]:
        async with FlowController(self._ip) as fc:
            await fc.open()
        return (True, "Set the MFC flowrate to its maximum")
