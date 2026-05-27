from commands.command import Command
from commands.utility_commands import LoopStartCommand, LoopEndCommand
from devices.heating_stage import HeatingStage
from devices.apis import APIS
from devices.sciencetech_uhe_nl_solar_sim import SciencetechUHENLSolarSim
from devices.stellarnet_spectrometer import StellarNetSpectrometer
from devices.multi_stepper import MultiStepper
from devices.newport_esp301 import NewportESP301
from devices.newport_94043a_solar_sim import Newport94043ASolarSim
from devices.festo_solenoid_valve import FestoSolenoidValve
from devices.ximea_camera import XimeaCamera
from devices.dummy_heater import DummyHeater
from devices.dummy_motor import DummyMotor
from devices.linear_stage_150 import LinearStage150
from devices.mts50_z8 import MTS50_Z8
from devices.p4pp import P4PP
from devices.sonicator import Sonicator
from devices.substrate_hotel import SubstrateHotel
from devices.substrate_dispenser import SubstrateDispenser
from devices.z812 import Z812
from devices.keithley_2450 import Keithley2450
from devices.mfc import MassFlowController
from devices.oxygen_sensor import OxygenSensor
from devices.sht85_sensor import SHT85HumidityTempSensor
from devices.device import Device, MiscDeviceClass
from devices.utility_device import UtilityCommands
from devices.psd6_syringe_pump import PSD6SyringePump
from devices.ximea_camera import XimeaCamera

from commands.linear_stage_150_commands import *
from commands.apis_commands import *
from commands.sciencetech_uhe_nl_solar_sim_commands import *
from commands.stellarnet_spectrometer_commands import *
from commands.mts50_z8_commands import *
from commands.p4pp_commands import *
from commands.z812_commands import *
from commands.dummy_heater_commands import *
from commands.dummy_motor_commands import *
from commands.dummy_meter_commands import *
from commands.keithley_2450_commands import *
from commands.festo_solenoid_valve_commands import *
from commands.ximea_camera_commands import *
from commands.utility_commands import *
from commands.heating_stage_commands import *
from commands.multi_stepper_commands import *
from commands.mfc_commands import *
from commands.sonicator_commands import *
from commands.substrate_hotel_commands import *
from commands.substrate_dispenser_commands import *
from commands.sht85_sensor_commands import *
from commands.newport_esp301_commands import *
from commands.newport_94043a_solar_sim_commands import *
from commands.utility_commands import *
from commands.psd6_syringe_pump_commands import *
from commands.ximea_camera_commands import *

import json
import numpy as np
from typing import Tuple, Union


named_devices = {
    "PrintingStage": HeatingStage,
    "AnnealingStage": HeatingStage,
    "MultiStepper1": MultiStepper,
    "PrinterMotorX": NewportESP301,
    "StellarNetSpectrometer": StellarNetSpectrometer,
    "Sonicator": Sonicator,
    "SubstrateHotel": SubstrateHotel,
    "SubstrateDispenser": SubstrateDispenser,
    "SampleCamera": XimeaCamera,
    "DummyHeater1": DummyHeater,
    "DummyHeater2": DummyHeater,
    "DummyMotor": DummyMotor,
    "DummyMotor1": DummyMotor,
    "DummyMotor2": DummyMotor,
}
command_directory = "commands/"
approved_devices = list(named_devices.keys())

# device_init_args = {
#     "DummyHeater": ["name", "heat_rate"],
#     "DummyMotor": ["name", "speed"],
# }


def dict_to_device(device: Device, type: str):
    device_cls = named_devices[type]
    arg_dict = device.get_init_args()

    # for attr in device_init_args[type]:
    #     arg_dict[attr] = dict["_"+attr]

    # print(arg_dict)
    return device_cls(**arg_dict)


def str_to_device(device_str: str):
    print(device_str)
    return eval(device_str)


def device_to_dict(device: Device):
    return device.get_init_args()


def evaluate(eval_str):
    return eval(eval_str)


class Encoder(json.JSONEncoder):
    def default(self, obj):
        if (
            isinstance(obj, Device)
            or isinstance(obj, Command)
            or isinstance(obj, MiscDeviceClass)
        ):
            return obj.__dict__
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


heating_stage_ref = {
    "obj": HeatingStage,
    "serial": True,
    "serial_sequence": ["HeatingStageConnect", "HeatingStageInitialize"],
    "import_device": "from devices.heating_stage import HeatingStage",
    "import_commands": "from commands.heating_stage_commands import *",
    "init": {
        "default_code": "HeatingStage(name='Stage', port='', baudrate=115200, timeout=0.1, heating_timeout=600.0)",
        "obj_name": "HeatingStage",
        "args": {
            "name": {
                "default": "Stage",
                "type": str,
                "notes": "Name of the device",
            },
            "port": {"default": "COM", "type": str, "notes": "Port"},
            "baudrate": {
                "default": 115200,
                "type": int,
                "notes": "Baudrate",
            },
            "timeout": {
                "default": 0.1,
                "type": float,
                "notes": "Timeout",
            },
            "heating_timeout": {
                "default": 600.0,
                "type": float,
                "notes": "Heating timeout",
            },
        },
    },
    "commands": {
        "HeatingStageConnect": {
            "default_code": "HeatingStageConnect(receiver= '')",
            "args": {
                "receiver": {
                    "default": "Stage",
                    "type": str,
                    "notes": "Name of the device",
                }
            },
            "obj": HeatingStageConnect,
        },
        "HeatingStageInitialize": {
            "default_code": "HeatingStageInitialize(receiver= '')",
            "args": {
                "receiver": {
                    "default": "Stage",
                    "type": str,
                    "notes": "Name of the device",
                }
            },
            "obj": HeatingStageInitialize,
        },
        "HeatingStageDeinitialize": {
            "default_code": "HeatingStageDeinitialize(receiver= '')",
            "args": {
                "receiver": {
                    "default": "Stage",
                    "type": str,
                    "notes": "Name of the device",
                }
            },
            "obj": HeatingStageDeinitialize,
        },
        "HeatingStageSetTemp": {
            "default_code": "HeatingStageSetTemp(receiver= '', temperature= 0.0)",
            "args": {
                "receiver": {
                    "default": "Stage",
                    "type": str,
                    "notes": "Name of the device",
                },
                "temperature": {
                    "default": 0.0,
                    "type": float,
                    "notes": "Temperature",
                },
            },
            "obj": HeatingStageSetTemp,
        },
        "HeatingStageSetSetPoint": {
            "default_code": "HeatingStageSetSetPoint(receiver= '', temperature= 0.0)",
            "args": {
                "receiver": {
                    "default": "Stage",
                    "type": str,
                    "notes": "Name of the device",
                },
                "temperature": {
                    "default": 0.0,
                    "type": float,
                    "notes": "Temperature",
                },
            },
            "obj": HeatingStageSetSetPoint,
        },
        "HeatingStageWaitForTemperature": {
            "default_code": "HeatingStageWaitForTemperature(receiver= '', target= 25.0, tolerance= 1.0, timeout= 600.0, poll_interval= 1.0, hold_duration= 30.0)",
            "args": {
                "receiver": {
                    "default": "Stage",
                    "type": str,
                    "notes": "Name of the device",
                },
                "target": {
                    "default": 25.0,
                    "type": float,
                    "notes": "Target temperature in C",
                },
                "tolerance": {
                    "default": 1.0,
                    "type": float,
                    "notes": "Allowed deviation in C",
                },
                "timeout": {
                    "default": 600.0,
                    "type": float,
                    "notes": "Maximum wait time in seconds",
                },
                "poll_interval": {
                    "default": 1.0,
                    "type": float,
                    "notes": "Polling interval in seconds",
                },
                "hold_duration": {
                    "default": 30.0,
                    "type": float,
                    "notes": "Time in seconds that temperature must stay within tolerance",
                },
            },
            "obj": HeatingStageWaitForTemperature,
        },
    },
}


devices_ref_redundancy = {
    "UtilityCommands": {
        "obj": UtilityCommands,
        "serial": False,
        "import_device": "from devices.utility_commands import UtilityCommands",
        "import_commands": "from commands.utility_commands import *",
        "init": {
            "default_code": "# Utility Commands used",
            "obj_name": "UtilityCommands",
            "args": {},
        },
        "commands": {
            "LoopStartCommand": {
                "default_code": "LoopStartCommand()",
                "args": {},
                "obj": LoopStartCommand,
            },
            "LoopEndCommand": {
                "default_code": "LoopEndCommand()",
                "args": {},
                "obj": LoopEndCommand,
            },
            "DelayPauseCommand": {
                "default_code": "DelayPauseCommand(delay=0.0)",
                "args": {
                    "delay": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Delay in seconds",
                    }
                },
                "obj": DelayPauseCommand,
            },
            "NotifySlackCommand": {
                "default_code": "NotifySlackCommand(message='Hello World')",
                "args": {
                    "message": {
                        "default": "Hello World",
                        "type": str,
                        "notes": "Message to send to slack",
                    }
                },
                "obj": NotifySlackCommand,
            },
            "LogUserMessageCommand": {
                "default_code": "LogUserMessageCommand(message='Hello World')",
                "args": {
                    "message": {
                        "default": "Hello World",
                        "type": str,
                        "notes": "Message to log",
                    }
                },
                "obj": LogUserMessageCommand,
            },
        },
    },
    "FestoSolenoidValve": {
        "obj": FestoSolenoidValve,
        "serial": True,
        "serial_sequence": ["FestoConnect", "FestoInitialize"],
        "import_device": "from devices.festo_solenoid_valve import FestoSolenoidValve",
        "import_commands": "from commands.festo_solenoid_valve_commands import *",
        "init": {
            "default_code": "FestoSolenoidValve(name='FestoSolenoidValve', port='COM5', baudrate=9600, timeout=0.1)",
            "obj_name": "FestoSolenoidValve",
            "args": {
                "name": {
                    "default": "FestoSolenoidValve",
                    "type": str,
                    "notes": "Name of the device.",
                },
                # "numchannel": {
                #     "default": 1,
                #     "type": int,
                #     "notes": "",
                # },
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
                    "default": 0.1,
                    "type": float,
                    "notes": "Timeout",
                },
            },
        },
        "commands": {
            "FestoConnect": {
                "default_code": "FestoConnect(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "FestoSolenoidValve",
                        "type": str,
                        "notes": "Name of the device",
                    },
                },
                "obj": FestoConnect,
            },
            "FestoInitialize": {
                "default_code": "FestoInitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "FestoSolenoidValve",
                        "type": str,
                        "notes": "Name of the device",
                    },
                },
                "obj": FestoInitialize,
            },
            "FestoDeinitialize": {
                "default_code": "FestoDeinitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "FestoSolenoidValve",
                        "type": str,
                        "notes": "Name of the device",
                    },
                },
                "obj": FestoDeinitialize,
            },
            "FestoValveOpen": {
                "default_code": "FestoValveOpen(receiver= '', valve_num=1)",
                "args": {
                    "receiver": {
                        "default": "FestoSolenoidValve",
                        "type": str,
                        "notes": "Name of the device",
                    },
                    "valve_num": {
                        "default": 1,
                        "type": int,
                        "notes": "Valve number to open. Arduino sketch maps 1/2/3 to pins 12/8/4.",
                    },
                },
                "obj": FestoValveOpen,
            },
            "FestoValveClosed": {
                "default_code": "FestoValveClosed(receiver= '', valve_num=1)",
                "args": {
                    "receiver": {
                        "default": "FestoSolenoidValve",
                        "type": str,
                        "notes": "Name of the device",
                    },
                    "valve_num": {
                        "default": 1,
                        "type": int,
                        "notes": "Valve number to close. Arduino sketch maps 1/2/3 to pins 12/8/4.",
                    },
                },
                "obj": FestoValveClosed,
            },
            "FestoCloseAll": {
                "default_code": "FestoCloseAll(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "FestoSolenoidValve",
                        "type": str,
                        "notes": "Name of the device",
                    },
                },
                "obj": FestoCloseAll,
            }
            # "FestoOpenTimed": {
            #     "default_code": "FestoOpenTimed(receiver= '', time=0)",
            #     "args": {
            #         "receiver": {
            #             "default": "FestoSolenoidValve",
            #             "type": str,
            #             "notes": "Name of the device",
            #         },
            #         "time": {
            #             "default": 0,
            #             "type": int,
            #             "notes": "Time to keep the valve open",
            #         },
            #     },
            #     "obj": FestoOpenTimed,
            # },
        },
    },
    "LinearStage150": {
        "obj": LinearStage150,
        "default_obj": LinearStage150(
            name="LinearStage150",
            port="COM5",
            baudrate=115200,
            timeout=0.1,
            destination=0x50,
            source=0x01,
            channel=1,
        ),
        "serial": True,
        "serial_sequence": ["LinearStage150Connect", "LinearStage150Initialize"],
        "import_device": "from devices.linear_stage_150 import LinearStage150",
        "import_commands": "from commands.linear_stage_150_commands import *",
        "telemetry": {
            "parameters": {
                "position": {
                    "function_name": "get_position",
                    "data_type": "float",
                    "units": "mm",
                }
            },
            "options": {"custom_init_args": ["port"]},
        },
        "init": {
            "default_code": "LinearStage150(name='LinearStage150', port='', baudrate=115200, timeout=0.1, destination=0x50, source=0x01, channel=1)",
            "obj_name": "LinearStage150",
            "args": {
                "name": {
                    "default": "LinearStage150",
                    "type": str,
                    "notes": "Name of the device.",
                },
                "port": {"default": "COM", "type": str, "notes": "Port"},
                "baudrate": {
                    "default": 115200,
                    "type": int,
                    "notes": "Baudrate",
                },
                "timeout": {
                    "default": 0.1,
                    "type": float,
                    "notes": "Timeout",
                },
                "destination": {
                    "default": 0x50,
                    "type": int,
                    "notes": "",
                },
                "source": {
                    "default": 0x01,
                    "type": int,
                    "notes": "",
                },
                "channel": {
                    "default": 1,
                    "type": int,
                    "notes": "",
                },
            },
        },
        "commands": {
            "LinearStage150Connect": {
                "default_code": "LinearStage150Connect(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "LinearStage150",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": LinearStage150Connect,
            },
            "LinearStage150Initialize": {
                "default_code": "LinearStage150Initialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "LinearStage150",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": LinearStage150Initialize,
            },
            "LinearStage150Deinitialize": {
                "default_code": "LinearStage150Deinitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "LinearStage150",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": LinearStage150Deinitialize,
            },
            "LinearStage150EnableMotor": {
                "default_code": "LinearStage150EnableMotor(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "LinearStage150",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": LinearStage150EnableMotor,
            },
            "LinearStage150DisableMotor": {
                "default_code": "LinearStage150DisableMotor(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "LinearStage150",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": LinearStage150DisableMotor,
            },
            "LinearStage150MoveAbsolute": {
                "default_code": "LinearStage150MoveAbsolute(receiver= '', position= 0)",
                "args": {
                    "receiver": {
                        "default": "LinearStage150",
                        "type": str,
                        "notes": "",
                    },
                    "position": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Absolute position in mm.",
                    },
                },
                "obj": LinearStage150MoveAbsolute,
            },
            "LinearStage150MoveRelative": {
                "default_code": "LinearStage150MoveRelative(receiver= '', distance= 0)",
                "args": {
                    "receiver": {
                        "default": "LinearStage150",
                        "type": str,
                        "notes": "",
                    },
                    "distance": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Relative distance in mm.",
                    },
                },
                "obj": LinearStage150MoveRelative,
            },
        },
    },
    "MTS50_Z8": {
        "obj": MTS50_Z8,
        "serial": True,
        "serial_sequence": ["MTS50_Z8Connect", "MTS50_Z8EnableMotor"],
        "import_device": "from devices.mts50_z8 import MTS50_Z8",
        "import_commands": "from commands.mts50_z8_commands import *",
        "init": {
            "default_code": "MTS50_Z8(name='MTS50_Z8', port='', baudrate=115200, timeout=0.1, destination=0x50, source=0x01, channel=1)",
            "obj_name": "MTS50_Z8",
            "args": {
                "name": {
                    "default": "MTS50_Z8",
                    "type": str,
                    "notes": "Name of the device.",
                },
                "port": {"default": "COM", "type": str, "notes": "Port"},
                "baudrate": {
                    "default": 115200,
                    "type": int,
                    "notes": "Baudrate",
                },
                "timeout": {
                    "default": 0.1,
                    "type": float,
                    "notes": "Timeout",
                },
                "destination": {
                    "default": 0x50,
                    "type": int,
                    "notes": "",
                },
                "source": {
                    "default": 0x01,
                    "type": int,
                    "notes": "",
                },
                "channel": {
                    "default": 1,
                    "type": int,
                    "notes": "",
                },
            },
        },
        "commands": {
            "MTS50_Z8Connect": {
                "default_code": "MTS50_Z8Connect(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "MTS50_Z8",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": MTS50_Z8Connect,
            },
            "MTS50_Z8Initialize": {
                "default_code": "MTS50_Z8Initialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "MTS50_Z8",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": MTS50_Z8Initialize,
            },
            "MTS50_Z8Deinitialize": {
                "default_code": "MTS50_Z8Deinitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "MTS50_Z8",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": MTS50_Z8Deinitialize,
            },
            "MTS50_Z8EnableMotor": {
                "default_code": "MTS50_Z8EnableMotor(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "MTS50_Z8",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": MTS50_Z8EnableMotor,
            },
            "MTS50_Z8DisableMotor": {
                "default_code": "MTS50_Z8DisableMotor(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "MTS50_Z8",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": MTS50_Z8DisableMotor,
            },
            "MTS50_Z8MoveAbsolute": {
                "default_code": "MTS50_Z8MoveAbsolute(receiver= '', position= 0)",
                "args": {
                    "receiver": {
                        "default": "MTS50_Z8",
                        "type": str,
                        "notes": "",
                    },
                    "position": {
                        "default": 0,
                        "type": int,
                        "notes": "",
                    },
                },
                "obj": MTS50_Z8MoveAbsolute,
            },
            "MTS50_Z8MoveRelative": {
                "default_code": "MTS50_Z8MoveRelative(receiver= '', distance= 0)",
                "args": {
                    "receiver": {
                        "default": "MTS50_Z8",
                        "type": str,
                        "notes": "",
                    },
                    "distance": {
                        "default": 0,
                        "type": int,
                        "notes": "",
                    },
                },
                "obj": MTS50_Z8MoveRelative,
            },
        },
    },
    "Z812": {
        "obj": Z812,
        "serial": True,
        "serial_sequence": ["Z812Connect", "Z812Initialize"],
        "import_device": "from devices.z812 import Z812",
        "import_commands": "from commands.z812_commands import *",
        "telemetry": {
            "parameters": {
                "position": {
                    "function_name": "get_position",
                    "data_type": "float",
                    "units": "mm",
                }
            },
            "options": {"custom_init_args": ["port"]},
        },
        "init": {
            "default_code": "Z812(name='Z812', port='', baudrate=115200, timeout=0.1, destination=0x50, source=0x01, channel=1)",
            "obj_name": "Z812",
            "args": {
                "name": {
                    "default": "Z812",
                    "type": str,
                    "notes": "Name of the device.",
                },
                "port": {"default": "COM", "type": str, "notes": "Port"},
                "baudrate": {
                    "default": 115200,
                    "type": int,
                    "notes": "Baudrate",
                },
                "timeout": {
                    "default": 0.1,
                    "type": float,
                    "notes": "Timeout",
                },
                "destination": {
                    "default": 0x50,
                    "type": int,
                    "notes": "",
                },
                "source": {
                    "default": 0x01,
                    "type": int,
                    "notes": "",
                },
                "channel": {
                    "default": 1,
                    "type": int,
                    "notes": "",
                },
            },
        },
        "commands": {
            "Z812Connect": {
                "default_code": "Z812Connect(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Z812",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": Z812Connect,
            },
            "Z812Initialize": {
                "default_code": "Z812Initialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Z812",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": Z812Initialize,
            },
            "Z812Deinitialize": {
                "default_code": "Z812Deinitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Z812",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": Z812Deinitialize,
            },
            "Z812EnableMotor": {
                "default_code": "Z812EnableMotor(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Z812",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": Z812EnableMotor,
            },
            "Z812DisableMotor": {
                "default_code": "Z812DisableMotor(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Z812",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": Z812DisableMotor,
            },
            "Z812MoveAbsolute": {
                "default_code": "Z812MoveAbsolute(receiver= '', position= 0.0)",
                "args": {
                    "receiver": {
                        "default": "Z812",
                        "type": str,
                        "notes": "",
                    },
                    "position": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Absolute position in mm.",
                    },
                },
                "obj": Z812MoveAbsolute,
            },
            "Z812MoveRelative": {
                "default_code": "Z812MoveRelative(receiver= '', distance= 0.0)",
                "args": {
                    "receiver": {
                        "default": "Z812",
                        "type": str,
                        "notes": "",
                    },
                    "distance": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Relative distance in mm.",
                    },
                },
                "obj": Z812MoveRelative,
            },
        },
    },
    "APIS": {
        "obj": APIS,
        "serial": True,
        "serial_sequence": ["APISConnect", "APISInitialize"],
        "import_device": "from devices.apis import APIS",
        "import_commands": "from commands.apis_commands import *",
        "telemetry": {
            "parameters": {
                "polarizer_angle": {
                    "function_name": "get_polarizer_angle",
                    "data_type": "float",
                    "units": "deg",
                },
                "sample_angle": {
                    "function_name": "get_sample_angle",
                    "data_type": "float",
                    "units": "deg",
                },
            },
            "options": {"custom_init_args": ["port"]},
        },
        "init": {
            "default_code": "APIS(name='APIS', port='', baudrate=9600, timeout=0.5, connection_wait_s=2.0, settling_time_s=1.5, command_delay_s=0.05, max_retries=3, polarizer_stage_to_servo_ratio=1.059, sample_stage_to_servo_ratio=1.059, polarizer_stage_direction=1, sample_stage_direction=1, polarizer_servo_zero_deg=0, sample_servo_zero_deg=0, use_camera=True, camera_save_directory='data/imaging/', camera_bayer_pattern='GBRG', camera_raw_max_value=1023.0, polarizer_baseline_path=None)",
            "obj_name": "APIS",
            "args": {
                "name": {
                    "default": "APIS",
                    "type": str,
                    "notes": "Name of the device.",
                },
                "port": {
                    "default": "COM",
                    "type": str,
                    "notes": "Arduino serial port for APIS.",
                },
                "baudrate": {
                    "default": 9600,
                    "type": int,
                    "notes": "APIS serial baudrate.",
                },
                "timeout": {
                    "default": 0.5,
                    "type": float,
                    "notes": "Serial readline timeout in seconds.",
                },
                "connection_wait_s": {
                    "default": 2.0,
                    "type": float,
                    "notes": "Time to wait for READY during connect.",
                },
                "settling_time_s": {
                    "default": 1.5,
                    "type": float,
                    "notes": "Post-move settling time before command completion.",
                },
                "command_delay_s": {
                    "default": 0.05,
                    "type": float,
                    "notes": "Delay between serial command transactions.",
                },
                "max_retries": {
                    "default": 3,
                    "type": int,
                    "notes": "Retry count for serial timeouts.",
                },
                "polarizer_stage_to_servo_ratio": {
                    "default": 1.059,
                    "type": float,
                    "notes": "Polarizer stage-to-servo calibration ratio.",
                },
                "sample_stage_to_servo_ratio": {
                    "default": 1.059,
                    "type": float,
                    "notes": "Sample stage-to-servo calibration ratio.",
                },
                "polarizer_stage_direction": {
                    "default": 1,
                    "type": int,
                    "notes": "Polarizer rotation sign.",
                },
                "sample_stage_direction": {
                    "default": 1,
                    "type": int,
                    "notes": "Sample rotation sign.",
                },
                "polarizer_servo_zero_deg": {
                    "default": 0,
                    "type": int,
                    "notes": "Polarizer servo zero offset.",
                },
                "sample_servo_zero_deg": {
                    "default": 0,
                    "type": int,
                    "notes": "Sample servo zero offset.",
                },
                "use_camera": {
                    "default": True,
                    "type": bool,
                    "notes": "Initialize and use the integrated Ximea camera.",
                },
                "camera_save_directory": {
                    "default": "data/imaging/",
                    "type": str,
                    "notes": "Default save directory for APIS image outputs.",
                },
                "camera_bayer_pattern": {
                    "default": "GBRG",
                    "type": str,
                    "notes": "Bayer pattern used when converting RAW16 data to RGB.",
                },
                "camera_raw_max_value": {
                    "default": 1023.0,
                    "type": float,
                    "notes": "Linear scaling maximum used for RAW16 to RGB conversion.",
                },
                "polarizer_baseline_path": {
                    "default": None,
                    "type": str,
                    "notes": "Optional path for persisted XPL/PPL polarizer baseline JSON.",
                },
            },
        },
        "commands": {
            "APISConnect": {
                "default_code": "APISConnect(receiver= '')",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""}
                },
                "obj": APISConnect,
            },
            "APISInitialize": {
                "default_code": "APISInitialize(receiver= '')",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""}
                },
                "obj": APISInitialize,
            },
            "APISDeinitialize": {
                "default_code": "APISDeinitialize(receiver= '')",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""}
                },
                "obj": APISDeinitialize,
            },
            "APISReset": {
                "default_code": "APISReset(receiver= '')",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""}
                },
                "obj": APISReset,
            },
            "APISEmergencyStop": {
                "default_code": "APISEmergencyStop(receiver= '')",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""}
                },
                "obj": APISEmergencyStop,
            },
            "APISHome": {
                "default_code": "APISHome(receiver= '')",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""}
                },
                "obj": APISHome,
            },
            "APISRotatePolarizer": {
                "default_code": "APISRotatePolarizer(receiver= '', angle_deg= 0.0)",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""},
                    "angle_deg": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Target polarizer stage angle in degrees.",
                    },
                },
                "obj": APISRotatePolarizer,
            },
            "APISRotateSample": {
                "default_code": "APISRotateSample(receiver= '', angle_deg= 0.0)",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""},
                    "angle_deg": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Target sample stage angle in degrees.",
                    },
                },
                "obj": APISRotateSample,
            },
            "APISSetPolarizerBaseline": {
                "default_code": "APISSetPolarizerBaseline(receiver= '', xpl_angle_deg= 120.0, persist=False, source='manual')",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""},
                    "xpl_angle_deg": {
                        "default": 120.0,
                        "type": float,
                        "notes": "XPL polarizer angle; PPL is derived as the reachable orthogonal angle.",
                    },
                    "persist": {
                        "default": False,
                        "type": bool,
                        "notes": "Save the resulting XPL/PPL baseline to JSON.",
                    },
                    "source": {
                        "default": "manual",
                        "type": str,
                        "notes": "Source label stored in the baseline JSON when persist is enabled.",
                    },
                },
                "obj": APISSetPolarizerBaseline,
            },
            "APISLoadPolarizerBaseline": {
                "default_code": "APISLoadPolarizerBaseline(receiver= '')",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""}
                },
                "obj": APISLoadPolarizerBaseline,
            },
            "APISSavePolarizerBaseline": {
                "default_code": "APISSavePolarizerBaseline(receiver= '', source='manual')",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""},
                    "source": {"default": "manual", "type": str, "notes": "Source label stored in baseline JSON."},
                },
                "obj": APISSavePolarizerBaseline,
            },
            "APISRotateXPL": {
                "default_code": "APISRotateXPL(receiver= '')",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""}
                },
                "obj": APISRotateXPL,
            },
            "APISRotatePPL": {
                "default_code": "APISRotatePPL(receiver= '')",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""}
                },
                "obj": APISRotatePPL,
            },
            "APISGetState": {
                "default_code": "APISGetState(receiver= '')",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""}
                },
                "obj": APISGetState,
            },
            "APISCaptureRaw16": {
                "default_code": "APISCaptureRaw16(receiver= '', filename=None, directory=None, exposure_time=None, gain=0.0)",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""},
                    "filename": {"default": None, "type": str, "notes": "Output filename without extension."},
                    "directory": {"default": None, "type": str, "notes": "Optional override save directory."},
                    "exposure_time": {"default": None, "type": int, "notes": "Optional camera exposure in microseconds."},
                    "gain": {"default": 0.0, "type": float, "notes": "Camera gain in dB. Default is 0."},
                },
                "obj": APISCaptureRaw16,
            },
            "APISCaptureRgb": {
                "default_code": "APISCaptureRgb(receiver= '', filename=None, directory=None, exposure_time=None, gain=0.0)",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""},
                    "filename": {"default": None, "type": str, "notes": "Output filename without extension."},
                    "directory": {"default": None, "type": str, "notes": "Optional override save directory."},
                    "exposure_time": {"default": None, "type": int, "notes": "Optional camera exposure in microseconds."},
                    "gain": {"default": 0.0, "type": float, "notes": "Camera gain in dB. Default is 0."},
                },
                "obj": APISCaptureRgb,
            },
            "APISConvertRaw16ToRgb": {
                "default_code": "APISConvertRaw16ToRgb(receiver= '', raw16_path='', rgb_path=None)",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""},
                    "raw16_path": {"default": "", "type": str, "notes": "Path to the saved RAW16 TIFF file."},
                    "rgb_path": {"default": None, "type": str, "notes": "Optional output path for the converted RGB TIFF."},
                },
                "obj": APISConvertRaw16ToRgb,
            },
            "APISRunImagingSequence": {
                "default_code": "APISRunImagingSequence(receiver= '', sample_id='sample', directory=None, sample_angles=None, xpl_exposure_time=400000, ppl_exposure_time=18000, do_xpl=True, do_ppl=True, xpl_polarizer_angle=None, ppl_polarizer_angle=None, gain=0.0)",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""},
                    "sample_id": {"default": "sample", "type": str, "notes": "Sample ID used for output folder and filenames."},
                    "directory": {"default": None, "type": str, "notes": "Optional output root directory."},
                    "sample_angles": {"default": None, "type": list, "notes": "Sample angles, or None for APIS default sequence."},
                    "xpl_exposure_time": {"default": 400000, "type": int, "notes": "XPL exposure in microseconds."},
                    "ppl_exposure_time": {"default": 18000, "type": int, "notes": "PPL exposure in microseconds."},
                    "do_xpl": {"default": True, "type": bool, "notes": "Capture XPL mode."},
                    "do_ppl": {"default": True, "type": bool, "notes": "Capture PPL mode."},
                    "xpl_polarizer_angle": {"default": None, "type": float, "notes": "Optional XPL polarizer angle override."},
                    "ppl_polarizer_angle": {"default": None, "type": float, "notes": "Optional PPL polarizer angle override."},
                    "gain": {"default": 0.0, "type": float, "notes": "Camera gain in dB."},
                },
                "obj": APISRunImagingSequence,
            },
            "APISRunPolarizerCalibration": {
                "default_code": "APISRunPolarizerCalibration(receiver= '', sample_id='polarizer_calibration', directory=None, exposure_time=200000, polarizer_angles=None, sample_angle=0.0, fine_radius_deg=10, fine_step_deg=1, gain=0.0)",
                "args": {
                    "receiver": {"default": "APIS", "type": str, "notes": ""},
                    "sample_id": {"default": "polarizer_calibration", "type": str, "notes": "Calibration sample ID used in output filenames."},
                    "directory": {"default": None, "type": str, "notes": "Optional calibration output root."},
                    "exposure_time": {"default": 200000, "type": int, "notes": "Calibration exposure in microseconds."},
                    "polarizer_angles": {"default": None, "type": list, "notes": "Coarse scan angles, or None for 0:max:5."},
                    "sample_angle": {"default": 0.0, "type": float, "notes": "Sample stage angle during calibration."},
                    "fine_radius_deg": {"default": 10, "type": int, "notes": "Fine scan radius around the darkest coarse angle."},
                    "fine_step_deg": {"default": 1, "type": int, "notes": "Fine scan angle step."},
                    "gain": {"default": 0.0, "type": float, "notes": "Camera gain in dB."},
                },
                "obj": APISRunPolarizerCalibration,
            },
        },
    },
    "P4PP": {
        "obj": P4PP,
        "serial": True,
        "serial_sequence": ["P4PPConnect", "P4PPInitialize"],
        "import_device": "from devices.p4pp import P4PP",
        "import_commands": "from commands.p4pp_commands import *",
        "telemetry": {
            "parameters": {
                "linear_position_mm": {
                    "function_name": "get_linear_position_mm",
                    "data_type": "float",
                    "units": "mm",
                },
                "rotational_position_deg": {
                    "function_name": "get_rotational_position_deg",
                    "data_type": "float",
                    "units": "deg",
                },
            },
            "options": {"custom_init_args": ["port"]},
        },
        "init": {
            "default_code": "P4PP(name='P4PP', port='', baudrate=115200, timeout=0.2, startup_delay=2.0, command_timeout=30.0, motion_timeout=60.0, home_timeout=60.0, measure_timeout=30.0, poll_interval=0.2, rotation_safety_linear_mm=45.0, measurement_resistor_ohms=681.0, save_directory='data/resistance/')",
            "obj_name": "P4PP",
            "args": {
                "name": {
                    "default": "P4PP",
                    "type": str,
                    "notes": "Name of the device.",
                },
                "port": {
                    "default": "COM",
                    "type": str,
                    "notes": "Arduino serial port for the P4PP controller.",
                },
                "baudrate": {
                    "default": 115200,
                    "type": int,
                    "notes": "P4PP serial baudrate.",
                },
                "timeout": {
                    "default": 0.2,
                    "type": float,
                    "notes": "Serial readline timeout in seconds.",
                },
                "startup_delay": {
                    "default": 2.0,
                    "type": float,
                    "notes": "Delay after opening serial to allow Arduino reset.",
                },
                "command_timeout": {
                    "default": 30.0,
                    "type": float,
                    "notes": "Timeout for position refresh and other short commands.",
                },
                "motion_timeout": {
                    "default": 60.0,
                    "type": float,
                    "notes": "Timeout for motion commands.",
                },
                "home_timeout": {
                    "default": 60.0,
                    "type": float,
                    "notes": "Timeout for homing commands.",
                },
                "measure_timeout": {
                    "default": 30.0,
                    "type": float,
                    "notes": "Timeout for MEASURE or MEASURE_N commands.",
                },
                "poll_interval": {
                    "default": 0.2,
                    "type": float,
                    "notes": "Position polling interval while motion or homing is active.",
                },
                "rotation_safety_linear_mm": {
                    "default": 45.0,
                    "type": float,
                    "notes": "Block rotational homing and moves when linear position is at or above this value in mm.",
                },
                "measurement_resistor_ohms": {
                    "default": 681.0,
                    "type": float,
                    "notes": "Measurement resistor selection. Allowed values are 681 and 68.1 ohm.",
                },
                "save_directory": {
                    "default": "data/resistance/",
                    "type": str,
                    "notes": "Default directory for saved resistance CSV files.",
                },
            },
        },
        "commands": {
            "P4PPConnect": {
                "default_code": "P4PPConnect(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "P4PP",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": P4PPConnect,
            },
            "P4PPInitialize": {
                "default_code": "P4PPInitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "P4PP",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": P4PPInitialize,
            },
            "P4PPDeinitialize": {
                "default_code": "P4PPDeinitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "P4PP",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": P4PPDeinitialize,
            },
            "P4PPRefreshPosition": {
                "default_code": "P4PPRefreshPosition(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "P4PP",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": P4PPRefreshPosition,
            },
            "P4PPHomeLinear": {
                "default_code": "P4PPHomeLinear(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "P4PP",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": P4PPHomeLinear,
            },
            "P4PPHomeRotational": {
                "default_code": "P4PPHomeRotational(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "P4PP",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": P4PPHomeRotational,
            },
            "P4PPHomeAll": {
                "default_code": "P4PPHomeAll(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "P4PP",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": P4PPHomeAll,
            },
            "P4PPMoveLinearAbsolute": {
                "default_code": "P4PPMoveLinearAbsolute(receiver= '', position_mm= 0.0)",
                "args": {
                    "receiver": {
                        "default": "P4PP",
                        "type": str,
                        "notes": "",
                    },
                    "position_mm": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Absolute linear position in mm.",
                    },
                },
                "obj": P4PPMoveLinearAbsolute,
            },
            "P4PPMoveLinearRelative": {
                "default_code": "P4PPMoveLinearRelative(receiver= '', distance_mm= 0.0)",
                "args": {
                    "receiver": {
                        "default": "P4PP",
                        "type": str,
                        "notes": "",
                    },
                    "distance_mm": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Relative linear distance in mm.",
                    },
                },
                "obj": P4PPMoveLinearRelative,
            },
            "P4PPMoveRotationalAbsolute": {
                "default_code": "P4PPMoveRotationalAbsolute(receiver= '', position_deg= 0.0)",
                "args": {
                    "receiver": {
                        "default": "P4PP",
                        "type": str,
                        "notes": "",
                    },
                    "position_deg": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Absolute rotational position in degrees.",
                    },
                },
                "obj": P4PPMoveRotationalAbsolute,
            },
            "P4PPMoveRotationalRelative": {
                "default_code": "P4PPMoveRotationalRelative(receiver= '', distance_deg= 0.0)",
                "args": {
                    "receiver": {
                        "default": "P4PP",
                        "type": str,
                        "notes": "",
                    },
                    "distance_deg": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Relative rotational distance in degrees.",
                    },
                },
                "obj": P4PPMoveRotationalRelative,
            },
            "P4PPMeasure": {
                "default_code": "P4PPMeasure(receiver= '', cycles= 20)",
                "args": {
                    "receiver": {
                        "default": "P4PP",
                        "type": str,
                        "notes": "",
                    },
                    "cycles": {
                        "default": 20,
                        "type": int,
                        "notes": "Number of measurement cycles. Uses firmware averaging when greater than 1.",
                    },
                },
                "obj": P4PPMeasure,
            },
            "P4PPSetMeasurementResistor": {
                "default_code": "P4PPSetMeasurementResistor(receiver= '', resistor_ohms= 681.0)",
                "args": {
                    "receiver": {
                        "default": "P4PP",
                        "type": str,
                        "notes": "",
                    },
                    "resistor_ohms": {
                        "default": 681.0,
                        "type": float,
                        "notes": "Measurement resistor selection. Use 681 or 68.1 ohm.",
                    },
                },
                "obj": P4PPSetMeasurementResistor,
            },
            "P4PPSaveMeasurementCsv": {
                "default_code": "P4PPSaveMeasurementCsv(receiver= '', sample_id=None, csv_path=None, notes=None)",
                "args": {
                    "receiver": {
                        "default": "P4PP",
                        "type": str,
                        "notes": "",
                    },
                    "sample_id": {
                        "default": None,
                        "type": str,
                        "notes": "Optional sample identifier for the CSV row.",
                    },
                    "csv_path": {
                        "default": None,
                        "type": str,
                        "notes": "Optional override path. Defaults to data/resistance/p4pp_measurements.csv.",
                    },
                    "notes": {
                        "default": None,
                        "type": str,
                        "notes": "Optional note stored with the measurement row.",
                    },
                },
                "obj": P4PPSaveMeasurementCsv,
            },
        },
    },
    "Keithley2450": {
        "obj": Keithley2450,
        "serial": True,
        "serial_sequence": ["Keithley2450Initialize"],
        "import_device": "from devices.keithley_2450 import Keithley2450",
        "import_commands": "from commands.keithley_2450_commands import *",
        "init": {
            "default_code": "Keithley2450(name='Keithley2450', ID='', query_delay=0)",
            "obj_name": "Keithley2450",
            "args": {
                "name": {
                    "default": "Keithley2450",
                    "type": str,
                    "notes": "Name of the device",
                },
                "ID": {
                    "default": "",
                    "type": str,
                    "notes": "ID of the device",
                },
                "query_delay": {
                    "default": 0,
                    "type": int,
                    "notes": "Delay between queries",
                },
            },
        },
        "commands": {
            "Keithley2450Initialize": {
                "default_code": "Keithley2450Initialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Keithley2450",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": Keithley2450Initialize,
            },
            "Keithley2450Deinitialize": {
                "default_code": "Keithley2450Deinitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Keithley2450",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": Keithley2450Deinitialize,
            },
            "KeithleyWait": {
                "default_code": "KeithleyWait(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Keithley2450",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": KeithleyWait,
            },
            "KeithleyWriteCommand": {
                "default_code": "KeithleyWriteCommand(receiver= '', command= '')",
                "args": {
                    "receiver": {
                        "default": "Keithley2450",
                        "type": str,
                        "notes": "",
                    },
                    "command": {
                        "default": "",
                        "type": str,
                        "notes": "",
                    },
                },
                "obj": KeithleyWriteCommand,
            },
            "KeithleySetTerminal": {
                "default_code": "KeithleySetTerminal(receiver= '', position= 'front')",
                "args": {
                    "receiver": {
                        "default": "Keithley2450",
                        "type": str,
                        "notes": "",
                    },
                    "position": {
                        "default": "front",
                        "type": str,
                        "notes": "",
                    },
                },
                "obj": KeithleySetTerminal,
            },
            "KeithleyErrorCheck": {
                "default_code": "KeithleyErrorCheck(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Keithley2450",
                        "type": str,
                        "notes": "",
                    }
                },
                "obj": KeithleyErrorCheck,
            },
            "KeithleyClearBuffer": {
                "default_code": "KeithleyClearBuffer(receiver= '', buffer='defbuffer1')",
                "args": {
                    "receiver": {
                        "default": "Keithley2450",
                        "type": str,
                        "notes": "",
                    },
                    "buffer": {
                        "default": "defbuffer1",
                        "type": str,
                        "notes": "",
                    },
                },
                "obj": KeithleyClearBuffer,
            },
            "KeithleyIVCharacteristic": {
                "default_code": "KeithleyIVCharacteristic(receiver= '', ilimit=0.0, vmin=0.0, vmax=0.0, delay=0.0, steps=60)",
                "args": {
                    "receiver": {
                        "default": "Keithley2450",
                        "type": str,
                        "notes": "",
                    },
                    "ilimit": {
                        "default": 0.0,
                        "type": float,
                        "notes": "",
                    },
                    "vmin": {
                        "default": 0.0,
                        "type": float,
                        "notes": "",
                    },
                    "vmax": {
                        "default": 0.0,
                        "type": float,
                        "notes": "",
                    },
                    "delay": {
                        "default": 0.0,
                        "type": float,
                        "notes": "",
                    },
                    "steps": {
                        "default": 60,
                        "type": int,
                        "notes": "",
                    },
                },
                "obj": KeithleyIVCharacteristic,
            },
            "KeithleyFourPoint": {
                "default_code": "KeithleyFourPoint(receiver= '', test_curr=0.0, vlimit=0.0, curr_reversal = False)",
                "args": {
                    "receiver": {
                        "default": "Keithley2450",
                        "type": str,
                        "notes": "",
                    },
                    "test_curr": {
                        "default": 0.0,
                        "type": float,
                        "notes": "",
                    },
                    "vlimit": {
                        "default": 0.0,
                        "type": float,
                        "notes": "",
                    },
                    "curr_reversal": {
                        "default": False,
                        "type": bool,
                        "notes": "",
                    },
                },
                "obj": KeithleyFourPoint,
            },
            "KeithleyGetData": {
                "default_code": "KeithleyGetData(receiver= '', filename=None, four_point= False)",
                "args": {
                    "receiver": {
                        "default": "Keithley2450",
                        "type": str,
                        "notes": "",
                    },
                    "filename": {
                        "default": None,
                        "type": str,
                        "notes": "",
                    },
                    "four_point": {
                        "default": False,
                        "type": bool,
                        "notes": "",
                    },
                },
                "obj": KeithleyGetData,
            },
        },
    },
    "PrintingStage": heating_stage_ref,
    "AnnealingStage": heating_stage_ref,
    "MultiStepper": {
        "obj": MultiStepper,
        "serial": True,
        "serial_sequence": ["MultiStepperConnect", "MultiStepperInitialize"],
        "import_device": "from devices.multi_stepper import MultiStepper",
        "import_commands": "from commands.multi_stepper_commands import *",
        "init": {
            "default_code": "MultiStepper(name='MultiStepper', port='', baudrate=115200, timeout=0.1, destination=0x50, source=0x01, channel=1)",
            "obj_name": "MultiStepper",
            "args": {
                "name": {
                    "default": "MultiStepper",
                    "type": str,
                    "notes": "Name of the device",
                },
                "port": {
                    "default": "COM",
                    "type": str,
                    "notes": "Port of the device",
                },
                "baudrate": {
                    "default": 115200,
                    "type": int,
                    "notes": "Baudrate of the device",
                },
                "timeout": {
                    "default": 1.0,
                    "type": float,
                    "notes": "Timeout of the device",
                },
                "stepper_list": {
                    "default": (1,),
                    "type": Tuple[int, ...],
                    "notes": "List of stepper numbers",
                },
                "move_timeout": {
                    "default": 30.0,
                    "type": float,
                    "notes": "Timeout for move commands",
                },
            },
        },
        "commands": {
            "MultiStepperConnect": {
                "default_code": "MultiStepperConnect(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "MultiStepper",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": MultiStepperConnect,
            },
            "MultiStepperInitialize": {
                "default_code": "MultiStepperInitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "MultiStepper",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": MultiStepperInitialize,
            },
            "MultiStepperDeinitialize": {
                "default_code": "MultiStepperDeinitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "MultiStepper",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": MultiStepperDeinitialize,
            },
            "MultiStepperMoveAbsolute": {
                "default_code": "MultiStepperMoveAbsolute(receiver= '', stepper_number= 0, position= 0)",
                "args": {
                    "receiver": {
                        "default": "MultiStepper",
                        "type": str,
                        "notes": "Name of the device",
                    },
                    "stepper_number": {
                        "default": 0,
                        "type": int,
                        "notes": "Number of the stepper",
                    },
                    "position": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Position to move to",
                    },
                },
                "obj": MultiStepperMoveAbsolute,
            },
            "MultiStepperMoveRelative": {
                "default_code": "MultiStepperMoveRelative(receiver= '', stepper_number= 0, distance= 0)",
                "args": {
                    "receiver": {
                        "default": "MultiStepper",
                        "type": str,
                        "notes": "Name of the device",
                    },
                    "stepper_number": {
                        "default": 0,
                        "type": int,
                        "notes": "Number of the stepper",
                    },
                    "distance": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Distance to move",
                    },
                },
                "obj": MultiStepperMoveRelative,
            },
        },
    },
    "SHT85HumidityTempSensor": {
        "obj": SHT85HumidityTempSensor,
        "serial": True,
        "serial_sequence": ["SHT85Connect", "SHT85Initialize"],
        "import_device": "from devices.sht85_sensor import SHT85HumidityTempSensor",
        "import_commands": "from commands.sht85_sensor_commands import *",
        "init": {
            "default_code": "SHT85HumidityTempSensor(name='SHT85HumidityTempSensor', port='', baudrate=9600, timeout=1.0)",
            "obj_name": "SHT85HumidityTempSensor",
            "args": {
                "name": {
                    "default": "SHT85HumidityTempSensor",
                    "type": str,
                    "notes": "Name of the device",
                },
                "port": {
                    "default": "COM",
                    "type": str,
                    "notes": "Port of the device",
                },
                "baudrate": {
                    "default": 9600,
                    "type": int,
                    "notes": "Baudrate of the device",
                },
                "timeout": {
                    "default": 1.0,
                    "type": float,
                    "notes": "Timeout of the device",
                },
            },
        },
        "commands": {
            "SHT85Connect": {
                "default_code": "SHT85Connect(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "SHT85HumidityTempSensor",
                        "type": str,
                        "notes": "Name of the device",
                    },
                },
                "obj": SHT85Connect,
            },
            "SHT85Initialize": {
                "default_code": "SHT85Initialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "SHT85HumidityTempSensor",
                        "type": str,
                        "notes": "Name of the device",
                    },
                },
                "obj": SHT85Initialize,
            },
            "SHT85Deinitialize": {
                "default_code": "SHT85Deinitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "SHT85HumidityTempSensor",
                        "type": str,
                        "notes": "Name of the device",
                    },
                },
                "obj": SHT85Deinitialize,
            },
            "SHT85GetHumidity": {
                "default_code": "SHT85GetHumidity(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "SHT85HumidityTempSensor",
                        "type": str,
                        "notes": "Name of the device",
                    },
                },
                "obj": SHT85GetHumidity,
            },
            "SHT85GetTemp": {
                "default_code": "SHT85GetTemp(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "SHT85HumidityTempSensor",
                        "type": str,
                        "notes": "Name of the device",
                    },
                },
                "obj": SHT85GetTemp,
            },
        },
    },
    "Sonicator": {
        "obj": Sonicator,
        "serial": True,
        "serial_sequence": ["SonicatorConnect", "SonicatorInitialize"],
        "import_device": "from devices.sonicator import Sonicator",
        "import_commands": "from commands.sonicator_commands import *",
        "init": {
            "default_code": "Sonicator(name='Sonicator', port='', baudrate=9600, timeout=0.5, connect_delay_s=3.0, response_timeout_s=3.0, power_probe_timeout_s=5.0, line_terminator='\\n', command_prefix='>', debug_io=False)",
            "obj_name": "Sonicator",
            "args": {
                "name": {
                    "default": "Sonicator",
                    "type": str,
                    "notes": "Name of the device",
                },
                "port": {
                    "default": "COM",
                    "type": str,
                    "notes": "Port of the Arduino Uno R3 wrapper",
                },
                "baudrate": {
                    "default": 9600,
                    "type": int,
                    "notes": "Baudrate of the device",
                },
                "timeout": {
                    "default": 0.5,
                    "type": float,
                    "notes": "Serial readline timeout in seconds.",
                },
                "connect_delay_s": {
                    "default": 3.0,
                    "type": float,
                    "notes": "Wait time after opening the serial port.",
                },
                "response_timeout_s": {
                    "default": 3.0,
                    "type": float,
                    "notes": "Timeout for status, start, stop, and button commands.",
                },
                "power_probe_timeout_s": {
                    "default": 5.0,
                    "type": float,
                    "notes": "Timeout for the intrusive power-probe command.",
                },
                "line_terminator": {
                    "default": "\\n",
                    "type": str,
                    "notes": "Line terminator sent after each command keyword.",
                },
                "command_prefix": {
                    "default": ">",
                    "type": str,
                    "notes": "Command header character expected by the Arduino sketch.",
                },
                "debug_io": {
                    "default": False,
                    "type": bool,
                    "notes": "Print raw TX/RX serial traffic for debugging.",
                },
            },
        },
        "commands": {
            "SonicatorConnect": {
                "default_code": "SonicatorConnect(receiver= '')",
                "args": {
                    "receiver": {"default": "Sonicator", "type": str, "notes": "Name of the device"}
                },
                "obj": SonicatorConnect,
            },
            "SonicatorInitialize": {
                "default_code": "SonicatorInitialize(receiver= '')",
                "args": {
                    "receiver": {"default": "Sonicator", "type": str, "notes": "Name of the device"}
                },
                "obj": SonicatorInitialize,
            },
            "SonicatorDeinitialize": {
                "default_code": "SonicatorDeinitialize(receiver= '', reset_init_flag=True, close_serial=False)",
                "args": {
                    "receiver": {"default": "Sonicator", "type": str, "notes": "Name of the device"},
                    "reset_init_flag": {"default": True, "type": bool, "notes": "Reset the initialized flag."},
                    "close_serial": {"default": False, "type": bool, "notes": "Close the serial port after deinitialize."},
                },
                "obj": SonicatorDeinitialize,
            },
            "SonicatorGetStatus": {
                "default_code": "SonicatorGetStatus(receiver= '')",
                "args": {
                    "receiver": {"default": "Sonicator", "type": str, "notes": "Name of the device"}
                },
                "obj": SonicatorGetStatus,
            },
            "SonicatorStartSonicating": {
                "default_code": "SonicatorStartSonicating(receiver= '')",
                "args": {
                    "receiver": {"default": "Sonicator", "type": str, "notes": "Name of the device"}
                },
                "obj": SonicatorStartSonicating,
            },
            "SonicatorStopSonicating": {
                "default_code": "SonicatorStopSonicating(receiver= '')",
                "args": {
                    "receiver": {"default": "Sonicator", "type": str, "notes": "Name of the device"}
                },
                "obj": SonicatorStopSonicating,
            },
            "SonicatorPressButton": {
                "default_code": "SonicatorPressButton(receiver= '')",
                "args": {
                    "receiver": {"default": "Sonicator", "type": str, "notes": "Name of the device"}
                },
                "obj": SonicatorPressButton,
            },
            "SonicatorProbePowerConnection": {
                "default_code": "SonicatorProbePowerConnection(receiver= '')",
                "args": {
                    "receiver": {"default": "Sonicator", "type": str, "notes": "Name of the device"}
                },
                "obj": SonicatorProbePowerConnection,
            },
        },
    },
    "SubstrateHotel": {
        "obj": SubstrateHotel,
        "serial": True,
        "serial_sequence": ["SubstrateHotelConnect", "SubstrateHotelInitialize"],
        "import_device": "from devices.substrate_hotel import SubstrateHotel",
        "import_commands": "from commands.substrate_hotel_commands import *",
        "init": {
            "default_code": "SubstrateHotel(name='SubstrateHotel', port='', baudrate=9600, timeout=1.0, connect_delay_s=5.0, ready_timeout_s=5.0, home_timeout_s=300.0, move_timeout_s=300.0)",
            "obj_name": "SubstrateHotel",
            "args": {
                "name": {"default": "SubstrateHotel", "type": str, "notes": "Name of the device"},
                "port": {"default": "COM", "type": str, "notes": "Arduino serial port"},
                "baudrate": {"default": 9600, "type": int, "notes": "Baudrate of the Arduino controller"},
                "timeout": {"default": 1.0, "type": float, "notes": "Serial readline timeout in seconds"},
                "connect_delay_s": {"default": 5.0, "type": float, "notes": "Delay after opening the serial port to allow Arduino reset"},
                "ready_timeout_s": {"default": 5.0, "type": float, "notes": "Timeout while waiting for the Arduino Ready banner"},
                "home_timeout_s": {"default": 300.0, "type": float, "notes": "Timeout for the homing operation"},
                "move_timeout_s": {"default": 300.0, "type": float, "notes": "Default timeout for absolute moves"},
            },
        },
        "commands": {
            "SubstrateHotelConnect": {
                "default_code": "SubstrateHotelConnect(receiver= '')",
                "args": {"receiver": {"default": "SubstrateHotel", "type": str, "notes": "Name of the device"}},
                "obj": SubstrateHotelConnect,
            },
            "SubstrateHotelInitialize": {
                "default_code": "SubstrateHotelInitialize(receiver= '')",
                "args": {"receiver": {"default": "SubstrateHotel", "type": str, "notes": "Name of the device"}},
                "obj": SubstrateHotelInitialize,
            },
            "SubstrateHotelDeinitialize": {
                "default_code": "SubstrateHotelDeinitialize(receiver= '', reset_init_flag=True, close_serial=False)",
                "args": {
                    "receiver": {"default": "SubstrateHotel", "type": str, "notes": "Name of the device"},
                    "reset_init_flag": {"default": True, "type": bool, "notes": "Reset the initialized flag."},
                    "close_serial": {"default": False, "type": bool, "notes": "Close the serial port after deinitialize."},
                },
                "obj": SubstrateHotelDeinitialize,
            },
            "SubstrateHotelHome": {
                "default_code": "SubstrateHotelHome(receiver= '')",
                "args": {"receiver": {"default": "SubstrateHotel", "type": str, "notes": "Name of the device"}},
                "obj": SubstrateHotelHome,
            },
            "SubstrateHotelMoveToPosition": {
                "default_code": "SubstrateHotelMoveToPosition(receiver= '', position_mm=0.0, speed_mm_per_s=20.0, move_timeout=None)",
                "args": {
                    "receiver": {"default": "SubstrateHotel", "type": str, "notes": "Name of the device"},
                    "position_mm": {"default": 0.0, "type": float, "notes": "Absolute target position in mm (0-430)."},
                    "speed_mm_per_s": {"default": 20.0, "type": float, "notes": "Requested move speed in mm/s."},
                    "move_timeout": {"default": None, "type": float, "notes": "Optional override timeout for this move."},
                },
                "obj": SubstrateHotelMoveToPosition,
            },
        },
    },
    "SubstrateDispenser": {
        "obj": SubstrateDispenser,
        "serial": True,
        "serial_sequence": ["SubstrateDispenserConnect", "SubstrateDispenserInitialize"],
        "import_device": "from devices.substrate_dispenser import SubstrateDispenser",
        "import_commands": "from commands.substrate_dispenser_commands import *",
        "init": {
            "default_code": "SubstrateDispenser(name='SubstrateDispenser', port='', baudrate=9600, timeout=1.0, connect_delay_s=5.0, ready_timeout_s=5.0, home_timeout_s=30.0, move_timeout_s=30.0)",
            "obj_name": "SubstrateDispenser",
            "args": {
                "name": {"default": "SubstrateDispenser", "type": str, "notes": "Name of the device"},
                "port": {"default": "COM", "type": str, "notes": "Arduino serial port"},
                "baudrate": {"default": 9600, "type": int, "notes": "Baudrate of the Arduino controller"},
                "timeout": {"default": 1.0, "type": float, "notes": "Serial readline timeout in seconds"},
                "connect_delay_s": {"default": 5.0, "type": float, "notes": "Delay after opening the serial port to allow Arduino reset"},
                "ready_timeout_s": {"default": 5.0, "type": float, "notes": "Timeout while waiting for the Arduino Ready banner"},
                "home_timeout_s": {"default": 30.0, "type": float, "notes": "Timeout for the homing operation"},
                "move_timeout_s": {"default": 30.0, "type": float, "notes": "Default timeout for absolute moves"},
            },
        },
        "commands": {
            "SubstrateDispenserConnect": {
                "default_code": "SubstrateDispenserConnect(receiver= '')",
                "args": {"receiver": {"default": "SubstrateDispenser", "type": str, "notes": "Name of the device"}},
                "obj": SubstrateDispenserConnect,
            },
            "SubstrateDispenserInitialize": {
                "default_code": "SubstrateDispenserInitialize(receiver= '')",
                "args": {"receiver": {"default": "SubstrateDispenser", "type": str, "notes": "Name of the device"}},
                "obj": SubstrateDispenserInitialize,
            },
            "SubstrateDispenserDeinitialize": {
                "default_code": "SubstrateDispenserDeinitialize(receiver= '', reset_init_flag=True, close_serial=False)",
                "args": {
                    "receiver": {"default": "SubstrateDispenser", "type": str, "notes": "Name of the device"},
                    "reset_init_flag": {"default": True, "type": bool, "notes": "Reset the initialized flag."},
                    "close_serial": {"default": False, "type": bool, "notes": "Close the serial port after deinitialize."},
                },
                "obj": SubstrateDispenserDeinitialize,
            },
            "SubstrateDispenserHome": {
                "default_code": "SubstrateDispenserHome(receiver= '')",
                "args": {"receiver": {"default": "SubstrateDispenser", "type": str, "notes": "Name of the device"}},
                "obj": SubstrateDispenserHome,
            },
            "SubstrateDispenserMoveToPosition": {
                "default_code": "SubstrateDispenserMoveToPosition(receiver= '', position_mm=0.0, speed_mm_per_s=20.0, move_timeout=None)",
                "args": {
                    "receiver": {"default": "SubstrateDispenser", "type": str, "notes": "Name of the device"},
                    "position_mm": {"default": 0.0, "type": float, "notes": "Absolute target position in mm (0-45)."},
                    "speed_mm_per_s": {"default": 20.0, "type": float, "notes": "Requested move speed in mm/s."},
                    "move_timeout": {"default": None, "type": float, "notes": "Optional override timeout for this move."},
                },
                "obj": SubstrateDispenserMoveToPosition,
            },
        },
    },
    "MassFlowController": {
        "obj": MassFlowController,
        "serial": True,
        "serial_sequence": ["MassFlowControllerInitialize"],
        "import_device": "from devices.mfc import MassFlowController",
        "import_commands": "from commands.mfc_commands import *",
        "init": {
            "default_code": "MassFlowController(name='MassFlowController', ip='192.168.2.155')",
            "obj_name": "MassFlowController",
            "args": {
                "name": {
                    "default": "MassFlowController",
                    "type": str,
                    "notes": "Name of the device",
                },
                "ip": {
                    "default": "192.168.2.155",
                    "type": str,
                    "notes": "IP of the device",
                },
            },
        },
        "commands": {
            "MFCInitialize": {
                "default_code": "MFCInitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "MassFlowController",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": MFCInitialize,
            },
            "MFCDeinitialize": {
                "default_code": "MFCDeinitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "MassFlowController",
                        "type": str,
                        "notes": "Name of the device",
                    },
                    "obj": MFCDeinitialize,
                },
            },
            "MFCGetData": {
                "default_code": "MFCGetData(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "MassFlowController",
                        "type": str,
                        "notes": "Name of the device",
                    },
                },
                "obj": MFCGetData,
            },
            "MFCSetGas": {
                "default_code": "MFCSetGas(receiver= '', gas= 'N2')",
                "args": {
                    "receiver": {
                        "default": "MassFlowController",
                        "type": str,
                        "notes": "Name of the device",
                    },
                    "gas": {
                        "default": "N2",
                        "type": str,
                        "notes": "Gas to set",
                    },
                },
                "obj": MFCSetGas,
            },
            "MFCSet": {
                "default_code": "MFCSet(receiver= '', setpoint= 0.0)",
                "args": {
                    "receiver": {
                        "default": "MassFlowController",
                        "type": str,
                        "notes": "Name of the device",
                    },
                    "setpoint": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Setpoint to set",
                    },
                },
                "obj": MFCSet,
            },
            "MFCOpen": {
                "default_code": "MFCOpen(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "MassFlowController",
                        "type": str,
                        "notes": "Name of the device",
                    },
                },
                "obj": MFCOpen,
            },
        },
    },
    "NewportESP301": {
        "obj": NewportESP301,
        "serial": True,
        "serial_sequence": ["NewportESP301Connect", "NewportESP301Initialize"],
        "import_device": "from devices.newport_esp301 import NewportESP301",
        "import_commands": "from commands.newport_esp301_commands import *",
        "init": {
            "default_code": "NewportESP301(name='NewportESP301', port='', baudrate=921600, timeout=1.0, axis_list=(1, 2, 3), default_speed=10.0, poll_interval=0.1, axis_configs={1: {'stage_model': 'ILS100CC', 'motion_type': 'linear', 'units': 'mm', 'home_mode': 'OR4', 'zero_position': 0.0, 'default_speed': 10.0}, 2: {'stage_model': 'UTS100PP', 'motion_type': 'linear', 'units': 'mm', 'home_mode': 'OR4', 'zero_position': 0.0, 'default_speed': 10.0}, 3: {'stage_model': 'PR50PP', 'motion_type': 'rotary', 'units': 'deg', 'home_mode': 'OR1', 'zero_position': 0.0, 'default_speed': 10.0}})",
            "obj_name": "NewportESP301",
            "args": {
                "name": {
                    "default": "NewportESP301",
                    "type": str,
                    "notes": "Name of the device",
                },
                "port": {
                    "default": "COM",
                    "type": str,
                    "notes": "Port of the device",
                },
                "baudrate": {
                    "default": 921600,
                    "type": int,
                    "notes": "Baudrate of the device",
                },
                "timeout": {
                    "default": 1.0,
                    "type": float,
                    "notes": "Timeout of the device",
                },
                "axis_list": {
                    "default": (1, 2, 3),
                    "type": Tuple[int, ...],
                    "notes": "List of axis numbers",
                },
                "default_speed": {
                    "default": 10.0,
                    "type": float,
                    "notes": "Default speed of the device",
                },
                "poll_interval": {
                    "default": 0.1,
                    "type": float,
                    "notes": "Poll interval of the device",
                },
                "axis_configs": {
                    "default": {
                        1: {"stage_model": "ILS100CC", "motion_type": "linear", "units": "mm", "home_mode": "OR4", "zero_position": 0.0, "default_speed": 10.0},
                        2: {"stage_model": "UTS100PP", "motion_type": "linear", "units": "mm", "home_mode": "OR4", "zero_position": 0.0, "default_speed": 10.0},
                        3: {"stage_model": "PR50PP", "motion_type": "rotary", "units": "deg", "home_mode": "OR1", "zero_position": 0.0, "default_speed": 10.0},
                    },
                    "type": dict,
                    "notes": "Axis-specific configuration keyed by axis number. Recommended ESP301-3N setup: axes 1 and 2 linear in mm with OR4, axis 3 rotary in deg with OR1.",
                },
            },
        },
        "commands": {
            "NewportESP301Connect": {
                "default_code": "NewportESP301Connect(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "NewportESP301",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": NewportESP301Connect,
            },
            "NewportESP301Initialize": {
                "default_code": "NewportESP301Initialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "NewportESP301",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": NewportESP301Initialize,
            },
            "NewportESP301Deinitialize": {
                "default_code": "NewportESP301Deinitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "NewportESP301",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": NewportESP301Deinitialize,
            },
            "NewportESP301MoveSpeedAbsolute": {
                "default_code": "NewportESP301MoveSpeedAbsolute(receiver= '', axis_number= 1, position= 0, speed= 20.0)",
                "args": {
                    "receiver": {
                        "default": "NewportESP301",
                        "type": str,
                        "notes": "Name of the device",
                    },
                    "axis_number": {
                        "default": 1,
                        "type": int,
                        "notes": "Axis number",
                    },
                    "position": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Position to move to",
                    },
                    "speed": {
                        "default": 20.0,
                        "type": float,
                        "notes": "Speed to move at",
                    },
                },
                "obj": NewportESP301MoveSpeedAbsolute,
            },
            "NewportESP301MoveSpeedRelative": {
                "default_code": "NewportESP301MoveSpeedRelative(receiver= '', axis_number= 1, distance= 0, speed= 20.0)",
                "args": {
                    "receiver": {
                        "default": "NewportESP301",
                        "type": str,
                        "notes": "Name of the device",
                    },
                    "axis_number": {
                        "default": 1,
                        "type": int,
                        "notes": "Axis number",
                    },
                    "distance": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Distance to move",
                    },
                    "speed": {
                        "default": 20.0,
                        "type": float,
                        "notes": "Speed to move at",
                    },
                },
                "obj": NewportESP301MoveSpeedRelative,
            },
        },
    },
    "Newport94043ASolarSim": {
        "obj": Newport94043ASolarSim,
        "serial": True,
        "serial_sequence": ["Newport94043ASolarSimConnect", "Newport94043ASolarSimInitialize"],
        "import_device": "from devices.newport_94043a_solar_sim import Newport94043ASolarSim",
        "import_commands": "from commands.newport_94043a_solar_sim_commands import *",
        "telemetry": {
            "parameters": {
                "watts": {
                    "function_name": "get_watts",
                    "data_type": "str",
                    "units": "W",
                },
                "amps": {
                    "function_name": "get_amps",
                    "data_type": "str",
                    "units": "A",
                },
                "volts": {
                    "function_name": "get_volts",
                    "data_type": "str",
                    "units": "V",
                },
            },
            "options": {"custom_init_args": ["port"]},
        },
        "init": {
            "default_code": "Newport94043ASolarSim(name='Newport94043ASolarSim', port='', baudrate=9600, timeout=1.0, line_terminator='\\r', lamp_hours_warning_threshold=1000.0, default_power_watts=400, max_power_watts=450)",
            "obj_name": "Newport94043ASolarSim",
            "args": {
                "name": {
                    "default": "Newport94043ASolarSim",
                    "type": str,
                    "notes": "Name of the device",
                },
                "port": {
                    "default": "COM",
                    "type": str,
                    "notes": "COM port via RS-232 to USB adapter",
                },
                "baudrate": {
                    "default": 9600,
                    "type": int,
                    "notes": "69920 RS-232 baudrate",
                },
                "timeout": {
                    "default": 1.0,
                    "type": float,
                    "notes": "Serial timeout in seconds",
                },
                "line_terminator": {
                    "default": "\r",
                    "type": str,
                    "notes": "Command terminator for RS-232",
                },
                "lamp_hours_warning_threshold": {
                    "default": 1000.0,
                    "type": float,
                    "notes": "Warn during initialize when lamp hours exceed this threshold.",
                },
                "default_power_watts": {
                    "default": 400,
                    "type": int,
                    "notes": "Default watts preset applied during initialize.",
                },
                "max_power_watts": {
                    "default": 450,
                    "type": int,
                    "notes": "Safety ceiling for watts preset values.",
                },
            },
        },
        "commands": {
            "Newport94043ASolarSimConnect": {
                "default_code": "Newport94043ASolarSimConnect(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimConnect,
            },
            "Newport94043ASolarSimInitialize": {
                "default_code": "Newport94043ASolarSimInitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimInitialize,
            },
            "Newport94043ASolarSimDeinitialize": {
                "default_code": "Newport94043ASolarSimDeinitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimDeinitialize,
            },
            "Newport94043ASolarSimIdentify": {
                "default_code": "Newport94043ASolarSimIdentify(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimIdentify,
            },
            "Newport94043ASolarSimStatusByte": {
                "default_code": "Newport94043ASolarSimStatusByte(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimStatusByte,
            },
            "Newport94043ASolarSimEventStatus": {
                "default_code": "Newport94043ASolarSimEventStatus(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimEventStatus,
            },
            "Newport94043ASolarSimLampStart": {
                "default_code": "Newport94043ASolarSimLampStart(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimLampStart,
            },
            "Newport94043ASolarSimLampStop": {
                "default_code": "Newport94043ASolarSimLampStop(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimLampStop,
            },
            "Newport94043ASolarSimSetPowerMode": {
                "default_code": "Newport94043ASolarSimSetPowerMode(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimSetPowerMode,
            },
            "Newport94043ASolarSimGetAmps": {
                "default_code": "Newport94043ASolarSimGetAmps(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimGetAmps,
            },
            "Newport94043ASolarSimGetVolts": {
                "default_code": "Newport94043ASolarSimGetVolts(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimGetVolts,
            },
            "Newport94043ASolarSimGetWatts": {
                "default_code": "Newport94043ASolarSimGetWatts(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimGetWatts,
            },
            "Newport94043ASolarSimGetLampHours": {
                "default_code": "Newport94043ASolarSimGetLampHours(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimGetLampHours,
            },
            "Newport94043ASolarSimGetPowerPreset": {
                "default_code": "Newport94043ASolarSimGetPowerPreset(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimGetPowerPreset,
            },
            "Newport94043ASolarSimGetCurrentLimit": {
                "default_code": "Newport94043ASolarSimGetCurrentLimit(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimGetCurrentLimit,
            },
            "Newport94043ASolarSimGetPowerLimit": {
                "default_code": "Newport94043ASolarSimGetPowerLimit(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    }
                },
                "obj": Newport94043ASolarSimGetPowerLimit,
            },
            "Newport94043ASolarSimSetPowerPreset": {
                "default_code": "Newport94043ASolarSimSetPowerPreset(receiver= '', watts= 400)",
                "args": {
                    "receiver": {
                        "default": "Newport94043ASolarSim",
                        "type": str,
                        "notes": "Name of the device",
                    },
                    "watts": {
                        "default": 400,
                        "type": int,
                        "notes": "Power preset in watts. Values above 450 W are rejected.",
                    },
                },
                "obj": Newport94043ASolarSimSetPowerPreset,
            },
        },
    },
    "SciencetechUHENLSolarSim": {
        "obj": SciencetechUHENLSolarSim,
        "serial": True,
        "serial_sequence": ["SciencetechUHENLSolarSimConnect", "SciencetechUHENLSolarSimInitialize"],
        "import_device": "from devices.sciencetech_uhe_nl_solar_sim import SciencetechUHENLSolarSim",
        "import_commands": "from commands.sciencetech_uhe_nl_solar_sim_commands import *",
        "init": {
            "default_code": "SciencetechUHENLSolarSim(name='SciencetechUHENLSolarSim', port='', baudrate=9600, timeout=2.0, line_terminator='\\r', connect_delay_s=3.0, command_delay_s=8.0, status_timeout_s=8.0, default_current_percent=85.0, default_attenuator_percent=100, debug_io=False)",
            "obj_name": "SciencetechUHENLSolarSim",
            "args": {
                "name": {
                    "default": "SciencetechUHENLSolarSim",
                    "type": str,
                    "notes": "Name of the device",
                },
                "port": {
                    "default": "COM",
                    "type": str,
                    "notes": "COM port via the UHE-NL RS-232 to USB cable",
                },
                "baudrate": {
                    "default": 9600,
                    "type": int,
                    "notes": "Serial baudrate",
                },
                "timeout": {
                    "default": 2.0,
                    "type": float,
                    "notes": "Serial timeout in seconds",
                },
                "line_terminator": {
                    "default": "\r",
                    "type": str,
                    "notes": "Command line terminator",
                },
                "connect_delay_s": {
                    "default": 3.0,
                    "type": float,
                    "notes": "Delay after opening the serial port",
                },
                "command_delay_s": {
                    "default": 8.0,
                    "type": float,
                    "notes": "Delay after each control command before polling feedback",
                },
                "status_timeout_s": {
                    "default": 8.0,
                    "type": float,
                    "notes": "Timeout while reading the multiline status response",
                },
                "default_current_percent": {
                    "default": 85.0,
                    "type": float,
                    "notes": "Output percentage setpoint applied during initialize after cooling is confirmed on",
                },
                "default_attenuator_percent": {
                    "default": 100,
                    "type": int,
                    "notes": "Attenuator transmission percentage applied during initialize",
                },
                "debug_io": {
                    "default": False,
                    "type": bool,
                    "notes": "Print raw TX/RX serial traffic for debugging",
                },
            },
        },
        "commands": {
            "SciencetechUHENLSolarSimConnect": {
                "default_code": "SciencetechUHENLSolarSimConnect(receiver= '')",
                "args": {
                    "receiver": {"default": "SciencetechUHENLSolarSim", "type": str, "notes": "Name of the device"}
                },
                "obj": SciencetechUHENLSolarSimConnect,
            },
            "SciencetechUHENLSolarSimInitialize": {
                "default_code": "SciencetechUHENLSolarSimInitialize(receiver= '')",
                "args": {
                    "receiver": {"default": "SciencetechUHENLSolarSim", "type": str, "notes": "Name of the device"}
                },
                "obj": SciencetechUHENLSolarSimInitialize,
            },
            "SciencetechUHENLSolarSimDeinitialize": {
                "default_code": "SciencetechUHENLSolarSimDeinitialize(receiver= '', reset_init_flag=True, close_serial=False)",
                "args": {
                    "receiver": {"default": "SciencetechUHENLSolarSim", "type": str, "notes": "Name of the device"},
                    "reset_init_flag": {"default": True, "type": bool, "notes": "Reset initialized flag"},
                    "close_serial": {"default": False, "type": bool, "notes": "Close the serial port"},
                },
                "obj": SciencetechUHENLSolarSimDeinitialize,
            },
            "SciencetechUHENLSolarSimCloseShutter": {
                "default_code": "SciencetechUHENLSolarSimCloseShutter(receiver= '')",
                "args": {
                    "receiver": {"default": "SciencetechUHENLSolarSim", "type": str, "notes": "Name of the device"}
                },
                "obj": SciencetechUHENLSolarSimCloseShutter,
            },
            "SciencetechUHENLSolarSimOpenShutter": {
                "default_code": "SciencetechUHENLSolarSimOpenShutter(receiver= '')",
                "args": {
                    "receiver": {"default": "SciencetechUHENLSolarSim", "type": str, "notes": "Name of the device"}
                },
                "obj": SciencetechUHENLSolarSimOpenShutter,
            },
            "SciencetechUHENLSolarSimEnableCooling": {
                "default_code": "SciencetechUHENLSolarSimEnableCooling(receiver= '')",
                "args": {
                    "receiver": {"default": "SciencetechUHENLSolarSim", "type": str, "notes": "Name of the device"}
                },
                "obj": SciencetechUHENLSolarSimEnableCooling,
            },
            "SciencetechUHENLSolarSimDisableCooling": {
                "default_code": "SciencetechUHENLSolarSimDisableCooling(receiver= '')",
                "args": {
                    "receiver": {"default": "SciencetechUHENLSolarSim", "type": str, "notes": "Name of the device"}
                },
                "obj": SciencetechUHENLSolarSimDisableCooling,
            },
            "SciencetechUHENLSolarSimEnableArcLamp": {
                "default_code": "SciencetechUHENLSolarSimEnableArcLamp(receiver= '')",
                "args": {
                    "receiver": {"default": "SciencetechUHENLSolarSim", "type": str, "notes": "Name of the device"}
                },
                "obj": SciencetechUHENLSolarSimEnableArcLamp,
            },
            "SciencetechUHENLSolarSimDisableArcLamp": {
                "default_code": "SciencetechUHENLSolarSimDisableArcLamp(receiver= '')",
                "args": {
                    "receiver": {"default": "SciencetechUHENLSolarSim", "type": str, "notes": "Name of the device"}
                },
                "obj": SciencetechUHENLSolarSimDisableArcLamp,
            },
            "SciencetechUHENLSolarSimOpenAttenuator": {
                "default_code": "SciencetechUHENLSolarSimOpenAttenuator(receiver= '')",
                "args": {
                    "receiver": {"default": "SciencetechUHENLSolarSim", "type": str, "notes": "Name of the device"}
                },
                "obj": SciencetechUHENLSolarSimOpenAttenuator,
            },
            "SciencetechUHENLSolarSimSetAttenuator": {
                "default_code": "SciencetechUHENLSolarSimSetAttenuator(receiver= '', percent=100)",
                "args": {
                    "receiver": {"default": "SciencetechUHENLSolarSim", "type": str, "notes": "Name of the device"},
                    "percent": {"default": 100, "type": int, "notes": "Attenuator transmission percentage"},
                },
                "obj": SciencetechUHENLSolarSimSetAttenuator,
            },
            "SciencetechUHENLSolarSimSetCurrent": {
                "default_code": "SciencetechUHENLSolarSimSetCurrent(receiver= '', percent=85.0)",
                "args": {
                    "receiver": {"default": "SciencetechUHENLSolarSim", "type": str, "notes": "Name of the device"},
                    "percent": {"default": 85.0, "type": float, "notes": "Lamp output percentage setpoint"},
                },
                "obj": SciencetechUHENLSolarSimSetCurrent,
            },
            "SciencetechUHENLSolarSimGetStatus": {
                "default_code": "SciencetechUHENLSolarSimGetStatus(receiver= '')",
                "args": {
                    "receiver": {"default": "SciencetechUHENLSolarSim", "type": str, "notes": "Name of the device"}
                },
                "obj": SciencetechUHENLSolarSimGetStatus,
            },
            "SciencetechUHENLSolarSimGetFeedback": {
                "default_code": "SciencetechUHENLSolarSimGetFeedback(receiver= '', feedback_type='lamp')",
                "args": {
                    "receiver": {"default": "SciencetechUHENLSolarSim", "type": str, "notes": "Name of the device"},
                    "feedback_type": {"default": "lamp", "type": str, "notes": "Feedback key such as lamp, cool, shutter, attenuator, output, current, voltage, power, hours"},
                },
                "obj": SciencetechUHENLSolarSimGetFeedback,
            },
        },
    },
    "StellarNetSpectrometer": {
        "obj": StellarNetSpectrometer,
        "serial": False,
        "serial_sequence": ["SpectrometerInitialize"],
        "import_device": "from devices.stellarnet_spectrometer import StellarNetSpectrometer",
        "import_commands": "from commands.stellarnet_spectrometer_commands import *",
        "init": {
            "default_code": "StellarNetSpectrometer(name='StellarNetSpectrometer', spec_keys=['UV-Vis'], save_directory='data/spectroscopy/', default_integration_time=(100,))",
            "obj_name": "StellarNetSpectrometer",
            "args": {
                "name": {
                    "default": "StellarNetSpectrometer",
                    "type": str,
                    "notes": "Name of the device",
                },
                "spec_keys": {
                    "default": ["UV-Vis"],
                    "type": list,
                    "notes": "Declared spectrometer keys. Common values are ['UV-Vis'] or ['UV-Vis', 'NIR'].",
                },
                "save_directory": {
                    "default": "data/spectroscopy/",
                    "type": str,
                    "notes": "Directory used when absorbance CSV files are saved.",
                },
                "default_integration_time": {
                    "default": (100,),
                    "type": tuple,
                    "notes": "Default integration time in ms for each declared spectrometer.",
                },
            },
        },
        "commands": {
            "SpectrometerInitialize": {
                "default_code": "SpectrometerInitialize(receiver= '')",
                "args": {
                    "receiver": {"default": "StellarNetSpectrometer", "type": str, "notes": "Name of the device"}
                },
                "obj": SpectrometerInitialize,
            },
            "SpectrometerDeinitialize": {
                "default_code": "SpectrometerDeinitialize(receiver= '', reset_init_flag=True)",
                "args": {
                    "receiver": {"default": "StellarNetSpectrometer", "type": str, "notes": "Name of the device"},
                    "reset_init_flag": {"default": True, "type": bool, "notes": "Reset the initialized flag."},
                },
                "obj": SpectrometerDeinitialize,
            },
            "SpectrometerUpdateDark": {
                "default_code": "SpectrometerUpdateDark(receiver= '', integration_times=(100,), scans_to_avg=(3,), smoothings=(0,), xtimings=(1,))",
                "args": {
                    "receiver": {"default": "StellarNetSpectrometer", "type": str, "notes": "Name of the device"},
                    "integration_times": {"default": (100,), "type": tuple, "notes": "Integration times in ms for each declared spectrometer."},
                    "scans_to_avg": {"default": (3,), "type": tuple, "notes": "Scans-to-average values for each declared spectrometer."},
                    "smoothings": {"default": (0,), "type": tuple, "notes": "Smoothing values for each declared spectrometer."},
                    "xtimings": {"default": (1,), "type": tuple, "notes": "X timing values for each declared spectrometer."},
                },
                "obj": SpectrometerUpdateDark,
            },
            "SpectrometerUpdateBlank": {
                "default_code": "SpectrometerUpdateBlank(receiver= '', integration_times=(100,), scans_to_avg=(3,), smoothings=(0,), xtimings=(1,))",
                "args": {
                    "receiver": {"default": "StellarNetSpectrometer", "type": str, "notes": "Name of the device"},
                    "integration_times": {"default": (100,), "type": tuple, "notes": "Integration times in ms for each declared spectrometer."},
                    "scans_to_avg": {"default": (3,), "type": tuple, "notes": "Scans-to-average values for each declared spectrometer."},
                    "smoothings": {"default": (0,), "type": tuple, "notes": "Smoothing values for each declared spectrometer."},
                    "xtimings": {"default": (1,), "type": tuple, "notes": "X timing values for each declared spectrometer."},
                },
                "obj": SpectrometerUpdateBlank,
            },
            "SpectrometerAdjDefIntegrationTime": {
                "default_code": "SpectrometerAdjDefIntegrationTime(receiver= '', scans_to_avg=(3,), smoothings=(0,), xtimings=(1,), target_max_count=52000, tolerance=2000)",
                "args": {
                    "receiver": {"default": "StellarNetSpectrometer", "type": str, "notes": "Name of the device"},
                    "scans_to_avg": {"default": (3,), "type": tuple, "notes": "Scans-to-average values for each declared spectrometer."},
                    "smoothings": {"default": (0,), "type": tuple, "notes": "Smoothing values for each declared spectrometer."},
                    "xtimings": {"default": (1,), "type": tuple, "notes": "X timing values for each declared spectrometer."},
                    "target_max_count": {"default": 52000, "type": int, "notes": "Target detector max count used to tune the default integration time."},
                    "tolerance": {"default": 2000, "type": int, "notes": "Allowed deviation from the target max count."},
                },
                "obj": SpectrometerAdjDefIntegrationTime,
            },
            "SpectrometerGetAbsorbance": {
                "default_code": "SpectrometerGetAbsorbance(receiver= '', save_to_file=True, filename=None, integration_times=(100,), scans_to_avg=(3,), smoothings=(0,), xtimings=(1,))",
                "args": {
                    "receiver": {"default": "StellarNetSpectrometer", "type": str, "notes": "Name of the device"},
                    "save_to_file": {"default": True, "type": bool, "notes": "Save absorbance CSV output to the spectrometer save directory."},
                    "filename": {"default": None, "type": str, "notes": "Optional output filename prefix. Uses a timestamp when omitted."},
                    "integration_times": {"default": (100,), "type": tuple, "notes": "Integration times in ms for each declared spectrometer."},
                    "scans_to_avg": {"default": (3,), "type": tuple, "notes": "Scans-to-average values for each declared spectrometer."},
                    "smoothings": {"default": (0,), "type": tuple, "notes": "Smoothing values for each declared spectrometer."},
                    "xtimings": {"default": (1,), "type": tuple, "notes": "X timing values for each declared spectrometer."},
                },
                "obj": SpectrometerGetAbsorbance,
            },
            "SpectrometerGetAbsorbancebyname": {
                "default_code": "SpectrometerGetAbsorbancebyname(receiver= '', sample_name='sample', save_to_file=True, repeat_measure=False, integration_times=None, scans_to_avg=(3,), smoothings=(0,), xtimings=(1,), absorbance_threshold=0.003)",
                "args": {
                    "receiver": {"default": "StellarNetSpectrometer", "type": str, "notes": "Name of the device"},
                    "sample_name": {"default": "sample", "type": str, "notes": "Sample name used to build absorbance filenames."},
                    "save_to_file": {"default": True, "type": bool, "notes": "Save absorbance CSV output to the spectrometer save directory."},
                    "repeat_measure": {"default": False, "type": bool, "notes": "Retained for compatibility with the older workflow."},
                    "integration_times": {"default": None, "type": tuple, "notes": "Optional integration times in ms. Uses the device default integration time when omitted."},
                    "scans_to_avg": {"default": (3,), "type": tuple, "notes": "Scans-to-average values for each declared spectrometer."},
                    "smoothings": {"default": (0,), "type": tuple, "notes": "Smoothing values for each declared spectrometer."},
                    "xtimings": {"default": (1,), "type": tuple, "notes": "X timing values for each declared spectrometer."},
                    "absorbance_threshold": {"default": 0.003, "type": float, "notes": "Compatibility placeholder for the older repeat-measure workflow."},
                },
                "obj": SpectrometerGetAbsorbancebyname,
            },
            "SpectrometerGetPhotoncountsbyname": {
                "default_code": "SpectrometerGetPhotoncountsbyname(receiver= '', sample_name='sample', save_to_file=True, repeat_measure=False, integration_times=None, scans_to_avg=(3,), smoothings=(0,), xtimings=(1,), absorbance_threshold=0.003)",
                "args": {
                    "receiver": {"default": "StellarNetSpectrometer", "type": str, "notes": "Name of the device"},
                    "sample_name": {"default": "sample", "type": str, "notes": "Sample name used to build photon count filenames."},
                    "save_to_file": {"default": True, "type": bool, "notes": "Save photon count CSV output to the spectrometer save directory."},
                    "repeat_measure": {"default": False, "type": bool, "notes": "Retained for compatibility with the older workflow."},
                    "integration_times": {"default": None, "type": tuple, "notes": "Optional integration times in ms. Uses the device default integration time when omitted."},
                    "scans_to_avg": {"default": (3,), "type": tuple, "notes": "Scans-to-average values for each declared spectrometer."},
                    "smoothings": {"default": (0,), "type": tuple, "notes": "Smoothing values for each declared spectrometer."},
                    "xtimings": {"default": (1,), "type": tuple, "notes": "X timing values for each declared spectrometer."},
                    "absorbance_threshold": {"default": 0.003, "type": float, "notes": "Compatibility placeholder for the older repeat-measure workflow."},
                },
                "obj": SpectrometerGetPhotoncountsbyname,
            },
            "SpectrometerGetSpecDecay": {
                "default_code": "SpectrometerGetSpecDecay(receiver= '', sample_name='sample', save_to_file=True, range_start=290.0, range_end=800.0, irradiance_file='reference/am15g_spectrum.csv', Wvlgth_col_name='wavelength_nm', Irrad_col_name='irradiance_w_m2_nm', decay_threshold=0.01)",
                "args": {
                    "receiver": {"default": "StellarNetSpectrometer", "type": str, "notes": "Name of the device"},
                    "sample_name": {"default": "sample", "type": str, "notes": "Sample name used to find the saved merged absorbance file."},
                    "save_to_file": {"default": True, "type": bool, "notes": "Save the spectral decay CSV to the spectrometer save directory."},
                    "range_start": {"default": 290.0, "type": float, "notes": "Start wavelength for spectral decay calculation."},
                    "range_end": {"default": 800.0, "type": float, "notes": "End wavelength for spectral decay calculation."},
                    "irradiance_file": {"default": "reference/am15g_spectrum.csv", "type": str, "notes": "Reference irradiance CSV stored relative to the spectrometer save directory."},
                    "Wvlgth_col_name": {"default": "wavelength_nm", "type": str, "notes": "Irradiance-table wavelength column name."},
                    "Irrad_col_name": {"default": "irradiance_w_m2_nm", "type": str, "notes": "Irradiance-table irradiance column name."},
                    "decay_threshold": {"default": 0.01, "type": float, "notes": "Reference absorbance threshold used when computing decay indices."},
                },
                "obj": SpectrometerGetSpecDecay,
            },
            "SpectrometerPlotSpecDecaySummary": {
                "default_code": "SpectrometerPlotSpecDecaySummary(receiver= '', sample_name='sample', range_start=290.0, range_end=800.0, save_to_file=True, output_filename=None, figure_dpi=180)",
                "args": {
                    "receiver": {"default": "StellarNetSpectrometer", "type": str, "notes": "Name of the device"},
                    "sample_name": {"default": "sample", "type": str, "notes": "Sample name used to find the saved specdecay and QC files."},
                    "range_start": {"default": 290.0, "type": float, "notes": "Start wavelength used for the absorbance snapshot panel."},
                    "range_end": {"default": 800.0, "type": float, "notes": "End wavelength used for the absorbance snapshot panel."},
                    "save_to_file": {"default": True, "type": bool, "notes": "Save the summary figure as PNG in the spectrometer save directory."},
                    "output_filename": {"default": None, "type": str, "notes": "Optional output PNG filename. Relative paths are resolved against the spectrometer save directory."},
                    "figure_dpi": {"default": 180, "type": int, "notes": "PNG export resolution."},
                },
                "obj": SpectrometerPlotSpecDecaySummary,
            },
        },
    },
    "DummyMotor": {
        "obj": DummyMotor,
        "default_obj": DummyMotor(name="DummyMotor", speed=20.0),
        "serial": True,
        "serial_sequence": ["DummyMotorInitialize"],
        "import_device": "from devices.dummy_motor import DummyMotor",
        "import_commands": "from commands.dummy_motor_commands import *",
        "telemetry": {
            "parameters": {
                "position": {
                    "function_name": "get_position",
                    "data_type": "float",
                    "units": "mm",
                },
                "speed": {
                    "function_name": "get_speed",
                    "data_type": "float",
                    "units": "mm/s",
                },
            },
            "options": {"custom_init_args": []},
        },
        "init": {
            "default_code": "DummyMotor(name='DummyMotor', speed=20.0)",
            "obj_name": "DummyMotor",
            "args": {
                "name": {
                    "default": "DummyMotor",
                    "type": str,
                    "notes": "Name of the device.",
                },
                "speed": {
                    "default": 20.0,
                    "type": float,
                    "notes": "Speed of the motor.",
                },
            },
        },
        "commands": {
            "DummyMotorInitialize": {
                "default_code": "DummyMotorInitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "DummyMotor",
                        "type": str,
                        "notes": "Name of the device.",
                    }
                },
                "obj": DummyMotorInitialize,
            },
            "DummyMotorDeinitialize": {
                "default_code": "DummyMotorDeinitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "DummyMotor",
                        "type": str,
                        "notes": "Name of the device.",
                    }
                },
                "obj": DummyMotorDeinitialize,
            },
            "DummyMotorSetSpeed": {
                "default_code": "DummyMotorSetSpeed(receiver= '', speed= 0.0)",
                "args": {
                    "receiver": {
                        "default": "DummyMotor",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "speed": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Speed of the motor.",
                    },
                },
                "obj": DummyMotorSetSpeed,
            },
            "DummyMotorMoveAbsolute": {
                "default_code": "DummyMotorMoveAbsolute(receiver= '', position= 0)",
                "args": {
                    "receiver": {
                        "default": "DummyMotor",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "position": {
                        "default": 0,
                        "type": float,
                        "notes": "Position to move to.",
                    },
                },
                "obj": DummyMotorMoveAbsolute,
            },
            "DummyMotorMoveRelative": {
                "default_code": "DummyMotorMoveRelative(receiver= '', distance= 0)",
                "args": {
                    "receiver": {
                        "default": "DummyMotor",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "distance": {
                        "default": 0,
                        "type": float,
                        "notes": "Distance to move.",
                    },
                },
                "obj": DummyMotorMoveRelative,
            },
            "DummyMotorMoveSpeedAbsolute": {
                "default_code": "DummyMotorMoveSpeedAbsolute(receiver= '', position= 0.0, speed= 0.0)",
                "args": {
                    "receiver": {
                        "default": "DummyMotor",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "position": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Position to move to.",
                    },
                    "speed": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Speed of the motor.",
                    },
                },
                "obj": DummyMotorMoveSpeedAbsolute,
            },
        },
    },
    # "Spectrometer": {"obj": StellarNetSpectrometer},
    "DummyHeater": {
        "obj": DummyHeater,
        "serial": True,
        "serial_sequence": ["DummyHeaterInitialize"],
        "import_device": "from devices.dummy_heater import DummyHeater",
        "import_commands": "from commands.dummy_heater_commands import *",
        "init": {
            "default_code": "DummyHeater(name='DummyHeater', heat_rate=20.0)",
            "obj_name": "DummyHeater",
            "args": {
                "name": {
                    "default": "DummyHeater",
                    "type": str,
                    "notes": "Name of the device.",
                },
                "heat_rate": {
                    "default": 20.0,
                    "type": float,
                    "notes": "Heat rate of the heater.",
                },
            },
        },
        "commands": {
            "DummyHeaterInitialize": {
                "default_code": "DummyHeaterInitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "DummyHeater",
                        "type": str,
                        "notes": "Name of the device.",
                    }
                },
                "obj": DummyHeaterInitialize,
            },
            "DummyHeaterDeinitialize": {
                "default_code": "DummyHeaterDeinitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "DummyHeater",
                        "type": str,
                        "notes": "Name of the device.",
                    }
                },
                "obj": DummyHeaterDeinitialize,
            },
            "DummyHeaterSetHeatRate": {
                "default_code": "DummyHeaterSetHeatRate(receiver= '', heat_rate= 0.0)",
                "args": {
                    "receiver": {
                        "default": "DummyHeater",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "heat_rate": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Heat rate of the heater.",
                    },
                },
                "obj": DummyHeaterSetHeatRate,
            },
            "DummyHeaterSetTemp": {
                "default_code": "DummyHeaterSetTemp(receiver= '', temperature= 0.0)",
                "args": {
                    "receiver": {
                        "default": "DummyHeater",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "temperature": {
                        "default": 0.0,
                        "type": float,
                        "notes": "Temperature to set the heater to.",
                    },
                },
                "obj": DummyHeaterSetTemp,
            },
        },
    },
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
    },
    "XimeaCamera": {
        "obj": XimeaCamera,
        "serial": True,
        "serial_sequence": ["XimeaCameraInitialize"],
        "import_device": "from devices.ximea_camera import XimeaCamera",
        "import_commands": "from commands.ximea_camera_commands import *",
        "init": {
            "default_code": "XimeaCamera(name='XimeaCamera')",
            "obj_name": "XimeaCamera",
            "args": {
                "name": {
                    "default": "XimeaCamera",
                    "type": str,
                    "notes": "Name of the device.",
                },
            },
        },
        "commands": {
            "XimeaCameraInitialize": {
                "default_code": "XimeaCameraInitialize(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "XimeaCamera",
                        "type": str,
                        "notes": "Name of the device.",
                    }
                },
                "obj": XimeaCameraInitialize,
            },
            "XimeaCameraDeinitialize": {
                "default_code": "XimeaCameraDeinitialize(receiver= '', reset_init_flag=True)",
                "args": {
                    "receiver": {
                        "default": "XimeaCamera",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "reset_init_flag": {
                        "default": True,
                        "type": str,
                        "notes": "Reset init flag.",
                    }
                },
                "obj": XimeaCameraDeinitialize,
            },
            "XimeaCameraGetImage": {
                "default_code": "XimeaCameraGetImage(receiver= '', save_to_file=True, filename=None, exposure_time=None, gain=None, show_pop_up=False)",
                "args": {
                    "receiver": {
                        "default": "XimeaCamera",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "save_to_file": {
                        "default": True,
                        "type": bool,
                        "notes": "Whether the image should be saved to file or not.",
                    },
                    "filename": {
                        "default": None,
                        "type": str,
                        "notes": "Filename to save the image to.",
                    },
                    "exposure_time": {
                        "default": None,
                        "type": int,
                        "notes": "Exposure time of the camera.",
                    },
                    "gain": {
                        "default": None,
                        "type": float,
                        "notes": "Gain of the camera.",
                    },
                    "show_pop_up": {
                        "default": False,
                        "type": bool,
                        "notes": "Whether to show a pop up of the image.",
                    },
                },
                "obj": XimeaCameraGetImage,
            },
            "XimeaCameraSetDefaultExposure": {
                "default_code": "XimeaCameraSetDefaultExposure(receiver= '', exposure_time=None)",
                "args": {
                    "receiver": {
                        "default": "XimeaCamera",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "exposure_time": {
                        "default": None,
                        "type": int,
                        "notes": "Updated exposure time.",
                    },
                },
                "obj": XimeaCameraSetDefaultExposure,
            },
            "XimeaCameraSetDefaultGain": {
                "default_code": "XimeaCameraSetDefaultGain(receiver= '', gain=None)",
                "args": {
                    "receiver": {
                        "default": "XimeaCamera",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "gain": {
                        "default": None,
                        "type": float,
                        "notes": "Updated gain.",
                    },
                },
                "obj": XimeaCameraSetDefaultGain,
            },
            "XimeaCameraUpdateWhiteBal": {
                "default_code": "XimeaCameraUpdateWhiteBal(receiver= '', exposure_time=None, gain=None)",
                "args": {
                    "receiver": {
                        "default": "XimeaCamera",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "exposure_time": {
                        "default": None,
                        "type": int,
                        "notes": "Updated exposure time.",
                    },
                    "gain": {
                        "default": None,
                        "type": float,
                        "notes": "Updated gain.",
                    },
                },
                "obj": XimeaCameraUpdateWhiteBal,
            },
            "XimeaCameraSetManualWhiteBal": {
                "default_code": "XimeaCameraSetManualWhiteBal(receiver= '', wb_kr=None, wb_kg=None, wb_kb=None)",
                "args": {
                    "receiver": {
                        "default": "XimeaCamera",
                        "type": str,
                        "notes": "Name of the device.",
                    },
                    "wb_kr": {
                        "default": None,
                        "type": float,
                        "notes": "White balance red.",
                    },
                    "wb_kg": {
                        "default": None,
                        "type": float,
                        "notes": "White balance green.",
                    },
                    "wb_kb": {
                        "default": None,
                        "type": float,
                        "notes": "White balance blue.",
                    },
                },
                "obj": XimeaCameraSetManualWhiteBal,
            },
            "XimeaCameraResetWhiteBal": {
                "default_code": "XimeaCameraResetWhiteBal(receiver= '')",
                "args": {
                    "receiver": {
                        "default": "XimeaCamera",
                        "type": str,
                        "notes": "Name of the device.",
                    }
                },
                "obj": XimeaCameraResetWhiteBal,
            },
        },
    },
}


# devices_ref = {
#     "PrintingStage": heating_stage_ref,
#     "AnnealingStage": heating_stage_ref,
#     "MultiStepper": {
#         "obj": MultiStepper,
#         "import_device": "from devices.multi_stepper import MultiStepper",
#         "import_commands": "from commands.multi_stepper_commands import *",
#         "init": "MultiStepper(name='MultiStepper', port='', baudrate=115200, timeout=0.1, destination=0x50, source=0x01, channel=1)",
#         "commands": {
#             "MultiStepperConnect": "MultiStepperConnect(receiver= '')",
#             "MultiStepperInitialize": "MultiStepperInitialize(receiver= '')",
#             "MultiStepperDeinitialize": "MultiStepperDeinitialize(receiver= '')",
#             "MultiStepperMoveAbsolute": "MultiStepperMoveAbsolute(receiver= '', stepper_number= 0, position= 0)",
#             "MultiStepperMoveRelative": "MultiStepperMoveRelative(receiver= '', stepper_number= 0, distance= 0)",
#         },
#     },
#     "PrinterMotorX": {"obj": NewportESP301},
#     # "Spectrometer": {"obj": StellarNetSpectrometer},
#     "XimeaCamera": {"obj": XimeaCamera},
#     "DummyHeater": {"obj": DummyHeater},
#     "DummyMotor": {"obj": DummyMotor},
#     "LinearStage150": {
#         "obj": LinearStage150,
#         "import_device": "from devices.linear_stage_150 import LinearStage150",
#         "import_commands": "from commands.linear_stage_150_commands import *",
#         "init": "LinearStage150(name='LinearStage150', port='', baudrate=115200, timeout=0.1, destination=0x50, source=0x01, channel=1)",
#         "commands": {
#             "LinearStage150Connect": "LinearStage150Connect(receiver= '')",
#             "LinearStage150Initialize": "LinearStage150Initialize(receiver= '')",
#             "LinearStage150Deinitialize": "LinearStage150Deinitialize(receiver= '')",
#             "LinearStage150EnableMotor": "LinearStage150EnableMotor(receiver= '')",
#             "LinearStage150DisableMotor": "LinearStage150DisableMotor(receiver= '')",
#             "LinearStage150MoveAbsolute": "LinearStage150MoveAbsolute(receiver= '', position= 0)",
#             "LinearStage150MoveRelative": "LinearStage150MoveRelative(receiver= '', distance= 0)",
#         },
#     },
# }
