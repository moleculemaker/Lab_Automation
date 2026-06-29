# Film characterization example combining Kinova handling, APIS rotation, and P4PP probing.
# run from root using 'python -m examples.example_film_characterization'

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
AAMP_APP_DIR = ROOT_DIR / "aamp_app"
for path in (ROOT_DIR, AAMP_APP_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from command_invoker import CommandInvoker
from command_sequence import CommandSequence
from devices.apis import APIS
from devices.kinova_arm import KinovaArm
from devices.p4pp import P4PP
from commands.apis_commands import *
from commands.kinova_arm_commands import *
from commands.p4pp_commands import *


APIS_PORT = "COM8"
P4PP_PORT = "COM19"
SAMPLE_ANGLES_DEG = [0, 45, 90]
P4PP_TOUCHDOWN_MM = 47.0
P4PP_ROTATION_CLEARANCE_MM = 40.0
P4PP_ROTATION_STEP_DEG = 45.0
P4PP_CONTACT_DELAY_S = 5.0
P4PP_MEASUREMENT_RESISTOR_OHMS = 681.0


def add_legacy_apis_rotation_commands(
    seq: CommandSequence,
    apis: APIS,
    sample_angles_deg,
    sample_delay_s: float = 0.5,
) -> None:
    # Keep the same logical flow as the old polarizer example:
    # polarizer at 0 deg, rotate the sample through each angle,
    # then polarizer at 90 deg and repeat.
    seq.add_command(APISRotatePolarizer(apis, angle_deg=0.0))
    for angle in sample_angles_deg:
        seq.add_command(APISRotateSample(apis, angle_deg=float(angle), delay=sample_delay_s))

    seq.add_command(APISRotatePolarizer(apis, angle_deg=90.0))
    for angle in sample_angles_deg:
        seq.add_command(APISRotateSample(apis, angle_deg=float(angle), delay=sample_delay_s))

    seq.add_command(APISRotatePolarizer(apis, angle_deg=0.0))
    seq.add_command(APISRotateSample(apis, angle_deg=0.0))


def add_p4pp_characterization_commands(seq: CommandSequence, p4pp: P4PP) -> None:
    # Measure at 0 deg, 45 deg, then 90 deg using 45 deg relative steps.
    seq.add_command(P4PPMoveLinearAbsolute(p4pp, position_mm=P4PP_TOUCHDOWN_MM))
    seq.add_command(P4PPMoveLinearAbsolute(p4pp, position_mm=P4PP_ROTATION_CLEARANCE_MM, delay=P4PP_CONTACT_DELAY_S))

    seq.add_command(P4PPMoveRotationalRelative(p4pp, distance_deg=P4PP_ROTATION_STEP_DEG))
    seq.add_command(P4PPMoveLinearAbsolute(p4pp, position_mm=P4PP_TOUCHDOWN_MM))
    seq.add_command(P4PPMoveLinearAbsolute(p4pp, position_mm=P4PP_ROTATION_CLEARANCE_MM, delay=P4PP_CONTACT_DELAY_S))

    seq.add_command(P4PPMoveRotationalRelative(p4pp, distance_deg=P4PP_ROTATION_STEP_DEG))
    seq.add_command(P4PPMoveLinearAbsolute(p4pp, position_mm=P4PP_TOUCHDOWN_MM))
    seq.add_command(P4PPMoveLinearAbsolute(p4pp, position_mm=P4PP_ROTATION_CLEARANCE_MM, delay=P4PP_CONTACT_DELAY_S))
    seq.add_command(P4PPHomeAll(p4pp))



def main() -> None:
    seq = CommandSequence()

    arm = KinovaArm("arm")
    apis = APIS(
        name="apis",
        port=APIS_PORT,
        baudrate=9600,
        timeout=0.5,
        connection_wait_s=2.0,
        settling_time_s=1.5,
        command_delay_s=0.05,
        max_retries=3,
        use_camera=False,
    )
    p4pp = P4PP(
        name="p4pp",
        port=P4PP_PORT,
        baudrate=115200,
        timeout=0.2,
        startup_delay=2.0,
        command_timeout=10.0,
        motion_timeout=60.0,
        home_timeout=60.0,
        measure_timeout=30.0,
        poll_interval=0.2,
        rotation_safety_linear_mm=45.0,
        measurement_resistor_ohms=P4PP_MEASUREMENT_RESISTOR_OHMS,
        save_directory="data/resistance/",
    )

    seq.add_device(arm)
    seq.add_device(apis)
    seq.add_device(p4pp)

    seq.add_command(KinovaArmConnect(arm))
    seq.add_command(APISConnect(apis))
    seq.add_command(P4PPConnect(p4pp))

    seq.add_command(APISInitialize(apis))
    seq.add_command(APISHome(apis))
    seq.add_command(P4PPInitialize(p4pp))
    seq.add_command(P4PPSetMeasurementResistor(p4pp, resistor_ohms=P4PP_MEASUREMENT_RESISTOR_OHMS))
    seq.add_command(P4PPHomeAll(p4pp))
    seq.add_command(KinovaArmInitialize(arm))

    seq.add_command(KinovaArmExecuteAction(arm, action_name="Home"))
    seq.add_command(KinovaArmOpenGripper(arm))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Sub_Handler_High_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Sub_Handler_Up_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Sub_Handler_Down_Angles"))
    seq.add_command(KinovaArmCloseGripper(arm))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Sub_Handler_Up_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Sub_Handler_High_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Print_Ready_Angles"))

    seq.add_command(KinovaArmExecuteAction(arm, action_name="Print_Down_Out_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Print_Down_In_Angles", delay=5))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Print_Up_In_Angles", delay=5))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Print_High_In_Angles", delay="P"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Print_Ready_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Sub_Handler_High_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="UV_Intermediate_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Image_Intermediate_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Image_High_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Image_Up_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Image_Down_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Image_Down_Out_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Image_Intermediate_Angles"))

    # Image sequence
    add_legacy_apis_rotation_commands(
        seq=seq,
        apis=apis,
        sample_angles_deg=SAMPLE_ANGLES_DEG,
    )

    seq.add_command(KinovaArmExecuteAction(arm, action_name="Image_Down_Out_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Image_Down_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Image_Up_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Image_High_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Image_Intermediate_Angles"))

    seq.add_command(KinovaArmExecuteAction(arm, action_name="Resistance_Intermediate_Angles", delay=5))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Resistance_High_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Resistance_Up_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Resistance_Down_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Resistance_Down_Out_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Resistance_Intermediate_Angles"))


    # Resistance sequence
    # add_p4pp_characterization_commands(seq=seq, p4pp=p4pp)

    # seq.add_command(KinovaArmExecuteAction(arm, action_name="Resistance_Down_Out_Angles", delay=5))
    # seq.add_command(KinovaArmExecuteAction(arm, action_name="Resistance_Down_Angles"))
    # seq.add_command(KinovaArmExecuteAction(arm, action_name="Resistance_Up_Angles"))
    # seq.add_command(KinovaArmExecuteAction(arm, action_name="Resistance_High_Angles"))
    # seq.add_command(KinovaArmExecuteAction(arm, action_name="Resistance_Intermediate_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Image_Intermediate_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="UV_Intermediate_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Sub_Handler_High_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Sub_Handler_Up_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Sub_Handler_Down_Angles"))
    seq.add_command(KinovaArmOpenGripper(arm))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Sub_Handler_Up_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Sub_Handler_High_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Home"))

    
    # Resistance sequence
    add_p4pp_characterization_commands(seq=seq, p4pp=p4pp)


    seq.add_command(APISDeinitialize(apis))
    seq.add_command(P4PPDeinitialize(p4pp))

    log_file = "logs/example_film_characterization.log"
    invoker = CommandInvoker(seq, log_to_file=True, log_filename=log_file, alert_slack=False)

    print("This example combines Kinova handling, APIS rotation, and P4PP characterization.")
    print("APIS camera support is disabled here; the APIS portion rotates the film before the P4PP probing sequence.")
    print("The P4PP portion probes at 0 deg, 45 deg, and 90 deg using 47 mm contact and 40 mm rotation clearance.")
    seq.print_command_names()
    userinput = input("\ntype 'y' to continue, type anything else to quit: ").strip().lower()
    if userinput == "y":
        result = invoker.invoke_commands()
        print(result)


if __name__ == "__main__":
    main()
