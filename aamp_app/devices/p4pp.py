import re
import csv
import os
import time
from collections import deque
from typing import Optional, Tuple

from .device import SerialDevice, check_initialized, check_serial


class P4PP(SerialDevice):
    """
    AAMP wrapper for the P4PP controller.

    Python-side behavior is based on the public driver in
    https://github.com/changhwang/P4PP .
    Firmware and hardware details should be referenced from
    https://github.com/polyprintillinois/P4PP .
    """

    POS_PATTERN = re.compile(r"^POS LIN:\s*(-?\d+)\s+ROT:\s*(-?\d+)$")
    RS_PATTERN = re.compile(r"Raw R_sheet:\s*(-?\d+(?:\.\d+)?)")
    CYCLE_PATTERN = re.compile(r"^CYCLE:(\d+)\s+Rs:(-?\d+(?:\.\d+)?)$")
    AVG_STD_PATTERN = re.compile(r"^AVG:(-?\d+(?:\.\d+)?)\s+STD:(-?\d+(?:\.\d+)?)$")
    LIN_TARGET_PATTERN = re.compile(r"^OK LIN_TARGET:\s*(-?\d+)$")
    ROT_TARGET_PATTERN = re.compile(r"^OK ROT_TARGET:\s*(-?\d+)$")

    LIN_STEPS_PER_MM = 200.0
    ROT_STEPS_PER_DEG = 4.444444
    LIN_MIN_STEPS = 0
    LIN_MAX_STEPS = 10000
    ROT_MIN_STEPS = 0
    ROT_MAX_STEPS = 1250

    DEFAULT_STARTUP_DELAY_S = 2.0
    DEFAULT_COMMAND_TIMEOUT_S = 30.0
    DEFAULT_MOTION_TIMEOUT_S = 60.0
    DEFAULT_HOME_TIMEOUT_S = 60.0
    DEFAULT_MEASURE_TIMEOUT_S = 30.0
    DEFAULT_POLL_INTERVAL_S = 0.2
    DEFAULT_ROTATION_SAFETY_LINEAR_MM = 45.0
    DEFAULT_MEASUREMENT_RESISTOR_OHMS = 681.0
    DEFAULT_SAVE_DIRECTORY = "data/resistance/"

    RESPONSE_OK_MEASURE_COMPLETE = "OK MEASURE_COMPLETE"
    RESPONSE_OK_HOMING_LIN_COMPLETE = "OK HOMING_LIN_COMPLETE"
    RESPONSE_OK_HOMING_ROT_COMPLETE = "OK HOMING_ROT_COMPLETE"
    RESPONSE_ERR_PREFIX = "ERR "
    RESPONSE_ERROR_PREFIX = "ERROR:"

    COMMAND_MEASURE = "MEASURE"
    COMMAND_MEASURE_N = "MEASURE_N"
    COMMAND_MOVE_LIN = "MOVE_LIN"
    COMMAND_MOVE_ROT = "MOVE_ROT"
    COMMAND_HOME_LIN = "HOME_LIN"
    COMMAND_HOME_ROT = "HOME_ROT"
    COMMAND_GET_POS = "GET_POS"
    COMMAND_STATUS = "STATUS"

    def __init__(
        self,
        name: str,
        port: str,
        baudrate: int = 115200,
        timeout: Optional[float] = 0.2,
        startup_delay: float = DEFAULT_STARTUP_DELAY_S,
        command_timeout: float = DEFAULT_COMMAND_TIMEOUT_S,
        motion_timeout: float = DEFAULT_MOTION_TIMEOUT_S,
        home_timeout: float = DEFAULT_HOME_TIMEOUT_S,
        measure_timeout: float = DEFAULT_MEASURE_TIMEOUT_S,
        poll_interval: float = DEFAULT_POLL_INTERVAL_S,
        rotation_safety_linear_mm: float = DEFAULT_ROTATION_SAFETY_LINEAR_MM,
        measurement_resistor_ohms: float = DEFAULT_MEASUREMENT_RESISTOR_OHMS,
        save_directory: str = DEFAULT_SAVE_DIRECTORY,
    ):
        super().__init__(name, port, baudrate, timeout)
        self._startup_delay = startup_delay
        self._command_timeout = command_timeout
        self._motion_timeout = motion_timeout
        self._home_timeout = home_timeout
        self._measure_timeout = measure_timeout
        self._poll_interval = poll_interval
        self._rotation_safety_linear_mm = rotation_safety_linear_mm
        self._measurement_resistor_ohms = measurement_resistor_ohms
        self._save_directory = save_directory

        self._has_homed_linear = False
        self._has_homed_rotational = False
        self._linear_steps = 0
        self._rotational_steps = 0
        self._target_linear_steps = None
        self._target_rotational_steps = None
        self._latest_result = None
        self._latest_std = None
        self._latest_raw_result = None
        self._cycle_results = []
        self._recent_lines = deque(maxlen=200)

    def get_init_args(self) -> dict:
        return {
            "name": self._name,
            "port": self._port,
            "baudrate": self._baudrate,
            "timeout": self._timeout,
            "startup_delay": self._startup_delay,
            "command_timeout": self._command_timeout,
            "motion_timeout": self._motion_timeout,
            "home_timeout": self._home_timeout,
            "measure_timeout": self._measure_timeout,
            "poll_interval": self._poll_interval,
            "rotation_safety_linear_mm": self._rotation_safety_linear_mm,
            "measurement_resistor_ohms": self._measurement_resistor_ohms,
            "save_directory": self._save_directory,
        }

    def update_init_args(self, args_dict: dict):
        self._name = args_dict["name"]
        self._port = args_dict["port"]
        self._baudrate = args_dict["baudrate"]
        self._timeout = args_dict["timeout"]
        self._startup_delay = args_dict["startup_delay"]
        self._command_timeout = args_dict["command_timeout"]
        self._motion_timeout = args_dict["motion_timeout"]
        self._home_timeout = args_dict["home_timeout"]
        self._measure_timeout = args_dict["measure_timeout"]
        self._poll_interval = args_dict["poll_interval"]
        self._rotation_safety_linear_mm = args_dict["rotation_safety_linear_mm"]
        self._measurement_resistor_ohms = args_dict["measurement_resistor_ohms"]
        self._save_directory = args_dict["save_directory"]

    @property
    def has_homed_linear(self) -> bool:
        return self._has_homed_linear

    @property
    def has_homed_rotational(self) -> bool:
        return self._has_homed_rotational

    @property
    def latest_result(self):
        return self._latest_result

    @property
    def latest_std(self):
        return self._latest_std

    @property
    def latest_raw_result(self):
        return self._latest_raw_result

    @property
    def cycle_results(self):
        return list(self._cycle_results)

    @staticmethod
    def lin_steps_to_mm(steps: int) -> float:
        return steps / P4PP.LIN_STEPS_PER_MM

    @staticmethod
    def rot_steps_to_deg(steps: int) -> float:
        return steps / P4PP.ROT_STEPS_PER_DEG

    @staticmethod
    def mm_to_lin_steps(mm: float) -> int:
        return int(round(mm * P4PP.LIN_STEPS_PER_MM))

    @staticmethod
    def deg_to_rot_steps(deg: float) -> int:
        return int(round(deg * P4PP.ROT_STEPS_PER_DEG))

    def start_serial(self, delay: Optional[float] = None) -> Tuple[bool, str]:
        if delay is None:
            delay = self._startup_delay
        return super().start_serial(delay=delay)

    def _send(self, command: str) -> None:
        self.ser.write((command.strip() + "\n").encode("utf-8"))

    def _readline(self) -> Tuple[bool, str]:
        response = self.ser.readline()
        if response == b"":
            return (False, "")
        return (True, response.decode("utf-8", errors="ignore").strip())

    def _clear_serial_buffer(self) -> None:
        if self.ser.is_open:
            self.ser.reset_input_buffer()

    def _handle_line(self, line: str) -> Tuple[bool, Optional[str]]:
        if not line:
            return (True, None)

        self._recent_lines.append(line)

        if line.startswith(self.RESPONSE_ERR_PREFIX) or line.startswith(self.RESPONSE_ERROR_PREFIX):
            return (False, line)

        if line == self.RESPONSE_OK_HOMING_LIN_COMPLETE:
            self._has_homed_linear = True
            self._linear_steps = 0
            self._target_linear_steps = None
            return (True, line)

        if line == self.RESPONSE_OK_HOMING_ROT_COMPLETE:
            self._has_homed_rotational = True
            self._rotational_steps = 0
            self._target_rotational_steps = None
            return (True, line)

        rs_match = self.RS_PATTERN.search(line)
        if rs_match:
            self._latest_raw_result = float(rs_match.group(1))
            self._latest_result = self._latest_raw_result
            return (True, line)

        cycle_match = self.CYCLE_PATTERN.match(line)
        if cycle_match:
            self._cycle_results.append(float(cycle_match.group(2)))
            return (True, line)

        avg_std_match = self.AVG_STD_PATTERN.match(line)
        if avg_std_match:
            self._latest_raw_result = float(avg_std_match.group(1))
            self._latest_result = self._latest_raw_result
            self._latest_std = float(avg_std_match.group(2))
            return (True, line)

        pos_match = self.POS_PATTERN.match(line)
        if pos_match:
            self._linear_steps = int(pos_match.group(1))
            self._rotational_steps = int(pos_match.group(2))
            return (True, line)

        lin_target_match = self.LIN_TARGET_PATTERN.match(line)
        if lin_target_match:
            self._target_linear_steps = int(lin_target_match.group(1))
            return (True, line)

        rot_target_match = self.ROT_TARGET_PATTERN.match(line)
        if rot_target_match:
            self._target_rotational_steps = int(rot_target_match.group(1))
            return (True, line)

        return (True, line)

    def _wait_for_condition(
        self,
        predicate,
        timeout_s: float,
        poll_position: bool = False,
    ) -> Tuple[bool, str]:
        deadline = time.monotonic() + timeout_s
        last_poll_at = 0.0
        while time.monotonic() < deadline:
            now = time.monotonic()
            if poll_position and (now - last_poll_at) >= self._poll_interval:
                self._send(self.COMMAND_GET_POS)
                last_poll_at = now

            was_successful, line = self._readline()
            if not was_successful:
                continue

            was_successful, error_message = self._handle_line(line)
            if not was_successful:
                return (False, error_message)

            if predicate(line):
                return (True, line)

        return (False, "Timed out waiting for P4PP response.")

    def _rotation_is_safe(self) -> Tuple[bool, str]:
        linear_mm = self.lin_steps_to_mm(self._linear_steps)
        if linear_mm >= self._rotation_safety_linear_mm:
            return (
                False,
                f"P4PP rotation blocked: linear axis is at {linear_mm:.3f} mm, which is at or above the safety limit of {self._rotation_safety_linear_mm:.3f} mm. Retract the probe first.",
            )
        return (True, "")

    @staticmethod
    def _normalize_measurement_resistor_ohms(resistor_ohms: float) -> Tuple[bool, float]:
        if abs(float(resistor_ohms) - 681.0) < 1e-6:
            return (True, 681.0)
        if abs(float(resistor_ohms) - 68.1) < 1e-6:
            return (True, 68.1)
        return (False, float(resistor_ohms))

    def get_measurement_resistor_info(self) -> dict:
        if abs(self._measurement_resistor_ohms - 68.1) < 1e-6:
            return {"R_set": 68.1, "label": "68.1 ohm", "range": "<= 10 kOhm/sq"}
        return {"R_set": 681.0, "label": "681 ohm", "range": "1 kOhm/sq - 100 kOhm/sq"}

    @staticmethod
    def _ensure_csv_directory(csv_path: str) -> None:
        directory = os.path.dirname(csv_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def build_measurement_csv_path(self, filename: str = "p4pp_measurements.csv", directory: Optional[str] = None) -> str:
        if directory is None:
            directory = self._save_directory
        return os.path.join(directory, filename)

    @check_initialized
    @check_serial
    def set_measurement_resistor(self, resistor_ohms: float) -> Tuple[bool, str]:
        was_successful, normalized = self._normalize_measurement_resistor_ohms(resistor_ohms)
        if not was_successful:
            return (False, "P4PP measurement resistor must be either 681 or 68.1 ohm.")
        self._measurement_resistor_ohms = normalized
        info = self.get_measurement_resistor_info()
        return (True, f"P4PP measurement resistor set to {info['label']} ({info['range']}).")

    @check_serial
    def initialize(self) -> Tuple[bool, str]:
        was_successful, response = self.refresh_position()
        if not was_successful:
            self._is_initialized = False
            return (was_successful, response)
        self._is_initialized = True
        return (
            True,
            "Successfully initialized P4PP. "
            + "For firmware and hardware details, see https://github.com/polyprintillinois/P4PP .",
        )

    def deinitialize(self) -> Tuple[bool, str]:
        self._is_initialized = False
        return (True, "Successfully deinitialized P4PP.")

    @check_serial
    def refresh_position(self) -> Tuple[bool, str]:
        self._clear_serial_buffer()
        self._send(self.COMMAND_GET_POS)
        was_successful, response = self._wait_for_condition(
            lambda line: bool(self.POS_PATTERN.match(line)),
            self._command_timeout,
            poll_position=False,
        )
        if not was_successful:
            return (was_successful, response)
        return (
            True,
            "Linear position: "
            + f"{self.lin_steps_to_mm(self._linear_steps):.3f} mm, rotational position: {self.rot_steps_to_deg(self._rotational_steps):.3f} deg.",
        )

    @check_initialized
    @check_serial
    def home_linear(self) -> Tuple[bool, str]:
        self._clear_serial_buffer()
        self._send(self.COMMAND_HOME_LIN)
        was_successful, response = self._wait_for_condition(
            lambda line: line == self.RESPONSE_OK_HOMING_LIN_COMPLETE,
            self._home_timeout,
            poll_position=True,
        )
        if not was_successful:
            return (was_successful, response)
        return (True, "Successfully homed P4PP linear axis.")

    @check_initialized
    @check_serial
    def home_rotational(self) -> Tuple[bool, str]:
        was_successful, message = self._rotation_is_safe()
        if not was_successful:
            return (was_successful, message)
        self._clear_serial_buffer()
        self._send(self.COMMAND_HOME_ROT)
        was_successful, response = self._wait_for_condition(
            lambda line: line == self.RESPONSE_OK_HOMING_ROT_COMPLETE,
            self._home_timeout,
            poll_position=True,
        )
        if not was_successful:
            return (was_successful, response)
        return (True, "Successfully homed P4PP rotational axis.")

    @check_initialized
    @check_serial
    def home_all(self) -> Tuple[bool, str]:
        was_successful, response = self.home_linear()
        if not was_successful:
            return (was_successful, response)
        return self.home_rotational()

    @check_initialized
    @check_serial
    def move_linear_mm(self, position_mm: float, relative: bool = False) -> Tuple[bool, str]:
        if not self._has_homed_linear:
            return (False, "P4PP linear axis must be homed before moving.")

        target_steps = self.mm_to_lin_steps(position_mm)
        final_target = self._linear_steps + target_steps if relative else target_steps
        if final_target < self.LIN_MIN_STEPS or final_target > self.LIN_MAX_STEPS:
            return (
                False,
                f"P4PP linear target {self.lin_steps_to_mm(final_target):.3f} mm is outside the allowed range.",
            )

        self._clear_serial_buffer()
        self._target_linear_steps = final_target
        self._send(f"{self.COMMAND_MOVE_LIN} {final_target}")
        was_successful, response = self._wait_for_condition(
            lambda line: self._linear_steps == final_target,
            self._motion_timeout,
            poll_position=True,
        )
        if not was_successful:
            return (was_successful, response)
        return (
            True,
            f"Successfully moved P4PP linear axis to {self.lin_steps_to_mm(final_target):.3f} mm.",
        )

    @check_initialized
    @check_serial
    def move_rotational_deg(self, position_deg: float, relative: bool = False) -> Tuple[bool, str]:
        if not self._has_homed_rotational:
            return (False, "P4PP rotational axis must be homed before moving.")
        was_successful, message = self._rotation_is_safe()
        if not was_successful:
            return (was_successful, message)

        target_steps = self.deg_to_rot_steps(position_deg)
        final_target = self._rotational_steps + target_steps if relative else target_steps
        if final_target < self.ROT_MIN_STEPS or final_target > self.ROT_MAX_STEPS:
            return (
                False,
                f"P4PP rotational target {self.rot_steps_to_deg(final_target):.3f} deg is outside the allowed range.",
            )

        self._clear_serial_buffer()
        self._target_rotational_steps = final_target
        self._send(f"{self.COMMAND_MOVE_ROT} {final_target}")
        was_successful, response = self._wait_for_condition(
            lambda line: self._rotational_steps == final_target,
            self._motion_timeout,
            poll_position=True,
        )
        if not was_successful:
            return (was_successful, response)
        return (
            True,
            f"Successfully moved P4PP rotational axis to {self.rot_steps_to_deg(final_target):.3f} deg.",
        )

    @check_initialized
    @check_serial
    def measure(self, cycles: int = 1) -> Tuple[bool, str]:
        if cycles < 1:
            return (False, "Measurement cycles must be at least 1.")

        self._latest_result = None
        self._latest_std = None
        self._latest_raw_result = None
        self._cycle_results = []

        self._clear_serial_buffer()
        if cycles == 1:
            self._send(self.COMMAND_MEASURE)
        else:
            self._send(f"{self.COMMAND_MEASURE_N} {int(cycles)}")

        was_successful, response = self._wait_for_condition(
            lambda line: line == self.RESPONSE_OK_MEASURE_COMPLETE,
            self._measure_timeout,
            poll_position=False,
        )
        if not was_successful:
            return (was_successful, response)

        if self._latest_result is None:
            info = self.get_measurement_resistor_info()
            return (True, f"P4PP measurement completed with {info['label']}, but no parsed R_sheet value was received.")

        info = self.get_measurement_resistor_info()
        message = f"P4PP measurement complete. R_sheet={self._latest_result}"
        if self._latest_std is not None:
            message += f", std={self._latest_std}"
        if cycles > 1:
            message += f", cycles={cycles}"
        message += f", R_set={info['label']}"
        return (True, message)

    @check_initialized
    def save_measurement_csv(
        self,
        sample_id: Optional[str] = None,
        csv_path: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Tuple[bool, str]:
        if self._latest_result is None:
            return (False, "No P4PP measurement result is available to save.")

        if csv_path is None:
            csv_path = self.build_measurement_csv_path()

        self._ensure_csv_directory(csv_path)
        file_exists = os.path.isfile(csv_path)
        info = self.get_measurement_resistor_info()
        row = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sample_id": sample_id or "",
            "linear_position_mm": self.lin_steps_to_mm(self._linear_steps),
            "rotational_position_deg": self.rot_steps_to_deg(self._rotational_steps),
            "cycles": len(self._cycle_results) if self._cycle_results else 1,
            "r_set_ohms": info["R_set"],
            "r_sheet": self._latest_result,
            "r_sheet_std": self._latest_std if self._latest_std is not None else "",
            "raw_r_sheet": self._latest_raw_result if self._latest_raw_result is not None else "",
            "notes": notes or "",
        }
        fieldnames = list(row.keys())
        try:
            with open(csv_path, "a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
        except Exception as exc:
            return (False, "Failed to save P4PP measurement CSV: " + str(exc))

        return (True, "Successfully saved P4PP measurement to " + csv_path)

    @check_initialized
    @check_serial
    def get_linear_position_mm(self) -> Tuple[bool, float]:
        return (True, self.lin_steps_to_mm(self._linear_steps))

    @check_initialized
    @check_serial
    def get_rotational_position_deg(self) -> Tuple[bool, float]:
        return (True, self.rot_steps_to_deg(self._rotational_steps))

    def drain_recent_lines(self):
        lines = list(self._recent_lines)
        self._recent_lines.clear()
        return lines
