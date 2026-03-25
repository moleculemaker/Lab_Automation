from typing import Optional, Tuple, Union
import serial
import time
import re

from .device import ArduinoSerialDevice, check_initialized, check_serial


class HeatingStage(ArduinoSerialDevice):
    def __init__(
            self, 
            name: str,  
            port: str, 
            baudrate: int, 
            timeout: Optional[float] = 1.0, 
            heating_timeout: float = 600.0):

        super().__init__(name, port, baudrate, timeout)
        self._heating_timeout = heating_timeout

    def get_init_args(self) -> dict:
        args_dict = {
            "name": self.name,
            "port": self._port,
            "baudrate": self._baudrate,
            "timeout": self._timeout,
            "heating_timeout": self._heating_timeout,
        }
        return args_dict
    
    def update_init_args(self, args_dict: dict):
        self.name = args_dict["name"]
        self._port = args_dict["port"]
        self._baudrate = args_dict["baudrate"]
        self._timeout = args_dict["timeout"]
        self._heating_timeout = args_dict["heating_timeout"]

    # no need to check serial as set_settemp and pid_on has these checks already
    def initialize(self) -> Tuple[bool, str]:
        self._is_initialized = True
        was_set, comment = self.set_settemp(26.0)

        if not was_set:
            self._is_initialized = False
            return (was_set, comment)

        was_turned_on, comment = self.pid_on()

        if not was_turned_on:
            self._is_initialized = False
            return (was_turned_on, comment)

        return (True, "Heating stage successfully initialized by setting to 26 C and turning PID ON.")

    def deinitialize(self, reset_init_flag: bool = True) -> Tuple[bool, str]:
        self._is_initialized = True
        was_set, comment = self.set_settemp(24.0)

        if not was_set:
            self._is_initialized = False
            return (was_set, comment)

        was_turned_off, comment = self.pid_off()

        if not was_turned_off:
            self._is_initialized = False
            return (was_turned_off, comment)

        if reset_init_flag:
            self._is_initialized = False

        return (True, "Heating stage successfully deinitialized by setting to 24 C and turning PID OFF.")

    @check_serial
    @check_initialized
    def set_settemp(self, temp: float) -> Tuple[bool, str]:
        # if not self.ser.is_open:
        #     return (False, "Serial port " + self._port + " is not open. ")
        # elif not self._is_initialized:
        #     return (False, "Heating stage is not initialized.")
        # else:
        command = ">set Ts " + str(temp) +"\n"
        self.ser.write(command.encode('ascii'))
        return self.check_ack_succ()

    @check_serial
    @check_initialized
    def set_temp(self, temp: float) -> Tuple[bool, str]:
        # if not self.ser.is_open:
        #     return (False, "Serial port " + self._port + " is not open. ")
        # elif not self._is_initialized:
        #     return (False, "Heating stage is not initialized.")
        # else:
        command = ">set T " + str(temp) +"\n"
        self.ser.write(command.encode('ascii'))
        return self.check_ack_succ(ack_timeout=1.0, succ_timeout=self._heating_timeout)

    @check_serial
    @check_initialized
    def pid_on(self) -> Tuple[bool, str]:
        # if not self.ser.is_open:
        #     return (False, "Serial port " + self._port + " is not open. ")
        # elif not self._is_initialized:
        #     return (False, "Heating stage is not initialized.")
        # else:
        command = ">pidon\n"
        self.ser.write(command.encode('ascii'))
        return self.check_ack_succ()

    @check_serial
    def pid_off(self) -> Tuple[bool, str]:
        # if not self.ser.is_open:
        #     return (False, "Serial port " + self._port + " is not open. ")
        # else:
        command = ">pidoff\n"
        self.ser.write(command.encode('ascii'))
        return self.check_ack_succ()
    
    @check_serial
    def is_pid_on(self) -> Tuple[bool, Union[bool, str]]:
        # if not self.ser.is_open:
        #     return (False, "Serial port " + self._port + " is not open. ")
        # else:
        command = ">pr pid\n"
        self.ser.write(command.encode('ascii'))
        was_successful, comment = self.check_ack_succ()

        if not was_successful:
            return (was_successful, comment)

        has_on_off, pid_state = super().parse_equal_sign(comment)

        if not has_on_off:
            return (has_on_off, "Message from device did not contain PID state.")

        if pid_state == "ON":
            is_on = True
        else:
            is_on = False

        return (True, is_on)

    @check_serial
    def temperature(self) -> Tuple[bool, Union[float, str]]:
        # if not self.ser.is_open:
        #     return (False, "Serial port " + self._port + " is not open. ")
        # else:
        command = ">pr T\n"
        self.ser.write(command.encode('ascii'))
        was_successful, comment = self.check_ack_succ()

        if not was_successful:
            return (was_successful, comment)

        has_temperature, temperature_str = super().parse_equal_sign(comment)

        if not has_temperature:
            return (has_temperature, "Message from device did not contain temperature.")

        match = re.search(r"-?\d+(?:\.\d+)?", temperature_str)
        if match is None:
            return (False, "Could not parse temperature from message: " + str(temperature_str))

        return (True, float(match.group(0)))

    @check_serial
    @check_initialized
    def wait_for_temperature(
        self,
        target: float,
        tolerance: float = 1.0,
        timeout: Optional[float] = None,
        poll_interval: float = 1.0,
        hold_duration: float = 30.0,
    ) -> Tuple[bool, str]:
        if tolerance < 0:
            return (False, "Tolerance must be non-negative.")
        if poll_interval <= 0:
            return (False, "Poll interval must be greater than zero.")
        if hold_duration < 0:
            return (False, "Hold duration must be non-negative.")

        if timeout is None:
            timeout = self._heating_timeout

        deadline = time.time() + timeout
        last_temp = None
        stable_since = None

        while time.time() <= deadline:
            was_successful, current_temp = self.temperature()
            if not was_successful:
                return (False, str(current_temp))

            last_temp = current_temp
            if abs(current_temp - target) <= tolerance:
                if stable_since is None:
                    stable_since = time.time()
                elif time.time() - stable_since >= hold_duration:
                    return (
                        True,
                        "Heating stage held target temperature "
                        + str(target)
                        + " C within ±"
                        + str(tolerance)
                        + " C for "
                        + str(hold_duration)
                        + " s. Current temperature: "
                        + str(current_temp)
                        + " C.",
                    )
            else:
                stable_since = None

            time.sleep(poll_interval)

        return (
            False,
            "Heating stage failed to reach target temperature "
            + str(target)
            + " C and hold it within ±"
            + str(tolerance)
            + " C for "
            + str(hold_duration)
            + " s within timeout. Last measured temperature: "
            + str(last_temp)
            + " C.",
        )



    
