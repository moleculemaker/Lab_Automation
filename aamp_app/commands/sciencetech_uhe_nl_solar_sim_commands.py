from .command import Command, CommandResult
from devices.sciencetech_uhe_nl_solar_sim import SciencetechUHENLSolarSim


class SciencetechUHENLSolarSimParentCommand(Command):
    receiver_cls = SciencetechUHENLSolarSim

    def __init__(self, receiver: SciencetechUHENLSolarSim, **kwargs):
        super().__init__(receiver, **kwargs)


class SciencetechUHENLSolarSimConnect(SciencetechUHENLSolarSimParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.connect())


class SciencetechUHENLSolarSimInitialize(SciencetechUHENLSolarSimParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.initialize())


class SciencetechUHENLSolarSimDeinitialize(SciencetechUHENLSolarSimParentCommand):
    def __init__(self, receiver: SciencetechUHENLSolarSim, reset_init_flag: bool = True, close_serial: bool = False, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["reset_init_flag"] = reset_init_flag
        self._params["close_serial"] = close_serial

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.deinitialize(
                reset_init_flag=self._params["reset_init_flag"],
                close_serial=self._params["close_serial"],
            )
        )


class SciencetechUHENLSolarSimCloseShutter(SciencetechUHENLSolarSimParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.close_shutter())


class SciencetechUHENLSolarSimOpenShutter(SciencetechUHENLSolarSimParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.open_shutter())


class SciencetechUHENLSolarSimEnableCooling(SciencetechUHENLSolarSimParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.enable_cooling())


class SciencetechUHENLSolarSimDisableCooling(SciencetechUHENLSolarSimParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.disable_cooling())


class SciencetechUHENLSolarSimEnableArcLamp(SciencetechUHENLSolarSimParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.enable_arc_lamp())


class SciencetechUHENLSolarSimDisableArcLamp(SciencetechUHENLSolarSimParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.disable_arc_lamp())


class SciencetechUHENLSolarSimOpenAttenuator(SciencetechUHENLSolarSimParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.open_attenuator())


class SciencetechUHENLSolarSimSetAttenuator(SciencetechUHENLSolarSimParentCommand):
    def __init__(self, receiver: SciencetechUHENLSolarSim, percent: int = 100, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["percent"] = percent

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.set_attenuator(self._params["percent"]))


class SciencetechUHENLSolarSimSetCurrent(SciencetechUHENLSolarSimParentCommand):
    def __init__(self, receiver: SciencetechUHENLSolarSim, percent: float = 85.0, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["percent"] = percent

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.set_current(self._params["percent"]))


class SciencetechUHENLSolarSimGetStatus(SciencetechUHENLSolarSimParentCommand):
    def execute(self) -> None:
        was_successful, message = self._receiver.get_status()
        if was_successful and isinstance(message, list):
            message = " | ".join(message)
        self._result = CommandResult(was_successful, message)


class SciencetechUHENLSolarSimGetFeedback(SciencetechUHENLSolarSimParentCommand):
    def __init__(self, receiver: SciencetechUHENLSolarSim, feedback_type: str, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["feedback_type"] = feedback_type

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.get_feedback(self._params["feedback_type"]))
