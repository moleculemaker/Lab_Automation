import os
import time
from decimal import Decimal, getcontext
from typing import Optional, Tuple

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

        self._state = self.STATE_LATCHED
        self._is_connected = False
        self._polarizer_angle = 0.0
        self._sample_angle = 0.0
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
