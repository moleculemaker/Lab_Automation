import time
from typing import Dict, Optional, Tuple, Union
import functools

from .device import SerialDevice, check_initialized, check_serial


def check_axis_num(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # could be a kwarg or arg
        if 'axis_number' in kwargs:
            axis_number = kwargs['axis_number']
        else:
            axis_number = args[0]
            
        if not self.is_axis_num_valid(axis_number):
            return (False, "Axis number is not valid or not part of passed tuple during construction.")
        return func(self, *args, **kwargs)
    return wrapper

class NewportESP301(SerialDevice):
    UNIT_CODE_BY_NAME = {
        "encoder_count": 0,
        "motor_step": 1,
        "mm": 2,
        "micrometer": 3,
        "inch": 4,
        "milli_inch": 5,
        "micro_inch": 6,
        "deg": 7,
        "gradian": 8,
        "radian": 9,
        "milliradian": 10,
        "microradian": 11,
    }

    DEFAULT_AXIS_CONFIG = {
        "motion_type": "linear",
        "units": "mm",
        "home_mode": "OR4",
        "zero_position": 0.0,
    }

    def __init__(
            self, 
            name: str,
            port: str,
            baudrate: int = 921600,
            timeout: Optional[float] = 1.0,
            axis_list: Tuple[int, ...] = (1,),
            default_speed: float = 20.0,
            poll_interval: float = 0.1,
            axis_configs: Optional[Dict[int, Dict[str, Union[str, float]]]] = None):

        super().__init__(name, port, baudrate, timeout)
        self._axis_list = axis_list
        self._default_speed = default_speed #make list
        # self._default_speed_list = defaults_speed_list
        self._poll_interval = poll_interval
        self._max_speed = 200.0 # make list
        # self._max_speed_list = max_speed_list
        self._axis_configs = self._normalize_axis_configs(axis_configs)

    def get_init_args(self) -> dict:
        args_dict = {
            "name": self._name,
            "port": self._port,
            "baudrate": self._baudrate,
            "timeout": self._timeout,
            "axis_list": self._axis_list,
            "default_speed": self._default_speed,
            "poll_interval": self._poll_interval,
            "axis_configs": self._axis_configs,
        }
        return args_dict

    def update_init_args(self, args_dict: dict):
        self._name = args_dict["name"]
        self._port = args_dict["port"]
        self._baudrate = args_dict["baudrate"]
        self._timeout = args_dict["timeout"]
        self._axis_list = args_dict["axis_list"]
        self._default_speed = args_dict["default_speed"]
        self._poll_interval = args_dict["poll_interval"]
        self._axis_configs = self._normalize_axis_configs(args_dict.get("axis_configs"))

    @property
    def default_speed(self) -> float:
        return self._default_speed

    @default_speed.setter
    def default_speed(self, speed: float):
        if speed > 0.0 and speed < self._max_speed:
            self._default_speed = speed

    def _normalize_axis_configs(
        self,
        axis_configs: Optional[Dict[int, Dict[str, Union[str, float]]]]
    ) -> Dict[int, Dict[str, Union[str, float]]]:
        normalized_configs: Dict[int, Dict[str, Union[str, float]]] = {}

        for axis in self._axis_list:
            config = dict(NewportESP301.DEFAULT_AXIS_CONFIG)
            if axis_configs and axis in axis_configs:
                config.update(axis_configs[axis])

            motion_type = str(config.get("motion_type", "linear")).lower()
            units = config.get("units")
            if units is None:
                units = "deg" if motion_type == "rotary" else "mm"
            else:
                units = str(units).lower()

            config["motion_type"] = motion_type
            config["units"] = units
            config["home_mode"] = str(config.get("home_mode", "OR4")).upper()
            config["zero_position"] = float(config.get("zero_position", 0.0))
            config["default_speed"] = float(config.get("default_speed", self._default_speed))
            config["max_speed"] = float(config.get("max_speed", self._max_speed))
            normalized_configs[axis] = config

        return normalized_configs

    def _get_axis_config(self, axis_number: int) -> Dict[str, Union[str, float]]:
        if axis_number not in self._axis_configs:
            self._axis_configs = self._normalize_axis_configs(self._axis_configs)
        return self._axis_configs[axis_number]

    def _get_unit_code(self, axis_number: int) -> int:
        units = str(self._get_axis_config(axis_number)["units"]).lower()
        if units not in NewportESP301.UNIT_CODE_BY_NAME:
            raise ValueError(f"Unsupported ESP301 unit '{units}' for axis {axis_number}")
        return NewportESP301.UNIT_CODE_BY_NAME[units]

    def _get_axis_default_speed(self, axis_number: int) -> float:
        return float(self._get_axis_config(axis_number)["default_speed"])

    def _get_axis_max_speed(self, axis_number: int) -> float:
        return float(self._get_axis_config(axis_number)["max_speed"])

    # check_error already has serial check
    # easier to just set is_intialized False at the very beginning
    # do for all receivers
    def initialize(self) -> Tuple[bool, str]:
        # if not self.ser.is_open:
        #     return (False, "Serial port " + self._port + " is not open. ")

        was_successful, message = self.check_error() # just used to flush error and serial input buffer if there is an error
        if not was_successful:
            return (was_successful, message)

        self.ser.reset_input_buffer() # flush the serial input buffer even if there was no error

        for axis in self._axis_list:
            # Make sure axis motor is turned on
            was_turned_on, message = self.axis_on(axis)
            if not was_turned_on:
                self._is_initialized = False
                return (was_turned_on, message)

            try:
                unit_code = self._get_unit_code(axis)
            except ValueError as exc:
                self._is_initialized = False
                return (False, str(exc))

            axis_max_speed = self._get_axis_max_speed(axis)
            axis_default_speed = self._get_axis_default_speed(axis)
            command = (
                str(axis) + "SN" + str(unit_code)
                + ";" + str(axis) + "SH0"
                + ";" + str(axis) + "VU" + str(axis_max_speed)
                + ";" + str(axis) + "VA" + str(axis_default_speed)
                + "\r"
            )
            self.ser.write(command.encode('ascii'))

        # Make sure initialization of settings was successful
        was_successful, message = self.check_error()
        if not was_successful:
            self._is_initialized = False
            return (was_successful, message)

        for axis in self._axis_list:
            was_homed, message = self.home(axis)
            if not was_homed:
                self._is_initialized = False
                return (was_homed, message)
    
        self._is_initialized = True
        return (True, "Successfully initialized ESP301 axes with axis-specific units, speed settings, and homing.")

    # move_speed_absolute already has serial check
    def deinitialize(self, reset_init_flag: bool = True) -> Tuple[bool, str]:
        # if not self.ser.is_open:
        #     return (False, "Serial port " + self._port + " is not open. ")

        for axis in self._axis_list:
            zero_position = float(self._get_axis_config(axis)["zero_position"])
            was_zeroed, message = self.move_speed_absolute(axis, zero_position, speed=None)
            if not was_zeroed:
                return (was_zeroed, message)

        if reset_init_flag:
            self._is_initialized = False

        return (True, "Successfully deinitialized axes by moving to position zero.")

    # make a home_all function
    @check_serial
    @check_axis_num
    def home(self, axis_number: int) -> Tuple[bool, str]:
        # if not self.ser.is_open:
        #     return (False, "Serial port " + self._port + " is not open. ")

        home_mode = str(self._get_axis_config(axis_number)["home_mode"])
        command = str(axis_number) + home_mode + "\r"
        self.ser.write(command.encode('ascii'))

        while self.is_any_moving():
            time.sleep(self._poll_interval)
        # pause one more time in case motor stopped moving but position has not been reset yet     
        time.sleep(self._poll_interval)

        was_successful, message = self.check_error()
        if not was_successful:
            return (was_successful, message)
        else:
            axis_config = self._get_axis_config(axis_number)
            return (
                True,
                "Successfully homed axis "
                + str(axis_number)
                + " using "
                + home_mode
                + " in "
                + str(axis_config["units"])
                + "."
            )

    # Consider a decorator for checks?
    @check_serial
    @check_initialized
    @check_axis_num
    def move_speed_absolute(self, axis_number: int = 1, position: Optional[float] = None, speed: Optional[float] = None) -> Tuple[bool, str]:
        # if not self.ser.is_open:
        # #     return (False, "Serial port " + self._port + " is not open. ")
        # if not self.is_axis_num_valid(axis_number):
        #     return (False, "Axis number is not valid or not part of passed tuple during construction.")
        # if not self._is_initialized:
        #     return (False, "ESP301 axes are not initialized.")
        
        # I want axis number to be the first arg so the decorator can pick it up as arg[0]
        # but I also want axis_number to have a default value of 1, so position needs a default value now
        if position is None:
            return (False, "Position was not specified")

        if speed is None:
            speed = self._get_axis_default_speed(axis_number)

        command = str(axis_number) + "VA" + str(speed) +"\r"
        self.ser.write(command.encode('ascii'))

        was_successful, message = self.check_error()
        if not was_successful:
            return (was_successful, message)

        if position >= 0.0:
            sign = "+"
        else:
            sign = "-"

        # removed the WS command because it causes timeouts when checking if moving 
        # command = str(axis_number) + "PA" + sign + str(abs(position)) + ";" + str(axis_number) + "WS\r"
        command = str(axis_number) + "PA" + sign + str(abs(position)) + "\r"
        self.ser.write(command.encode('ascii'))

        while self.is_moving(axis_number):
            time.sleep(self._poll_interval)

        was_successful, message = self.check_error()
        if not was_successful:
            return (was_successful, message)
        else:
            return (True, "Successfully completed absolute move at " + str(position))

    @check_serial
    @check_initialized
    @check_axis_num
    def move_speed_relative(self, axis_number: int = 1, distance: Optional[float] = None, speed: Optional[float] = None) -> Tuple[bool, str]:
        # if not self.ser.is_open:
        # #     return (False, "Serial port " + self._port + " is not open. ")
        # if not self.is_axis_num_valid(axis_number):
        #     return (False, "Axis number is not valid or not part of passed tuple during construction.")
        # if not self._is_initialized:
        #     return (False, "ESP301 axes are not initialized.")
        if distance is None:
            return (False, "Distance was not specified")
        
        if speed is None:
            speed = self._get_axis_default_speed(axis_number)

        command = str(axis_number) + "VA" + str(speed) +"\r"
        self.ser.write(command.encode('ascii'))

        was_successful, message = self.check_error()
        if not was_successful:
            return (was_successful, message)

        if distance >= 0.0:
            sign = "+"
        else:
            sign = "-"

        # removed the WS command because it causes timeouts when checking if moving 
        # command = str(axis_number) + "PR" + sign + str(abs(distance)) + ";" + str(axis_number) + "WS\r"
        command = str(axis_number) + "PR" + sign + str(abs(distance)) + "\r"

        self.ser.write(command.encode('ascii'))

        while self.is_moving(axis_number):
            time.sleep(self._poll_interval)

        was_successful, message = self.check_error()
        if not was_successful:
            return (was_successful, message)
        else:
            return (True, "Successfully completed relative move by " + str(distance))
        

    def is_axis_num_valid(self, axis_number: int) -> bool:
        if axis_number in self._axis_list:
            return True
        else:
            return False
    
    # check axis num
    @check_serial
    @check_axis_num
    def is_moving(self, axis_number: int = 1) -> bool:
        # if not self.ser.is_open:
        #     return False
        # else:
        command = str(axis_number) + "MD?\r"
        self.ser.write(command.encode('ascii'))
        response = self.ser.readline()

        if response.strip().decode('ascii') == '0':
            # motion is not done = is moving
            return True
        else:
            # includes timeout case
            return False

    def is_any_moving(self) -> bool:
        is_moving_list = []
        for ndx, axis_number in enumerate(self._axis_list):
            command = str(axis_number) + "MD?\r"
            self.ser.write(command.encode('ascii'))
            response = self.ser.readline()

            if response.strip().decode('ascii') == '0':
                is_moving_list.append(True)
            else:
                is_moving_list.append(False)

        if any(is_moving_list):
            return True
        else: 
            return False

    @check_serial
    def check_error(self) -> Tuple[bool, str]:
        # not needed for queries, but use when instructing to do something
        
        # if not self.ser.is_open:
        #     return (False, "Serial port " + self._port + " is not open. ")

        command = "TB?\r"
        self.ser.write(command.encode('ascii'))
        response = self.ser.readline()

        if response == b'':
            return (False, "Response timed out.")
        
        response = response.strip().decode('ascii')

        if response[0] == '0':
            return (True, "No errors.")
        else:
            # flush the error buffer
            for n in range(10):
                self.ser.write(command.encode('ascii'))
                self.ser.readline()
            # flush the serial input buffer
            time.sleep(0.1)
            self.ser.reset_input_buffer()
            return (False, response)
    
    @check_serial
    @check_axis_num
    def position(self, axis_number: int = 1) -> Tuple[bool, Union[str, float]]:
        # if not self.ser.is_open:
        #     return (False, "Serial port " + self._port + " is not open. ")
        # if not self.is_axis_num_valid(axis_number):
        #     return (False, "Axis number is not valid or not part of passed tuple during construction.")

        command = str(axis_number) + "TP\r"
        self.ser.write(command.encode('ascii'))
        position_str = self.ser.readline()
        if position_str == b'':
            return (False, "Response timed out.")
        else:    
            return (True, float(position_str.strip().decode('ascii')))

    @check_serial
    @check_axis_num
    def axis_on(self, axis_number: int = 1) -> Tuple[bool, str]:
        # if not self.ser.is_open:
        #     return (False, "Serial port " + self._port + " is not open. ")
        # if not self.is_axis_num_valid(axis_number):
        #     return (False, "Axis number is not valid or not part of passed tuple during construction.")

        command = str(axis_number) + "MO\r"
        self.ser.write(command.encode('ascii'))

        was_successful, message = self.check_error()
        if not was_successful:
            return (was_successful, message)

        command = str(axis_number) + "MO?\r"
        self.ser.write(command.encode('ascii'))
        response = self.ser.readline()

        if response.strip().decode('ascii') == '1':
            return (True, "Axis " + str(axis_number) + " motor successfully turned ON.")
        else:
            # also means timeout
            return (False, "Axis " + str(axis_number) + " motor failed to turned ON.")

    @check_serial
    @check_axis_num
    def axis_off(self, axis_number: int = 1) -> Tuple[bool, str]:
        # if not self.ser.is_open:
        #     return (False, "Serial port " + self._port + " is not open. ")
        # if not self.is_axis_num_valid(axis_number):
        #     return (False, "Axis number is not valid or not part of passed tuple during construction.")

        command = str(axis_number) + "MF\r"
        self.ser.write(command.encode('ascii'))

        was_successful, message = self.check_error()
        if not was_successful:
            return (was_successful, message)

        command = str(axis_number) + "MF?\r"
        self.ser.write(command.encode('ascii'))
        response = self.ser.readline()

        if response.strip().decode('ascii') == '0':
            return (True, "Axis " + str(axis_number) + " motor successfully turned OFF.")
        else:
            # also means timeout
            return (False, "Axis " + str(axis_number) + " motor failed to turned OFF.")
