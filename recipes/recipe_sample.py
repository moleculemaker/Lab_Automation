import time
import os
from command_invoker import CommandInvoker
from command_sequence import CommandSequence
from utilities.solution_map import SolutionMap
from commands.solution_map_commands import FindAndStoreSolutionPosition, GetSolutionWithStoredPosition

from devices.ximea_camera import XimeaCamera
from devices.newport_esp301 import NewportESP301
from devices.kinova_arm import KinovaArm
from devices.heating_stage import HeatingStage
from devices.polarizer_servo_motor import PolarizerServoMotor
from devices.psd6_syringe_pump import PSD6SyringePump

from commands.ximea_camera_commands import *
from commands.newport_esp301_commands import *
from commands.kinova_arm_commands import *
from commands.heating_stage_commands import *
from commands.psd6_syringe_pump_commands import *
from commands.polarizer_servo_motor_commands import *

def format_speed(speed):
    if speed >= 1:
        return f"{int(speed)}"
    else:
        # Convert to exponential notation
        # Example: 0.2 -> 2E-1, 0.02 -> 2E-2
        exponent = 0
        normalized = speed
        while normalized < 1:
            normalized *= 10
            exponent -= 1
        return f"{int(normalized)}E{exponent}"

# Sample Metadata
round_num = 0  # x
sample_num = $sample_no  # y
polymer = "$polymer"
solvent = "$solvent"
concentration = $concentration  # mg/ml
speed = $motor_speed  # a: mm/s
speed_str = format_speed(speed)
temperature = $temperature  # b: °C
gap = $printing_gap  # c: um
volume = $precursor_volume  # d: ul

# configure devices
polarizer = PolarizerServoMotor('polarizer', 'COM22')
printer = NewportESP301('printer', 'COM6')
arm = KinovaArm('kinova')
heating_stage = HeatingStage('heating_stage', 'COM16',115200)
xi = XimeaCamera('xi')
pump1 = PSD6SyringePump('pump1', 'COM4')
pump2 = PSD6SyringePump('pump2', 'COM5')
solution_map = SolutionMap()

# add devices
seq = CommandSequence()
seq.add_device(printer)
seq.add_device(arm)
seq.add_device(heating_stage)
seq.add_device(polarizer)
seq.add_device(xi)
seq.add_device(pump1)
seq.add_device(pump2)
seq.add_device(solution_map)

# initialize commands
seq.add_command(NewportESP301Connect(printer))
seq.add_command(NewportESP301Initialize(printer))
seq.add_command(KinovaArmConnect(arm))
seq.add_command(KinovaArmInitialize(arm))
seq.add_command(HeatingStageConnect(heating_stage))
seq.add_command(HeatingStageInitialize(heating_stage))
seq.add_command(PolarizerConnect(polarizer))
seq.add_command(PolarizerInitialize(polarizer))
seq.add_command(PSD6SyringePumpConnect(pump1))
seq.add_command(PSD6SyringePumpConnect(pump2))
seq.add_command(PSD6SyringePumpInitialize(pump1))
seq.add_command(PSD6SyringePumpInitialize(pump2))
seq.add_command(XimeaCameraInitialize(xi))

# get substrate to the printing stage
seq.add_command(KinovaArmExecuteAction(arm, action_name='Home'))
seq.add_command(KinovaArmOpenGripper(arm))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Sub_Handler_Up'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Sub_Handler_Down'))
seq.add_command(KinovaArmCloseGripper(arm))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Sub_Handler_Up'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Substrate_Hotel_Down'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Substrate_1_Down'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Substrate_1_Up'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Substrate_Hotel_Up'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Sub_Handler_Up'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Home'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Printer_Up_Out'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Printer_Up_In'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Printer_Down_In'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Printer_Down_Out'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Home'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Sub_Handler_Up'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Sub_Handler_Down'))
seq.add_command(KinovaArmOpenGripper(arm))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Sub_Handler_Up'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Home'))

# set printing temperature
seq.add_command(HeatingStageSetSetPoint(heating_stage, temperature))

# get solution

# Sahas - commenting this out for now because the user can manually enter solution position in the recipe builder UI
# find_solution_cmd = FindAndStoreSolutionPosition(solution_map, polymer, solvent, concentration)
# seq.add_command(find_solution_cmd)

seq.add_command(KinovaArmExecuteAction(arm, action_name='Liq_Handler_Up'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Liq_Handler_Down'))
seq.add_command(KinovaArmCloseGripper(arm))
seq.add_command(KinovaArmExecuteAction(arm, action_name='Liq_Handler_Up'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='$solution_position' + '_Up'))
seq.add_command(KinovaArmExecuteAction(arm, action_name='$solution_position' + '_Down'))

# Set Exposure Time
CROSSPOL_EXPOSURE = 50000
NORMAL_EXPOSURE = 12000  

# Set Save Path (data/imaging is excluded)
BASE_DIR = polymer  # P42gTTT
CROSSPOL_DIR = os.path.join(BASE_DIR, 'crosspol')   # P42gTTT/crosspol
NORMAL_DIR = os.path.join(BASE_DIR, 'normal')       # P42gTTT/normal

# Set Base Sample Name
base_sample_name = f"R{round_num}S{sample_num}_{polymer}_{solvent}_{concentration}mgml_{speed_str}mms_{temperature}C_{gap}um_{volume}ul"



# Take Cross-pol Images (polarizer 0 degree)
seq.add_command(RotatePolarizerAbsolute(polarizer, angle=0))

sample_angles = [90, 60, 45, 30, 0]
for angle in sample_angles:
    seq.add_command(RotateSampleAbsolute(polarizer, angle=angle))
    filename = os.path.join(CROSSPOL_DIR, f"{base_sample_name}_crosspol_{angle}deg")
    seq.add_command(
        XimeaCameraGetImage(xi, 
                          filename=filename,
                          y_upper=10,
                          y_length=1000, 
                          x_upper=500, 
                          x_length=1000,
                          exposure_time=CROSSPOL_EXPOSURE,
                          check_uniform=False)
    )

# Take Normal Images (polarizer 90 degree)
seq.add_command(RotatePolarizerAbsolute(polarizer, angle=90))

for angle in sample_angles:
    seq.add_command(RotateSampleAbsolute(polarizer, angle=angle))
    filename = os.path.join(NORMAL_DIR, f"{base_sample_name}_normal_{angle}deg")
    seq.add_command(
        XimeaCameraGetImage(xi, 
                          filename=filename,
                          y_upper=10,
                          y_length=1000, 
                          x_upper=500, 
                          x_length=1000,
                          exposure_time=NORMAL_EXPOSURE,
                          check_uniform=False)
    )

# Return to initial position
seq.add_command(RotatePolarizerAbsolute(polarizer, angle=0))
seq.add_command(RotateSampleAbsolute(polarizer, angle=0))

# Create necessary folders (include full path)
os.makedirs(os.path.join('data', 'imaging', CROSSPOL_DIR), exist_ok=True)
os.makedirs(os.path.join('data', 'imaging', NORMAL_DIR), exist_ok=True)

invoker = CommandInvoker(seq, False)
res = invoker.invoke_commands()
print(res)
