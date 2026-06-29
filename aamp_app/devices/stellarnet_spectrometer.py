from typing import Union, Tuple, Dict, List, Optional
from datetime import datetime
import os
import re
import time

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from scipy.optimize import minimize
try:
    import stellarnet_driver3 as sn
    _driver_import_error = None
except Exception as exc:
    sn = None
    _driver_import_error = str(exc)

from .device import Device, check_initialized

# TODO
# convert to serial device parent when arduino added
# add shutter and lamp control
# check slicing as second index is not included in slice
# type hinting of ndarrays?
# type hint the static methods?

class StellarNetSpectrometer(Device):
    SUPPORTED_SPEC_KEYS = ("UV-Vis", "NIR")
    save_directory = 'data/spectroscopy/'
    MERGE_UV_START = 210.0
    MERGE_NIR_END = 1700.0
    MERGE_OVERLAP_START = 900.0
    MERGE_OVERLAP_END = 1030.0
    MERGE_WINDOW_NM = 10.0
    MERGE_RAW_ABS_TOLERANCE = 0.01
    MERGE_SIGNAL_MIN_P95 = 0.02
    MERGE_SCALE_MIN = 0.5
    MERGE_SCALE_MAX = 2.0
    MERGE_SCALE_FIT_MEDIAN_TOLERANCE = 0.02
    MERGE_FIXED_CROSSOVER_NM = 900.0

    def __init__(
            self,
            name: str,
            spec_keys: Union[str, List[str], Tuple[str, ...]] = ("UV-Vis",),
            save_directory: str = save_directory,
            default_integration_time: Optional[Union[int, List[int], Tuple[int, ...]]] = None):
        super().__init__(name)
        self.spectrometer_dict = {}
        self.wavelength_dict = {}
        self.dark_spectra_dict = {}
        self.blank_spectra_dict = {}
        self.absorbance_dict = {}
        self.photoncounts_dict = {}
        self.merged_absorbance = None
        self.num_spectrometers = 0
        self.spec_keys = self._normalize_spec_keys(spec_keys)
        self.save_directory = save_directory
        self.default_integration_time = self._normalize_detector_setting(
            default_integration_time,
            "default_integration_time",
            default_value=100,
        )

    def get_init_args(self) -> dict:
        return {
            "name": self._name,
            "spec_keys": self.spec_keys,
            "save_directory": self.save_directory,
            "default_integration_time": self.default_integration_time,
        }

    def update_init_args(self, args_dict: dict):
        self._name = args_dict["name"]
        self.spec_keys = self._normalize_spec_keys(args_dict["spec_keys"])
        self.save_directory = args_dict["save_directory"]
        self.default_integration_time = self._normalize_detector_setting(
            args_dict.get("default_integration_time"),
            "default_integration_time",
            default_value=100,
        )

    @classmethod
    def _normalize_spec_keys(
        cls,
        spec_keys: Union[str, List[str], Tuple[str, ...], None],
    ) -> Tuple[str, ...]:
        if spec_keys is None:
            spec_keys = ("UV-Vis",)
        elif isinstance(spec_keys, str):
            spec_keys = (spec_keys,)

        normalized = []
        for spec_key in spec_keys:
            cleaned_key = str(spec_key).strip().rstrip(",")
            if cleaned_key not in cls.SUPPORTED_SPEC_KEYS:
                raise ValueError(
                    "Unsupported spectrometer key: "
                    + cleaned_key
                    + ". Supported keys: "
                    + ", ".join(cls.SUPPORTED_SPEC_KEYS)
                )
            if cleaned_key not in normalized:
                normalized.append(cleaned_key)

        if not normalized:
            raise ValueError("At least one spectrometer key must be selected.")
        return tuple(normalized)

    def _normalize_detector_setting(
        self,
        values: Optional[Union[int, float, List[Union[int, float]], Tuple[Union[int, float], ...]]],
        value_name: str,
        default_value: int,
    ) -> Tuple[int, ...]:
        if values is None:
            return tuple(default_value for _ in self.spec_keys)

        if isinstance(values, (int, float, np.integer, np.floating)):
            normalized_values = [values] * len(self.spec_keys)
        elif isinstance(values, str):
            normalized_values = [values] * len(self.spec_keys)
        else:
            normalized_values = list(values)
            if not normalized_values:
                raise ValueError(value_name + " cannot be empty.")
            if len(normalized_values) == 1:
                normalized_values = normalized_values * len(self.spec_keys)
            elif len(normalized_values) < len(self.spec_keys):
                raise ValueError(
                    value_name
                    + " must provide at least "
                    + str(len(self.spec_keys))
                    + " values for spec_keys "
                    + str(list(self.spec_keys))
                    + "."
                )
            elif len(normalized_values) > len(self.spec_keys):
                normalized_values = normalized_values[:len(self.spec_keys)]

        return tuple(int(value) for value in normalized_values)

    def _normalize_measurement_settings(
        self,
        integration_times: Optional[Union[int, List[int], Tuple[int, ...]]] = None,
        scans_to_avg: Union[int, List[int], Tuple[int, ...]] = (3, 3),
        smoothings: Union[int, List[int], Tuple[int, ...]] = (0, 0),
        xtimings: Union[int, List[int], Tuple[int, ...]] = (1, 1),
    ) -> Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...], Tuple[int, ...]]:
        if integration_times is None:
            integration_times = self.default_integration_time
        return (
            self._normalize_detector_setting(integration_times, "integration_times", default_value=100),
            self._normalize_detector_setting(scans_to_avg, "scans_to_avg", default_value=3),
            self._normalize_detector_setting(smoothings, "smoothings", default_value=0),
            self._normalize_detector_setting(xtimings, "xtimings", default_value=1),
        )

    def find_file(self, dir_path: str, substr: str, substr2: str) -> Optional[str]:
        if not os.path.isdir(dir_path):
            return None

        for _root, _dirs, files in os.walk(dir_path):
            for fname in files:
                if substr in fname and substr2 in fname:
                    return fname
        return None

    def _measurement_qc_log_path(self, sample_name: str) -> str:
        return os.path.join(self.save_directory, sample_name + "_measurement_qc_log.csv")

    def _append_measurement_qc_log(self, sample_name: str, qc_rows: List[dict]) -> None:
        if not qc_rows:
            return
        os.makedirs(self.save_directory, exist_ok=True)
        fullpath = self._measurement_qc_log_path(sample_name)
        df = pd.DataFrame(qc_rows)
        write_header = not os.path.exists(fullpath)
        df.to_csv(fullpath, mode='a', index=False, header=write_header)

    @staticmethod
    def _linear_interpolate(
        x_source: np.ndarray,
        y_source: np.ndarray,
        x_new: np.ndarray,
    ) -> np.ndarray:
        if x_source.size < 2:
            return np.full_like(x_new, np.nan, dtype=float)
        source_order = np.argsort(x_source)
        xs = x_source[source_order]
        ys = y_source[source_order]
        result = np.interp(x_new, xs, ys, left=np.nan, right=np.nan)
        return result

    @staticmethod
    def _trapz(x_values: np.ndarray, y_values: np.ndarray) -> float:
        if x_values.size < 2 or y_values.size < 2:
            return 0.0
        return float(np.trapezoid(y_values, x_values))

    @staticmethod
    def _compute_decay_metrics_with_spacing(
        wavelength_values: np.ndarray,
        reference_absorbance: np.ndarray,
        current_absorbance: np.ndarray,
        decay_threshold: float,
    ) -> Tuple[float, float, float, float]:
        valid_mask = (
            np.isfinite(wavelength_values)
            & np.isfinite(reference_absorbance)
            & np.isfinite(current_absorbance)
            & (reference_absorbance > decay_threshold)
        )
        if np.count_nonzero(valid_mask) < 2:
            return (0.0, 0.0, 0.0, 0.0)

        x_valid = wavelength_values[valid_mask]
        reference_valid = np.maximum(reference_absorbance[valid_mask], 0.0)
        current_valid = np.nan_to_num(current_absorbance[valid_mask], nan=0.0, posinf=0.0, neginf=0.0)
        signed_delta = current_valid - reference_valid

        norm = StellarNetSpectrometer._trapz(x_valid, reference_valid)
        if norm <= 0:
            return (0.0, 0.0, 0.0, 0.0)

        magnitude = np.abs(signed_delta)
        positive = np.maximum(signed_delta, 0.0)
        negative_abs = np.maximum(-signed_delta, 0.0)

        decay_mag = StellarNetSpectrometer._trapz(x_valid, magnitude) / norm
        decay_signed = StellarNetSpectrometer._trapz(x_valid, signed_delta) / norm
        decay_positive = StellarNetSpectrometer._trapz(x_valid, positive) / norm
        decay_negative_abs = StellarNetSpectrometer._trapz(x_valid, negative_abs) / norm
        return (
            float(decay_mag),
            float(decay_signed),
            float(decay_positive),
            float(decay_negative_abs),
        )

    @staticmethod
    def _parse_elapsed_seconds_from_columns(columns: List[str]) -> np.ndarray:
        elapsed_seconds = []
        for column_name in columns:
            match = re.search(r'(-?\d+(?:\.\d+)?)', str(column_name))
            if match is None:
                elapsed_seconds.append(float('nan'))
            else:
                elapsed_seconds.append(float(match.group(1)))
        return np.asarray(elapsed_seconds, dtype=float)

    @staticmethod
    def _interpolate_crossing_time(
        times: np.ndarray,
        values: np.ndarray,
        target: float,
    ) -> Optional[float]:
        valid = np.isfinite(times) & np.isfinite(values)
        if np.count_nonzero(valid) < 2:
            return None
        times_valid = times[valid]
        values_valid = values[valid]
        order = np.argsort(times_valid)
        times_valid = times_valid[order]
        values_valid = values_valid[order]

        for idx in range(len(times_valid) - 1):
            t0, t1 = times_valid[idx], times_valid[idx + 1]
            v0, v1 = values_valid[idx], values_valid[idx + 1]
            if v0 == target:
                return float(t0)
            if v1 == target:
                return float(t1)
            if (v0 - target) * (v1 - target) > 0:
                continue
            if v1 == v0:
                return float(t0)
            ratio = (target - v0) / (v1 - v0)
            return float(t0 + ratio * (t1 - t0))
        return None

    def _load_irradiance_reference(
        self,
        irradiance_file: str,
        wavelength_col_name: str,
        irradiance_col_name: str,
    ) -> Tuple[bool, Union[Tuple[np.ndarray, np.ndarray], str]]:
        irradiance_path = os.path.join(self.save_directory, irradiance_file)
        if not os.path.exists(irradiance_path):
            return (False, "Irradiance table is missing: " + irradiance_path)

        last_error = None
        for read_kwargs in ({}, {"sep": "\t"}):
            try:
                df_irrad = pd.read_csv(irradiance_path, **read_kwargs)
            except Exception as exc:
                last_error = str(exc)
                continue

            wavelength_candidates = [wavelength_col_name, "wavelength_nm", "Wvlgth nm"]
            irradiance_candidates = [
                irradiance_col_name,
                "irradiance_w_m2_nm",
                "irradiance(trapezoid : W/m2)",
            ]

            wavelength_column = next((col for col in wavelength_candidates if col in df_irrad.columns), None)
            irradiance_column = next((col for col in irradiance_candidates if col in df_irrad.columns), None)
            if wavelength_column is None or irradiance_column is None:
                continue

            wavelength = pd.to_numeric(df_irrad[wavelength_column], errors="coerce").to_numpy(dtype=float)
            irradiance = pd.to_numeric(df_irrad[irradiance_column], errors="coerce").to_numpy(dtype=float)
            valid = np.isfinite(wavelength) & np.isfinite(irradiance)
            wavelength = wavelength[valid]
            irradiance = irradiance[valid]
            if wavelength.size < 2:
                continue

            order = np.argsort(wavelength)
            wavelength = wavelength[order]
            irradiance = np.maximum(irradiance[order], 0.0)
            return (True, (wavelength, irradiance))

        error_message = last_error if last_error is not None else "Unsupported irradiance table format."
        return (False, error_message)

    @staticmethod
    def num_specs_connected() -> int:
        if sn is None:
            return 0
        num_connected = 0
        start_wav = [-1.]
        while True:
            try:
                spec, wav = sn.array_get_spec(num_connected)
                start_wav.append(wav[0].item())
                if start_wav[num_connected+1] == start_wav[num_connected]:
                    break
                else:
                    num_connected += 1
            except:
                break
        return num_connected

    def initialize(self) -> Tuple[bool, str]:
        #lamp on
        #shutter in/out
        #any other Arduino initialization
        if sn is None:
            self._is_initialized = False
            return (
                False,
                "stellarnet_driver3 is unavailable. "
                + ("Driver import error: " + _driver_import_error + " " if _driver_import_error else "")
                + "Add the vendor driver file and Python USB dependency referenced in README before using StellarNetSpectrometer.",
            )

        connected_spectrometers = self.num_specs_connected()
        if connected_spectrometers == 0:
            self._is_initialized = False
            return (False, "There are no spectrometers connected")

        detected_spectrometer_dict = {}
        detected_wavelength_dict = {}
        for ndx in range(connected_spectrometers):
            spectrometer, wavelengths = sn.array_get_spec(ndx)
            if wavelengths[0] < 200.0:
                # UV-VIS
                detected_spectrometer_dict['UV-Vis'] = spectrometer
                detected_wavelength_dict['UV-Vis'] = wavelengths
            else:
                # NIR
                detected_spectrometer_dict['NIR'] = spectrometer
                detected_wavelength_dict['NIR'] = wavelengths
            # For additional spectrometers add to the if else ladder

        missing_spec_keys = [
            spec_key for spec_key in self.spec_keys if spec_key not in detected_spectrometer_dict
        ]
        if not missing_spec_keys:
            self.spectrometer_dict = {
                spec_key: detected_spectrometer_dict[spec_key] for spec_key in self.spec_keys
            }
            self.wavelength_dict = {
                spec_key: detected_wavelength_dict[spec_key] for spec_key in self.spec_keys
            }
            self.num_spectrometers = len(self.spec_keys)
            self._is_initialized = True
            return (
                True,
                "Successfully initialized requested spectrometers: "
                + str(list(self.spec_keys))
                + ". Detected connected spectrometers: "
                + str(list(detected_spectrometer_dict.keys()))
            )

        self._is_initialized = False
        self.spectrometer_dict = detected_spectrometer_dict
        self.wavelength_dict = detected_wavelength_dict
        self.num_spectrometers = len(detected_spectrometer_dict)
        return (
            False,
            "Not all declared spectrometers were initialized. Missing: "
            + str(missing_spec_keys)
            + ". Detected connected spectrometers: "
            + str(list(detected_spectrometer_dict.keys()))
        )

    def deinitialize(self, reset_init_flag: bool = True) -> Tuple[bool, str]:
        # turn off lamp?
        # move shutter the position  so that initialize can  be ready to move the shutter  correct position when starting the instrument
        if reset_init_flag:
            self._is_initialized = False

        return (True, "Pass, nothing to deinitialize for now.")

    @check_initialized
    def check_max_count(
            self,
            spec_key: str,
            integration_time: int = 100,
            scans_to_avg: int = 3,
            smoothing: int = 0,
            xtiming: int = 1) -> Tuple[bool, Union[float, str]]:

        if spec_key not in self.spectrometer_dict.keys():
            return (False, spec_key + " spectrometer is not found")

        self.spectrometer_dict[spec_key]['device'].set_config(
            int_time=integration_time,
            scans_to_avg=scans_to_avg,
            x_smooth=smoothing,
            x_timing=xtiming)
        spectrum_array = sn.array_spectrum(self.spectrometer_dict[spec_key], self.wavelength_dict[spec_key])
        max_count = float(np.amax(spectrum_array[:, 1], axis=0))
        return (True, max_count)

    @check_initialized
    def adjust_default_integration_time(
            self,
            scans_to_avg: Union[int, List[int], Tuple[int, ...]] = (3, 3),
            smoothings: Union[int, List[int], Tuple[int, ...]] = (0, 0),
            xtimings: Union[int, List[int], Tuple[int, ...]] = (1, 1),
            target_max_count: int = 52000,
            tolerance: int = 2000,
            max_iterations: int = 8) -> Tuple[bool, str]:

        if self.num_spectrometers != len(self.spec_keys):
            return (False, "Spectrometers are not all connected")

        scans_to_avg = self._normalize_detector_setting(scans_to_avg, "scans_to_avg", default_value=3)
        smoothings = self._normalize_detector_setting(smoothings, "smoothings", default_value=0)
        xtimings = self._normalize_detector_setting(xtimings, "xtimings", default_value=1)
        integration_time_testing = list(self.default_integration_time)
        for ndx, spec_key in enumerate(self.spec_keys):
            for _ in range(max_iterations):
                result, max_count = self.check_max_count(
                    spec_key,
                    integration_time=integration_time_testing[ndx],
                    scans_to_avg=scans_to_avg[ndx],
                    smoothing=smoothings[ndx],
                    xtiming=xtimings[ndx],
                )
                if not result:
                    return (False, max_count)

                if max_count <= 0:
                    break
                if abs(max_count - target_max_count) <= tolerance:
                    break

                next_integration_time = int(np.ceil(integration_time_testing[ndx] * target_max_count / max_count))
                next_integration_time = max(1, next_integration_time)
                if next_integration_time == integration_time_testing[ndx]:
                    break

                integration_time_testing[ndx] = next_integration_time
                time.sleep(0.5)

        self.default_integration_time = tuple(integration_time_testing)
        return (True, "Successfully adjusted default integration time to " + str(self.default_integration_time))

    @staticmethod
    def _compute_absorbance(dark_spec, blank_spec, sam_spec):
        sam_dark_diff = sam_spec - dark_spec
        blank_dark_diff = blank_spec - dark_spec
        absorbance = np.zeros_like(sam_dark_diff, dtype=float)
        absorbance[(blank_dark_diff > 0) & (sam_dark_diff <= 0)] = 5.0
        valid_index = (blank_dark_diff > 0) & (sam_dark_diff > 0)
        absorbance[valid_index] = -np.log10(sam_dark_diff[valid_index] / blank_dark_diff[valid_index])
        absorbance = np.nan_to_num(absorbance, nan=0.0, posinf=5.0, neginf=0.0)
        absorbance[absorbance < 0] = 0
        absorbance[absorbance > 5] = 5
        return absorbance

    def _merge_absorbance_byname_onedetector(
            self,
            save_to_file: bool,
            filename: str,
            sample_name: str,
            comment_list: List[str]) -> Tuple[bool, str]:

        uv_array = self.absorbance_dict[self.spec_keys[0]].copy()
        uv_array = self.truncate_ends_by_wavelength(uv_array, 210.0, 1700.0)
        merged_array = uv_array[uv_array[:, 0].argsort()]
        self.merged_absorbance = merged_array

        if save_to_file:
            os.makedirs(self.save_directory, exist_ok=True)
            fname = self.find_file(self.save_directory, sample_name, 'merged.csv')
            if fname is None:
                data = pd.DataFrame()
                data['Wavelength'] = np.squeeze(self.merged_absorbance[:, 0].copy())
                copy_abs = self.merged_absorbance[:, 1].copy()
                copy_abs[copy_abs < 0] = 0
                data['0'] = np.squeeze(copy_abs)
                fullfilename = os.path.join(self.save_directory, filename + '_merged.csv')
            else:
                fullfilename = os.path.join(self.save_directory, fname)
                timestamp_match = re.search(r'_(\d+)_', fname)
                time_interval = 0
                if timestamp_match is not None:
                    time_zero = datetime.strptime(timestamp_match.group(1), '%Y%m%d%H%M%S')
                    time_interval = int((datetime.now() - time_zero).total_seconds())
                df_old = pd.read_csv(fullfilename, comment='#')
                df_new = pd.DataFrame()
                df_new['Wavelength'] = np.squeeze(self.merged_absorbance[:, 0].copy())
                copy_abs = self.merged_absorbance[:, 1].copy()
                copy_abs[copy_abs < 0] = 0
                df_new[str(time_interval)] = np.squeeze(copy_abs)
                data = df_old.drop(columns='Index', errors='ignore').merge(df_new, how='inner', on='Wavelength')

            comment_list = list(comment_list)
            comment_list.append("# To merge, NIR data is scaled first then shifted\n")
            comment_list.append("# scale = none\n")
            comment_list.append("# shift = none\n")
            comment_list.append("# First column is Wavelength, later columns are absorbance at elapsed time in seconds\n")
            with open(fullfilename, 'w') as file:
                file.writelines(comment_list)
            data.to_csv(fullfilename, mode='a', index_label='Index')

        return (True, "Successfully merged absorbance spectra for single detector")

    @check_initialized
    def get_spectrum_counts(
            self, 
            spec_key: str, 
            integration_time: int = 100, 
            scans_to_avg: int = 3,  
            smoothing: int = 0, 
            xtiming: int = 1) -> Tuple[bool, str]:

        # if not self._is_initialized:
        #     return (False, "Spectrometer system not initialized")

        if spec_key in self.spectrometer_dict.keys():
            self.spectrometer_dict[spec_key]['device'].set_config(
                int_time=integration_time, 
                scans_to_avg=scans_to_avg, 
                x_smooth=smoothing, 
                x_timing=xtiming)

            spectrum_array = sn.array_spectrum(self.spectrometer_dict[spec_key], self.wavelength_dict[spec_key])

            max_count = np.amax(spectrum_array[:,1], axis=0)
            print("Max count: " + str(max_count))
            if max_count > 65500:
                return (False, spec_key + " detector is saturated, lower integration time")
            return (True, spectrum_array)
        else:
            return (False, spec_key + " spectrometer is not found" )

    def get_all_spectra_counts(
            self,
            integration_times: Optional[Union[int, List[int], Tuple[int, ...]]] = None,
            scans_to_avg: Union[int, List[int], Tuple[int, ...]] = (3, 3),
            smoothings: Union[int, List[int], Tuple[int, ...]] = (0, 0),
            xtimings: Union[int, List[int], Tuple[int, ...]] = (1, 1)) -> Tuple[bool, str]:

        # Modify the variable 'spec_keys' if you don't intend to use all spectrometers
        if self.num_spectrometers != len(self.spec_keys):
            return (False, "Spectrometers are not all connected")

        integration_times, scans_to_avg, smoothings, xtimings = self._normalize_measurement_settings(
            integration_times,
            scans_to_avg,
            smoothings,
            xtimings,
        )
        spectrum_array_dict = {}
        # print(spec_keys)
        # using self.spec_keys to ensure that the order within the parameter tuple matches the order of the declared spec_keys
        for ndx, spec_key in enumerate(self.spec_keys):
            # this function should already check if the spec_key is valid
            result, spectrum_array = self.get_spectrum_counts(
                                        spec_key,
                                        integration_time=integration_times[ndx], 
                                        scans_to_avg=scans_to_avg[ndx], 
                                        smoothing=smoothings[ndx], 
                                        xtiming=xtimings[ndx])
            if not result:
                return result, spectrum_array

            spectrum_array_dict[spec_key] = spectrum_array

        return (True, spectrum_array_dict)


    def update_all_dark_spectra(
            self,
            integration_times: Optional[Union[int, List[int], Tuple[int, ...]]] = None,
            scans_to_avg: Union[int, List[int], Tuple[int, ...]] = (3, 3),
            smoothings: Union[int, List[int], Tuple[int, ...]] = (0, 0),
            xtimings: Union[int, List[int], Tuple[int, ...]] = (1, 1)) -> Tuple[bool, str]:

        result, spectrum_array_dict = self.get_all_spectra_counts(
                                        integration_times, 
                                        scans_to_avg, 
                                        smoothings, 
                                        xtimings)

        if not result:
            return result, spectrum_array_dict

        for key, value in spectrum_array_dict.items():
            self.dark_spectra_dict[key] = value

        return (True, "All dark spectra stored")

    def update_all_blank_spectra(
            self,
            integration_times: Optional[Union[int, List[int], Tuple[int, ...]]] = None,
            scans_to_avg: Union[int, List[int], Tuple[int, ...]] = (3, 3),
            smoothings: Union[int, List[int], Tuple[int, ...]] = (0, 0),
            xtimings: Union[int, List[int], Tuple[int, ...]] = (1, 1)) -> Tuple[bool, str]:

        result, spectrum_array_dict = self.get_all_spectra_counts(
                                        integration_times, 
                                        scans_to_avg, 
                                        smoothings, 
                                        xtimings)

        if not result:
            return result, spectrum_array_dict

        for key, value in spectrum_array_dict.items():
            self.blank_spectra_dict[key] = value

        return (True, "All blank spectra stored")

    def get_all_absorbance(
            self,
            save_to_file: bool = False,
            filename: Optional[str] = None,
            integration_times: Optional[Union[int, List[int], Tuple[int, ...]]] = None,
            scans_to_avg: Union[int, List[int], Tuple[int, ...]] = (3, 3),
            smoothings: Union[int, List[int], Tuple[int, ...]] = (0, 0),
            xtimings: Union[int, List[int], Tuple[int, ...]] = (1, 1)) -> Tuple[bool, str]:

        integration_times, scans_to_avg, smoothings, xtimings = self._normalize_measurement_settings(
            integration_times,
            scans_to_avg,
            smoothings,
            xtimings,
        )

        # get the sample spectra
        result, spectrum_array_dict = self.get_all_spectra_counts(
                                        integration_times, 
                                        scans_to_avg, 
                                        smoothings, 
                                        xtimings)
        if save_to_file and filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = timestamp


        # check if failed
        if not result:
            return result, spectrum_array_dict

        # check that dark/blank spectra exists for each initialized spectrometer
        for key in self.spectrometer_dict.keys():
            if not key in self.blank_spectra_dict:
                return (False, "Blank spectra for " + key + " is missing")
            if not key in self.dark_spectra_dict:
                return (False, "Dark spectra for " + key + " is missing")

        # Calculate absorbance for each spectra, save to self
        # Absorbance is -log10((Isample - Idark)/(Iblank - Idark))
        for ndx, spec_key in enumerate(self.spec_keys):
            wavelength = self.wavelength_dict[spec_key].copy()
            dark_spec = self.dark_spectra_dict[spec_key][:,1].copy()
            blank_spec = self.blank_spectra_dict[spec_key][:,1].copy()
            sam_spec = spectrum_array_dict[spec_key][:,1].copy()

            absorbance = np.expand_dims(self._compute_absorbance(dark_spec, blank_spec, sam_spec), axis=1)
            absorbance_array = np.hstack((wavelength, absorbance))

            self.absorbance_dict[spec_key] = absorbance_array
            
            # save all data related to absorbance calculation to a file per spectrometer
            if save_to_file:
                os.makedirs(self.save_directory, exist_ok=True)
                data = pd.DataFrame()
                data[spec_key + ' Wavelength'] = np.squeeze(wavelength)
                data[spec_key + ' Dark Counts'] = np.squeeze(dark_spec)
                data[spec_key + ' Blank Counts'] = np.squeeze(blank_spec)
                data[spec_key + ' Sample Counts'] = np.squeeze(sam_spec)
                data[spec_key + ' Absorbance'] = np.squeeze(absorbance)
                
                comment = ["# spec_key = " + spec_key + "\n",
                            "# integration_time = " + str(integration_times[ndx]) + "\n",
                            "# scans_to_avg = " + str(scans_to_avg[ndx]) + "\n",
                            "# smoothing = " + str(smoothings[ndx]) + "\n",
                            "# xtiming = " + str(xtimings[ndx]) + "\n"]
                
                fullfilename = self.save_directory + filename + '_' + spec_key + '.csv'
                with open(fullfilename, 'w') as file:
                    file.writelines(comment)
                data.to_csv(fullfilename, mode='a', index_label='Index')

        if save_to_file:
            all_comments = ["# spec_keys = " + str(self.spec_keys) + "\n"
                            "# integration_times = " + str(integration_times) + "\n",
                            "# scans_to_avg = " + str(scans_to_avg) + "\n",
                            "# smoothings = " + str(smoothings) + "\n",
                            "# xtimings = " + str(xtimings) + "\n"]
        else:
            all_comments = ['#\n',]
        # Merge the absorbance spectra and optionally save to file
        if len(self.spec_keys) == 1:
            result, message = self._merge_absorbance_byname_onedetector(save_to_file, filename, filename, all_comments)
        elif len(self.spec_keys) > 1:
            result, message = self.merge_absorbance(save_to_file, filename, all_comments)

        if not result:
            return result, message

        if save_to_file:
            return (True, "All absorbance spectra stored to instance and saved to file: " + self.save_directory + filename)
        else:
            return (True, "All absorbance spectra stored to instance but not saved to file")

    def get_all_absorbance_byname(
            self,
            sample_name: str,
            save_to_file: bool = False,
            repeat_measure: bool = False,
            integration_times: Optional[Union[int, List[int], Tuple[int, ...]]] = None,
            scans_to_avg: Union[int, List[int], Tuple[int, ...]] = (3, 3),
            smoothings: Union[int, List[int], Tuple[int, ...]] = (0, 0),
            xtimings: Union[int, List[int], Tuple[int, ...]] = (1, 1),
            absorbance_threshold: float = 0.003) -> Tuple[bool, str]:

        integration_times, scans_to_avg, smoothings, xtimings = self._normalize_measurement_settings(
            integration_times,
            scans_to_avg,
            smoothings,
            xtimings,
        )

        filename = sample_name + '_' + datetime.now().strftime('%Y%m%d%H%M%S')
        for attempt in range(3):
            warning_by_spec = {}
            result, spectrum_array_dict = self.get_all_spectra_counts(
                integration_times,
                scans_to_avg,
                smoothings,
                xtimings)
            if not result:
                return result, spectrum_array_dict

            existing_files = {}
            if save_to_file and repeat_measure:
                for spec_key in self.spec_keys:
                    existing_files[spec_key] = self.find_file(self.save_directory, sample_name, spec_key)

            for key in self.spectrometer_dict.keys():
                if key not in self.blank_spectra_dict:
                    return (False, "Blank spectra for " + key + " is missing")
                if key not in self.dark_spectra_dict:
                    return (False, "Dark spectra for " + key + " is missing")

            retry_needed = False
            prepared_rows = {}

            for ndx, spec_key in enumerate(self.spec_keys):
                wavelength = self.wavelength_dict[spec_key].copy()
                dark_spec = self.dark_spectra_dict[spec_key][:, 1].copy()
                blank_spec = self.blank_spectra_dict[spec_key][:, 1].copy()
                sam_spec = spectrum_array_dict[spec_key][:, 1].copy()
                absorbance = self._compute_absorbance(dark_spec, blank_spec, sam_spec)
                absorbance_array = np.hstack((wavelength, np.expand_dims(absorbance, axis=1)))
                self.absorbance_dict[spec_key] = absorbance_array

                fname = existing_files.get(spec_key) if repeat_measure else None
                qc_record = {
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "spec_key": spec_key,
                    "measurement_valid": 1,
                    "relative_diff": "",
                    "previous_mean": "",
                    "current_mean": "",
                    "previous_sum": "",
                    "current_sum": "",
                    "valid_points": "",
                    "threshold": absorbance_threshold,
                    "attempt_used": attempt + 1,
                    "elapsed_seconds": 0,
                    "reason": "first_measurement" if fname is None else "comparison_not_needed",
                    "data_file": "",
                }
                if fname is not None:
                    fullfilename = os.path.join(self.save_directory, fname)
                    df_old = pd.read_csv(fullfilename, comment='#')
                    last_column_name = df_old.columns[-1]
                    df_cur = pd.DataFrame()
                    df_cur[spec_key + ' Wavelength'] = np.squeeze(wavelength)
                    df_cur[spec_key + ' current_absorbance'] = np.squeeze(absorbance)
                    data = df_old.drop(columns='Index', errors='ignore').merge(
                        df_cur,
                        how='inner',
                        on=spec_key + ' Wavelength')

                    current_absorbance = data[spec_key + ' current_absorbance'].to_numpy()
                    last_absorbance = data[last_column_name].to_numpy()
                    wavelength_list = data.iloc[:, 0].to_numpy()

                    if last_absorbance.shape == current_absorbance.shape:
                        valid_index = (
                            (last_absorbance > 0)
                            & (last_absorbance < 5)
                            & (current_absorbance > 0)
                            & (current_absorbance < 5)
                            & (wavelength_list > 285)
                            & (wavelength_list < 800)
                        )
                        if np.any(valid_index):
                            previous_sum = float(np.sum(np.abs(last_absorbance[valid_index])))
                            current_sum = float(np.sum(np.abs(current_absorbance[valid_index])))
                            previous_mean = float(np.mean(last_absorbance[valid_index]))
                            current_mean = float(np.mean(current_absorbance[valid_index]))
                            absorbance_diff = (
                                np.sum(np.abs(last_absorbance[valid_index] - current_absorbance[valid_index]))
                                / previous_sum
                            )
                            diff_message = (
                                f"{spec_key}: relative_diff={absorbance_diff:.6f}, "
                                f"previous_mean={previous_mean:.6f}, current_mean={current_mean:.6f}, "
                                f"previous_sum={previous_sum:.6f}, current_sum={current_sum:.6f}, "
                                f"valid_points={int(np.count_nonzero(valid_index))}, attempt={attempt + 1}"
                            )
                            timestamp_match = re.search(r'_(\d+)_', fname)
                            time_interval = 0
                            if timestamp_match is not None:
                                time_zero = datetime.strptime(timestamp_match.group(1), '%Y%m%d%H%M%S')
                                time_interval = int((datetime.now() - time_zero).total_seconds())
                            qc_record.update({
                                "measurement_valid": int(absorbance_diff <= absorbance_threshold),
                                "relative_diff": absorbance_diff,
                                "previous_mean": previous_mean,
                                "current_mean": current_mean,
                                "previous_sum": previous_sum,
                                "current_sum": current_sum,
                                "valid_points": int(np.count_nonzero(valid_index)),
                                "elapsed_seconds": time_interval,
                                "reason": "within_threshold" if absorbance_diff <= absorbance_threshold else "difference_exceeded_threshold",
                            })
                            if absorbance_diff > absorbance_threshold:
                                warning_by_spec[spec_key] = diff_message
                                if attempt < 2:
                                    retry_needed = True
                                    break
                            else:
                                warning_by_spec.pop(spec_key, None)
                    else:
                        qc_record.update({
                            "measurement_valid": 1,
                            "reason": "no_overlap_for_comparison",
                        })

                prepared_rows[spec_key] = {
                    "wavelength": wavelength,
                    "dark_spec": dark_spec,
                    "blank_spec": blank_spec,
                    "sam_spec": sam_spec,
                    "absorbance": absorbance,
                    "existing_file": fname,
                    "qc_record": qc_record,
                }

            if retry_needed:
                continue

            if save_to_file:
                os.makedirs(self.save_directory, exist_ok=True)
                qc_rows = []
                for ndx, spec_key in enumerate(self.spec_keys):
                    row = prepared_rows[spec_key]
                    wavelength = row["wavelength"]
                    dark_spec = row["dark_spec"]
                    blank_spec = row["blank_spec"]
                    sam_spec = row["sam_spec"]
                    absorbance = row["absorbance"]
                    fname = row["existing_file"]
                    qc_record = row["qc_record"]

                    comment = [
                        "# spec_key = " + spec_key + "\n",
                        "# integration_time = " + str(integration_times[ndx]) + "\n",
                        "# scans_to_avg = " + str(scans_to_avg[ndx]) + "\n",
                        "# smoothing = " + str(smoothings[ndx]) + "\n",
                        "# xtiming = " + str(xtimings[ndx]) + "\n",
                    ]

                    if fname is None:
                        data = pd.DataFrame()
                        data[spec_key + ' Wavelength'] = np.squeeze(wavelength)
                        data[spec_key + ' Dark Counts'] = np.squeeze(dark_spec)
                        data[spec_key + ' Blank Counts'] = np.squeeze(blank_spec)
                        data[spec_key + ' Sample Counts at time 0'] = np.squeeze(sam_spec)
                        data[spec_key + ' Absorbance at time 0'] = np.squeeze(absorbance)
                        fullfilename = os.path.join(self.save_directory, filename + '_' + spec_key + '.csv')
                        qc_record["elapsed_seconds"] = 0
                    else:
                        fullfilename = os.path.join(self.save_directory, fname)
                        timestamp_match = re.search(r'_(\d+)_', fname)
                        time_interval = 0
                        if timestamp_match is not None:
                            time_zero = datetime.strptime(timestamp_match.group(1), '%Y%m%d%H%M%S')
                            time_interval = int((datetime.now() - time_zero).total_seconds())

                        df_old = pd.read_csv(fullfilename, comment='#')
                        df_new = pd.DataFrame()
                        df_new[spec_key + ' Wavelength'] = np.squeeze(wavelength)
                        df_new[spec_key + ' Sample Counts at time ' + str(time_interval)] = np.squeeze(sam_spec)
                        df_new[spec_key + ' Absorbance at time ' + str(time_interval)] = np.squeeze(absorbance)
                        data = df_old.drop(columns='Index', errors='ignore').merge(
                            df_new,
                            how='inner',
                            on=spec_key + ' Wavelength')
                        qc_record["elapsed_seconds"] = time_interval

                    with open(fullfilename, 'w') as file:
                        file.writelines(comment)
                    data.to_csv(fullfilename, mode='a', index_label='Index')
                    qc_record["data_file"] = os.path.basename(fullfilename)
                    qc_rows.append(qc_record)

                self._append_measurement_qc_log(sample_name, qc_rows)

            break

        if save_to_file:
            all_comments = [
                "# spec_keys = " + str(self.spec_keys) + "\n",
                "# integration_times = " + str(integration_times) + "\n",
                "# scans_to_avg = " + str(scans_to_avg) + "\n",
                "# smoothings = " + str(smoothings) + "\n",
                "# xtimings = " + str(xtimings) + "\n",
            ]
        else:
            all_comments = ['#\n']

        if len(self.spec_keys) == 1:
            result, message = self._merge_absorbance_byname_onedetector(save_to_file, filename, sample_name, all_comments)
        else:
            result, message = self.merge_absorbance(save_to_file, filename, all_comments)

        if not result:
            return result, message

        if save_to_file:
            if warning_by_spec:
                warning_summary = " | ".join(
                    "WARNING " + warning_message for warning_message in warning_by_spec.values()
                )
                return (
                    True,
                    "All absorbance spectra stored to instance and saved to file: "
                    + self.save_directory
                    + filename
                    + ". QC log updated: "
                    + self._measurement_qc_log_path(sample_name)
                    + ". "
                    + warning_summary
                )
            return (
                True,
                "All absorbance spectra stored to instance and saved to file: "
                + self.save_directory
                + filename
                + ". QC log updated: "
                + self._measurement_qc_log_path(sample_name)
            )
        return (True, "All absorbance spectra stored to instance but not saved to file")

    def get_all_counts_byname(
            self,
            sample_name: str,
            save_to_file: bool = False,
            repeat_measure: bool = False,
            integration_times: Optional[Union[int, List[int], Tuple[int, ...]]] = None,
            scans_to_avg: Union[int, List[int], Tuple[int, ...]] = (3, 3),
            smoothings: Union[int, List[int], Tuple[int, ...]] = (0, 0),
            xtimings: Union[int, List[int], Tuple[int, ...]] = (1, 1),
            absorbance_threshold: float = 0.003) -> Tuple[bool, str]:

        del absorbance_threshold
        integration_times, scans_to_avg, smoothings, xtimings = self._normalize_measurement_settings(
            integration_times,
            scans_to_avg,
            smoothings,
            xtimings,
        )

        result, spectrum_array_dict = self.get_all_spectra_counts(
            integration_times,
            scans_to_avg,
            smoothings,
            xtimings)
        if not result:
            return result, spectrum_array_dict

        existing_files = {}
        if save_to_file and repeat_measure:
            for spec_key in self.spec_keys:
                existing_files[spec_key] = self.find_file(
                    self.save_directory,
                    sample_name,
                    spec_key + '_photoncounts')

        filename = sample_name + '_' + datetime.now().strftime('%Y%m%d%H%M%S')

        for ndx, spec_key in enumerate(self.spec_keys):
            wavelength = self.wavelength_dict[spec_key].copy()
            photoncounts = spectrum_array_dict[spec_key][:, 1].copy()
            photoncounts = np.nan_to_num(photoncounts, nan=0.0, posinf=0.0, neginf=0.0)
            photoncounts[photoncounts < 0] = 0
            self.photoncounts_dict[spec_key] = np.hstack((wavelength, np.expand_dims(photoncounts, axis=1)))

            if save_to_file:
                os.makedirs(self.save_directory, exist_ok=True)
                comment = [
                    "# spec_key = " + spec_key + "\n",
                    "# integration_time = " + str(integration_times[ndx]) + "\n",
                    "# scans_to_avg = " + str(scans_to_avg[ndx]) + "\n",
                    "# smoothing = " + str(smoothings[ndx]) + "\n",
                    "# xtiming = " + str(xtimings[ndx]) + "\n",
                ]
                fname = existing_files.get(spec_key) if repeat_measure else None
                if fname is None:
                    data = pd.DataFrame()
                    data[spec_key + ' Wavelength'] = np.squeeze(wavelength)
                    data[spec_key + ' Photon Counts at time 0'] = np.squeeze(photoncounts)
                    fullfilename = os.path.join(self.save_directory, filename + '_' + spec_key + '_photoncounts.csv')
                else:
                    fullfilename = os.path.join(self.save_directory, fname)
                    timestamp_match = re.search(r'_(\d+)_', fname)
                    time_interval = 0
                    if timestamp_match is not None:
                        time_zero = datetime.strptime(timestamp_match.group(1), '%Y%m%d%H%M%S')
                        time_interval = int((datetime.now() - time_zero).total_seconds())
                    df_old = pd.read_csv(fullfilename, comment='#')
                    df_new = pd.DataFrame()
                    df_new[spec_key + ' Wavelength'] = np.squeeze(wavelength)
                    df_new[spec_key + ' Photon Counts at time ' + str(time_interval)] = np.squeeze(photoncounts)
                    data = df_old.drop(columns='Index', errors='ignore').merge(
                        df_new,
                        how='inner',
                        on=spec_key + ' Wavelength')

                with open(fullfilename, 'w') as file:
                    file.writelines(comment)
                data.to_csv(fullfilename, mode='a', index_label='Index')

        if save_to_file:
            return (True, "Photon counts saved to file: " + self.save_directory + filename)
        return (True, "Photon counts stored to instance but not saved to file")

    def get_spec_decay(
            self,
            sample_name: str,
            save_to_file: bool = False,
            range_start: float = 290.0,
            range_end: float = 800.0,
            irradiance_file: str = "reference/am15g_spectrum.csv",
            Wvlgth_col_name: str = "wavelength_nm",
            Irrad_col_name: str = "irradiance_w_m2_nm",
            decay_threshold: float = 0.01) -> Tuple[bool, str]:

        fname = self.find_file(self.save_directory, sample_name, 'merged.csv')
        if fname is None:
            return (False, "Absorbance of " + sample_name + " is missing")

        fullfilename = os.path.join(self.save_directory, fname)
        df_old = pd.read_csv(fullfilename, comment='#')
        if len(df_old.columns) <= 3:
            return (False, "Only original absorbance recorded")

        wavelength_list = pd.to_numeric(df_old.iloc[:, 1], errors='coerce').to_numpy(dtype=float)
        data_mask = np.logical_and(wavelength_list >= range_start, wavelength_list <= range_end)
        if np.count_nonzero(data_mask) < 2:
            return (False, "Insufficient wavelength points in the selected spectral decay range.")

        absorbance_df = df_old.iloc[:, 2:].apply(pd.to_numeric, errors='coerce')
        decayed_absorbance = absorbance_df.to_numpy(dtype=float)[data_mask]
        original_absorbance = absorbance_df.iloc[:, 0].to_numpy(dtype=float)[data_mask]
        wavelength_list_inrange = wavelength_list[data_mask]
        time_columns = [str(column_name) for column_name in df_old.columns[2:]]
        elapsed_seconds = self._parse_elapsed_seconds_from_columns(time_columns)
        elapsed_hours = elapsed_seconds / 3600.0

        result, irradiance_data = self._load_irradiance_reference(
            irradiance_file,
            Wvlgth_col_name,
            Irrad_col_name)
        if not result:
            return (False, str(irradiance_data))
        wavelength_list_irr, irradiance_reference = irradiance_data
        if range_start < np.min(wavelength_list_irr) or range_end > np.max(wavelength_list_irr):
            return (False, "Incompatible range with irradiance table")

        irradiance_interp = self._linear_interpolate(wavelength_list_irr, irradiance_reference, wavelength_list_inrange)
        irradiance_interp = np.nan_to_num(irradiance_interp, nan=0.0, posinf=0.0, neginf=0.0)
        total_irradiance = self._trapz(wavelength_list_inrange, irradiance_interp)

        overlap_percent = np.zeros(decayed_absorbance.shape[1], dtype=float)
        for idx in range(decayed_absorbance.shape[1]):
            absorbed_fraction = 1.0 - np.power(10.0, -decayed_absorbance[:, idx])
            absorbed_fraction = np.clip(np.nan_to_num(absorbed_fraction, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)
            absorbed_weighted = irradiance_interp * absorbed_fraction
            absorbed_irradiance = self._trapz(wavelength_list_inrange, absorbed_weighted)
            overlap_percent[idx] = (
                absorbed_irradiance / total_irradiance * 100.0 if total_irradiance > 0 else 0.0
            )

        baseline_overlap = overlap_percent[0]
        if baseline_overlap > 0:
            retention_percent = overlap_percent / baseline_overlap * 100.0
        else:
            retention_percent = np.zeros_like(overlap_percent)
        overlap_delta_vs_t0 = overlap_percent - baseline_overlap
        overlap_abs_change_vs_t0 = np.abs(retention_percent - 100.0)

        decay_mag = np.zeros(decayed_absorbance.shape[1], dtype=float)
        decay_signed = np.zeros(decayed_absorbance.shape[1], dtype=float)
        decay_positive = np.zeros(decayed_absorbance.shape[1], dtype=float)
        decay_negative_abs = np.zeros(decayed_absorbance.shape[1], dtype=float)

        for idx in range(decayed_absorbance.shape[1]):
            (
                decay_mag[idx],
                decay_signed[idx],
                decay_positive[idx],
                decay_negative_abs[idx],
            ) = self._compute_decay_metrics_with_spacing(
                wavelength_list_inrange,
                original_absorbance,
                decayed_absorbance[:, idx],
                decay_threshold,
            )

        t80_h = self._interpolate_crossing_time(elapsed_hours, decay_mag, 0.20)

        df_specdecay = pd.DataFrame()
        df_specdecay['time_s'] = elapsed_seconds
        df_specdecay['time_h'] = elapsed_hours
        df_specdecay['spectral_overlap_percent'] = overlap_percent
        df_specdecay['spectral_overlap_delta_vs_t0_percent'] = overlap_delta_vs_t0
        df_specdecay['retention_vs_t0_percent'] = retention_percent
        df_specdecay['spectral_overlap_abs_change_vs_t0_percent'] = overlap_abs_change_vs_t0
        df_specdecay['decay_index_mag'] = decay_mag
        df_specdecay['decay_index_signed'] = decay_signed
        df_specdecay['decay_index_positive'] = decay_positive
        df_specdecay['decay_index_negative_abs'] = decay_negative_abs
        df_specdecay['t80_h'] = t80_h

        if save_to_file:
            new_filename = os.path.join(self.save_directory, sample_name + "_specdecay.csv")
            comment = [
                "# range start from (wavelength) " + str(range_start) + " (nm)\n",
                "# end at = " + str(range_end) + "\n",
                "# irradiance_file = " + str(irradiance_file) + "\n",
                "# decay_threshold = " + str(decay_threshold) + "\n",
                "# methodology = UVVis_Converter style overlap/interpolate/trapz and decay index summary with wavelength-spacing weighting\n",
            ]
            with open(new_filename, 'w') as file:
                file.writelines(comment)
            df_specdecay.to_csv(new_filename, mode='a', index_label='Index')
            return (True, "Spectral decay saved to file: " + new_filename)
        return (True, "Spectral decay calculated but not saved to file")

    def plot_spec_decay_summary(
            self,
            sample_name: str,
            range_start: float = 290.0,
            range_end: float = 800.0,
            save_to_file: bool = True,
            output_filename: Optional[str] = None,
            figure_dpi: int = 180) -> Tuple[bool, str]:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except Exception as exc:
            return (False, "matplotlib is required to plot spectral decay summaries: " + str(exc))

        specdecay_path = os.path.join(self.save_directory, sample_name + "_specdecay.csv")
        if not os.path.exists(specdecay_path):
            fname = self.find_file(self.save_directory, sample_name, 'specdecay.csv')
            if fname is None:
                return (False, "Spectral decay of " + sample_name + " is missing")
            specdecay_path = os.path.join(self.save_directory, fname)

        df_specdecay = pd.read_csv(specdecay_path, comment='#')
        if df_specdecay.empty:
            return (False, "Spectral decay file is empty: " + specdecay_path)

        required_columns = [
            "time_h",
            "spectral_overlap_percent",
            "retention_vs_t0_percent",
            "decay_index_mag",
            "decay_index_signed",
            "decay_index_positive",
            "decay_index_negative_abs",
        ]
        missing_columns = [column for column in required_columns if column not in df_specdecay.columns]
        if missing_columns:
            return (False, "Spectral decay file is missing columns: " + ", ".join(missing_columns))

        time_h = pd.to_numeric(df_specdecay["time_h"], errors="coerce").to_numpy(dtype=float)
        overlap_percent = pd.to_numeric(
            df_specdecay["spectral_overlap_percent"], errors="coerce").to_numpy(dtype=float)
        retention_percent = pd.to_numeric(
            df_specdecay["retention_vs_t0_percent"], errors="coerce").to_numpy(dtype=float)
        decay_mag = pd.to_numeric(df_specdecay["decay_index_mag"], errors="coerce").to_numpy(dtype=float)
        decay_signed = pd.to_numeric(df_specdecay["decay_index_signed"], errors="coerce").to_numpy(dtype=float)
        decay_positive = pd.to_numeric(df_specdecay["decay_index_positive"], errors="coerce").to_numpy(dtype=float)
        decay_negative_abs = pd.to_numeric(
            df_specdecay["decay_index_negative_abs"], errors="coerce").to_numpy(dtype=float)

        t80_h = None
        if "t80_h" in df_specdecay.columns:
            t80_values = pd.to_numeric(df_specdecay["t80_h"], errors="coerce").to_numpy(dtype=float)
            finite_t80 = t80_values[np.isfinite(t80_values)]
            if finite_t80.size > 0:
                t80_h = float(finite_t80[0])

        merged_path = None
        merged_name = self.find_file(self.save_directory, sample_name, 'merged.csv')
        if merged_name is not None:
            merged_path = os.path.join(self.save_directory, merged_name)

        qc_path = self._measurement_qc_log_path(sample_name)
        df_qc = pd.read_csv(qc_path) if os.path.exists(qc_path) else None

        fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
        fig.suptitle(sample_name)

        ax_overlap = axes[0, 0]
        ax_overlap.plot(time_h, overlap_percent, color="#1f77b4", linewidth=1.8, label="Overlap [%]")
        ax_overlap.set_xlabel("Time [h]")
        ax_overlap.set_ylabel("Spectral Overlap [%]", color="#1f77b4")
        ax_overlap.tick_params(axis='y', labelcolor="#1f77b4")
        ax_overlap.grid(alpha=0.25)
        ax_retention = ax_overlap.twinx()
        ax_retention.plot(time_h, retention_percent, color="#ff7f0e", linewidth=1.5, label="Retention [%]")
        ax_retention.set_ylabel("Retention vs t0 [%]", color="#ff7f0e")
        ax_retention.tick_params(axis='y', labelcolor="#ff7f0e")
        if t80_h is not None and np.isfinite(t80_h):
            ax_overlap.axvline(t80_h, color="black", linestyle="--", linewidth=1.0, alpha=0.7)
            ax_overlap.text(
                t80_h,
                np.nanmax(overlap_percent) if np.any(np.isfinite(overlap_percent)) else 0.0,
                f"t80={t80_h:.2f} h",
                fontsize=8,
                ha="left",
                va="bottom",
            )
        ax_overlap.set_title("Overlap / Retention")

        ax_decay = axes[0, 1]
        ax_decay.plot(time_h, decay_mag, color="#d62728", linewidth=1.8, label="Decay magnitude")
        ax_decay.plot(time_h, decay_positive, color="#2ca02c", linewidth=1.2, label="Positive")
        ax_decay.plot(time_h, decay_negative_abs, color="#9467bd", linewidth=1.2, label="Negative abs")
        ax_decay.plot(time_h, decay_signed, color="#7f7f7f", linewidth=1.0, linestyle="--", label="Signed")
        if t80_h is not None and np.isfinite(t80_h):
            ax_decay.axvline(t80_h, color="black", linestyle="--", linewidth=1.0, alpha=0.7)
        ax_decay.set_xlabel("Time [h]")
        ax_decay.set_ylabel("Decay Index")
        ax_decay.set_title("Decay Indices")
        ax_decay.grid(alpha=0.25)
        ax_decay.legend(loc="best", fontsize=8)

        ax_abs = axes[1, 0]
        if merged_path is not None and os.path.exists(merged_path):
            df_merged = pd.read_csv(merged_path, comment='#')
            wavelength = pd.to_numeric(df_merged.iloc[:, 1], errors="coerce").to_numpy(dtype=float)
            absorbance_df = df_merged.iloc[:, 2:].apply(pd.to_numeric, errors='coerce')
            mask = np.logical_and(wavelength >= range_start, wavelength <= range_end)
            if np.count_nonzero(mask) >= 2 and absorbance_df.shape[1] >= 1:
                selected_indices = sorted(set([0, absorbance_df.shape[1] // 2, absorbance_df.shape[1] - 1]))
                colors = ["#1f77b4", "#ff7f0e", "#d62728"]
                for color, idx in zip(colors, selected_indices):
                    label = f"t={absorbance_df.columns[idx]} s"
                    ax_abs.plot(
                        wavelength[mask],
                        absorbance_df.iloc[:, idx].to_numpy(dtype=float)[mask],
                        linewidth=1.1,
                        color=color,
                        label=label,
                    )
                ax_abs.legend(loc="best", fontsize=8)
            else:
                ax_abs.text(0.5, 0.5, "Merged absorbance range unavailable", ha="center", va="center")
        else:
            ax_abs.text(0.5, 0.5, "Merged absorbance file not found", ha="center", va="center")
        ax_abs.set_xlabel("Wavelength [nm]")
        ax_abs.set_ylabel("Absorbance")
        ax_abs.set_title(f"Absorbance Snapshots ({range_start:.0f}-{range_end:.0f} nm)")
        ax_abs.grid(alpha=0.25)

        ax_qc = axes[1, 1]
        if df_qc is not None and not df_qc.empty:
            qc_time_h = pd.to_numeric(df_qc.get("elapsed_seconds", np.nan), errors="coerce").to_numpy(dtype=float) / 3600.0
            measurement_valid = pd.to_numeric(df_qc.get("measurement_valid", np.nan), errors="coerce").to_numpy(dtype=float)
            colors = np.where(measurement_valid > 0.5, "#2ca02c", "#d62728")
            ax_qc.scatter(qc_time_h, measurement_valid, c=colors, s=22, label="measurement_valid")
            ax_qc.set_ylim(-0.1, 1.1)
            ax_qc.set_yticks([0, 1])
            ax_qc.set_xlabel("Time [h]")
            ax_qc.set_ylabel("Measurement Valid")
            ax_qc.grid(alpha=0.25)
            valid_count = int(np.nansum(measurement_valid > 0.5))
            ax_qc.set_title(f"QC Summary ({valid_count}/{len(measurement_valid)} valid)")

            if "relative_diff" in df_qc.columns:
                relative_diff = pd.to_numeric(df_qc["relative_diff"], errors="coerce").to_numpy(dtype=float)
                qc_threshold = pd.to_numeric(df_qc.get("threshold", np.nan), errors="coerce").to_numpy(dtype=float)
                ax_qc_diff = ax_qc.twinx()
                ax_qc_diff.plot(qc_time_h, relative_diff, color="#ff7f0e", linewidth=1.3, alpha=0.9, label="relative_diff")
                finite_threshold = qc_threshold[np.isfinite(qc_threshold)]
                if finite_threshold.size > 0:
                    ax_qc_diff.axhline(
                        float(finite_threshold[0]),
                        color="#ff7f0e",
                        linestyle="--",
                        linewidth=1.0,
                        alpha=0.7,
                    )
                ax_qc_diff.set_ylabel("Relative Diff", color="#ff7f0e")
                ax_qc_diff.tick_params(axis='y', labelcolor="#ff7f0e")
        else:
            ax_qc.text(0.5, 0.5, "QC log not found", ha="center", va="center")
            ax_qc.set_title("QC Summary")
            ax_qc.set_xticks([])
            ax_qc.set_yticks([])

        if output_filename is None:
            figure_path = os.path.join(self.save_directory, sample_name + "_specdecay_summary.png")
        else:
            figure_path = output_filename if os.path.isabs(output_filename) else os.path.join(self.save_directory, output_filename)

        if save_to_file:
            fig.savefig(figure_path, dpi=figure_dpi, bbox_inches='tight')
            plt.close(fig)
            return (True, "Spectral decay summary figure saved to file: " + figure_path)

        plt.close(fig)
        return (True, "Spectral decay summary figure created but not saved to file")

    # hard coded for UV-Vis and NIR
    # what happens if only 1 spectrometer is connected/being used?
    def merge_absorbance(self, save_to_file: bool, filename: str, comment_list: List[str]) -> Tuple[bool, str]:
        result, merge_output = self.merge_uv_nir_absorbance_arrays(
            self.absorbance_dict['UV-Vis'],
            self.absorbance_dict['NIR'],
        )
        if not result:
            return (False, merge_output)

        self.merged_absorbance = merge_output["merged_array"]
        metadata = merge_output["metadata"]

        if save_to_file:
            os.makedirs(self.save_directory, exist_ok=True)
            data = pd.DataFrame()
            data['Wavelength'] = np.squeeze(self.merged_absorbance[:, 0].copy())
            data['Absorbance'] = np.squeeze(self.merged_absorbance[:, 1].copy())

            fullfilename = os.path.join(self.save_directory, filename + '_merged.csv')
            comment_list = list(comment_list)
            comment_list.append("# merge_method = qc_stitch_scale_only\n")
            comment_list.append("# merge_mode = " + str(metadata["merge_mode"]) + "\n")
            comment_list.append("# merge_reason = " + str(metadata["merge_reason"]) + "\n")
            comment_list.append("# crossover_nm = " + str(metadata["crossover_nm"]) + "\n")
            comment_list.append("# scale = " + str(metadata["scale"]) + "\n")
            comment_list.append("# shift = " + str(metadata["shift"]) + "\n")
            comment_list.append("# overlap_range_nm = " + str((metadata["overlap_start_nm"], metadata["overlap_end_nm"])) + "\n")
            comment_list.append("# uv_overlap_p95 = " + str(metadata["uv_overlap_p95"]) + "\n")
            comment_list.append("# best_raw_window_diff = " + str(metadata["best_raw_window_diff"]) + "\n")
            comment_list.append("# scale_only = " + str(metadata["scale_only"]) + "\n")
            comment_list.append("# scaled_median_diff = " + str(metadata["scaled_median_diff"]) + "\n")
            comment_list.append("# negative_values_clipped = " + str(metadata["negative_values_clipped"]) + "\n")
            with open(fullfilename, 'w') as file:
                file.writelines(comment_list)
            data.to_csv(fullfilename, mode='a', index_label='Index')

        return (
            True,
            "Successfully merged UV-Vis and NIR absorbance spectra using "
            + str(metadata["merge_mode"])
        )

    @staticmethod
    def _best_window_median_diff(
            wavelengths,
            y1,
            y2,
            window_nm: float,
            min_points: int = 5) -> Tuple[float, float]:
        best_diff = float('inf')
        best_wavelength = float('nan')
        for wavelength in wavelengths:
            window_index = np.abs(wavelengths - wavelength) <= window_nm
            if np.count_nonzero(window_index) < min_points:
                continue
            median_diff = float(np.median(np.abs(y1[window_index] - y2[window_index])))
            if median_diff < best_diff:
                best_diff = median_diff
                best_wavelength = float(wavelength)
        return best_diff, best_wavelength

    @staticmethod
    def _sanitize_absorbance_array(array) -> np.ndarray:
        clean_array = np.asarray(array, dtype=float)
        if clean_array.ndim != 2 or clean_array.shape[1] < 2:
            raise ValueError("Absorbance array must have at least two columns.")
        clean_array = clean_array[:, :2]
        valid_index = np.isfinite(clean_array[:, 0]) & np.isfinite(clean_array[:, 1])
        clean_array = clean_array[valid_index]
        return clean_array[clean_array[:, 0].argsort()]

    @staticmethod
    def merge_uv_nir_absorbance_arrays(uv_array, nir_array) -> Tuple[bool, Union[dict, str]]:
        try:
            uv_array = StellarNetSpectrometer._sanitize_absorbance_array(uv_array)
            nir_array = StellarNetSpectrometer._sanitize_absorbance_array(nir_array)
        except ValueError as exc:
            return (False, str(exc))

        overlap_start = StellarNetSpectrometer.MERGE_OVERLAP_START
        overlap_end = StellarNetSpectrometer.MERGE_OVERLAP_END
        overlap_index = (nir_array[:, 0] >= overlap_start) & (nir_array[:, 0] <= overlap_end)
        overlap_wavelength = nir_array[overlap_index, 0].copy()
        nir_overlap = nir_array[overlap_index, 1].copy()
        uv_overlap = StellarNetSpectrometer._linear_interpolate(
            uv_array[:, 0],
            uv_array[:, 1],
            overlap_wavelength,
        )

        valid_overlap = np.isfinite(overlap_wavelength) & np.isfinite(uv_overlap) & np.isfinite(nir_overlap)
        overlap_wavelength = overlap_wavelength[valid_overlap]
        uv_overlap = uv_overlap[valid_overlap]
        nir_overlap = nir_overlap[valid_overlap]

        metadata = {
            "merge_mode": "fixed_stitch_invalid_overlap",
            "merge_reason": "not enough valid overlap points",
            "overlap_start_nm": overlap_start,
            "overlap_end_nm": overlap_end,
            "window_nm": StellarNetSpectrometer.MERGE_WINDOW_NM,
            "raw_abs_tolerance": StellarNetSpectrometer.MERGE_RAW_ABS_TOLERANCE,
            "signal_min_p95": StellarNetSpectrometer.MERGE_SIGNAL_MIN_P95,
            "scale_min": StellarNetSpectrometer.MERGE_SCALE_MIN,
            "scale_max": StellarNetSpectrometer.MERGE_SCALE_MAX,
            "scale_fit_median_tolerance": StellarNetSpectrometer.MERGE_SCALE_FIT_MEDIAN_TOLERANCE,
            "uv_overlap_p95": float('nan'),
            "uv_overlap_median": float('nan'),
            "nir_overlap_p95": float('nan'),
            "best_raw_window_diff": float('inf'),
            "best_raw_window_nm": float('nan'),
            "scale_only": float('nan'),
            "scaled_median_diff": float('nan'),
            "best_scaled_window_diff": float('inf'),
            "best_scaled_window_nm": float('nan'),
            "scale": 1.0,
            "shift": 0.0,
            "crossover_nm": StellarNetSpectrometer.MERGE_FIXED_CROSSOVER_NM,
            "negative_values_clipped": 0,
        }

        if overlap_wavelength.size >= 10:
            uv_p95 = float(np.percentile(uv_overlap, 95))
            nir_p95 = float(np.percentile(nir_overlap, 95))
            raw_diff, raw_nm = StellarNetSpectrometer._best_window_median_diff(
                overlap_wavelength,
                uv_overlap,
                nir_overlap,
                StellarNetSpectrometer.MERGE_WINDOW_NM,
            )
            denom = float(np.sum(nir_overlap * nir_overlap))
            scale_only = float(np.sum(uv_overlap * nir_overlap) / denom) if denom > 0 else float('nan')
            scaled_overlap = nir_overlap * scale_only if np.isfinite(scale_only) else np.full_like(nir_overlap, np.nan)
            scaled_median_diff = (
                float(np.median(np.abs(uv_overlap - scaled_overlap)))
                if np.all(np.isfinite(scaled_overlap))
                else float('nan')
            )
            scaled_window_diff, scaled_nm = StellarNetSpectrometer._best_window_median_diff(
                overlap_wavelength,
                uv_overlap,
                scaled_overlap,
                StellarNetSpectrometer.MERGE_WINDOW_NM,
            )

            metadata.update({
                "uv_overlap_p95": uv_p95,
                "uv_overlap_median": float(np.median(uv_overlap)),
                "nir_overlap_p95": nir_p95,
                "best_raw_window_diff": raw_diff,
                "best_raw_window_nm": raw_nm,
                "scale_only": scale_only,
                "scaled_median_diff": scaled_median_diff,
                "best_scaled_window_diff": scaled_window_diff,
                "best_scaled_window_nm": scaled_nm,
            })

            if uv_p95 < StellarNetSpectrometer.MERGE_SIGNAL_MIN_P95:
                metadata.update({
                    "merge_mode": "fixed_stitch_low_overlap_signal",
                    "merge_reason": "UV overlap signal is too low for reliable fitting",
                    "crossover_nm": StellarNetSpectrometer.MERGE_FIXED_CROSSOVER_NM,
                    "scale": 1.0,
                    "shift": 0.0,
                })
            elif raw_diff <= StellarNetSpectrometer.MERGE_RAW_ABS_TOLERANCE:
                metadata.update({
                    "merge_mode": "raw_stitch",
                    "merge_reason": "raw UV and NIR spectra match within window tolerance",
                    "crossover_nm": raw_nm if np.isfinite(raw_nm) else StellarNetSpectrometer.MERGE_FIXED_CROSSOVER_NM,
                    "scale": 1.0,
                    "shift": 0.0,
                })
            elif (
                    np.isfinite(scale_only)
                    and StellarNetSpectrometer.MERGE_SCALE_MIN <= scale_only <= StellarNetSpectrometer.MERGE_SCALE_MAX
                    and scaled_median_diff <= StellarNetSpectrometer.MERGE_SCALE_FIT_MEDIAN_TOLERANCE):
                metadata.update({
                    "merge_mode": "scale_only_stitch",
                    "merge_reason": "raw spectra do not meet tolerance; scale-only fit is within bounds",
                    "crossover_nm": scaled_nm if np.isfinite(scaled_nm) else StellarNetSpectrometer.MERGE_FIXED_CROSSOVER_NM,
                    "scale": scale_only,
                    "shift": 0.0,
                })
            else:
                metadata.update({
                    "merge_mode": "fixed_stitch_unreliable_fit",
                    "merge_reason": "raw match and scale-only fit did not pass QC",
                    "crossover_nm": StellarNetSpectrometer.MERGE_FIXED_CROSSOVER_NM,
                    "scale": 1.0,
                    "shift": 0.0,
                })

        uv_part = StellarNetSpectrometer.truncate_ends_by_wavelength(
            uv_array,
            StellarNetSpectrometer.MERGE_UV_START,
            float(metadata["crossover_nm"]),
        )
        nir_adjusted = nir_array.copy()
        nir_adjusted[:, 1] = StellarNetSpectrometer.scale_shift_data(
            [float(metadata["scale"]), float(metadata["shift"])],
            nir_adjusted[:, 1],
        )
        nir_part = nir_adjusted[
            np.logical_and(
                nir_adjusted[:, 0] > float(metadata["crossover_nm"]),
                nir_adjusted[:, 0] < StellarNetSpectrometer.MERGE_NIR_END,
            )
        ]

        if uv_part.size == 0 or nir_part.size == 0:
            return (False, "Unable to stitch UV-Vis and NIR arrays with crossover " + str(metadata["crossover_nm"]))

        merged_array = np.vstack((uv_part, nir_part))
        merged_array = merged_array[merged_array[:, 0].argsort()]
        negative_index = merged_array[:, 1] < 0
        metadata["negative_values_clipped"] = int(np.count_nonzero(negative_index))
        merged_array[negative_index, 1] = 0.0

        return (True, {"merged_array": merged_array, "metadata": metadata})

    # y and return are ndarrays
    @staticmethod
    def scale_shift_data(params: List[float], y):
        scale = params[0]
        shift = params[1]
        return y * scale + shift
        # return (y + shift) * scale

    @staticmethod
    def truncate_ends_by_wavelength(array, start: float, end: float):
        # expects array to be two columns with first being wavelength and second being the data of interest (counts, absorbance, etc.)
        return array[np.logical_and(array[:,0]>start, array[:,0]<end)]

    @staticmethod
    def find_nearest(x, x0):
        ndx = np.abs(x - x0).argmin()
        return ndx, x[ndx]

    @staticmethod
    def merge_error(params, x1, y1, x2, y2, x_start, x_end):
        # y1 (UV-Vis) has higher resolution (2048) than y2 (NIR, 512)
        # so although we will adjust y2 to match y1, y1 will be interpolated onto x2
        # get the overlapped slice of the data that is not being interpolated (x2)
        x2_start_ndx = StellarNetSpectrometer.find_nearest(x2, x_start)[0]
        x2_end_ndx = StellarNetSpectrometer.find_nearest(x2, x_end)[0]
        x2_slice = x2[x2_start_ndx : x2_end_ndx].copy()
        # adjust y2
        new_y2 = StellarNetSpectrometer.scale_shift_data(params, y2)
        y2_slice = new_y2[x2_start_ndx : x2_end_ndx].copy()
        # get interpolated function of y1(x1)
        y1_interp = interp1d(x1, y1)
        # get y1 interpolated onto x2
        y1_slice = y1_interp(x2_slice)
        # calc error
        sum_squares = ((y1_slice - y2_slice) ** 2).sum()
        return sum_squares

    def servo_shutter_in(self):
        pass

    def servo_shutter_out(self):
        pass

    def lamp_relay_on(self):
        pass

    def lamp_relay_off(self):
        pass


# Considered making get_spectrum_counts generalized to accept either a single spectrometer (spec_key + params) 
# or any sized list of spec_keys + list of params.
# I ended up not doing it this way and making get_spectrum_counts take only 1 spectrometer
# Then I made a second function get_all_spectra_counts that calls get_spectrum_counts multiple times.
# My subsequent functions to get dark spectra, blank spectra, absorbance spectra then work with get_all_spectra_counts
# At first this seems more complicated. However, I did it to avoid list/tuple type checking and len() checking for every single param
# and because I wanted to avoid the following situation:
# 1) User gets dark and blank spectra for all spectrometers and proceeds to use them to get absorption spectras
# 2) Later, user needs needs to retake the dark/blank spectra but makes an error and uses the generalized methods for NOT all spectrometers
# 3) User proceeds to calculate all absorption spectra for all spectrometers
# In this case, not all spectrometers had their dark/blank spectra correctly retaken.
# The data is then incorrect for those spectrometers since they use the old dark/blank but the user has no idea this just happened.
# Another option is to null all spectrometer dark/blanks when even only retaking for 1 spectrometer, but requires implementing checks and error messages
# It is easier at the moment to just enforce all spectrometers are used all the time by writing methods that always use all spectrometers
# However, The "get_all_..." methods can generalize to 1 spectrometer based on the spec_keys arg passed during construction
