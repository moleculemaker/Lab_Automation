from .command import Command, CommandResult
from devices.heating_stage import HeatingStage

#parent class for all HeatingStage commands
class HeatingStageParentCommand(Command):
    """Parent class for all HeatingStage commands."""
    receiver_cls = HeatingStage

    def __init__(self, receiver: HeatingStage, **kwargs):
        super().__init__(receiver, **kwargs)

class HeatingStageConnect(HeatingStageParentCommand):
    """Open serial port of heating stage's arduino controller."""
    
    def __init__(self, receiver: HeatingStage, **kwargs):
        super().__init__(receiver, **kwargs)

    def execute(self) -> None:
        # the serial port parameters should already be set in the HeatingStage instance
        self._result = CommandResult(*self._receiver.start_serial())

class HeatingStageInitialize(HeatingStageParentCommand):
    """Initialize heating stage by setting to room temperature and turning PID ON."""
    
    def __init__(self, receiver: HeatingStage, **kwargs):
        super().__init__(receiver, **kwargs)

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.initialize())

class HeatingStageDeinitialize(HeatingStageParentCommand):
    """Deinitialize heating stage by setting to room temperature and turning PID OFF."""
    
    def __init__(self, receiver: HeatingStage, reset_init_flag: bool = True, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['reset_init_flag'] = reset_init_flag

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.deinitialize(self._params['reset_init_flag']))


class HeatingStageSetTemp(HeatingStageParentCommand):
    """Set heating stage temperature. Execution completes when stabilized."""
    
    def __init__(self, receiver: HeatingStage, temperature: float, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['temperature'] = temperature

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.set_temp(self._params['temperature']))

class HeatingStageSetSetPoint(HeatingStageParentCommand):
    """Set heating stage setpoint temperature. Execution completes immediately after setting setpoint, even if temperature is not stabilized."""
    
    def __init__(self, receiver: HeatingStage, temperature: float, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['temperature'] = temperature

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.set_settemp(self._params['temperature']))


class HeatingStageWaitForTemperature(HeatingStageParentCommand):
    """Wait until the heating stage reaches the target temperature within a tolerance."""

    def __init__(
        self,
        receiver: HeatingStage,
        target: float,
        tolerance: float = 1.0,
        timeout: float = 600.0,
        poll_interval: float = 1.0,
        hold_duration: float = 30.0,
        **kwargs
    ):
        super().__init__(receiver, **kwargs)
        self._params['target'] = target
        self._params['tolerance'] = tolerance
        self._params['timeout'] = timeout
        self._params['poll_interval'] = poll_interval
        self._params['hold_duration'] = hold_duration

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.wait_for_temperature(
                self._params['target'],
                self._params['tolerance'],
                self._params['timeout'],
                self._params['poll_interval'],
                self._params['hold_duration'],
            )
        )
