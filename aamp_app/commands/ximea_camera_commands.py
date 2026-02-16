from typing import Optional

from .command import Command, CommandResult
from devices.ximea_camera import XimeaCamera


class XimeaCameraParentCommand(Command):
    """Parent class for all XimeaCamera commands."""
    receiver_cls = XimeaCamera

    def __init__(self, receiver: XimeaCamera, **kwargs):
        super().__init__(receiver, **kwargs)


class XimeaCameraInitialize(XimeaCameraParentCommand):
    """Initialize camera by opening communication with camera and optionally set defaults."""

    def __init__(self, receiver: XimeaCamera, **kwargs):
        super().__init__(receiver, **kwargs)

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.initialize())


class XimeaCameraDeinitialize(XimeaCameraParentCommand):
    """Deinitialize camera by stopping any acquisition and closing communication with camera."""

    def __init__(self, receiver: XimeaCamera, reset_init_flag: bool = True, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['reset_init_flag'] = reset_init_flag

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.deinitialize(self._params['reset_init_flag']))

class XimeaCameraUpdateBackground(XimeaCameraParentCommand):
    def __init__(
            self,
            receiver: XimeaCamera,
            save_to_file: bool = True,
            filename: str = None,
            exposure_time: Optional[int] = None,
            gain: Optional[float] = None,
            **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['save_to_file'] = save_to_file
        self._params['filename'] = filename
        self._params['exposure_time'] = exposure_time
        self._params['gain'] = gain

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.update_background(self._params['save_to_file'], self._params['filename'],
                                              self._params['exposure_time'], self._params['gain']))


class XimeaCameraUpdateCompRef(XimeaCameraParentCommand):
    def __init__(
            self,
            receiver: XimeaCamera,
            save_to_file: bool = True,
            filename: str = None,
            exposure_time: Optional[int] = None,
            gain: Optional[float] = None,
            **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['save_to_file'] = save_to_file
        self._params['filename'] = filename
        self._params['exposure_time'] = exposure_time
        self._params['gain'] = gain

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.update_completeness_ref(self._params['save_to_file'], self._params['filename'],
                                                    self._params['exposure_time'], self._params['gain']))


class XimeaCameraCheckComp(XimeaCameraParentCommand):
    def __init__(
            self,
            receiver: XimeaCamera,
            save_to_file: bool = True,
            filename: str = None,
            exposure_time: Optional[int] = None,
            gain: Optional[float] = None,
            **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['save_to_file'] = save_to_file
        self._params['filename'] = filename
        self._params['exposure_time'] = exposure_time
        self._params['gain'] = gain

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.check_completeness(self._params['save_to_file'], self._params['filename'],
                                               self._params['exposure_time'], self._params['gain']))


class XimeaCameraUpdateVertBound(XimeaCameraParentCommand):
    def __init__(
            self,
            receiver: XimeaCamera,
            exposure_time: Optional[int] = None,
            gain: Optional[float] = None,
            **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['exposure_time'] = exposure_time
        self._params['gain'] = gain

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.update_vertical_bound(self._params['exposure_time'], self._params['gain']))


class XimeaCameraGetImage(XimeaCameraParentCommand):
    """Get image and save to file, display image, or both, check uniform in certain range. No filename = timestamped filename. No exposure or gain = use defaults."""

    def __init__(
            self,
            receiver: XimeaCamera,
            save_to_file: bool = True,
            filename: str = None,
            check_uniform: bool = True,
            y_upper: int = 100,
            y_length: int = 700,
            x_upper: int = None,
            x_length: int = None,
            exposure_time: Optional[int] = None,
            gain: Optional[float] = None,
            show_pop_up: bool = False,
            **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['save_to_file'] = save_to_file
        self._params['filename'] = filename
        self._params['check_uniform'] = check_uniform
        self._params['y_upper'] = y_upper
        self._params['y_length'] = y_length
        self._params['x_upper'] = x_upper
        self._params['x_length'] = x_length
        self._params['exposure_time'] = exposure_time
        self._params['gain'] = gain
        self._params['show_pop_up'] = show_pop_up

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.get_image(self._params['save_to_file'], self._params['filename'],
                                                               self._params['check_uniform'], self._params['y_upper'],
                                                               self._params['y_length'], self._params['x_upper'],
                                                               self._params['x_length'],
                                                               self._params['exposure_time'], self._params['gain'],
                                                               self._params['show_pop_up']))


class XimeaCameraSetDefaultExposure(XimeaCameraParentCommand):
    """Set the default exposure time to use if no exposure time is passed when getting image."""

    def __init__(self, receiver: XimeaCamera, exposure_time: int, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['exposure_time'] = exposure_time

    def execute(self) -> None:
        self._receiver.default_exposure_time = self._params['exposure_time']
        if self._receiver.default_exposure_time == self._params['exposure_time']:
            self._result = CommandResult(True, "Default exposure time successfully set to " + str(
                self._params['exposure_time']))
        else:
            self._result = CommandResult(False, "Failed to set the default exposure time to " + str(
                self._params['exposure_time']) + ". The default exposure time must be > 0.")


class XimeaCameraSetDefaultGain(XimeaCameraParentCommand):
    """Set the default gain to use if no gain is passed when getting image."""

    def __init__(self, receiver: XimeaCamera, gain: float, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['gain'] = gain

    def execute(self) -> None:
        self._receiver.default_gain = self._params['gain']
        if self._receiver.default_gain == self._params['gain']:
            self._result = CommandResult(True, "Default gain successfully set to " + str(self._params['gain']))
        else:
            # unsure what the upper limit is at the moment
            self._result = CommandResult(False, "Failed to set the default gain to " + str(
                self._params['gain']) + ". The default gain must be >= 0 and has an upper limit.")


class XimeaCameraUpdateWhiteBal(XimeaCameraParentCommand):
    """Update the white balance coefficients using the current camera feed."""

    def __init__(self, receiver: XimeaCamera, exposure_time: int = None, gain: Optional[float] = None, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['exposure_time'] = exposure_time
        self._params['gain'] = gain

    def execute(self) -> None:
        self._result = CommandResult(
            *self._receiver.update_white_balance(self._params['exposure_time'], self._params['gain']))


class XimeaCameraSetManualWhiteBal(XimeaCameraParentCommand):
    """Set any of the red, green, and blue white balance coefficients manually."""

    def __init__(self, receiver: XimeaCamera, wb_kr: Optional[float] = None, wb_kg: Optional[float] = None,
                 wb_kb: Optional[float] = None, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['wb_kr'] = wb_kr
        self._params['wb_kg'] = wb_kg
        self._params['wb_kb'] = wb_kb

    def execute(self) -> None:
        self._result = CommandResult(
            self._receiver.set_white_balance_manually(self._params['wb_kr'], self._params['wb_kg'],
                                                      self._params['wb_kb']))


class XimeaCameraResetWhiteBal(XimeaCameraParentCommand):
    """Reset the red, green, and blue white balance coefficients to defaults."""

    def __init__(self, receiver: XimeaCamera, **kwargs):
        super().__init__(receiver, **kwargs)

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.reset_white_balance_rgb_coeffs())

