from typing import Optional, Tuple

from .device import ArduinoSerialDevice, check_initialized, check_serial


class SubstrateLinearStageBase(ArduinoSerialDevice):
    """Shared Arduino serial wrapper for the substrate hotel/dispenser linear stages."""

    def __init__(
            self,
            name: str,
            port: str,
            max_position_mm: float,
            baudrate: int = 9600,
            timeout: float = 1.0,
            connect_delay_s: float = 5.0,
            ready_timeout_s: float = 5.0,
            home_timeout_s: float = 30.0,
            move_timeout_s: float = 30.0):
        super().__init__(name, port, baudrate, timeout)
        self._max_position_mm = float(max_position_mm)
        self._connect_delay_s = float(connect_delay_s)
        self._ready_timeout_s = float(ready_timeout_s)
        self._home_timeout_s = float(home_timeout_s)
        self._move_timeout_s = float(move_timeout_s)

    def get_init_args(self) -> dict:
        return {
            "name": self._name,
            "port": self._port,
            "max_position_mm": self._max_position_mm,
            "baudrate": self._baudrate,
            "timeout": self._timeout,
            "connect_delay_s": self._connect_delay_s,
            "ready_timeout_s": self._ready_timeout_s,
            "home_timeout_s": self._home_timeout_s,
            "move_timeout_s": self._move_timeout_s,
        }

    def update_init_args(self, args_dict: dict):
        self._name = args_dict["name"]
        self._port = args_dict["port"]
        self._max_position_mm = float(args_dict["max_position_mm"])
        self._baudrate = args_dict["baudrate"]
        self._timeout = args_dict["timeout"]
        self._connect_delay_s = float(args_dict.get("connect_delay_s", 5.0))
        self._ready_timeout_s = float(args_dict.get("ready_timeout_s", 5.0))
        self._home_timeout_s = float(args_dict.get("home_timeout_s", 30.0))
        self._move_timeout_s = float(args_dict.get("move_timeout_s", 30.0))

    def connect(self) -> Tuple[bool, str]:
        return self.start_serial(delay=self._connect_delay_s)

    @check_serial
    def initialize(self) -> Tuple[bool, str]:
        ready_success, ready_message = self.get_response(response_timeout=self._ready_timeout_s)
        if not ready_success or "Ready" not in ready_message:
            self._is_initialized = False
            return (False, "Arduino did not send ready signal. Response: " + str(ready_message))

        success, message = self.home()
        if not success:
            self._is_initialized = False
            return (False, "Homing failed: " + str(message))

        self._is_initialized = True
        return (True, "Device initialized and homed.")

    @check_serial
    def deinitialize(
            self,
            reset_init_flag: bool = True,
            close_serial: bool = False) -> Tuple[bool, str]:
        if reset_init_flag:
            self._is_initialized = False
        if close_serial and self.ser.is_open:
            self.ser.close()
        return (True, "Device deinitialized.")

    @check_serial
    def home(self) -> Tuple[bool, str]:
        self.ser.write(b'H\n')
        return self.check_ack_succ(succ_timeout=self._home_timeout_s)

    @check_serial
    @check_initialized
    def move_to_position(
            self,
            position_mm: float,
            speed_mm_per_s: float,
            move_timeout: Optional[float] = None) -> Tuple[bool, str]:
        if not (0.0 <= float(position_mm) <= self._max_position_mm):
            return (
                False,
                f"Command error: position {position_mm} mm is out of range (0-{self._max_position_mm} mm).",
            )

        command = f"M{float(position_mm)},{float(speed_mm_per_s)}\n".encode("ascii")
        self.ser.write(command)

        ack_success, ack_message = self.check_response(
            self.char_ACK,
            self.char_delimiter,
            response_timeout=2.0,
        )
        if not ack_success:
            return (False, "Did not receive ACK for move command: " + str(ack_message))

        timeout_s = self._move_timeout_s if move_timeout is None else float(move_timeout)
        succ_success, succ_message = self.check_response(
            self.char_SUCC,
            self.char_delimiter,
            response_timeout=timeout_s,
        )
        if not succ_success:
            return (False, "Move did not complete successfully: " + str(succ_message))

        return (True, succ_message)
