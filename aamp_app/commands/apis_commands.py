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


class APISSetPolarizerBaseline(APISParentCommand):
    """Set APIS XPL angle and derive the reachable orthogonal PPL angle."""

    def __init__(
        self,
        receiver: APIS,
        xpl_angle_deg: float,
        persist: bool = False,
        source: str = "manual",
        **kwargs
    ):
        super().__init__(receiver, **kwargs)
        self._params["xpl_angle_deg"] = xpl_angle_deg
        self._params["persist"] = persist
        self._params["source"] = source

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.set_polarizer_baseline(
                self._params["xpl_angle_deg"],
                persist=self._params["persist"],
                source=self._params["source"],
            )
        )


class APISLoadPolarizerBaseline(APISParentCommand):
    """Load the persisted APIS XPL/PPL polarizer baseline."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.load_polarizer_baseline())


class APISSavePolarizerBaseline(APISParentCommand):
    """Persist the current APIS XPL/PPL polarizer baseline."""

    def __init__(self, receiver: APIS, source: str = "manual", **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["source"] = source

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.save_polarizer_baseline(source=self._params["source"])
        )


class APISRotateXPL(APISParentCommand):
    """Rotate the APIS polarizer to the configured XPL baseline angle."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.rotate_xpl())


class APISRotatePPL(APISParentCommand):
    """Rotate the APIS polarizer to the configured PPL baseline angle."""

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.rotate_ppl())


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


class APISRunImagingSequence(APISParentCommand):
    """Run the current APIS XPL/PPL RAW16 imaging sequence with metadata logging."""

    def __init__(
        self,
        receiver: APIS,
        sample_id: str,
        directory: str = None,
        sample_angles=None,
        xpl_exposure_time: int = APIS.XIMEA_DEFAULT_XPL_EXPOSURE_US,
        ppl_exposure_time: int = APIS.XIMEA_DEFAULT_PPL_EXPOSURE_US,
        do_xpl: bool = True,
        do_ppl: bool = True,
        xpl_polarizer_angle: float = None,
        ppl_polarizer_angle: float = None,
        gain: float = 0.0,
        **kwargs
    ):
        super().__init__(receiver, **kwargs)
        self._params["sample_id"] = sample_id
        self._params["directory"] = directory
        self._params["sample_angles"] = sample_angles
        self._params["xpl_exposure_time"] = xpl_exposure_time
        self._params["ppl_exposure_time"] = ppl_exposure_time
        self._params["do_xpl"] = do_xpl
        self._params["do_ppl"] = do_ppl
        self._params["xpl_polarizer_angle"] = xpl_polarizer_angle
        self._params["ppl_polarizer_angle"] = ppl_polarizer_angle
        self._params["gain"] = gain

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.run_imaging_sequence(
                sample_id=self._params["sample_id"],
                directory=self._params["directory"],
                sample_angles=self._params["sample_angles"],
                xpl_exposure_time=self._params["xpl_exposure_time"],
                ppl_exposure_time=self._params["ppl_exposure_time"],
                do_xpl=self._params["do_xpl"],
                do_ppl=self._params["do_ppl"],
                xpl_polarizer_angle=self._params["xpl_polarizer_angle"],
                ppl_polarizer_angle=self._params["ppl_polarizer_angle"],
                gain=self._params["gain"],
            )
        )


class APISRunPolarizerCalibration(APISParentCommand):
    """Run a RAW16 polarizer scan and update APIS XPL/PPL baseline angles."""

    def __init__(
        self,
        receiver: APIS,
        sample_id: str = "polarizer_calibration",
        directory: str = None,
        exposure_time: int = APIS.XIMEA_DEFAULT_POLARIZER_CALIBRATION_EXPOSURE_US,
        polarizer_angles=None,
        sample_angle: float = 0.0,
        fine_radius_deg: int = APIS.POLARIZER_CALIBRATION_FINE_RADIUS_DEG,
        fine_step_deg: int = APIS.POLARIZER_CALIBRATION_FINE_STEP_DEG,
        gain: float = 0.0,
        **kwargs
    ):
        super().__init__(receiver, **kwargs)
        self._params["sample_id"] = sample_id
        self._params["directory"] = directory
        self._params["exposure_time"] = exposure_time
        self._params["polarizer_angles"] = polarizer_angles
        self._params["sample_angle"] = sample_angle
        self._params["fine_radius_deg"] = fine_radius_deg
        self._params["fine_step_deg"] = fine_step_deg
        self._params["gain"] = gain

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.run_polarizer_calibration(
                sample_id=self._params["sample_id"],
                directory=self._params["directory"],
                exposure_time=self._params["exposure_time"],
                polarizer_angles=self._params["polarizer_angles"],
                sample_angle=self._params["sample_angle"],
                fine_radius_deg=self._params["fine_radius_deg"],
                fine_step_deg=self._params["fine_step_deg"],
                gain=self._params["gain"],
            )
        )
