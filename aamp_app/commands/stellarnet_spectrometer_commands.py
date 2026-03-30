from typing import Tuple, Optional

from .command import Command, CommandResult
from devices.stellarnet_spectrometer import StellarNetSpectrometer

class SpectrometerParentCommand(Command):
    """Parent class for all StellarNet Spectrometer commands."""
    receiver_cls = StellarNetSpectrometer

    def __init__(self, receiver: StellarNetSpectrometer, **kwargs):
        super().__init__(receiver, **kwargs)

class SpectrometerInitialize(SpectrometerParentCommand):
    """Initialize spectrometer by verifying connection and getting each spectrometer object and wavelength array."""

    def __init__(self, receiver: StellarNetSpectrometer, **kwargs):
        super().__init__(receiver, **kwargs)

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.initialize())

class SpectrometerDeinitialize(SpectrometerParentCommand):
    """Deinitialize the spectrometer, currently does nothing except optionally change init flag."""

    def __init__(self, receiver: StellarNetSpectrometer, reset_init_flag: bool = True, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['reset_init_flag'] = reset_init_flag

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.deinitialize(self._params['reset_init_flag']))

class SpectrometerUpdateDark(SpectrometerParentCommand):
    """Update the stored dark spectra for all spectrometers."""

    def __init__(
            self, 
            receiver: StellarNetSpectrometer, 
            integration_times: Optional[Tuple[int, ...]] = None, 
            scans_to_avg: Tuple[int, ...] = (3, 3), 
            smoothings: Tuple[int, ...] = (0, 0), 
            xtimings: Tuple[int, ...] = (1, 1),
            **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['integration_times'] = integration_times
        self._params['scans_to_avg'] = scans_to_avg
        self._params['smoothings'] = smoothings
        self._params['xtimings'] = xtimings

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.update_all_dark_spectra(
            self._params['integration_times'],
            self._params['scans_to_avg'],
            self._params['smoothings'],
            self._params['xtimings']))

class SpectrometerUpdateBlank(SpectrometerParentCommand):
    """Update the stored blank spectra for all spectrometers."""

    def __init__(
            self, 
            receiver: StellarNetSpectrometer, 
            integration_times: Optional[Tuple[int, ...]] = None, 
            scans_to_avg: Tuple[int, ...] = (3, 3), 
            smoothings: Tuple[int, ...] = (0, 0), 
            xtimings: Tuple[int, ...] = (1, 1),
            **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['integration_times'] = integration_times
        self._params['scans_to_avg'] = scans_to_avg
        self._params['smoothings'] = smoothings
        self._params['xtimings'] = xtimings

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.update_all_blank_spectra(
            self._params['integration_times'],
            self._params['scans_to_avg'],
            self._params['smoothings'],
            self._params['xtimings']))

class SpectrometerAdjDefIntegrationTime(SpectrometerParentCommand):
    def __init__(
            self,
            receiver: StellarNetSpectrometer,
            scans_to_avg: Tuple[int, ...] = (3, 3),
            smoothings: Tuple[int, ...] = (0, 0),
            xtimings: Tuple[int, ...] = (1, 1),
            target_max_count: int = 52000,
            tolerance: int = 2000,
            **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['scans_to_avg'] = scans_to_avg
        self._params['smoothings'] = smoothings
        self._params['xtimings'] = xtimings
        self._params['target_max_count'] = target_max_count
        self._params['tolerance'] = tolerance

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.adjust_default_integration_time(
            self._params['scans_to_avg'],
            self._params['smoothings'],
            self._params['xtimings'],
            self._params['target_max_count'],
            self._params['tolerance']))

class SpectrometerGetAbsorbance(SpectrometerParentCommand):
    """Calculate and update the stored absorbance spectra, merge spectra, and optionally save to file. No filename = timestamped filename."""

    def __init__(
            self, 
            receiver: StellarNetSpectrometer,
            save_to_file: bool = True, 
            filename: Optional[str] = None,
            integration_times: Optional[Tuple[int, ...]] = None, 
            scans_to_avg: Tuple[int, ...] = (3, 3), 
            smoothings: Tuple[int, ...] = (0, 0), 
            xtimings: Tuple[int, ...] = (1, 1),
            **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['save_to_file'] = save_to_file
        self._params['filename'] = filename
        self._params['integration_times'] = integration_times
        self._params['scans_to_avg'] = scans_to_avg
        self._params['smoothings'] = smoothings
        self._params['xtimings'] = xtimings

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.get_all_absorbance(
            self._params['save_to_file'],
            self._params['filename'],
            self._params['integration_times'],
            self._params['scans_to_avg'],
            self._params['smoothings'],
            self._params['xtimings']))

class SpectrometerGetAbsorbancebyname(SpectrometerParentCommand):
    def __init__(
            self,
            receiver: StellarNetSpectrometer,
            sample_name: Optional[str] = None,
            save_to_file: bool = True,
            repeat_measure: bool = False,
            integration_times: Optional[Tuple[int, ...]] = None,
            scans_to_avg: Tuple[int, ...] = (3, 3),
            smoothings: Tuple[int, ...] = (0, 0),
            xtimings: Tuple[int, ...] = (1, 1),
            absorbance_threshold: float = 0.003,
            **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['sample_name'] = sample_name
        self._params['save_to_file'] = save_to_file
        self._params['repeat_measure'] = repeat_measure
        self._params['integration_times'] = integration_times
        self._params['scans_to_avg'] = scans_to_avg
        self._params['smoothings'] = smoothings
        self._params['xtimings'] = xtimings
        self._params['absorbance_threshold'] = absorbance_threshold

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.get_all_absorbance_byname(
            self._params['sample_name'],
            self._params['save_to_file'],
            self._params['repeat_measure'],
            self._params['integration_times'],
            self._params['scans_to_avg'],
            self._params['smoothings'],
            self._params['xtimings'],
            self._params['absorbance_threshold']))

class SpectrometerGetPhotoncountsbyname(SpectrometerParentCommand):
    def __init__(
            self,
            receiver: StellarNetSpectrometer,
            sample_name: Optional[str] = None,
            save_to_file: bool = True,
            repeat_measure: bool = False,
            integration_times: Optional[Tuple[int, ...]] = None,
            scans_to_avg: Tuple[int, ...] = (3, 3),
            smoothings: Tuple[int, ...] = (0, 0),
            xtimings: Tuple[int, ...] = (1, 1),
            absorbance_threshold: float = 0.003,
            **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['sample_name'] = sample_name
        self._params['save_to_file'] = save_to_file
        self._params['repeat_measure'] = repeat_measure
        self._params['integration_times'] = integration_times
        self._params['scans_to_avg'] = scans_to_avg
        self._params['smoothings'] = smoothings
        self._params['xtimings'] = xtimings
        self._params['absorbance_threshold'] = absorbance_threshold

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.get_all_counts_byname(
            self._params['sample_name'],
            self._params['save_to_file'],
            self._params['repeat_measure'],
            self._params['integration_times'],
            self._params['scans_to_avg'],
            self._params['smoothings'],
            self._params['xtimings'],
            self._params['absorbance_threshold']))

class SpectrometerGetSpecDecay(SpectrometerParentCommand):
    def __init__(
            self,
            receiver: StellarNetSpectrometer,
            sample_name: str,
            save_to_file: bool = False,
            range_start: float = 290.0,
            range_end: float = 800.0,
            irradiance_file: str = "reference/am15g_spectrum.csv",
            Wvlgth_col_name: str = "wavelength_nm",
            Irrad_col_name: str = "irradiance_w_m2_nm",
            decay_threshold: float = 0.01,
            **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['sample_name'] = sample_name
        self._params['save_to_file'] = save_to_file
        self._params['range_start'] = range_start
        self._params['range_end'] = range_end
        self._params['irradiance_file'] = irradiance_file
        self._params['Wvlgth_col_name'] = Wvlgth_col_name
        self._params['Irrad_col_name'] = Irrad_col_name
        self._params['decay_threshold'] = decay_threshold

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.get_spec_decay(
            self._params['sample_name'],
            self._params['save_to_file'],
            self._params['range_start'],
            self._params['range_end'],
            self._params['irradiance_file'],
            self._params['Wvlgth_col_name'],
            self._params['Irrad_col_name'],
            self._params['decay_threshold']))

class SpectrometerPlotSpecDecaySummary(SpectrometerParentCommand):
    def __init__(
            self,
            receiver: StellarNetSpectrometer,
            sample_name: str,
            range_start: float = 290.0,
            range_end: float = 800.0,
            save_to_file: bool = True,
            output_filename: Optional[str] = None,
            figure_dpi: int = 180,
            **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['sample_name'] = sample_name
        self._params['range_start'] = range_start
        self._params['range_end'] = range_end
        self._params['save_to_file'] = save_to_file
        self._params['output_filename'] = output_filename
        self._params['figure_dpi'] = figure_dpi

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.plot_spec_decay_summary(
            self._params['sample_name'],
            self._params['range_start'],
            self._params['range_end'],
            self._params['save_to_file'],
            self._params['output_filename'],
            self._params['figure_dpi']))

class SpectrometerShutterIn(SpectrometerParentCommand):
    pass

class SpectrometerShutterOut(SpectrometerParentCommand):
    pass

class SpectrometerLampOn(SpectrometerParentCommand):
    pass

class SpectrometerLampOff(SpectrometerParentCommand):
    pass
