from .command import Command, CommandResult
from devices.substrate_dispenser import SubstrateDispenser


class SubstrateDispenserParentCommand(Command):
    receiver_cls = SubstrateDispenser

    def __init__(self, receiver: SubstrateDispenser, **kwargs):
        super().__init__(receiver, **kwargs)


class SubstrateDispenserConnect(SubstrateDispenserParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.connect())


class SubstrateDispenserInitialize(SubstrateDispenserParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.initialize())


class SubstrateDispenserDeinitialize(SubstrateDispenserParentCommand):
    def __init__(
            self,
            receiver: SubstrateDispenser,
            reset_init_flag: bool = True,
            close_serial: bool = False,
            **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["reset_init_flag"] = reset_init_flag
        self._params["close_serial"] = close_serial

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.deinitialize(
            self._params["reset_init_flag"],
            self._params["close_serial"],
        ))


class SubstrateDispenserHome(SubstrateDispenserParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.home())


class SubstrateDispenserMoveToPosition(SubstrateDispenserParentCommand):
    def __init__(
            self,
            receiver: SubstrateDispenser,
            position_mm: float,
            speed_mm_per_s: float = 20.0,
            move_timeout: float = None,
            **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["position_mm"] = position_mm
        self._params["speed_mm_per_s"] = speed_mm_per_s
        self._params["move_timeout"] = move_timeout

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.move_to_position(
            self._params["position_mm"],
            self._params["speed_mm_per_s"],
            self._params["move_timeout"],
        ))
