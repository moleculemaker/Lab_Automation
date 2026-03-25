from .command import Command, CommandResult
from devices.apis import APIS


class APISParentCommand(Command):
    """Parent class for all APIS commands."""

    receiver_cls = APIS

    def __init__(self, receiver: APIS, **kwargs):
        super().__init__(receiver, **kwargs)


class APISConnect(APISParentCommand):
    """Open the serial port and run the APIS READY/RESET handshake."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.connect())


class APISInitialize(APISParentCommand):
    """Initialize APIS by resetting it into the ARMED state."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.initialize())


class APISDeinitialize(APISParentCommand):
    """Deinitialize APIS by sending ESTOP and closing the serial port."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.deinitialize())


class APISReset(APISParentCommand):
    """Send RESET to arm APIS."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.reset())


class APISEmergencyStop(APISParentCommand):
    """Send ESTOP to latch and detach the APIS servos."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.emergency_stop())


class APISHome(APISParentCommand):
    """Move both APIS stages to 0 degrees."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.home())


class APISRotatePolarizer(APISParentCommand):
    """Rotate the APIS polarizer stage to a target stage angle in degrees."""

    def __init__(self, receiver: APIS, angle_deg: float, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["angle_deg"] = angle_deg

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.rotate_polarizer(self._params["angle_deg"]))


class APISRotateSample(APISParentCommand):
    """Rotate the APIS sample stage to a target stage angle in degrees."""

    def __init__(self, receiver: APIS, angle_deg: float, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["angle_deg"] = angle_deg

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.rotate_sample(self._params["angle_deg"]))


class APISGetState(APISParentCommand):
    """Return the cached APIS state."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.get_state())


class APISCaptureRaw16(APISParentCommand):
    """Capture a RAW16 TIFF from the APIS Ximea camera."""

    def __init__(
        self,
        receiver: APIS,
        filename: str = None,
        directory: str = None,
        exposure_time: int = None,
        gain: float = 0.0,
        **kwargs
    ):
        super().__init__(receiver, **kwargs)
        self._params["filename"] = filename
        self._params["directory"] = directory
        self._params["exposure_time"] = exposure_time
        self._params["gain"] = gain

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.capture_raw16(
                filename=self._params["filename"],
                directory=self._params["directory"],
                exposure_time=self._params["exposure_time"],
                gain=self._params["gain"],
            )
        )


class APISCaptureRgb(APISParentCommand):
    """Capture an APIS-style RGB preview TIFF from the APIS Ximea camera."""

    def __init__(
        self,
        receiver: APIS,
        filename: str = None,
        directory: str = None,
        exposure_time: int = None,
        gain: float = 0.0,
        **kwargs
    ):
        super().__init__(receiver, **kwargs)
        self._params["filename"] = filename
        self._params["directory"] = directory
        self._params["exposure_time"] = exposure_time
        self._params["gain"] = gain

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.capture_rgb(
                filename=self._params["filename"],
                directory=self._params["directory"],
                exposure_time=self._params["exposure_time"],
                gain=self._params["gain"],
            )
        )


class APISConvertRaw16ToRgb(APISParentCommand):
    """Convert a saved RAW16 TIFF into an APIS-style RGB preview TIFF."""

    def __init__(
        self,
        receiver: APIS,
        raw16_path: str,
        rgb_path: str = None,
        **kwargs
    ):
        super().__init__(receiver, **kwargs)
        self._params["raw16_path"] = raw16_path
        self._params["rgb_path"] = rgb_path

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.convert_raw16_to_rgb(
                raw16_path=self._params["raw16_path"],
                rgb_path=self._params["rgb_path"],
            )
        )
