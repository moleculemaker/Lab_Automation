from .command import Command, CommandResult
from devices.substrate_hotel import SubstrateHotel


class SubstrateHotelParentCommand(Command):
    receiver_cls = SubstrateHotel

    def __init__(self, receiver: SubstrateHotel, **kwargs):
        super().__init__(receiver, **kwargs)


class SubstrateHotelConnect(SubstrateHotelParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.connect())


class SubstrateHotelInitialize(SubstrateHotelParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.initialize())


class SubstrateHotelDeinitialize(SubstrateHotelParentCommand):
    def __init__(
            self,
            receiver: SubstrateHotel,
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


class SubstrateHotelHome(SubstrateHotelParentCommand):
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.home())


class SubstrateHotelMoveToPosition(SubstrateHotelParentCommand):
    def __init__(
            self,
            receiver: SubstrateHotel,
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
