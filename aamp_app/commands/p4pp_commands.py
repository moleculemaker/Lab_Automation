from .command import Command, CommandResult
from devices.p4pp import P4PP


class P4PPParentCommand(Command):
    """Parent class for all P4PP commands."""

    receiver_cls = P4PP

    def __init__(self, receiver: P4PP, **kwargs):
        super().__init__(receiver, **kwargs)


class P4PPConnect(P4PPParentCommand):
    """Open the serial port for the P4PP controller."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.start_serial())


class P4PPInitialize(P4PPParentCommand):
    """Initialize the P4PP controller by syncing its current position."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.initialize())


class P4PPDeinitialize(P4PPParentCommand):
    """Deinitialize the P4PP controller."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.deinitialize())


class P4PPRefreshPosition(P4PPParentCommand):
    """Refresh the cached linear and rotational positions from firmware."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.refresh_position())


class P4PPHomeLinear(P4PPParentCommand):
    """Home the P4PP linear axis."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.home_linear())


class P4PPHomeRotational(P4PPParentCommand):
    """Home the P4PP rotational axis."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.home_rotational())


class P4PPHomeAll(P4PPParentCommand):
    """Home both the P4PP linear and rotational axes."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.home_all())


class P4PPMoveLinearAbsolute(P4PPParentCommand):
    """Move the P4PP linear axis to an absolute position in mm."""

    def __init__(self, receiver: P4PP, position_mm: float, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["position_mm"] = position_mm

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.move_linear_mm(self._params["position_mm"], relative=False))


class P4PPMoveLinearRelative(P4PPParentCommand):
    """Move the P4PP linear axis by a relative distance in mm."""

    def __init__(self, receiver: P4PP, distance_mm: float, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["distance_mm"] = distance_mm

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.move_linear_mm(self._params["distance_mm"], relative=True))


class P4PPMoveRotationalAbsolute(P4PPParentCommand):
    """Move the P4PP rotational axis to an absolute position in degrees."""

    def __init__(self, receiver: P4PP, position_deg: float, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["position_deg"] = position_deg

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.move_rotational_deg(self._params["position_deg"], relative=False))


class P4PPMoveRotationalRelative(P4PPParentCommand):
    """Move the P4PP rotational axis by a relative distance in degrees."""

    def __init__(self, receiver: P4PP, distance_deg: float, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["distance_deg"] = distance_deg

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.move_rotational_deg(self._params["distance_deg"], relative=True))


class P4PPMeasure(P4PPParentCommand):
    """Trigger a P4PP measurement. Multi-cycle mode uses firmware averaging."""

    def __init__(self, receiver: P4PP, cycles: int = 1, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["cycles"] = cycles

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.measure(self._params["cycles"]))


class P4PPSetMeasurementResistor(P4PPParentCommand):
    """Select the P4PP measurement resistor configuration: 681 or 68.1 ohm."""

    def __init__(self, receiver: P4PP, resistor_ohms: float = 681.0, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["resistor_ohms"] = resistor_ohms

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.set_measurement_resistor(self._params["resistor_ohms"]))


class P4PPSaveMeasurementCsv(P4PPParentCommand):
    """Append the latest P4PP measurement result to a CSV file."""

    def __init__(
        self,
        receiver: P4PP,
        sample_id: str = None,
        csv_path: str = None,
        notes: str = None,
        **kwargs
    ):
        super().__init__(receiver, **kwargs)
        self._params["sample_id"] = sample_id
        self._params["csv_path"] = csv_path
        self._params["notes"] = notes

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.save_measurement_csv(
                sample_id=self._params["sample_id"],
                csv_path=self._params["csv_path"],
                notes=self._params["notes"],
            )
        )
