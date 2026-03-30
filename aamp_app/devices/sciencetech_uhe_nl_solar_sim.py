import re
import time
from typing import Optional, Tuple

from .device import SerialDevice, check_initialized, check_serial


class SciencetechUHENLSolarSim(SerialDevice):
    """
    RS-232 wrapper for the Sciencetech UHE-NL solar simulator power control path.

    The UHE-NL operating instructions confirm that RS-232 computer control is available,
    while the detailed command strings are inferred from the existing lab draft in
    `to_implement/sciencetech_lamp.py`.
    """

    STATUS_LINE_MAP = {
        "current": 3,
        "voltage": 4,
        "power": 5,
        "po": 6,
        "cool": 7,
        "lamp": 8,
        "starts": 9,
        "runtime": 10,
        "output": 11,
        "hours": 12,
        "lamp minutes": 13,
        "shutter": 14,
        "attenuator": 15,
        "stabilization": 16,
    }
    STATUS_LABEL_MAP = {
        "current": ("CURRENT", "I"),
        "voltage": ("VOLTAGE", "V"),
        "power": ("POWER", "P"),
        "po": ("PO",),
        "cool": ("COOL", "COOLING", "FANS"),
        "lamp": ("LAMP",),
        "starts": ("STARTS",),
        "runtime": ("RUNTIME", "RUN TIME", "TIME"),
        "output": ("OUTPUT",),
        "hours": ("HOURS",),
        "lamp minutes": ("MINUTES", "LAMP MINUTES"),
        "shutter": ("SHUTTER",),
        "attenuator": ("ATTENUATOR", "TRANSMISSION"),
        "stabilization": ("STABILIZATION",),
    }

    def __init__(
        self,
        name: str,
        port: str,
        baudrate: int = 9600,
        timeout: Optional[float] = 2.0,
        line_terminator: str = "\r",
        connect_delay_s: float = 3.0,
        command_delay_s: float = 8.0,
        status_timeout_s: float = 8.0,
        default_current_percent: float = 85.0,
        default_attenuator_percent: int = 100,
        debug_io: bool = False,
    ):
        super().__init__(name, port, baudrate, timeout)
        self._line_terminator = line_terminator
        self._connect_delay_s = connect_delay_s
        self._command_delay_s = command_delay_s
        self._status_timeout_s = status_timeout_s
        self._default_current_percent = default_current_percent
        self._default_attenuator_percent = default_attenuator_percent
        self._debug_io = debug_io
        self._requested_output_percent = default_current_percent

    def get_init_args(self) -> dict:
        return {
            "name": self._name,
            "port": self._port,
            "baudrate": self._baudrate,
            "timeout": self._timeout,
            "line_terminator": self._line_terminator,
            "connect_delay_s": self._connect_delay_s,
            "command_delay_s": self._command_delay_s,
            "status_timeout_s": self._status_timeout_s,
            "default_current_percent": self._default_current_percent,
            "default_attenuator_percent": self._default_attenuator_percent,
            "debug_io": self._debug_io,
        }

    def update_init_args(self, args_dict: dict):
        self._name = args_dict["name"]
        self._port = args_dict["port"]
        self._baudrate = args_dict["baudrate"]
        self._timeout = args_dict["timeout"]
        self._line_terminator = args_dict["line_terminator"]
        self._connect_delay_s = args_dict["connect_delay_s"]
        self._command_delay_s = args_dict["command_delay_s"]
        self._status_timeout_s = args_dict["status_timeout_s"]
        self._default_current_percent = args_dict["default_current_percent"]
        self._default_attenuator_percent = args_dict["default_attenuator_percent"]
        self._debug_io = args_dict["debug_io"]
        self._requested_output_percent = self._default_current_percent

    def _debug(self, message: str):
        if self._debug_io:
            print(f"[{self._name} debug] {message}")

    def connect(self) -> Tuple[bool, str]:
        return self.start_serial(delay=self._connect_delay_s)

    @check_serial
    def initialize(self) -> Tuple[bool, str]:
        was_successful, message = self.get_feedback("lamp")
        if not was_successful:
            self._is_initialized = False
            return (False, message)
        lamp_state = self._extract_last_number(message)
        if lamp_state is not None and int(lamp_state) == 1:
            self._is_initialized = False
            return (False, "Lamp is currently on. Turn the lamp off before initialize.")

        was_successful, message = self.enable_cooling()
        if not was_successful:
            self._is_initialized = False
            return (False, message)

        if self._default_attenuator_percent >= 100:
            was_successful, message = self.open_attenuator()
        else:
            was_successful, message = self.set_attenuator(self._default_attenuator_percent)
        if not was_successful:
            self._is_initialized = False
            return (False, message)

        was_successful, message = self.set_current(self._default_current_percent)
        if not was_successful:
            self._is_initialized = False
            return (False, message)

        self._is_initialized = True
        return (
            True,
            "Successfully initialized the UHE-NL solar simulator control path. "
            + f"Cooling on, attenuator set to {self._default_attenuator_percent}%, "
            + f"output setpoint set to {self._default_current_percent:.1f}%.",
        )

    def deinitialize(self, reset_init_flag: bool = True, close_serial: bool = False) -> Tuple[bool, str]:
        lamp_message = None
        if self.ser.is_open:
            was_successful, message = self.get_feedback("lamp")
            if not was_successful:
                return (False, message)
            lamp_state = self._extract_last_number(message)
            if lamp_state is not None and int(lamp_state) == 1:
                was_successful, lamp_message = self.disable_arc_lamp()
                if not was_successful:
                    return (False, lamp_message)
        if close_serial and self.ser.is_open:
            self.ser.close()
        if reset_init_flag:
            self._is_initialized = False
        message = "Successfully deinitialized the UHE-NL solar simulator interface."
        if lamp_message is not None:
            message += " Arc lamp was turned off. Cooling was left on for post-shutdown cooldown."
        return (True, message)

    @check_serial
    def _send_command(self, command: str):
        self._debug(f"TX -> {command!r}")
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self.ser.write((command + self._line_terminator).encode("ascii"))
        self.ser.flush()
        time.sleep(self._command_delay_s)

    @staticmethod
    def _extract_last_number(text: str) -> Optional[float]:
        matches = re.findall(r"-?\d+(?:\.\d+)?", text)
        if not matches:
            return None
        return float(matches[-1])

    @check_serial
    def get_status(self) -> Tuple[bool, list]:
        self._debug("TX -> 'FS'")
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self.ser.write(("FS" + self._line_terminator).encode("ascii"))
        self.ser.flush()

        answer = []
        start_t = time.time()
        while (time.time() - start_t) < self._status_timeout_s:
            line = self.ser.readline().decode("ascii", errors="ignore").strip()
            if not line:
                continue
            self._debug(f"RX <- {line!r}")
            if line == "END":
                return (True, answer)
            answer.append(line)

        return (False, "Timed out while waiting for full status response.")

    @check_serial
    def get_feedback(self, feedback_type: str) -> Tuple[bool, str]:
        type_lower = feedback_type.lower()
        if type_lower not in self.STATUS_LINE_MAP:
            return (False, "Invalid feedback type")

        was_successful, response = self.get_status()
        if not was_successful:
            return (False, response)

        prefixes = self.STATUS_LABEL_MAP.get(type_lower, ())
        for line in response:
            line_upper = line.upper()
            for prefix in prefixes:
                normalized_prefix = prefix.upper()
                if line_upper.startswith(normalized_prefix + "=") or line_upper.startswith(normalized_prefix + ":"):
                    return (True, line)

        line_index = self.STATUS_LINE_MAP[type_lower]
        if len(response) <= line_index:
            return (False, "Status response did not contain expected feedback lines.")

        return (True, response[line_index])

    def _verify_binary_feedback(self, feedback_type: str, expected: int, label: str, state_text: str, action_verb: str):
        was_successful, message = self.get_feedback(feedback_type)
        if not was_successful:
            return (False, message)

        value = self._extract_last_number(message)
        if value is None:
            return (False, f"Failed to parse {label} feedback: {message}")
        if int(value) == expected:
            return (True, f"Successfully {action_verb} {label.lower()}.")
        return (False, f"{label} did not reach the {state_text} state after command. Feedback: {message}")

    @check_serial
    def close_shutter(self) -> Tuple[bool, str]:
        was_successful, message = self.get_feedback("shutter")
        if not was_successful:
            return (False, message)
        value = self._extract_last_number(message)
        if value is not None and int(value) == 1:
            return (True, "Shutter is closed.")

        self._send_command("S1")
        return self._verify_binary_feedback("shutter", 1, "Shutter", "closed", "close")

    @check_serial
    def open_shutter(self) -> Tuple[bool, str]:
        was_successful, message = self.get_feedback("shutter")
        if not was_successful:
            return (False, message)
        value = self._extract_last_number(message)
        if value is not None and int(value) == 0:
            return (True, "Shutter is open.")

        self._send_command("S0")
        return self._verify_binary_feedback("shutter", 0, "Shutter", "open", "open")

    @check_serial
    def enable_cooling(self) -> Tuple[bool, str]:
        was_successful, message = self.get_feedback("cool")
        if not was_successful:
            return (False, message)
        value = self._extract_last_number(message)
        if value is not None and int(value) == 1:
            return (True, "Cooling is enabled.")

        self._send_command("C1")
        return self._verify_binary_feedback("cool", 1, "Cooling", "enabled", "enable")

    @check_serial
    def disable_cooling(self) -> Tuple[bool, str]:
        was_successful, message = self.get_feedback("cool")
        if not was_successful:
            return (False, message)
        value = self._extract_last_number(message)
        if value is not None and int(value) == 0:
            return (True, "Cooling is disabled.")

        self._send_command("C0")
        return self._verify_binary_feedback("cool", 0, "Cooling", "disabled", "disable")

    @check_serial
    def enable_arc_lamp(self) -> Tuple[bool, str]:
        was_successful, message = self.get_feedback("cool")
        if not was_successful:
            return (False, message)
        cool_state = self._extract_last_number(message)
        if cool_state is None:
            return (False, f"Failed to parse cooling feedback: {message}")
        if int(cool_state) != 1:
            return (False, "Cooling must be on before enabling the arc lamp.")

        was_successful, message = self.get_feedback("lamp")
        if not was_successful:
            return (False, message)
        value = self._extract_last_number(message)
        if value is not None and int(value) == 1:
            return (True, "Arc lamp is enabled.")

        self._send_command("L1")
        return self._verify_binary_feedback("lamp", 1, "Arc lamp", "enabled", "enable")

    @check_serial
    def disable_arc_lamp(self) -> Tuple[bool, str]:
        was_successful, message = self.get_feedback("lamp")
        if not was_successful:
            return (False, message)
        value = self._extract_last_number(message)
        if value is not None and int(value) == 0:
            return (True, "Arc lamp is disabled.")

        self._send_command("L0")
        return self._verify_binary_feedback("lamp", 0, "Arc lamp", "disabled", "disable")

    @check_serial
    def open_attenuator(self) -> Tuple[bool, str]:
        self._send_command("A1xxxx")
        was_successful, message = self.get_feedback("attenuator")
        if not was_successful:
            return (False, message)

        percent_read = self._extract_last_number(message)
        if percent_read is None:
            return (False, f"Failed to parse attenuator feedback: {message}")
        if int(round(percent_read)) == 100:
            return (True, "Successfully opened attenuator to 100%.")
        return (False, f"Failed to fully open attenuator. Feedback: {message}")

    @check_serial
    def set_attenuator(self, percent: int) -> Tuple[bool, str]:
        if percent < 0 or percent > 100:
            return (False, "Invalid attenuator percentage")

        self._send_command(f"A={int(percent):03d}x")
        was_successful, message = self.get_feedback("attenuator")
        if not was_successful:
            return (False, message)

        percent_read = self._extract_last_number(message)
        if percent_read is None:
            return (False, f"Failed to parse attenuator feedback: {message}")
        if int(round(percent_read)) == int(percent):
            return (True, f"Successfully set attenuator transmission to {percent}%.")
        return (False, f"Failed to set attenuator transmission to {percent}%. Feedback: {message}")

    @check_serial
    def set_current(self, percent: float) -> Tuple[bool, str]:
        if percent < 0 or percent > 100:
            return (False, "Invalid current percentage")

        scaled = int(round(percent * 10))
        self._requested_output_percent = percent
        self._send_command(f"P={scaled:04d}")

        was_successful, lamp_feedback = self.get_feedback("lamp")
        if not was_successful:
            return (False, lamp_feedback)
        lamp_state = self._extract_last_number(lamp_feedback)

        was_successful, message = self.get_feedback("output")
        if not was_successful:
            return (False, message)

        percent_read = self._extract_last_number(message)
        if percent_read is None:
            return (False, f"Failed to parse output current feedback: {message}")
        percent_read = percent_read / 10.0 if percent_read > 100 else percent_read

        if lamp_state is not None and int(lamp_state) == 0:
            if abs(percent_read - percent) <= 0.2:
                return (True, f"Successfully set output current setpoint to {percent:.1f}%.")
            self._debug(
                "Lamp is off; controller is reporting OUTPUT while lamp is off as "
                + f"{message!r}. Treating the setpoint command as accepted."
            )
            return (
                True,
                f"Sent output current setpoint command for {percent:.1f}% while lamp was off. "
                + f"Controller feedback remained {message}.",
            )

        if abs(percent_read - percent) <= 0.2:
            return (True, f"Successfully set output current setpoint to {percent:.1f}%.")
        was_successful, status = self.get_status()
        if was_successful:
            status_text = " | ".join(status)
            return (
                False,
                f"Failed to set output current setpoint to {percent:.1f}%. "
                + f"Feedback: {message}. Full status: {status_text}",
            )
        return (False, f"Failed to set output current setpoint to {percent:.1f}%. Feedback: {message}")
