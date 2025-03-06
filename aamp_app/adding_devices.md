# Adding Devices to the Device Dropdown
This is a step-by-step guide for how to add devices and commands to the dropdowns in the View tab

### Step 1:

Ensure that you have the device_name.py file and the device_name_commands.py file for the device you want to add. device_name.py should be in aamp_app/devices and device_name_commands.py should be in aamp_app/commands. You will have to refer to both of these files later to populate the util file correctly.

### Step 2:

Navigate to aamp_app/util.py. This file contains the configurations for each devices and their respective commands as they show up in the UI.

### Step 3:

Import the device at the top of the file. For example:
```python
from devices.psd6_syringe_pump import PSD6SyringePump
```

Also import all functions from its respective commands file:
```python
from commands.psd6_syringe_pump_commands import *
```

### Step 4:

Add the device to the devices_ref_redundancy object. The device specifications should match what is outlined in the device's python file. All parameters that don't already have a default value defined in the class and are not optional must be included. For example, here is the python file defining the PSD6SyringePump:
```python
class PSD6SyringePump(SerialDevice):
    status_dict = {
        '@': "Pump busy - no error",
        '`': "Pump ready - no error",
        'a': "Initialization error - pump failed to initialize",
        'b': "Invalid command - unrecognized command is used.",
        'c': "Invalid operand - invalid parameter is given with a command.",
        'd': "Invalid command sequence - command communication protocol is incorrect",
        'f': "EEPROM failure - EEPROM is faulty",
        'g': "Syringe not initialized - syringe failed to initialize",
        'i': "Syringe overload - syringe encounters excessive back pressure",
        'j': "Valve overload - valve drive encounters excessive back pressure",
        'k': "Syringe move not allowed - valve is in the bypass or throughput position, syringe move commands are not allowed",
        'o': "Pump busy - command buffer is full"
    }
    
    # volume_factor = {'ul': 1.0, 'ml': 1000.0}
    # time_factor = {'s': 1.0, 'min': 1.0/60.0}
    
    def __init__(
            self,
            name: str,
            port: str,
            baudrate: int = 9600,
            timeout: Optional[float] = 10.0,
            stroke_volume: float = 5000.0, 
            stroke_steps: int = 6000,
            default_flowrate: float = 1000.0,
            # volume_unit: str = 'ul',
            # time_unit: str = 's',
            port_dead_volumes: List[float] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            poll_interval: float = 0.1):

        super().__init__(name, port, baudrate, timeout)
        self._stroke_volume = stroke_volume
        self._stroke_steps = stroke_steps
        self._default_flowrate = default_flowrate
        # self._volume_unit = volume_unit
        # self._time_unit = time_unit
        self._port_dead_volumes = port_dead_volumes
        self._poll_interval = poll_interval
        
        # technically if I send a command that is out of range of these values
        # the pump should be able to give me an error message anyways
        # but if I store a default flowrate in this object I'd rather
        # have it be correct, than let the pump handle it because
        # setting a wrong default flowrate here does not yield an error until
        # later when some other command is sent that uses it
        self._max_steps_per_sec = 10000
        self._min_steps_per_sec = 2
        
        # # this is ok to leave out since anything using a position immediately issues a command
        # self._min_position = 0
        # self._max_position = 6000

```

And here is the corresponding device specification in JSON in util.py:
```python
"PSD6SyringePump": {
        "obj": PSD6SyringePump,
        "serial": True,
        "serial_sequence": ["PSD6SyringePumpInitialize"],
        "import_device": "from devices.psd6_syringe_pump import PSD6SyringePump",
        "import_commands": "from commands.psd6_syringe_pump_commands import *",
        "init": {
            "default_code": "PSD6SyringePump(name='PSD6SyringePump', port='COM5', baudrate=9600, timeout=10.0)",
            "obj_name": "PSD6SyringePump",
            "args": {
                "name": {
                    "default": "PSD6SyringePump",
                    "type": str,
                    "notes": "Name of the device.",
                },
                "port": {
                    "default": "COM5",
                    "type": str,
                    "notes": "Port",
                },
                "baudrate": {
                    "default": 9600,
                    "type": int,
                    "notes": "Baudrate",
                },
                "timeout": {
                    "default": 10.0,
                    "type": float,
                    "notes": "Timeout",
                },
            },
        },
        # ...
}
```

### Step 5:

Add a nested object to the device object containing each command. Similarly to the previous step, this requires looking at what parameters each function takes and their defaults. Here are the functions in the commands file:

```python
class PSD6SyringePumpConnect(PSD6SyringePumpParentCommand):
    """Open the serial port to the PSD6 syringe pump."""

    def __init__(self, receiver: PSD6SyringePump, **kwargs):
        super().__init__(receiver, **kwargs)

    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.start_serial())
        
class PSD6SyringePumpInitialize(PSD6SyringePumpParentCommand):
    def __init__(self, receiver: PSD6SyringePump, **kwargs):
        super().__init__(receiver, **kwargs)
        
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.initialize())
        
class PSD6SyringePumpMoveValve(PSD6SyringePumpParentCommand):
    def __init__(self, receiver: PSD6SyringePump, valve_num: int, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['valve_num'] = valve_num
        
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.move_valve_position(self._params['valve_num']))
        
class PSD6SyringePumpMoveAbsolute(PSD6SyringePumpParentCommand):
    def __init__(self, receiver: PSD6SyringePump, volume: float, valve_num: Optional[int] = None, flowrate: Optional[float] = None, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['volume'] = volume
        self._params['valve_num'] = valve_num
        self._params['flowrate'] = flowrate
        
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.move_syringe_absolute_volume(self._params['volume'], self._params['valve_num'], self._params['flowrate']))
        
class PSD6SyringePumpInfuse(PSD6SyringePumpParentCommand):
    def __init__(self, receiver: PSD6SyringePump, volume: float, valve_num: Optional[int] = None, flowrate: Optional[float] = None, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['volume'] = volume
        self._params['valve_num'] = valve_num
        self._params['flowrate'] = flowrate
        
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.infuse_syringe_volume(self._params['volume'], self._params['valve_num'], self._params['flowrate']))

class PSD6SyringePumpWithdraw(PSD6SyringePumpParentCommand):
    def __init__(self, receiver: PSD6SyringePump, volume: float, valve_num: Optional[int] = None, flowrate: Optional[float] = None, **kwargs):
        super().__init__(receiver, **kwargs)
        self._params['volume'] = volume
        self._params['valve_num'] = valve_num
        self._params['flowrate'] = flowrate
        
    def execute(self) -> None:
        self._result = CommandResult(*self._receiver.withdraw_syringe_volume(self._params['volume'], self._params['valve_num'], self._params['flowrate']))
```

And here are the corresponding command objects in the util file:
```python
# As a nested object within the previously defined device object...
"commands": {
            "PSD6SyringePumpConnect": {
                "default_code": "PSD6SyringePumpConnect(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "PSD6SyringePump",
                        "type": str,
                        "notes": "Name of the device.",
                    }
                },
                "obj": PSD6SyringePumpConnect,
            },
            "PSD6SyringePumpInitialize": {
                "default_code": "PSD6SyringePumpInitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "PSD6SyringePump",
                        "type": str,
                        "notes": "Name of the device.",
                    }
                },
                "obj": PSD6SyringePumpInitialize,
            },
            "PSD6SyringePumpMoveValve": {
                "default_code": "PSD6SyringePumpMoveValve(receiver= '', valve_num=0)",
                "args": {
                    "receiver": {
                        "default": "PSD6SyringePump",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "valve_num": {
                        "default": 0,
                        "type": int,
                        "notes": "Valve number.",
                    },
                },
                "obj": PSD6SyringePumpMoveValve,
            },
            "PSD6SyringePumpMoveAbsolute": {
                "default_code": "PSD6SyringePumpMoveAbsolute(receiver= '', volume=0.0, valve_num= 0, flowrate=0.0)",
                "args": {
                    "receiver": {
                        "default": "PSD6SyringePump",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "volume": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Volume.",
                    },
                    "valve_num": {
                        "default": 0,
                        "type": int,
                        "notes": "Valve number.",
                    },
                    "flowrate": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Flowrate.",
                    },
                },
                "obj": PSD6SyringePumpMoveAbsolute,
            },
            "PSD6SyringePumpInfuse": {
                "default_code": "PSD6SyringePumpInfuse(receiver= '', volume=0.0, valve_num= 0, flowrate=0.0)",
                "args": {
                    "receiver": {
                        "default": "PSD6SyringePump",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "volume": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Volume.",
                    },
                    "valve_num": {
                        "default": 0,
                        "type": int,
                        "notes": "Valve number.",
                    },
                    "flowrate": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Flowrate.",
                    },
                },
                "obj": PSD6SyringePumpInfuse,
            },
            "PSD6SyringePumpWithdraw": {
                "default_code": "PSD6SyringePumpWithdraw(receiver= '', volume=0.0, valve_num= 0, flowrate=0.0)",
                "args": {
                    "receiver": {
                        "default": "PSD6SyringePump",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "volume": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Volume.",
                    },
                    "valve_num": {
                        "default": 0,
                        "type": int,
                        "notes": "Valve number.",
                    },
                    "flowrate": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Flowrate.",
                    },
                },
                "obj": PSD6SyringePumpWithdraw,
            },
        },
```

### Step 6:

To confirm that everything is working correctly, ensure all of the dropdowns are propagated correctly with the new device and commands, and that they can all be added to the database. 