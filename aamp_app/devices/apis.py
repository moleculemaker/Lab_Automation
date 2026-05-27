import csv
import json
import os
import time
from decimal import Decimal, getcontext
from typing import Optional, Tuple

import cv2
import numpy as np

from .device import SerialDevice, check_initialized, check_serial
from .ximea_camera import XimeaCamera


class APIS(SerialDevice):
    """
    AAMP wrapper for the APIS Arduino controller.

    Python-side behavior is based on the public code in
    https://github.com/changhwang/APIS .
    Firmware and hardware details should be referenced from
    https://github.com/polyprintillinois/APIS .
    """

    SERIAL_BAUDRATE = 9600
    SERIAL_TIMEOUT_S = 0.5
    CONNECTION_WAIT_S = 2.0
    COMMAND_DELAY_S = 0.05
    SETTLING_TIME_S = 1.5
    MAX_RETRIES = 3

    SERVO_MIN_ANGLE = 0
    SERVO_MAX_ANGLE = 180

    POLARIZER_STAGE_TO_SERVO_RATIO = 1.059
    SAMPLE_STAGE_TO_SERVO_RATIO = 1.059
    POLARIZER_STAGE_DIRECTION = 1
    SAMPLE_STAGE_DIRECTION = 1
    POLARIZER_SERVO_ZERO_DEG = 0
    SAMPLE_SERVO_ZERO_DEG = 0
    POLARIZER_STAGE_MIN_ANGLE = 0.0
    SAMPLE_STAGE_MIN_ANGLE = 0.0
    POLARIZER_STAGE_MAX_ANGLE = (SERVO_MAX_ANGLE - POLARIZER_SERVO_ZERO_DEG) / POLARIZER_STAGE_TO_SERVO_RATIO
    SAMPLE_STAGE_MAX_ANGLE = (SERVO_MAX_ANGLE - SAMPLE_SERVO_ZERO_DEG) / SAMPLE_STAGE_TO_SERVO_RATIO

    CMD_POLARIZER = 10
    CMD_SAMPLE = 11
    CMD_HOME = 96
    CMD_RESET = 98
    CMD_ESTOP = 99

    STATE_LATCHED = "LATCHED"
    STATE_ARMED = "ARMED"

    XIMEA_DEFAULT_PPL_EXPOSURE_US = 18000
    XIMEA_DEFAULT_XPL_EXPOSURE_US = 400000
    XIMEA_DEFAULT_POLARIZER_CALIBRATION_EXPOSURE_US = 200000
    XIMEA_DEFAULT_NORMAL_EXPOSURE_US = XIMEA_DEFAULT_PPL_EXPOSURE_US
    XIMEA_DEFAULT_CROSSPOL_EXPOSURE_US = XIMEA_DEFAULT_XPL_EXPOSURE_US

    POLARIZER_PPL_ANGLE_DEG = 30
    POLARIZER_XPL_ANGLE_DEG = 120
    POLARIZER_CALIBRATION_FINE_RADIUS_DEG = 10
    POLARIZER_CALIBRATION_FINE_STEP_DEG = 1

    CAMERA_PREVIEW_WB_GAINS = (1.40, 1.00, 1.20)
    CAMERA_PREVIEW_GAMMA = 1.0 / 2.2

    def __init__(
        self,
        name: str,
        port: str,
        baudrate: int = SERIAL_BAUDRATE,
        timeout: Optional[float] = SERIAL_TIMEOUT_S,
        connection_wait_s: float = CONNECTION_WAIT_S,
        settling_time_s: float = SETTLING_TIME_S,
        command_delay_s: float = COMMAND_DELAY_S,
        max_retries: int = MAX_RETRIES,
        polarizer_stage_to_servo_ratio: float = POLARIZER_STAGE_TO_SERVO_RATIO,
        sample_stage_to_servo_ratio: float = SAMPLE_STAGE_TO_SERVO_RATIO,
        polarizer_stage_direction: int = POLARIZER_STAGE_DIRECTION,
        sample_stage_direction: int = SAMPLE_STAGE_DIRECTION,
        polarizer_servo_zero_deg: int = POLARIZER_SERVO_ZERO_DEG,
        sample_servo_zero_deg: int = SAMPLE_SERVO_ZERO_DEG,
        use_camera: bool = True,
        camera_save_directory: str = "data/imaging/",
        camera_bayer_pattern: str = XimeaCamera.DEFAULT_RAW_BAYER_PATTERN,
        camera_raw_max_value: float = XimeaCamera.DEFAULT_RAW_MAX_VALUE,
        polarizer_baseline_path: Optional[str] = None,
    ):
        super().__init__(name, port, baudrate, timeout)
        self._connection_wait_s = connection_wait_s
        self._settling_time_s = settling_time_s
        self._command_delay_s = command_delay_s
        self._max_retries = max_retries
        self._polarizer_stage_to_servo_ratio = polarizer_stage_to_servo_ratio
        self._sample_stage_to_servo_ratio = sample_stage_to_servo_ratio
        self._polarizer_stage_direction = polarizer_stage_direction
        self._sample_stage_direction = sample_stage_direction
        self._polarizer_servo_zero_deg = polarizer_servo_zero_deg
        self._sample_servo_zero_deg = sample_servo_zero_deg
        self._use_camera = use_camera
        self._camera_save_directory = camera_save_directory
        self._camera_bayer_pattern = camera_bayer_pattern
        self._camera_raw_max_value = camera_raw_max_value
        self._polarizer_baseline_path = polarizer_baseline_path

        self._state = self.STATE_LATCHED
        self._is_connected = False
        self._polarizer_angle = 0.0
        self._sample_angle = 0.0
        self._polarizer_xpl_angle_deg = self.POLARIZER_XPL_ANGLE_DEG
        self._polarizer_ppl_angle_deg = self.derive_ppl_angle_from_xpl(self._polarizer_xpl_angle_deg)
        self.load_polarizer_baseline()
        self.last_calibration_info = {}
        self.last_run_info = {}
        self.camera = XimeaCamera(name=f"{name}_camera") if use_camera else None
        if self.camera is not None:
            self.camera.save_directory = camera_save_directory

    def get_init_args(self) -> dict:
        return {
            "name": self._name,
            "port": self._port,
            "baudrate": self._baudrate,
            "timeout": self._timeout,
            "connection_wait_s": self._connection_wait_s,
            "settling_time_s": self._settling_time_s,
            "command_delay_s": self._command_delay_s,
            "max_retries": self._max_retries,
            "polarizer_stage_to_servo_ratio": self._polarizer_stage_to_servo_ratio,
            "sample_stage_to_servo_ratio": self._sample_stage_to_servo_ratio,
            "polarizer_stage_direction": self._polarizer_stage_direction,
            "sample_stage_direction": self._sample_stage_direction,
            "polarizer_servo_zero_deg": self._polarizer_servo_zero_deg,
            "sample_servo_zero_deg": self._sample_servo_zero_deg,
            "use_camera": self._use_camera,
            "camera_save_directory": self._camera_save_directory,
            "camera_bayer_pattern": self._camera_bayer_pattern,
            "camera_raw_max_value": self._camera_raw_max_value,
            "polarizer_baseline_path": self._polarizer_baseline_path,
        }

    def update_init_args(self, args_dict: dict):
        self._name = args_dict["name"]
        self._port = args_dict["port"]
        self._baudrate = args_dict["baudrate"]
        self._timeout = args_dict["timeout"]
        self._connection_wait_s = args_dict["connection_wait_s"]
        self._settling_time_s = args_dict["settling_time_s"]
        self._command_delay_s = args_dict["command_delay_s"]
        self._max_retries = args_dict["max_retries"]
        self._polarizer_stage_to_servo_ratio = args_dict["polarizer_stage_to_servo_ratio"]
        self._sample_stage_to_servo_ratio = args_dict["sample_stage_to_servo_ratio"]
        self._polarizer_stage_direction = args_dict["polarizer_stage_direction"]
        self._sample_stage_direction = args_dict["sample_stage_direction"]
        self._polarizer_servo_zero_deg = args_dict["polarizer_servo_zero_deg"]
        self._sample_servo_zero_deg = args_dict["sample_servo_zero_deg"]
        self._use_camera = args_dict["use_camera"]
        self._camera_save_directory = args_dict["camera_save_directory"]
        self._camera_bayer_pattern = args_dict["camera_bayer_pattern"]
        self._camera_raw_max_value = args_dict["camera_raw_max_value"]
        self._polarizer_baseline_path = args_dict.get("polarizer_baseline_path")
        self.load_polarizer_baseline()
        self.camera = XimeaCamera(name=f"{self._name}_camera") if self._use_camera else None
        if self.camera is not None:
            self.camera.save_directory = self._camera_save_directory

    @property
    def state(self) -> str:
        return self._state

    @property
    def polarizer_angle(self) -> float:
        return self._polarizer_angle

    @property
    def sample_angle(self) -> float:
        return self._sample_angle

    @property
    def xpl_angle(self) -> float:
        return self._polarizer_xpl_angle_deg

    @property
    def ppl_angle(self) -> float:
        return self._polarizer_ppl_angle_deg

    def connect(self) -> Tuple[bool, str]:
        was_successful, response = self.start_serial(delay=2.0)
        if not was_successful:
            self._is_connected = False
            return (was_successful, response)

        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

        start_t = time.time()
        while (time.time() - start_t) < self._connection_wait_s:
            if self.ser.in_waiting:
                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                if line == "READY":
                    self._is_connected = True
                    self._state = self.STATE_LATCHED
                    return (True, "APIS connected. Arduino boot message READY received; state is LATCHED.")
            time.sleep(0.1)

        was_successful, response = self._send_raw_command(self.CMD_RESET, 0)
        if was_successful and "OK RESET" in response:
            self._is_connected = True
            self._state = self.STATE_ARMED
            return (True, "APIS connected without READY handshake; force RESET succeeded and system is ARMED.")

        self._is_connected = False
        return (False, "APIS connection failed. No READY received and RESET fallback failed: " + response)

    @check_serial
    def initialize(self) -> Tuple[bool, str]:
        if not self._is_connected:
            return (False, "APIS is not connected. Run connect first.")
        was_successful, response = self.reset()
        if not was_successful:
            self._is_initialized = False
            return (was_successful, response)
        if self.camera is not None:
            was_successful, response = self.camera.initialize(set_defaults=True)
            if not was_successful:
                self._is_initialized = False
                return (was_successful, response)
            self.camera.save_directory = self._camera_save_directory
        self._is_initialized = True
        return (
            True,
            "Successfully initialized APIS and armed the controller. "
            + "For firmware and hardware details, see https://github.com/polyprintillinois/APIS .",
        )

    def deinitialize(self) -> Tuple[bool, str]:
        if self.camera is not None and self.camera.is_initialized:
            self.camera.deinitialize(reset_init_flag=True)
        if self.ser.is_open:
            self.emergency_stop()
            self.ser.close()
        self._is_initialized = False
        self._is_connected = False
        self._state = self.STATE_LATCHED
        return (True, "Successfully deinitialized APIS, sent ESTOP, and closed the serial port.")

    def _format_command(self, pp: int, aaa: int) -> str:
        return f"{int(pp):02d}{int(aaa):03d}"

    def _send_raw_command(self, pp: int, aaa: int) -> Tuple[bool, str]:
        if not self.ser or not self.ser.is_open:
            return (False, "ERR NO_CONNECTION")

        cmd_str = self._format_command(pp, aaa)
        attempt = 0
        while attempt < self._max_retries:
            try:
                self.ser.reset_input_buffer()
                self.ser.write((cmd_str + "\n").encode("utf-8"))
                self.ser.flush()
                response = self.ser.readline().decode("utf-8", errors="ignore").strip()
                if not response:
                    attempt += 1
                    time.sleep(0.2 * (2 ** max(0, attempt - 1)))
                    continue
                time.sleep(self._command_delay_s)
                return (True, response)
            except Exception as exc:
                return (False, "ERR EXCEPTION " + str(exc))

        return (False, "ERR TIMEOUT")

    def _send_command(self, pp: int, aaa: int) -> Tuple[bool, str]:
        was_successful, response = self._send_raw_command(pp, aaa)
        if not was_successful:
            return (False, response)
        if not response.startswith("OK"):
            return (False, response)
        return (True, response)

    @check_initialized
    @check_serial
    def emergency_stop(self) -> Tuple[bool, str]:
        was_successful, response = self._send_command(self.CMD_ESTOP, 0)
        if was_successful:
            self._state = self.STATE_LATCHED
        return (was_successful, response)

    @check_serial
    def reset(self) -> Tuple[bool, str]:
        was_successful, response = self._send_command(self.CMD_RESET, 0)
        if was_successful:
            self._state = self.STATE_ARMED
        return (was_successful, response)

    def _stage_to_servo_angle(
        self,
        stage_angle: float,
        ratio: float,
        direction: int,
        zero_offset: int,
        axis_name: str,
    ) -> Tuple[bool, int]:
        servo_angle = zero_offset + (direction * stage_angle * ratio)
        servo_cmd = int(round(servo_angle))
        if servo_cmd < self.SERVO_MIN_ANGLE or servo_cmd > self.SERVO_MAX_ANGLE:
            return (
                False,
                f"{axis_name} angle {stage_angle:.2f} deg maps to servo command {servo_cmd}, outside {self.SERVO_MIN_ANGLE}-{self.SERVO_MAX_ANGLE}.",
            )
        return (True, servo_cmd)

    @check_initialized
    @check_serial
    def home(self) -> Tuple[bool, str]:
        was_successful, response = self.rotate_polarizer(0.0)
        if not was_successful:
            return (was_successful, response)
        return self.rotate_sample(0.0)

    @check_initialized
    @check_serial
    def rotate_polarizer(self, angle_deg: float) -> Tuple[bool, str]:
        if angle_deg < self.POLARIZER_STAGE_MIN_ANGLE or angle_deg > self.POLARIZER_STAGE_MAX_ANGLE:
            return (
                False,
                f"Polarizer angle {angle_deg:.2f} deg is outside the allowed stage range 0-{self.POLARIZER_STAGE_MAX_ANGLE:.2f} deg.",
            )
        was_successful, servo_cmd = self._stage_to_servo_angle(
            angle_deg,
            self._polarizer_stage_to_servo_ratio,
            self._polarizer_stage_direction,
            self._polarizer_servo_zero_deg,
            "Polarizer",
        )
        if not was_successful:
            return (False, servo_cmd)
        was_successful, response = self._send_command(self.CMD_POLARIZER, servo_cmd)
        if was_successful:
            self._polarizer_angle = angle_deg
            time.sleep(self._settling_time_s)
        return (was_successful, response)

    @check_initialized
    @check_serial
    def rotate_sample(self, angle_deg: float) -> Tuple[bool, str]:
        if angle_deg < self.SAMPLE_STAGE_MIN_ANGLE or angle_deg > self.SAMPLE_STAGE_MAX_ANGLE:
            return (
                False,
                f"Sample angle {angle_deg:.2f} deg is outside the allowed stage range 0-{self.SAMPLE_STAGE_MAX_ANGLE:.2f} deg.",
            )
        was_successful, servo_cmd = self._stage_to_servo_angle(
            angle_deg,
            self._sample_stage_to_servo_ratio,
            self._sample_stage_direction,
            self._sample_servo_zero_deg,
            "Sample",
        )
        if not was_successful:
            return (False, servo_cmd)
        was_successful, response = self._send_command(self.CMD_SAMPLE, servo_cmd)
        if was_successful:
            self._sample_angle = angle_deg
            time.sleep(self._settling_time_s)
        return (was_successful, response)

    @check_initialized
    @check_serial
    def get_state(self) -> Tuple[bool, str]:
        return (True, self._state)

    @check_initialized
    def get_polarizer_angle(self) -> Tuple[bool, float]:
        return (True, self._polarizer_angle)

    @check_initialized
    def get_sample_angle(self) -> Tuple[bool, float]:
        return (True, self._sample_angle)

    @staticmethod
    def choose_orthogonal_polarizer_angle(
        xpl_angle: float,
        min_angle: float = POLARIZER_STAGE_MIN_ANGLE,
        max_angle: float = POLARIZER_STAGE_MAX_ANGLE,
        prefer_positive: bool = True,
    ) -> Tuple[int, int]:
        xpl_angle = int(round(xpl_angle))
        min_angle = int(min_angle)
        max_angle = int(max_angle)
        offsets = (90, -90) if prefer_positive else (-90, 90)
        for offset in offsets:
            candidate = xpl_angle + offset
            if min_angle <= candidate <= max_angle:
                return (candidate, offset)
        raise ValueError(
            f"No valid PPL angle for XPL={xpl_angle} deg within range {min_angle}-{max_angle}."
        )

    @classmethod
    def derive_ppl_angle_from_xpl(cls, xpl_angle: float, prefer_positive: bool = True) -> int:
        ppl_angle, _ = cls.choose_orthogonal_polarizer_angle(
            xpl_angle,
            cls.POLARIZER_STAGE_MIN_ANGLE,
            cls.POLARIZER_STAGE_MAX_ANGLE,
            prefer_positive=prefer_positive,
        )
        return ppl_angle

    @staticmethod
    def build_angle_window(
        center_angle: float,
        radius: int,
        min_angle: float,
        max_angle: float,
        step: int = 1,
    ) -> list:
        if step <= 0:
            raise ValueError("Angle window step must be positive.")
        start = max(int(min_angle), int(round(center_angle)) - int(radius))
        end = min(int(max_angle), int(round(center_angle)) + int(radius))
        return list(range(start, end + 1, int(step)))

    @staticmethod
    def parse_angle_spec(angle_spec, min_angle: float, max_angle: float) -> Tuple[list, str]:
        if angle_spec is None:
            return ([], "Angles are empty.")
        if isinstance(angle_spec, str):
            raw = angle_spec.strip()
            if not raw:
                return ([], "Angles are empty.")
            parts = [p for p in raw.replace(",", " ").split() if p]
        else:
            parts = list(angle_spec)

        angles = []
        for part in parts:
            token = str(part).strip()
            if ":" in token:
                nums = token.split(":")
                if len(nums) not in (2, 3):
                    return ([], f"Invalid range token: '{token}'")
                try:
                    start = int(nums[0])
                    end = int(nums[1])
                    step = int(nums[2]) if len(nums) == 3 else 1
                except ValueError:
                    return ([], f"Invalid range token: '{token}'")
                if step == 0:
                    return ([], f"Step cannot be 0 in '{token}'")
                if start < min_angle or start > max_angle or end < min_angle or end > max_angle:
                    return ([], f"Range out of bounds ({min_angle}-{max_angle}): '{token}'")
                stop = end + 1 if step > 0 else end - 1
                angles.extend(list(range(start, stop, step)))
            else:
                try:
                    value = int(float(token))
                except ValueError:
                    return ([], f"Invalid angle token: '{token}'")
                if value < min_angle or value > max_angle:
                    return ([], f"Angle out of bounds ({min_angle}-{max_angle}): '{token}'")
                angles.append(value)

        if not angles:
            return ([], "No valid angles found.")
        return (angles, "")

    def _get_polarizer_baseline_path(self) -> str:
        return self._polarizer_baseline_path or os.path.join("data", "polarizer_baseline.json")

    def load_polarizer_baseline(self) -> Tuple[bool, str]:
        baseline_path = self._get_polarizer_baseline_path()
        if not os.path.isfile(baseline_path):
            return (
                True,
                f"Using default APIS polarizer baseline: XPL={self._polarizer_xpl_angle_deg} deg, "
                f"PPL={self._polarizer_ppl_angle_deg} deg.",
            )

        try:
            with open(baseline_path, "r", encoding="utf-8") as file_obj:
                baseline = json.load(file_obj)
            xpl_angle_deg = baseline["xpl_angle_deg"]
        except Exception as exc:
            return (False, f"Failed to load APIS polarizer baseline from {baseline_path}: {exc}")

        was_successful, response = self.set_polarizer_baseline(
            xpl_angle_deg,
            persist=False,
            source="saved baseline",
        )
        if not was_successful:
            return (False, response)
        return (True, f"Loaded APIS polarizer baseline from {baseline_path}. {response}")

    def save_polarizer_baseline(self, source: str = "manual") -> Tuple[bool, str]:
        baseline_path = self._get_polarizer_baseline_path()
        payload = {
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "source": source,
            "xpl_angle_deg": int(self._polarizer_xpl_angle_deg),
            "ppl_angle_deg": int(self._polarizer_ppl_angle_deg),
            "ppl_offset_deg": int(self._polarizer_ppl_angle_deg - self._polarizer_xpl_angle_deg),
        }
        try:
            os.makedirs(os.path.dirname(baseline_path) or ".", exist_ok=True)
            with open(baseline_path, "w", encoding="utf-8") as file_obj:
                json.dump(payload, file_obj, indent=2)
        except Exception as exc:
            return (False, f"Failed to save APIS polarizer baseline to {baseline_path}: {exc}")
        return (True, f"Saved APIS polarizer baseline to {baseline_path}.")

    def set_polarizer_baseline(
        self,
        xpl_angle_deg: float,
        persist: bool = False,
        source: str = "manual",
    ) -> Tuple[bool, str]:
        if xpl_angle_deg < self.POLARIZER_STAGE_MIN_ANGLE or xpl_angle_deg > self.POLARIZER_STAGE_MAX_ANGLE:
            return (
                False,
                f"XPL angle {xpl_angle_deg:.2f} deg is outside the allowed polarizer range "
                f"{self.POLARIZER_STAGE_MIN_ANGLE}-{self.POLARIZER_STAGE_MAX_ANGLE:.2f} deg.",
            )
        try:
            ppl_angle, offset = self.choose_orthogonal_polarizer_angle(
                xpl_angle_deg,
                self.POLARIZER_STAGE_MIN_ANGLE,
                self.POLARIZER_STAGE_MAX_ANGLE,
            )
        except ValueError as exc:
            return (False, str(exc))

        self._polarizer_xpl_angle_deg = int(round(xpl_angle_deg))
        self._polarizer_ppl_angle_deg = int(ppl_angle)
        persist_msg = ""
        if persist:
            was_successful, persist_msg = self.save_polarizer_baseline(source=source)
            if not was_successful:
                return (False, persist_msg)
            persist_msg = " " + persist_msg
        return (
            True,
            f"APIS polarizer baseline set: XPL={self._polarizer_xpl_angle_deg} deg, "
            f"PPL=XPL{offset:+d} -> {self._polarizer_ppl_angle_deg} deg.{persist_msg}",
        )

    @check_initialized
    @check_serial
    def rotate_xpl(self) -> Tuple[bool, str]:
        return self.rotate_polarizer(self._polarizer_xpl_angle_deg)

    @check_initialized
    @check_serial
    def rotate_ppl(self) -> Tuple[bool, str]:
        return self.rotate_polarizer(self._polarizer_ppl_angle_deg)

    @staticmethod
    def format_speed(speed: float) -> str:
        getcontext().prec = 50
        speed_dec = Decimal(str(speed))
        if speed_dec == 0:
            return "0"
        if speed_dec >= 1 and speed_dec == speed_dec.to_integral_value():
            return f"{int(speed_dec)}"
        integer_part = "".join(map(str, speed_dec.as_tuple().digits))
        exponent = speed_dec.as_tuple().exponent
        return f"{integer_part}E{exponent}"

    @classmethod
    def build_sample_basename(
        cls,
        round_num,
        sample_num,
        polymer: str,
        solvent: str,
        concentration: int,
        speed: float,
        temperature: int,
        gap: int,
        volume: int,
    ) -> str:
        speed_str = cls.format_speed(speed)
        return (
            f"R{round_num}S{sample_num}_{polymer}_{solvent}_{concentration}mgml_"
            f"{speed_str}mms_{temperature}C_{gap}um_{volume}ul"
        )

    @staticmethod
    def resolve_mode_directory(root_save_dir: str, polymer: str, mode: str) -> str:
        mode_dir = os.path.join(root_save_dir, polymer, mode)
        os.makedirs(mode_dir, exist_ok=True)
        return mode_dir

    @staticmethod
    def build_mode_filename(base_sample_name: str, mode: str, angle_deg: float) -> str:
        return f"{base_sample_name}_{mode}_{int(angle_deg)}deg"

    @staticmethod
    def _append_calibration_log(log_path: str, row: dict) -> None:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        fieldnames = [
            "timestamp",
            "mode",
            "exposure_us",
            "gain",
            "polarizer_angle",
            "sample_angle",
            "signal_mean",
            "filepath",
            "arduino_response",
            "attempt_count",
        ]
        file_exists = os.path.isfile(log_path)
        with open(log_path, mode="a", newline="", encoding="utf-8") as file_obj:
            writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({key: row.get(key, "") for key in fieldnames})

    @staticmethod
    def _write_json(filepath: str, data: dict) -> None:
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as file_obj:
            json.dump(data, file_obj, indent=2)

    def _capture_imaging_phase(
        self,
        *,
        mode_name: str,
        display_name: str,
        sample_angles,
        exposure_time: int,
        polarizer_angle: float,
        output_dir: str,
        sample_id: str,
        log_path: str,
        metadata: dict,
        gain: float,
    ) -> Tuple[bool, str]:
        os.makedirs(output_dir, exist_ok=True)

        was_successful, response = self.rotate_polarizer(polarizer_angle)
        if not was_successful:
            return (False, f"Failed to move Polarizer to {polarizer_angle}: {response}")

        for angle in sample_angles:
            was_successful, response = self.rotate_sample(angle)
            if not was_successful and mode_name == "xpl":
                was_successful, response = self.rotate_sample(angle)
            if not was_successful:
                return (False, f"Failed to move Sample to {angle}: {response}")

            filename = f"{sample_id}_{mode_name}_{int(angle):03d}"
            image_path = os.path.join(output_dir, filename + ".tif")
            was_successful, response = self.camera.capture_raw16(
                save_to_file=True,
                filename=filename,
                directory=output_dir,
                exposure_time=exposure_time,
                gain=gain,
            )
            if not was_successful:
                return (False, response)

            timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
            self._append_calibration_log(
                log_path,
                {
                    "timestamp": timestamp,
                    "mode": mode_name,
                    "exposure_us": exposure_time,
                    "gain": gain,
                    "polarizer_angle": polarizer_angle,
                    "sample_angle": angle,
                    "filepath": image_path,
                    "arduino_response": "OK",
                    "attempt_count": 1,
                },
            )
            metadata["images"].append(
                {
                    "filename": os.path.basename(image_path),
                    "mode": mode_name,
                    "display_name": display_name,
                    "polarizer_angle_deg": polarizer_angle,
                    "sample_angle_deg": angle,
                    "exposure_us": exposure_time,
                    "filepath": image_path,
                    "timestamp": timestamp,
                }
            )

        return (True, f"{display_name} capture complete.")

    @check_initialized
    @check_serial
    def run_imaging_sequence(
        self,
        sample_id: str,
        directory: Optional[str] = None,
        sample_angles=None,
        xpl_exposure_time: int = XIMEA_DEFAULT_XPL_EXPOSURE_US,
        ppl_exposure_time: int = XIMEA_DEFAULT_PPL_EXPOSURE_US,
        do_xpl: bool = True,
        do_ppl: bool = True,
        xpl_polarizer_angle: Optional[float] = None,
        ppl_polarizer_angle: Optional[float] = None,
        gain: float = 0.0,
    ) -> Tuple[bool, str]:
        if self.camera is None:
            return (False, "APIS camera support is disabled for this device instance.")
        if not (do_xpl or do_ppl):
            return (False, "No modes enabled for APIS imaging sequence.")
        if sample_angles is None:
            sample_angles = [90, 60, 45, 30, 0]
        sample_angles, angle_error = self.parse_angle_spec(
            sample_angles,
            self.SAMPLE_STAGE_MIN_ANGLE,
            self.SAMPLE_STAGE_MAX_ANGLE,
        )
        if not sample_angles:
            return (False, angle_error)

        xpl_angle = self._polarizer_xpl_angle_deg if xpl_polarizer_angle is None else xpl_polarizer_angle
        ppl_angle = self._polarizer_ppl_angle_deg if ppl_polarizer_angle is None else ppl_polarizer_angle
        save_root = directory or self._camera_save_directory
        sample_root = os.path.join(save_root, sample_id)
        log_path = os.path.join(sample_root, f"{sample_id}_log.csv")
        metadata_path = os.path.join(sample_root, f"{sample_id}_metadata.json")
        metadata = {
            "sample_id": sample_id,
            "sequence_started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "sequence_completed": False,
            "error_message": "",
            "save_root": save_root,
            "mode_angles_deg": {
                "xpl": xpl_angle if do_xpl else None,
                "ppl": ppl_angle if do_ppl else None,
            },
            "images": [],
        }
        run_info = {
            "saved_frame_count": 0,
            "sequence_completed": False,
            "body_error": "",
            "metadata_path": metadata_path,
        }

        try:
            was_successful, response = self.reset()
            if not was_successful:
                raise RuntimeError(response)

            if do_xpl:
                was_successful, response = self._capture_imaging_phase(
                    mode_name="xpl",
                    display_name="XPL",
                    sample_angles=sample_angles,
                    exposure_time=xpl_exposure_time,
                    polarizer_angle=xpl_angle,
                    output_dir=os.path.join(sample_root, "xpl"),
                    sample_id=sample_id,
                    log_path=log_path,
                    metadata=metadata,
                    gain=gain,
                )
                if not was_successful:
                    raise RuntimeError(response)

            if do_ppl:
                was_successful, response = self._capture_imaging_phase(
                    mode_name="ppl",
                    display_name="PPL",
                    sample_angles=sample_angles,
                    exposure_time=ppl_exposure_time,
                    polarizer_angle=ppl_angle,
                    output_dir=os.path.join(sample_root, "ppl"),
                    sample_id=sample_id,
                    log_path=log_path,
                    metadata=metadata,
                    gain=gain,
                )
                if not was_successful:
                    raise RuntimeError(response)

            self.home()
            metadata["sequence_completed"] = True
            run_info["sequence_completed"] = True
        except Exception as exc:
            metadata["error_message"] = str(exc)
            run_info["body_error"] = str(exc)
            try:
                self.emergency_stop()
            except Exception:
                pass
        finally:
            run_info["saved_frame_count"] = len(metadata["images"])
            metadata["saved_frame_count"] = len(metadata["images"])
            try:
                self._write_json(metadata_path, metadata)
            except Exception as exc:
                run_info["body_error"] = run_info["body_error"] or str(exc)
                metadata["error_message"] = metadata["error_message"] or str(exc)
            self.last_run_info = run_info

        if run_info["body_error"]:
            return (False, "APIS imaging sequence failed: " + run_info["body_error"])
        return (
            True,
            f"APIS imaging sequence complete. Saved {run_info['saved_frame_count']} frame(s). "
            f"Metadata: {metadata_path}",
        )

    def _capture_polarizer_scan(
        self,
        *,
        sample_id: str,
        exposure_time: int,
        gain: float,
        sample_angle: float,
        polarizer_angles,
        scan_phase: str,
        output_dir: str,
        log_path: str,
    ) -> Tuple[bool, object]:
        results = []
        for angle in polarizer_angles:
            was_successful, response = self.rotate_polarizer(float(angle))
            if not was_successful:
                return (False, response)

            filename = f"{sample_id}_polarizer_cal_{scan_phase}_{int(angle):03d}"
            image_path = os.path.join(output_dir, filename + ".tif")
            was_successful, response = self.camera.capture_raw16(
                save_to_file=True,
                filename=filename,
                directory=output_dir,
                exposure_time=exposure_time,
                gain=gain,
            )
            if not was_successful:
                return (False, response)

            image_data = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            if image_data is None:
                return (False, f"Failed to read calibration image: {image_path}")
            signal_mean = float(np.asarray(image_data, dtype=np.float32).mean())
            row = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "mode": "polarizer_calibration",
                "exposure_us": exposure_time,
                "gain": gain,
                "polarizer_angle": angle,
                "sample_angle": sample_angle,
                "signal_mean": signal_mean,
                "filepath": image_path,
                "arduino_response": scan_phase.upper(),
                "attempt_count": 1,
            }
            self._append_calibration_log(log_path, row)
            results.append(
                {
                    "filename": os.path.basename(image_path),
                    "scan_phase": scan_phase,
                    "polarizer_angle_deg": int(angle),
                    "sample_angle_deg": sample_angle,
                    "exposure_us": exposure_time,
                    "mean_signal": signal_mean,
                    "filepath": image_path,
                    "timestamp": row["timestamp"],
                }
            )
        return (True, results)

    @check_initialized
    @check_serial
    def run_polarizer_calibration(
        self,
        sample_id: str = "polarizer_calibration",
        directory: Optional[str] = None,
        exposure_time: int = XIMEA_DEFAULT_POLARIZER_CALIBRATION_EXPOSURE_US,
        polarizer_angles=None,
        sample_angle: float = 0.0,
        fine_radius_deg: int = POLARIZER_CALIBRATION_FINE_RADIUS_DEG,
        fine_step_deg: int = POLARIZER_CALIBRATION_FINE_STEP_DEG,
        gain: float = 0.0,
    ) -> Tuple[bool, str]:
        if self.camera is None:
            return (False, "APIS camera support is disabled for this device instance.")

        if polarizer_angles is None:
            polarizer_angles = f"{int(self.POLARIZER_STAGE_MIN_ANGLE)}:{int(self.POLARIZER_STAGE_MAX_ANGLE)}:5"
        polarizer_angles, angle_error = self.parse_angle_spec(
            polarizer_angles,
            self.POLARIZER_STAGE_MIN_ANGLE,
            self.POLARIZER_STAGE_MAX_ANGLE,
        )
        if not polarizer_angles:
            return (False, angle_error)

        sample_root = os.path.join(directory or self._camera_save_directory, sample_id)
        calibration_dir = os.path.join(sample_root, "polarizer_calibration")
        log_path = os.path.join(sample_root, f"{sample_id}_log.csv")
        metadata_path = os.path.join(sample_root, f"{sample_id}_polarizer_calibration.json")
        os.makedirs(calibration_dir, exist_ok=True)

        metadata = {
            "sample_id": sample_id,
            "capture_type": "polarizer_calibration",
            "calibration_sample_angle_deg": sample_angle,
            "coarse_scan_angles_deg": list(polarizer_angles),
            "fine_radius_deg": fine_radius_deg,
            "fine_step_deg": fine_step_deg,
            "exposure_us": exposure_time,
            "gain": gain,
            "images": [],
            "scan_results": [],
            "sequence_completed": False,
            "error_message": "",
        }

        try:
            was_successful, response = self.reset()
            if not was_successful:
                raise RuntimeError(response)

            was_successful, response = self.rotate_sample(sample_angle)
            if not was_successful:
                raise RuntimeError(response)

            was_successful, coarse_results = self._capture_polarizer_scan(
                sample_id=sample_id,
                exposure_time=exposure_time,
                gain=gain,
                sample_angle=sample_angle,
                polarizer_angles=polarizer_angles,
                scan_phase="coarse",
                output_dir=calibration_dir,
                log_path=log_path,
            )
            if not was_successful:
                raise RuntimeError(coarse_results)

            metadata["scan_results"].extend(coarse_results)
            metadata["images"].extend(coarse_results)
            coarse_xpl = min(
                coarse_results,
                key=lambda item: (item["mean_signal"], item["polarizer_angle_deg"]),
            )
            fine_angles = self.build_angle_window(
                coarse_xpl["polarizer_angle_deg"],
                fine_radius_deg,
                self.POLARIZER_STAGE_MIN_ANGLE,
                self.POLARIZER_STAGE_MAX_ANGLE,
                fine_step_deg,
            )
            metadata["coarse_darkest_angle_deg"] = coarse_xpl["polarizer_angle_deg"]
            metadata["coarse_darkest_signal_mean"] = coarse_xpl["mean_signal"]
            metadata["fine_scan_angles_deg"] = fine_angles

            was_successful, fine_results = self._capture_polarizer_scan(
                sample_id=sample_id,
                exposure_time=exposure_time,
                gain=gain,
                sample_angle=sample_angle,
                polarizer_angles=fine_angles,
                scan_phase="fine",
                output_dir=calibration_dir,
                log_path=log_path,
            )
            if not was_successful:
                raise RuntimeError(fine_results)

            metadata["scan_results"].extend(fine_results)
            metadata["images"].extend(fine_results)
            xpl_candidate = min(
                fine_results,
                key=lambda item: (item["mean_signal"], item["polarizer_angle_deg"]),
            )
            was_successful, response = self.set_polarizer_baseline(
                xpl_candidate["polarizer_angle_deg"],
                persist=True,
                source="calibration baseline",
            )
            if not was_successful:
                raise RuntimeError(response)

            _, ppl_offset = self.choose_orthogonal_polarizer_angle(self._polarizer_xpl_angle_deg)
            metadata["recommended_xpl_angle_deg"] = self._polarizer_xpl_angle_deg
            metadata["recommended_ppl_angle_deg"] = self._polarizer_ppl_angle_deg
            metadata["recommended_ppl_offset_deg"] = ppl_offset
            metadata["xpl_signal_mean"] = xpl_candidate["mean_signal"]
            metadata["sequence_completed"] = True

            self.home()
            self.last_calibration_info = metadata
            with open(metadata_path, "w", encoding="utf-8") as file_obj:
                json.dump(metadata, file_obj, indent=2)

            return (
                True,
                "Polarizer calibration complete. "
                f"XPL={self._polarizer_xpl_angle_deg} deg, "
                f"PPL={self._polarizer_ppl_angle_deg} deg. Metadata: {metadata_path}",
            )
        except Exception as exc:
            metadata["error_message"] = str(exc)
            self.last_calibration_info = metadata
            try:
                with open(metadata_path, "w", encoding="utf-8") as file_obj:
                    json.dump(metadata, file_obj, indent=2)
            except Exception:
                pass
            try:
                self.emergency_stop()
            except Exception:
                pass
            return (False, "Polarizer calibration failed: " + str(exc))

    def _resolve_capture_directory(self, directory: Optional[str], mode_subdir: Optional[str] = None) -> str:
        base_dir = directory or self._camera_save_directory
        if mode_subdir:
            base_dir = os.path.join(base_dir, mode_subdir)
        os.makedirs(base_dir, exist_ok=True)
        return base_dir

    @check_initialized
    def capture_raw16(
        self,
        filename: Optional[str] = None,
        directory: Optional[str] = None,
        exposure_time: Optional[int] = None,
        gain: float = 0.0,
    ) -> Tuple[bool, str]:
        if self.camera is None:
            return (False, "APIS camera support is disabled for this device instance.")
        return self.camera.capture_raw16(
            save_to_file=True,
            filename=filename,
            directory=self._resolve_capture_directory(directory, "raw16"),
            exposure_time=exposure_time,
            gain=gain,
        )

    @check_initialized
    def capture_rgb(
        self,
        filename: Optional[str] = None,
        directory: Optional[str] = None,
        exposure_time: Optional[int] = None,
        gain: float = 0.0,
    ) -> Tuple[bool, str]:
        if self.camera is None:
            return (False, "APIS camera support is disabled for this device instance.")
        return self.camera.capture_rgb_no_correction(
            save_to_file=True,
            filename=filename,
            directory=self._resolve_capture_directory(directory, "rgb"),
            exposure_time=exposure_time,
            gain=gain,
            bayer_pattern=self._camera_bayer_pattern,
            raw_max_value=self._camera_raw_max_value,
            wb_gains=self.CAMERA_PREVIEW_WB_GAINS,
            gamma=self.CAMERA_PREVIEW_GAMMA,
        )

    @check_initialized
    def convert_raw16_to_rgb(
        self,
        raw16_path: str,
        rgb_path: Optional[str] = None,
    ) -> Tuple[bool, str]:
        return XimeaCamera.convert_saved_raw16_to_rgb(
            raw16_path=raw16_path,
            rgb_path=rgb_path,
            bayer_pattern=self._camera_bayer_pattern,
            raw_max_value=self._camera_raw_max_value,
            wb_gains=self.CAMERA_PREVIEW_WB_GAINS,
            gamma=self.CAMERA_PREVIEW_GAMMA,
        )
