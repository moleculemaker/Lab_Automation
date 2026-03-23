from .command import Command, CommandResult
from devices.z812 import Z812


class Z812ParentCommand(Command):
    """Parent class for all Z812 commands."""

    receiver_cls = Z812

    def __init__(self, receiver: Z812, **kwargs):
        super().__init__(receiver, **kwargs)


class Z812Connect(Z812ParentCommand):
    """Open a serial port for the Z812 stage."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.start_serial())


class Z812Initialize(Z812ParentCommand):
    """Initialize the Z812 stage by homing it."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.initialize())


class Z812Deinitialize(Z812ParentCommand):
    """Deinitialize the Z812 stage."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.deinitialize())


class Z812EnableMotor(Z812ParentCommand):
    """Enable the Z812 motor."""

    def __init__(self, receiver: Z812, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["state"] = True

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.set_enabled_state(self._params["state"]))


class Z812DisableMotor(Z812ParentCommand):
    """Disable the Z812 motor."""

    def __init__(self, receiver: Z812, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["state"] = False

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.set_enabled_state(self._params["state"]))


class Z812MoveAbsolute(Z812ParentCommand):
    """Move the Z812 stage to an absolute position in mm."""

    def __init__(self, receiver: Z812, position: float, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["position"] = position

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.move_absolute(self._params["position"]))


class Z812MoveRelative(Z812ParentCommand):
    """Move the Z812 stage by a relative distance in mm."""

    def __init__(self, receiver: Z812, distance: float, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["distance"] = distance

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.move_relative(self._params["distance"]))
