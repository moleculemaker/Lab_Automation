from typing import Optional, Tuple
from struct import pack, unpack
import time

from .device import SerialDevice, check_serial, check_initialized


class Z812(SerialDevice):
    DEVICE_UNIT_SCALE = 34555
    MIN_POSITION_MM = 0.0
    MAX_POSITION_MM = 12.0
    HOME_TIMEOUT_S = 120.0
    MOVE_TIMEOUT_S = 120.0

    def __init__(
        self,
        name: str,
        port: str = "COM6",
        baudrate: int = 115200,
        timeout: Optional[float] = 0.1,
        destination: int = 0x50,
        source: int = 0x01,
        channel: int = 1,
    ):
        super().__init__(name, port, baudrate, timeout)
        self._destination = destination
        self._source = source
        self._channel = channel
        self._is_enabled = False

    def _wait_for_message(self, expected_header: bytes, timeout_s: float) -> Tuple[bool, str]:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            response = self.ser.read(2)
            if response == expected_header:
                return (True, "")
            if response == b"":
                continue
        return (False, "Response timed out while waiting for Z812 controller message.")

    def _validate_position(self, position: float) -> Tuple[bool, str]:
        if position < self.MIN_POSITION_MM or position > self.MAX_POSITION_MM:
            return (
                False,
                "Position "
                + str(position)
                + " is out of range. Expected "
                + str(self.MIN_POSITION_MM)
                + " to "
                + str(self.MAX_POSITION_MM)
                + " mm.",
            )
        return (True, "")

    def get_init_args(self) -> dict:
        return {
            "name": self._name,
            "port": self._port,
            "baudrate": self._baudrate,
            "timeout": self._timeout,
            "destination": self._destination,
            "source": self._source,
            "channel": self._channel,
        }

    def update_init_args(self, args_dict: dict):
        self._name = args_dict["name"]
        self._port = args_dict["port"]
        self._baudrate = args_dict["baudrate"]
        self._timeout = args_dict["timeout"]
        self._destination = args_dict["destination"]
        self._source = args_dict["source"]
        self._channel = args_dict["channel"]

    @check_serial
    def initialize(self) -> Tuple[bool, str]:
        self._is_initialized = False

        was_enabled, message = self.set_enabled_state(True)
        if not was_enabled:
            return (was_enabled, message)

        self.ser.write(pack("<HBBBB", 0x0443, self._channel, 0x00, self._destination, self._source))
        was_homed, message = self._wait_for_message(pack("<H", 0x0444), self.HOME_TIMEOUT_S)
        if not was_homed:
            return (was_homed, message)

        self.ser.flushInput()
        self.ser.flushOutput()
        self._is_initialized = True
        return (True, "Successfully initialized Z812 by homing it.")

    def deinitialize(self) -> Tuple[bool, str]:
        if self.ser.is_open:
            self.set_enabled_state(False)
        self._is_initialized = False
        return (True, "Successfully deinitialized Z812.")

    @check_serial
    def get_enabled_state(self) -> bool:
        self.ser.write(pack("<HBBBB", 0x0211, self._channel, 0x00, self._destination, self._source))
        response = self.ser.read(6)
        if len(response) < 4:
            return False
        self._is_enabled = response[2] == 0x01
        return self._is_enabled

    @check_serial
    def set_enabled_state(self, state: bool) -> Tuple[bool, str]:
        if state:
            self.ser.write(pack("<HBBBB", 0x0210, self._channel, 0x01, self._destination, self._source))
        else:
            self.ser.write(pack("<HBBBB", 0x0210, self._channel, 0x02, self._destination, self._source))
        time.sleep(0.1)
        self.ser.flushInput()
        self.ser.flushOutput()
        self._is_enabled = state
        return (True, "Successfully set enable state to " + str(state) + ".")

    @check_serial
    @check_initialized
    def get_position(self) -> float:
        self.ser.write(pack("<HBBBB", 0x0411, self._channel, 0x00, self._destination, self._source))
        _, _, position_dunits = unpack("<6sHI", self.ser.read(12))
        return position_dunits / float(self.DEVICE_UNIT_SCALE)

    @check_serial
    @check_initialized
    def move_absolute(self, position: float) -> Tuple[bool, str]:
        is_valid_position, message = self._validate_position(position)
        if not is_valid_position:
            return (False, message)

        dunit_pos = int(self.DEVICE_UNIT_SCALE * position)
        self.ser.write(
            pack(
                "<HBBBBHI",
                0x0453,
                0x06,
                0x00,
                self._destination | 0x80,
                self._source,
                self._channel,
                dunit_pos,
            )
        )
        was_moved, message = self._wait_for_message(pack("<H", 0x0464), self.MOVE_TIMEOUT_S)
        if not was_moved:
            return (was_moved, message)

        self.ser.flushInput()
        self.ser.flushOutput()
        return (True, "Successfully moved Z812 to position " + str(position) + " mm.")

    @check_serial
    @check_initialized
    def move_relative(self, distance: float) -> Tuple[bool, str]:
        target_position = self.get_position() + distance
        is_valid_position, message = self._validate_position(target_position)
        if not is_valid_position:
            return (False, message)

        dunit_pos = int(self.DEVICE_UNIT_SCALE * distance)
        self.ser.write(
            pack(
                "<HBBBBHI",
                0x0448,
                0x06,
                0x00,
                self._destination | 0x80,
                self._source,
                self._channel,
                dunit_pos,
            )
        )
        was_moved, message = self._wait_for_message(pack("<H", 0x0464), self.MOVE_TIMEOUT_S)
        if not was_moved:
            return (was_moved, message)

        self.ser.flushInput()
        self.ser.flushOutput()
        return (True, "Successfully moved Z812 by distance " + str(distance) + " mm.")
