from typing import Optional, Tuple

from .device import SerialDevice, check_serial, check_initialized


class Newport94043ASolarSim(SerialDevice):
    DEFAULT_POWER_WATTS = 400
    MAX_POWER_WATTS = 450
    MODE_TIMEOUT_S = 3.0
    POWER_PRESET_TIMEOUT_S = 3.0
    LAMP_START_TIMEOUT_S = 10.0
    LAMP_STOP_TIMEOUT_S = 10.0

    def __init__(
        self,
        name: str,
        port: str,
        baudrate: int = 9600,
        timeout: Optional[float] = 1.0,
        line_terminator: str = "\r",
        lamp_hours_warning_threshold: float = 1000.0,
        default_power_watts: int = DEFAULT_POWER_WATTS,
        max_power_watts: int = MAX_POWER_WATTS,
    ):
        super().__init__(name, port, baudrate, timeout)
        self._line_terminator = line_terminator
        self._lamp_hours_warning_threshold = lamp_hours_warning_threshold
        self._default_power_watts = default_power_watts
        self._max_power_watts = max_power_watts

    def get_init_args(self) -> dict:
        return {
            "name": self._name,
            "port": self._port,
            "baudrate": self._baudrate,
            "timeout": self._timeout,
            "line_terminator": self._line_terminator,
            "lamp_hours_warning_threshold": self._lamp_hours_warning_threshold,
            "default_power_watts": self._default_power_watts,
            "max_power_watts": self._max_power_watts,
        }

    def update_init_args(self, args_dict: dict):
        self._name = args_dict["name"]
        self._port = args_dict["port"]
        self._baudrate = args_dict["baudrate"]
        self._timeout = args_dict["timeout"]
        self._line_terminator = args_dict["line_terminator"]
        self._lamp_hours_warning_threshold = args_dict["lamp_hours_warning_threshold"]
        self._default_power_watts = args_dict["default_power_watts"]
        self._max_power_watts = args_dict["max_power_watts"]

    def _send(self, command: str) -> None:
        self.ser.write((command + self._line_terminator).encode("ascii"))

    def _readline(self) -> Tuple[bool, str]:
        response = self.ser.readline()
        if response == b"":
            return (False, "Response timed out.")
        return (True, response.decode("ascii", errors="replace").strip())

    def _query(self, command: str) -> Tuple[bool, str]:
        self.ser.reset_input_buffer()
        self._send(command)
        return self._readline()

    def _query_with_timeout(self, command: str, timeout_s: float) -> Tuple[bool, str]:
        original_timeout = self.ser.timeout
        self.ser.timeout = timeout_s
        try:
            return self._query(command)
        finally:
            self.ser.timeout = original_timeout

    @staticmethod
    def _parse_esr(response: str) -> Tuple[bool, str]:
        if not response.startswith("ESR"):
            return (False, "Unexpected response: " + response)
        hex_value = response[3:]
        try:
            esr_value = int(hex_value, 16)
        except ValueError:
            return (False, "Could not parse ESR response: " + response)

        has_error = bool(esr_value & 0b00111100)
        if has_error:
            return (False, "69920 returned error status " + response)
        return (True, response)

    @check_serial
    def initialize(self) -> Tuple[bool, str]:
        was_successful, response = self._set_mode(power_mode=True)
        if not was_successful:
            self._is_initialized = False
            return (was_successful, response)

        was_successful, response = self._set_power_preset(self._default_power_watts)
        if not was_successful:
            self._is_initialized = False
            return (was_successful, response)

        was_successful, lamp_hours_response = self._get_lamp_hours()
        if not was_successful:
            self._is_initialized = False
            return (was_successful, lamp_hours_response)

        self._is_initialized = True
        lamp_hours = self.parse_lamp_hours(lamp_hours_response)
        message = (
            "Successfully initialized 94043A solar simulator through 69920 power supply in power mode. "
            f"Default power preset set to {self._default_power_watts} W. Lamp hours: {lamp_hours:.0f} h."
        )
        if lamp_hours >= self._lamp_hours_warning_threshold:
            message += " Lamp has exceeded the replacement threshold. Replace the lamp and reset 69920 lamp hours from the front panel."
        return (True, message)

    def deinitialize(self) -> Tuple[bool, str]:
        self._is_initialized = False
        return (True, "Successfully deinitialized 69920.")

    @check_serial
    def identify(self) -> Tuple[bool, str]:
        return self._query("IDN?")

    @check_serial
    def status_byte(self) -> Tuple[bool, str]:
        return self._query("STB?")

    @check_serial
    def event_status_register(self) -> Tuple[bool, str]:
        return self._query("ESR?")

    @check_initialized
    @check_serial
    def lamp_start(self) -> Tuple[bool, str]:
        was_successful, response = self._query_with_timeout("START", self.LAMP_START_TIMEOUT_S)
        if not was_successful:
            return (was_successful, response)
        return self._parse_esr(response)

    @check_initialized
    @check_serial
    def lamp_stop(self) -> Tuple[bool, str]:
        was_successful, response = self._query_with_timeout("STOP", self.LAMP_STOP_TIMEOUT_S)
        if not was_successful:
            return (was_successful, response)
        return self._parse_esr(response)

    @check_initialized
    @check_serial
    def set_mode(self, power_mode: bool = True) -> Tuple[bool, str]:
        return self._set_mode(power_mode)

    @check_serial
    def _set_mode(self, power_mode: bool = True) -> Tuple[bool, str]:
        mode_value = 0 if power_mode else 1
        was_successful, response = self._query_with_timeout(f"MODE={mode_value}", self.MODE_TIMEOUT_S)
        if not was_successful:
            return (was_successful, response)
        return self._parse_esr(response)

    def set_power_mode(self) -> Tuple[bool, str]:
        return self.set_mode(power_mode=True)

    @check_initialized
    @check_serial
    def get_amps(self) -> Tuple[bool, str]:
        return self._query("AMPS?")

    @check_initialized
    @check_serial
    def get_volts(self) -> Tuple[bool, str]:
        return self._query("VOLTS?")

    @check_initialized
    @check_serial
    def get_watts(self) -> Tuple[bool, str]:
        return self._query("WATTS?")

    @check_initialized
    @check_serial
    def get_lamp_hours(self) -> Tuple[bool, str]:
        return self._get_lamp_hours()

    @check_serial
    def _get_lamp_hours(self) -> Tuple[bool, str]:
        return self._query("LAMP HRS?")

    @staticmethod
    def parse_lamp_hours(response: str) -> float:
        cleaned = response.strip()
        return float(cleaned)

    @check_initialized
    @check_serial
    def get_current_limit(self) -> Tuple[bool, str]:
        return self._query("A-LIM?")

    @check_initialized
    @check_serial
    def get_power_limit(self) -> Tuple[bool, str]:
        return self._query("P-LIM?")

    @check_initialized
    @check_serial
    def get_power_preset(self) -> Tuple[bool, str]:
        return self._query("P-PRESET?")

    @check_initialized
    @check_serial
    def set_power_preset(self, watts: int) -> Tuple[bool, str]:
        return self._set_power_preset(watts)

    @check_serial
    def _set_power_preset(self, watts: int) -> Tuple[bool, str]:
        if watts < 0:
            return (False, "Power preset must be non-negative.")
        if watts > self._max_power_watts:
            return (
                False,
                "Power preset "
                + str(watts)
                + " W exceeds the configured safety limit of "
                + str(self._max_power_watts)
                + " W for the 94043A solar simulator.",
            )
        was_successful, response = self._query_with_timeout(
            f"P-PRESET={int(watts)}",
            self.POWER_PRESET_TIMEOUT_S,
        )
        if not was_successful:
            return (was_successful, response)
        return self._parse_esr(response)
