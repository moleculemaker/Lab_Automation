from abc import ABC, abstractmethod
from typing import Optional, Tuple
import time
import functools
try:
    import serial
except ImportError:
    pass
import json


# Decorator to check if is initialized, optional custom message on fail
# Originally in Device class as a method, but moved to module scope
def check_initialized(func=None, *, message=None):
    if func is None:
        return functools.partial(check_initialized, message=message)

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self._is_initialized:
            if message is None:
                return (False, type(self).__name__ + " object is not initialized.")
            else:
                return (False, message)
        return func(self, *args, **kwargs)
    return wrapper

# consider optional flag to set is_initialized to False on fail
# this is so if this decorator is applied to the initialize function
# the function will have a chance to set is_initialized to False before the wrapper returns
# Note that in some cases the initialize function starts by calling another function that already checks serial
def check_serial(func=None, *, message=None):
    if func is None:
        return functools.partial(check_initialized, message=message)

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.ser.is_open:
            if message is None:
                return (False, "Serial port " + self._port + " is not open.")
            else:
                return (False, message)
        return func(self, *args, **kwargs)
    return wrapper


# *args, **kwargs https://stackoverflow.com/questions/6034662/python-method-overriding-does-signature-matter
# Consider using *args and **kwargs, although you lose the ability of the IDE to hint at the args needed in a signature

class Device(ABC):
    """The Device abstract base class that contains attributes that all devices/receivers should have."""

    def __init__(self, name: str):
        self._name = name
        self._is_initialized = False

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name

    @property
    def is_initialized(self) -> bool:
        """Whether or not the device has been initialized.

        Returns
        -------
        bool
            Returns True if the device is initialized, otherwise returns False.
        """
        return self._is_initialized

    @abstractmethod
    def initialize(self) -> Tuple[bool, str]:
        """The initialize abstract method that all devices should implement.

        Returns
        -------
        Tuple[bool, str]
            Returns a bool describing whether the initialization was successful and a string describing the result.
        """
        pass

    @abstractmethod
    def deinitialize(self) -> Tuple[bool, str]:
        """The deinitialize abstract method that all devices should implement.

        Returns
        -------
        Tuple[bool, str]
            Returns a bool describing whether the deinitialization was successful and a string describing the result.
        """
        pass

    @abstractmethod # uncomment and implement method in all devices
    def get_init_args(self) -> dict:
        """The get_args abstract method that all devices should implement. Method should return a dict with only the arguments needed to initialize the device.

        Returns
        -------
        dict
            Returns a dict containing the arguments needed to initialize the device.
        """
        pass

    @abstractmethod # uncomment and implement method in all devices
    def update_init_args(self, args_dict: dict):
        """The update_init_args abstract method that all devices should implement. Method should update the arguments needed to initialize the device.
        
        Parameters
        ----------
        
        args_dict : dict
            A dict containing the arguments needed to initialize the device.
        """
        pass


class SerialDevice(Device):
    """A Device that uses serial communication."""

    def __init__(self, name: str, port: str, baudrate: int, timeout: Optional[float] = 1.0):
        super().__init__(name)
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self.ser = serial.Serial()

    @property
    def port(self) -> str:
        return self._port
    
    @port.setter
    def port(self, port: str):
        self._port = port

    @property
    def baudrate(self) -> int:
        return self._baudrate
    
    @baudrate.setter
    def baudrate(self, baudrate: int):
        self._baudrate = baudrate

    @property
    def timeout(self) -> Optional[float]:
        return self._timeout
    
    @timeout.setter
    def timeout(self, timeout: Optional[float]):
        self._timeout = timeout

    def start_serial(self, delay: float = 5.0) -> Tuple[bool, str]:
        """Set the serial port parameters and try to open the serial port

        Parameters
        ----------
        delay : float, optional
            How long to wait after opening the serial port before returning, by default 5.0

        Returns
        -------
        Tuple[bool, str]
            Was the serial port opened?, Result message
        """
        # self.ser.port = self._port
        # self.ser.baudrate = self._baudrate
        # self.ser.timeout = self._timeout
        try:
            if not self.ser.is_open:
                self.ser.port = self._port
                self.ser.baudrate = self._baudrate
                self.ser.timeout = self._timeout
                self.ser.open()   
                # delay at least 5s for arduino
                time.sleep(delay)  
                return (True, "Serial port " + self._port + " successfully opened.") 
            # If setting self.ser... before try, then it will restart an arduino and maybe other devices
            # time.sleep(delay)  
            return (True, "Serial port " + self._port + " already opened.")
        except serial.serialutil.SerialException as inst:
            return (False, "Serial port " + self._port + " failed to open. " + str(inst))     
  

class ArduinoSerialDevice(SerialDevice):
    """An arduino serial device that implements the custom ACK/NACK/SUCC/FAIL communication protocol."""

    char_ACK = "ACK"
    char_SUCC = "SUCC"
    char_delimiter = ":"
    partial_timeout = 2.0 # time in seconds to wait if a partial message is received but not newline footer

    def __init__(self, name: str, port: str, baudrate: int, timeout: Optional[float] = 1.0):
        super().__init__(name, port, baudrate, timeout)

    def check_ack_succ(self, ack_timeout: float = 1.0, succ_timeout: float = 1.0) -> Tuple[bool, str]:
        """Checks whether the instruction was acknowledged and successful.

        Parameters
        ----------
        ack_timeout : float, optional
            How long to wait for ACK/NACK response, by default 1.0
        succ_timeout : float, optional
            How long to wait for SUCC/FAIL response, by default 1.0

        Returns
        -------
        Tuple[bool, str]
            Was the instruction acknowledged and succesful?, Result message
        """
        was_acknowledged, ack_comment = self.check_response(
            ArduinoSerialDevice.char_ACK, 
            ArduinoSerialDevice.char_delimiter, 
            ack_timeout)

        if not was_acknowledged:
            return (was_acknowledged, ack_comment)

        return self.check_response(
            ArduinoSerialDevice.char_SUCC, 
            ArduinoSerialDevice.char_delimiter, 
            succ_timeout)
   
    # in future may alter control_char to be of type Union[str, bytes] and be able to process a byte control character
    def check_response(self, control_char: str, delimiter: str, response_timeout: float = 1.0) -> Tuple[bool, str]:
        """Checks whether a response with a particular starting string was received.

        Parameters
        ----------
        control_char : str
            The string that is being checked for
        delimiter : str
            The delimiter between the control_char string and any additional information or data.
        response_timeout : float, optional
            How long to wait for the response, by default 1.0

        Returns
        -------
        Tuple[bool, str]
            Was the desired control_char string received?, Result message
        """
        was_successful, message = self.get_response(response_timeout)
        if not was_successful:
            return (False, message)
        else:
            response_result = message
        
        if delimiter in response_result:
            # the response comes with a message/comment
            response_char = response_result.split(delimiter)[0].strip()
            response_comment = response_result.split(delimiter)[1].strip()
        else:
            # the response does not come with a message
            response_char = response_result.strip()
            response_comment = ""

        if response_char != control_char:
            return (False, "Did not receive the control char or str " + control_char + ". Instead received: " + response_result + ".")

        return (True, "Successfully received the control char or str " + control_char + " with message: " + response_comment + ".")

    def get_response(self, response_timeout: float = 1.0) -> Tuple[bool, str]:
        retry_count = 0
        partial_retries = ArduinoSerialDevice.partial_timeout // self._timeout
        response_retries = response_timeout // self._timeout

        if response_retries < 1:
            response_retries = 1
        
        # using integer retries of period self.timeout, this is because changing ser.timeout directly causes problems
        response_result = b''
        while response_result.decode('ascii') == "" and retry_count < response_retries:
            response_result = self.ser.readline()
            retry_count += 1

        # https://stackoverflow.com/questions/61166544/readline-in-pyserial-sometimes-captures-incomplete-values-being-streamed-from
        # in case readline times out in the middle of a message before \n
        retry_count = 0
        while response_result.decode('ascii') != "" and "\\n" not in str(response_result) and retry_count < partial_retries:
            temp_result = self.ser.readline()
            retry_count += 1
            
            # "not not" is correct, means not empty, != ""
            if not not temp_result.decode('ascii'):
                response_result = (response_result.decode('ascii') + temp_result.decode('ascii')).encode('ascii')
        
        if retry_count == partial_retries and "\\n" not in str(response_result):
            return (False, "Timed out. Partial message received.")

        response_result = response_result.strip().decode('ascii')

        if response_result == "":
            return (False, "Timed out. Did not receive any response.")

        return (True, response_result)
    
    @staticmethod
    def parse_equal_sign(text: str) -> Tuple[bool, str]:
        """For strings that contain information, get the desired information that is located at the end of the string which follows an = sign.

        Parameters
        ----------
        text : str
            the string that contains an = sign followed by the desired information.

        Returns
        -------
        Tuple[bool, str]
            Whether the string contained an = sign, and the desired information as a string.
        """
        if "=" in text:
            last_token = text.split("=")[-1]
            return (True, last_token.strip())
        else:
            return (False, "")
        

class MiscDeviceClass():
    def exists():
        return True
