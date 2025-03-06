from .device import ArduinoSerialDevice, SerialDevice, check_initialized, check_serial
import serial
from time import sleep
from typing import Optional, Tuple


class SHT85HumidityTempSensor(ArduinoSerialDevice):
    """Humidity and Temperature Sensor"""

    def __init__(
        self, name: str, port: str, baudrate: int = 9600, timeout: Optional[float] = 1.0
    ):
        super().__init__(name, port, baudrate, timeout)
        # self.ser = serial.Serial()
        # self.ser.bytesize = serial.EIGHTBITS
        # self.ser.parity = serial.PARITY_NONE

    def get_init_args(self) -> dict:
        args_dict = {
            "name": self._name,
            "port": self._port,
            "baudrate": self._baudrate,
            "timeout": self._timeout,
        }
        return args_dict

    def update_init_args(self, args_dict: dict):
        self._name = args_dict["name"]
        self._port = args_dict["port"]
        self._baudrate = args_dict["baudrate"]
        self._timeout = args_dict["timeout"]

    def initialize(self) -> Tuple[bool, str]:
        # self.ser.setDTR(False)
        # self.ser.flushInput()
        # self.ser.setDTR(True)
        # self.ser.open()
        self._is_initialized = True
        return (True, "Initialized humidity and temperature sensor")

    def deinitialize(self) -> Tuple[bool, str]:
        self.ser.close()
        self._is_initialized = False
        return (True, "Deinitialized humidity and temperature sensor")

    @check_serial
    @check_initialized
    def get_humidity(self) -> Tuple[bool, float, str]:
        self.ser.write(b"H")
        sleep(0.75)
        humidity = float(self.ser.readline().strip().decode())
        return (True, f"The relative humidity is {humidity}%")

    @check_serial
    @check_initialized
    def get_temp(self) -> Tuple[bool, float, str]:
        self.ser.write(b"T")
        sleep(0.75)
        temp = float(self.ser.readline().strip().decode())
        return (True, f"The temperature is {temp} degrees C")
