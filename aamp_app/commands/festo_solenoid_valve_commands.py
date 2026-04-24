from typing import List
from devices.festo_solenoid_valve import FestoSolenoidValve
from .command import Command, CommandResult


class FestoParentCommand(Command):
    """Parent class for all Festo Solenoid Valve commands."""

    receiver_cls = FestoSolenoidValve

    def __init__(self, receiver: FestoSolenoidValve, **kwargs):
        super().__init__(receiver, **kwargs)


class FestoConnect(Command):
    """Open the serial port to the festo valve"""

    receiver_cls = FestoSolenoidValve

    def __init__(self, receiver: FestoSolenoidValve, **kwargs):
        super().__init__(receiver, **kwargs)

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.start_serial())


class FestoInitialize(FestoParentCommand):
    """Initialize the solenoid valve"""

    def __init__(self, receiver: FestoSolenoidValve, **kwargs):
        super().__init__(receiver, **kwargs)

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.initialize())


class FestoDeinitialize(FestoParentCommand):
    """Deinitialize the solenoid valve"""

    def __init__(self, receiver: FestoSolenoidValve, **kwargs):
        super().__init__(receiver, **kwargs)

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.deinitialize())


class FestoValveOpen(FestoParentCommand):
    """Open the solenoid valve and keep open"""

    def __init__(self, receiver: FestoSolenoidValve, valve_num: int, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["valve_num"] = valve_num

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.valve_open(self._params["valve_num"])
        )


class FestoValveClosed(FestoParentCommand):
    """Close the solenoid valve and keep closed"""

    def __init__(self, receiver: FestoSolenoidValve, valve_num: int, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["valve_num"] = valve_num

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.valve_closed(self._params["valve_num"])
        )


class FestoCloseAll(FestoParentCommand):
    """Close all solenoid valves"""

    def __init__(self, receiver: FestoSolenoidValve, **kwargs):
        super().__init__(receiver, **kwargs)

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.close_all())
