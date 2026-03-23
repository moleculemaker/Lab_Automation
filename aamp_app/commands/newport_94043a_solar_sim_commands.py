from .command import Command, CommandResult
from devices.newport_94043a_solar_sim import Newport94043ASolarSim


class Newport94043ASolarSimParentCommand(Command):
    """Parent class for all Newport94043ASolarSim commands controlled through the 69920 power supply."""

    receiver_cls = Newport94043ASolarSim

    def __init__(self, receiver: Newport94043ASolarSim, **kwargs):
        super().__init__(receiver, **kwargs)


class Newport94043ASolarSimConnect(Newport94043ASolarSimParentCommand):
    """Open a serial port for the 94043A solar simulator via the 69920 power supply."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.start_serial(delay=0.5))


class Newport94043ASolarSimInitialize(Newport94043ASolarSimParentCommand):
    """Initialize the 94043A solar simulator through the 69920 power supply and set power mode."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.initialize())


class Newport94043ASolarSimDeinitialize(Newport94043ASolarSimParentCommand):
    """Deinitialize the 94043A solar simulator interface."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.deinitialize())


class Newport94043ASolarSimIdentify(Newport94043ASolarSimParentCommand):
    """Query the 69920 power supply model identifier used by the 94043A solar simulator."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.identify())


class Newport94043ASolarSimStatusByte(Newport94043ASolarSimParentCommand):
    """Query the 69920 status byte."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.status_byte())


class Newport94043ASolarSimEventStatus(Newport94043ASolarSimParentCommand):
    """Query the 69920 event status register."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.event_status_register())


class Newport94043ASolarSimLampStart(Newport94043ASolarSimParentCommand):
    """Start the lamp through the 69920 power supply."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.lamp_start())


class Newport94043ASolarSimLampStop(Newport94043ASolarSimParentCommand):
    """Stop the lamp through the 69920 power supply."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.lamp_stop())


class Newport94043ASolarSimSetPowerMode(Newport94043ASolarSimParentCommand):
    """Set the 94043A solar simulator control path to power mode through the 69920 power supply."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.set_power_mode())


class Newport94043ASolarSimGetAmps(Newport94043ASolarSimParentCommand):
    """Read the displayed lamp current from the 69920 power supply."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.get_amps())


class Newport94043ASolarSimGetVolts(Newport94043ASolarSimParentCommand):
    """Read the displayed lamp voltage from the 69920 power supply."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.get_volts())


class Newport94043ASolarSimGetWatts(Newport94043ASolarSimParentCommand):
    """Read the displayed lamp power from the 69920 power supply."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.get_watts())


class Newport94043ASolarSimGetLampHours(Newport94043ASolarSimParentCommand):
    """Read accumulated lamp hours from the 69920 power supply."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.get_lamp_hours())


class Newport94043ASolarSimGetPowerPreset(Newport94043ASolarSimParentCommand):
    """Read the configured power preset from the 69920 power supply."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.get_power_preset())


class Newport94043ASolarSimGetCurrentLimit(Newport94043ASolarSimParentCommand):
    """Read the configured current limit from the 69920 power supply."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.get_current_limit())


class Newport94043ASolarSimGetPowerLimit(Newport94043ASolarSimParentCommand):
    """Read the configured power limit from the 69920 power supply."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.get_power_limit())


class Newport94043ASolarSimSetPowerPreset(Newport94043ASolarSimParentCommand):
    """Set the power preset in watts through the 69920 power supply."""

    def __init__(self, receiver: Newport94043ASolarSim, watts: int, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["watts"] = watts

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.set_power_preset(self._params["watts"]))
