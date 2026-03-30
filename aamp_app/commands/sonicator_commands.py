from .command import Command, CommandResult
from devices.sonicator import Sonicator


class SonicatorParentCommand(Command):
    receiver_cls = Sonicator

    def __init__(self, receiver: Sonicator, **kwargs):
        super().__init__(receiver, **kwargs)


class SonicatorConnect(SonicatorParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.connect())


class SonicatorInitialize(SonicatorParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.initialize())


class SonicatorDeinitialize(SonicatorParentCommand):
    def __init__(
        self,
        receiver: Sonicator,
        reset_init_flag: bool = True,
        close_serial: bool = False,
        **kwargs,
    ):
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


class SonicatorGetStatus(SonicatorParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.get_status())


class SonicatorProbePowerConnection(SonicatorParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.probe_power_connection())


class SonicatorStartSonicating(SonicatorParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.start_sonicating())


class SonicatorStopSonicating(SonicatorParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.stop_sonicating())


class SonicatorPressButton(SonicatorParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.press_button())
