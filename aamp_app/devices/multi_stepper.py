from typing import Optional, Tuple, Union
import serial
import functools

from .device import ArduinoSerialDevice, check_initialized, check_serial


def check_stepper_num(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # could be a kwarg or arg
        if 'stepper_number' in kwargs:
            stepper_number = kwargs['stepper_number']
        else:
            stepper_number = args[0]

        if not self.is_stepper_num_valid(stepper_number):
            return (False, "Stepper number is not valid or not part of passed tuple during construction.")
        return func(self, *args, **kwargs)
    return wrapper


class MultiStepper(ArduinoSerialDevice):
    def __init__(
            self,
            name: str, 
            port: str, 
            baudrate: int, 
            timeout: Optional[float] = 1.0, 
            stepper_list: Tuple[int, ...] = (1,),
            move_timeout: float = 30.0):
        
        super().__init__(name, port, baudrate, timeout)
        self._stepper_list = stepper_list
        self._move_timeout = move_timeout # max move timeout for ALL possible motors controlled by arduino

    def get_init_args(self) -> dict:
        args_dict = {
            "name": self._name,
            "port": self._port,
            "baudrate": self._baudrate,
            "timeout": self._timeout,
            "stepper_list": self._stepper_list,
            "move_timeout": self._move_timeout
        }
        return args_dict

    def update_init_args(self, args_dict: dict):
        self._name = args_dict["name"]
        self._port = args_dict["port"]
        self._baudrate = args_dict["baudrate"]
        self._timeout = args_dict["timeout"]
        self._stepper_list = args_dict["stepper_list"]
        self._move_timeout = args_dict["move_timeout"]

    def initialize(self):
        for stepper in self._stepper_list:
            was_homed, comment = self.home(stepper)
            if not was_homed:
                self._is_initialized = False
                return (was_homed, comment)

        self._is_initialized = True
        return (True, "All stepper motors " + str(self._stepper_list) + " successfully homed and initialized. All current positions set to zero.")

    def deinitialize(self, reset_init_flag: bool = True):
        for stepper in self._stepper_list:
            was_zeroed, comment = self.move_absolute(stepper, 0.0)
            if not was_zeroed:
                return (was_zeroed, comment)

        if reset_init_flag:
            self._is_initialized = False

        return (True, "All stepper motors " + str(self._stepper_list) + " successfully deinitialized by moving to position zero.")
    
    @check_serial
    @check_stepper_num
    def home(self, stepper_number: int) -> Tuple[bool, str]:
        # if not self.ser.is_open:    
        #     return (False, "Serial port " + self._port + " is not open. ")
        # if not self.is_stepper_num_valid(stepper_number):
        #     return (False, "Stepper number is not valid or not part of passed tuple during construction.")

        command = ">hm " + str(stepper_number) + "\n"
        self.ser.write(command.encode('ascii'))
        return self.check_ack_succ(ack_timeout=1, succ_timeout=self._move_timeout)

    @check_serial
    @check_initialized
    @check_stepper_num
    def move_absolute(self, stepper_number: int, position: float) -> Tuple[bool, str]:
        # if not self.ser.is_open:    
        #     return (False, "Serial port " + self._port + " is not open. ")
        # elif not self.is_stepper_num_valid(stepper_number):
        #     return (False, "Stepper number is not valid or not part of passed tuple during construction.")
        # elif not self._is_initialized:
        #     return (False, "Stepper motor " + str(stepper_number) + " is not initialized.")
        # else:
        # if not self.is_stepper_num_valid(stepper_number):
        #     return (False, "Stepper number is not valid or not part of passed tuple during construction.")

        command = ">mv " + str(stepper_number) + " " + str(position) + "\n"
        self.ser.write(command.encode('ascii'))
        return self.check_ack_succ(ack_timeout=1, succ_timeout=self._move_timeout)

    @check_serial
    @check_initialized
    @check_stepper_num
    def move_relative(self, stepper_number: int, distance: float) -> Tuple[bool, str]:
        # if not self.ser.is_open:    
        #     return (False, "Serial port " + self._port + " is not open. ")
        # elif not self.is_stepper_num_valid(stepper_number):
        #     return (False, "Stepper number is not valid or not part of passed tuple during construction.")
        # elif not self._is_initialized:
        #     return (False, "Stepper motor " + str(stepper_number) + " is not initialized.")
        # else:
        # if not self.is_stepper_num_valid(stepper_number):
        #     return (False, "Stepper number is not valid or not part of passed tuple during construction.")

        command = ">mvr " + str(stepper_number) + " " + str(distance) + "\n"
        self.ser.write(command.encode('ascii'))
        return self.check_ack_succ(ack_timeout=1.0, succ_timeout=self._move_timeout)

    @check_serial
    @check_initialized
    @check_stepper_num
    def position(self, stepper_number: int) -> Tuple[bool, Union[float, str]]:
        # if not self.ser.is_open:    
        #     return (False, "Serial port " + self._port + " is not open. ")
        # elif not self.is_stepper_num_valid(stepper_number):
        #     return (False, "Stepper number is not valid or not part of passed tuple during construction.")
        # elif not self._is_initialized:
        #     return (False, "Stepper motor " + str(stepper_number) + " is not initialized.")
        # else:
        # if not self.is_stepper_num_valid(stepper_number):
        #     return (False, "Stepper number is not valid or not part of passed tuple during construction.")

        command = ">wm " + str(stepper_number) + "\n"
        self.ser.write(command.encode('ascii'))
        was_successful, comment = self.check_ack_succ()

        if not was_successful:
            return (was_successful, comment)

        has_position, position_str = super().parse_equal_sign(comment)

        if not has_position:
            return (has_position, "Message from device did not contain motor position.")
        
        return (True, float(position_str))
 
    def is_stepper_num_valid(self, stepper_number: int) -> bool:
        if stepper_number in self._stepper_list:
            return True
        else:
            return False


# The arduino program is able to check if the passed stepper number is valid or not and return True/False
# Therefore, I initially concluded that there is no need to validate the stepper number argument in the methods here or pass it during construction
# However, suppose there are (1, 2, 3) steppers and we only pass (1,2) to initialize_all, then the MultiStepper object will be flagged as 
# being initialized and it will be possible to send commands to stepper #3. Although the arduino may be able to prevent moving stepper #3 if its not homed
# it is technically possible for the command to be valid from the host's perspective which in this particular case should not happen even if the arduino will catch it
# Also suppose the arduino doesn't have a check at it's level then we will be able to move stepper #3 without properly initializing it
# therefore we should declare during construction which steppers we plan to use with an immutable tuple 
# and still check that a passed stepper_number argument is always in that tuple

# currently the way we determine if the movement completed or not is by waiting for the arduino to send a SUCC confirmation once it reaches its target
# this means that the host side needs to implement a timeout longer than the movement duration, either using a blanket large value or based on the speed, distance, and a safe extra time
# At the moment a blanket timeout value is used based on the known stepper application
# Other better or worse ways would be the following:
# -poll the position of the arduino repeatedly until it matches with the desired target position. 
#   However, if the arduino gets stuck this could infinite loop meaning we need another timeout
#   Additionally if there is small error between target and acceptable position, that needs to be accounted for and just adds more complexity
# -poll whether the arduino is moving or not. Better than polling position but what if arduino never moves or never stops for some reason. 
#   this means we may still need to implement a timeout and also have the arduino spit out error messages for these cases
#
# Regarding the speed of the stepper motor, at the moment it is coded into the Arduino. It can easily be changed to a modifiable parameter set by a serial command
# And then we can control it from here. But at the moment this is not implemented as my current use case for custom stepper motors is purely for positioning purposes only