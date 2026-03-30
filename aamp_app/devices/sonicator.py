import time
from typing import Optional, Tuple

from .device import ArduinoSerialDevice, check_initialized, check_serial


class Sonicator(ArduinoSerialDevice):
    """
    Arduino Uno R3 wrapper for a sonicator front-panel button and status LED interface.

    The expected wiring follows the older lab draft:
    - Uno `5V` to sonicator interface board `5V`
    - Uno `GND` to sonicator interface board `GND`
    - Uno `D7` as the sonicator button-drive output
    - Uno `D8` as the sonication-status input

    Serial protocol:
    - `>status`
    - `>button`
    - `>power`
    - `>turnon`
    - `>turnoff`
    """

    RESPONSE_MESSAGES = {
        "SIW": "Sonicator is sonicating.",
        "SNW": "Sonicator is idle.",
        "BIP": "Pressed the sonicator button.",
        "PIO": "Sonicator power connection is present.",
        "PNO": "Sonicator power connection is not present.",
        "SAN": "Sonicator is already sonicating.",
        "STN": "Successfully started sonication.",
        "SAF": "Sonicator is already idle.",
        "STF": "Successfully stopped sonication.",
        "INV": "Invalid command.",
        "ERR": "Controller reported a state-transition error.",
    }

    def __init__(
        self,
        name: str,
        port: str,
        baudrate: int = 9600,
        timeout: Optional[float] = 0.5,
        connect_delay_s: float = 3.0,
        response_timeout_s: float = 3.0,
        power_probe_timeout_s: float = 5.0,
        line_terminator: str = "\n",
        command_prefix: str = ">",
        debug_io: bool = False,
    ):
        super().__init__(name, port, baudrate, timeout)
        self._connect_delay_s = connect_delay_s
        self._response_timeout_s = response_timeout_s
        self._power_probe_timeout_s = power_probe_timeout_s
        self._line_terminator = line_terminator
        self._command_prefix = command_prefix
        self._debug_io = debug_io

    def get_init_args(self) -> dict:
        return {
            "name": self._name,
            "port": self._port,
            "baudrate": self._baudrate,
            "timeout": self._timeout,
            "connect_delay_s": self._connect_delay_s,
            "response_timeout_s": self._response_timeout_s,
            "power_probe_timeout_s": self._power_probe_timeout_s,
            "line_terminator": self._line_terminator,
            "command_prefix": self._command_prefix,
            "debug_io": self._debug_io,
        }

    def update_init_args(self, args_dict: dict):
        self._name = args_dict["name"]
        self._port = args_dict["port"]
        self._baudrate = args_dict["baudrate"]
        self._timeout = args_dict["timeout"]
        self._connect_delay_s = args_dict["connect_delay_s"]
        self._response_timeout_s = args_dict["response_timeout_s"]
        self._power_probe_timeout_s = args_dict["power_probe_timeout_s"]
        self._line_terminator = args_dict["line_terminator"]
        self._command_prefix = args_dict["command_prefix"]
        self._debug_io = args_dict["debug_io"]

    def _debug(self, message: str):
        if self._debug_io:
            print(f"[{self._name} debug] {message}")

    def connect(self) -> Tuple[bool, str]:
        return self.start_serial(delay=self._connect_delay_s)

    @check_serial
    def initialize(self) -> Tuple[bool, str]:
        was_successful, status_code = self._request_code("status", self._response_timeout_s)
        if not was_successful:
            self._is_initialized = False
            return (False, status_code)

        init_message = "Successfully initialized sonicator control path. Sonicator is idle."
        if status_code == "SIW":
            was_successful, stop_message = self._stop_sonicating_internal()
            if not was_successful:
                self._is_initialized = False
                return (False, stop_message)
            init_message = (
                "Successfully initialized sonicator control path. "
                + "Sonication was stopped during initialize."
            )
        elif status_code != "SNW":
            self._is_initialized = False
            return (False, self._unexpected_code_message("status", status_code))

        self._is_initialized = True
        return (
            True,
            init_message + " Power connection was not explicitly probed.",
        )

    def deinitialize(self, reset_init_flag: bool = True, close_serial: bool = False) -> Tuple[bool, str]:
        stop_message = None
        if self.ser.is_open:
            was_successful, status_code = self._request_code("status", self._response_timeout_s)
            if not was_successful:
                return (False, status_code)
            if status_code == "SIW":
                was_successful, stop_message = self._stop_sonicating_internal()
                if not was_successful:
                    return (False, stop_message)
            elif status_code != "SNW":
                return (False, self._unexpected_code_message("status", status_code))

        if close_serial and self.ser.is_open:
            self.ser.close()
        if reset_init_flag:
            self._is_initialized = False

        message = "Successfully deinitialized the sonicator interface."
        if stop_message is not None:
            message += " Sonication was stopped during deinitialize."
        return (True, message)

    @check_serial
    def probe_power_connection(self) -> Tuple[bool, str]:
        was_successful, status_code = self._request_code("status", self._response_timeout_s)
        if not was_successful:
            return (False, status_code)
        if status_code == "SIW":
            return (
                True,
                "Sonicator power connection is present. Status indicates sonication is active, so the intrusive power probe was skipped.",
            )
        if status_code != "SNW":
            return (False, self._unexpected_code_message("status", status_code))

        was_successful, response_code = self._request_code("power", self._power_probe_timeout_s)
        if not was_successful:
            return (False, response_code)
        if response_code == "PIO":
            return (True, self.RESPONSE_MESSAGES[response_code])
        if response_code == "PNO":
            return (False, self.RESPONSE_MESSAGES[response_code])
        return (False, self._unexpected_code_message("power", response_code))

    @check_serial
    def get_status(self) -> Tuple[bool, str]:
        was_successful, status_code = self._request_code("status", self._response_timeout_s)
        if not was_successful:
            return (False, status_code)
        if status_code in ("SIW", "SNW"):
            return (True, self.RESPONSE_MESSAGES[status_code])
        return (False, self._unexpected_code_message("status", status_code))

    @check_serial
    @check_initialized
    def start_sonicating(self) -> Tuple[bool, str]:
        was_successful, response_code = self._request_code("turnon", self._response_timeout_s)
        if not was_successful:
            return (False, response_code)
        if response_code in ("SAN", "STN"):
            return (True, self.RESPONSE_MESSAGES[response_code])
        return (False, self._unexpected_code_message("turnon", response_code))

    @check_serial
    @check_initialized
    def stop_sonicating(self) -> Tuple[bool, str]:
        return self._stop_sonicating_internal()

    @check_serial
    @check_initialized
    def press_button(self) -> Tuple[bool, str]:
        was_successful, response_code = self._request_code("button", self._response_timeout_s)
        if not was_successful:
            return (False, response_code)
        if response_code == "BIP":
            return (True, self.RESPONSE_MESSAGES[response_code])
        return (False, self._unexpected_code_message("button", response_code))

    def _stop_sonicating_internal(self) -> Tuple[bool, str]:
        was_successful, response_code = self._request_code("turnoff", self._response_timeout_s)
        if not was_successful:
            return (False, response_code)
        if response_code in ("SAF", "STF"):
            return (True, self.RESPONSE_MESSAGES[response_code])
        return (False, self._unexpected_code_message("turnoff", response_code))

    def _unexpected_code_message(self, command_keyword: str, response_code: str) -> str:
        if response_code in self.RESPONSE_MESSAGES:
            return (
                f"Unexpected response for '{command_keyword}': "
                + f"{response_code} ({self.RESPONSE_MESSAGES[response_code]})"
            )
        return f"Received unknown response code for '{command_keyword}': {response_code}"

    @check_serial
    def _request_code(self, command_keyword: str, response_timeout_s: float) -> Tuple[bool, str]:
        command = f"{self._command_prefix}{command_keyword}{self._line_terminator}"
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self._debug(f"TX -> {command!r}")
        self.ser.write(command.encode("ascii"))
        self.ser.flush()
        return self._read_response_code(response_timeout_s)

    def _read_response_code(self, response_timeout_s: float) -> Tuple[bool, str]:
        deadline = time.time() + response_timeout_s
        chunks = []

        while time.time() < deadline:
            piece = self.ser.readline()
            if not piece:
                continue
            chunks.append(piece)
            if b"\n" in piece or b"\r" in piece:
                break

        if not chunks:
            return (False, "Timed out waiting for sonicator response.")

        response = b"".join(chunks).decode("ascii", errors="ignore").strip()
        self._debug(f"RX <- {response!r}")
        if response == "":
            return (False, "Received an empty sonicator response.")
        return (True, response)
