# Printing recipe example scaffold.
# run from root using 'python -m examples.example_printing_recipe'

import sys
from pathlib import Path
from typing import Dict

ROOT_DIR = Path(__file__).resolve().parents[1]
AAMP_APP_DIR = ROOT_DIR / "aamp_app"
for path in (ROOT_DIR, AAMP_APP_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from command_invoker import CommandInvoker
from command_sequence import CommandSequence
from commands.newport_esp301_commands import *
from commands.kinova_arm_commands import *
from commands.psd6_syringe_pump_commands import *
from commands.sonicator_commands import *
from devices.kinova_arm import KinovaArm
from devices.newport_esp301 import NewportESP301
from devices.psd6_syringe_pump import PSD6SyringePump
from devices.sonicator import Sonicator
from recipes.user_recipes.example_mongodb_recipe_lookup import (
    DEFAULT_CAMPAIGN_NAME,
    build_recipe_params,
    fetch_campaign,
    fetch_parameter_set,
    get_mongo_helper,
    list_batch_numbers,
    list_sample_numbers,
    load_env,
    prompt_choice,
    prompt_with_default,
)


ESP301_PORT = "COM6"
PSD6_1ML_PORT = "COM14"
PSD6_25ML_PORT = "COM17"
SONICATOR_PORT = "COM13"
PSD6_1ML_STROKE_VOLUME_UL = 1_000.0
PSD6_25ML_STROKE_VOLUME_UL = 25_000.0
PSD6_1ML_DEFAULT_FLOWRATE_UL_S = 50.0
PSD6_25ML_DEFAULT_FLOWRATE_UL_S = 500.0

PSD6_PORT_LIQUID_HANDLER = 1
PSD6_PORT_IPA = 2
PSD6_PORT_AIR_EMPTY = 5
PSD6_PORT_WASTE = 6
PSD6_PORT_SAFE_IDLE = PSD6_PORT_AIR_EMPTY
PSD6_AIR_PURGE_FLOWRATE_UL_S = 5.0
PSD6_LOAD_FLOWRATE_UL_S = 10.0
PSD6_PURGE_FLOWRATE_UL_S = 10.0
PSD6_AIR_PURGE_VOLUME_UL = 100.0
PSD6_LOAD_VOLUME_UL = 1_000.0
PSD6_FIRST_PURGE_VOLUME_UL = 700.0
PSD6_RELOAD_VOLUME_UL = 300.0
PSD6_SECOND_PURGE_VOLUME_UL = 500.0
PSD6_CLEANING_FLOWRATE_UL_S = 1_000.0
PSD6_CLEANING_VOLUME_UL = 15_000.0
PSD6_CLEANING_RESERVOIR_DRAIN_REPEATS = 2
PSD6_PORT_SONICATOR_RESERVOIR = 1
PSD6_PORT_ACETONE = 3
PSD6_PORT_TOLUENE = 4
PSD6_CLEANING_SOLVENT_PORTS = (
    (PSD6_PORT_IPA, "IPA"),
    (PSD6_PORT_ACETONE, "acetone"),
    (PSD6_PORT_TOLUENE, "toluene"),
)
SONICATION_TIME_S = 30.0

ESP301_AXIS_CONFIGS = {
    1: {
        "stage_model": "ILS100CC",
        "motion_type": "linear",
        "units": "mm",
        "home_mode": "OR4",
        "zero_position": 0.0,
        "default_speed": 10.0,
    },
    2: {
        "stage_model": "UTS100PP",
        "motion_type": "linear",
        "units": "mm",
        "home_mode": "OR4",
        "zero_position": 0.0,
        "default_speed": 10.0,
    },
}


PRINTING_AXIS2_POSITION_AT_0_UM = 36.9
PRINTING_AXIS2_MM_PER_UM_GAP = 0.001


def printing_gap_to_axis2_position(printing_gap_um: float) -> float:
    return PRINTING_AXIS2_POSITION_AT_0_UM - PRINTING_AXIS2_MM_PER_UM_GAP * printing_gap_um


def load_recipe_params() -> Dict[str, object]:
    load_env()
    mongo = get_mongo_helper()

    campaign_name = prompt_with_default("Campaign name", DEFAULT_CAMPAIGN_NAME)
    if not campaign_name:
        raise ValueError("Campaign name is required.")

    campaign_doc = fetch_campaign(mongo, campaign_name)
    batch_no = prompt_choice("batch_no values", list_batch_numbers(mongo, campaign_doc))
    sample_no = prompt_choice("sample_no values", list_sample_numbers(mongo, campaign_doc, batch_no))

    campaign_doc, set_doc = fetch_parameter_set(mongo, campaign_doc, batch_no, sample_no)
    params = build_recipe_params(batch_no, sample_no, set_doc)
    params["campaign_name"] = campaign_doc["campaign_name"]
    return params


def build_sequence(params: Dict[str, object]) -> CommandSequence:
    seq = CommandSequence()
    printing_speed = float(params["motor_speed"])
    printing_gap_um = float(params["printing_gap"])
    precursor_volume_ul = float(params["precursor_volume"])
    printing_ready_axis2_position = printing_gap_to_axis2_position(printing_gap_um)

    esp301 = NewportESP301(
        name="esp301",
        port=ESP301_PORT,
        axis_list=(1, 2),
        default_speed=10.0,
        poll_interval=0.1,
        axis_configs=ESP301_AXIS_CONFIGS,
    )
    arm = KinovaArm("arm")
    sonicator = Sonicator(
        name="sonicator",
        port=SONICATOR_PORT,
        baudrate=9600,
        timeout=0.5,
        connect_delay_s=3.0,
        response_timeout_s=3.0,
        power_probe_timeout_s=5.0,
        line_terminator="\n",
        command_prefix=">",
        debug_io=False,
    )
    liquid_handler_pump = PSD6SyringePump(
        name="psd6_1ml_liquid_handler",
        port=PSD6_1ML_PORT,
        baudrate=9600,
        timeout=10.0,
        stroke_volume=PSD6_1ML_STROKE_VOLUME_UL,
        stroke_steps=6000,
        default_flowrate=PSD6_1ML_DEFAULT_FLOWRATE_UL_S,
        port_dead_volumes=[0.0] * 6,
        poll_interval=0.1,
    )
    solvent_pump = PSD6SyringePump(
        name="psd6_25ml_solvent",
        port=PSD6_25ML_PORT,
        baudrate=9600,
        timeout=10.0,
        stroke_volume=PSD6_25ML_STROKE_VOLUME_UL,
        stroke_steps=6000,
        default_flowrate=PSD6_25ML_DEFAULT_FLOWRATE_UL_S,
        port_dead_volumes=[0.0] * 6,
        poll_interval=0.1,
    )

    seq.add_device(esp301)
    seq.add_device(arm)
    seq.add_device(sonicator)
    seq.add_device(liquid_handler_pump)
    seq.add_device(solvent_pump)

    seq.add_command(NewportESP301Connect(esp301))
    seq.add_command(KinovaArmConnect(arm))
    seq.add_command(SonicatorConnect(sonicator))
    seq.add_command(PSD6SyringePumpConnect(liquid_handler_pump))
    seq.add_command(PSD6SyringePumpConnect(solvent_pump))
    seq.add_command(NewportESP301Initialize(esp301))    # initialize printer head (0,0)
    seq.add_command(KinovaArmInitialize(arm))
    seq.add_command(SonicatorInitialize(sonicator))
    seq.add_command(PSD6SyringePumpInitialize(liquid_handler_pump))
    seq.add_command(PSD6SyringePumpInitialize(solvent_pump))
    seq.add_command(PSD6SyringePumpMoveAbsolute(liquid_handler_pump, volume=0.0, valve_num=PSD6_PORT_AIR_EMPTY, flowrate=PSD6_AIR_PURGE_FLOWRATE_UL_S))
    seq.add_command(PSD6SyringePumpWithdraw(liquid_handler_pump, volume=PSD6_AIR_PURGE_VOLUME_UL, valve_num=PSD6_PORT_AIR_EMPTY, flowrate=PSD6_AIR_PURGE_FLOWRATE_UL_S))
    seq.add_command(PSD6SyringePumpInfuse(liquid_handler_pump, volume=PSD6_AIR_PURGE_VOLUME_UL, valve_num=PSD6_PORT_LIQUID_HANDLER, flowrate=PSD6_AIR_PURGE_FLOWRATE_UL_S))
    for drain_idx in range(PSD6_CLEANING_RESERVOIR_DRAIN_REPEATS):
        seq.add_command(PSD6SyringePumpMoveAbsolute(solvent_pump, volume=0.0, valve_num=PSD6_PORT_SONICATOR_RESERVOIR, flowrate=PSD6_CLEANING_FLOWRATE_UL_S))
        seq.add_command(PSD6SyringePumpWithdraw(solvent_pump, volume=PSD6_CLEANING_VOLUME_UL, valve_num=PSD6_PORT_SONICATOR_RESERVOIR, flowrate=PSD6_CLEANING_FLOWRATE_UL_S))
        seq.add_command(PSD6SyringePumpInfuse(solvent_pump, volume=PSD6_CLEANING_VOLUME_UL, valve_num=PSD6_PORT_WASTE, flowrate=PSD6_CLEANING_FLOWRATE_UL_S))
    seq.add_command(PSD6SyringePumpMoveValve(liquid_handler_pump, valve_num=PSD6_PORT_SAFE_IDLE))
    seq.add_command(PSD6SyringePumpMoveValve(solvent_pump, valve_num=PSD6_PORT_SAFE_IDLE))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Home"))

    ## move printer head to sonicator up position(79, 10) to not mess with the arm ##
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=2, position=10.0, speed=10.0)) 
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=1, position=79.0, speed=10.0)) # sonicator up position (79,10)
    

    ## move arm to liquid dispenser ##
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Print_Ready_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Liq_Handler_Up_Out_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Liq_Handler_Down_Out_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Liq_Handler_Down_Angles"))
    seq.add_command(KinovaArmCloseGripper(arm))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Liq_Handler_Up_Angles", delay=1))

    ## move liquid dispenser to designated solution position(solution map needs to be implemented) ##
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Solution_Hotel_Ready_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Solution_1_High_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Solution_1_Up_Angles", delay=5))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Solution_1_Down_Angles"))

    ## withdraw solution using PSD6 pump ##
    ## liquid_handler_pump valve map: 1=liquid handler, 2=IPA, 5=air/empty, 6=waste ##
    seq.add_command(PSD6SyringePumpMoveAbsolute(liquid_handler_pump, volume=0.0, valve_num=PSD6_PORT_LIQUID_HANDLER, flowrate=PSD6_LOAD_FLOWRATE_UL_S))
    seq.add_command(PSD6SyringePumpWithdraw(liquid_handler_pump, volume=PSD6_LOAD_VOLUME_UL, valve_num=PSD6_PORT_LIQUID_HANDLER, flowrate=PSD6_LOAD_FLOWRATE_UL_S))
    seq.add_command(PSD6SyringePumpInfuse(liquid_handler_pump, volume=PSD6_FIRST_PURGE_VOLUME_UL, valve_num=PSD6_PORT_LIQUID_HANDLER, flowrate=PSD6_PURGE_FLOWRATE_UL_S))
    seq.add_command(PSD6SyringePumpWithdraw(liquid_handler_pump, volume=PSD6_RELOAD_VOLUME_UL, valve_num=PSD6_PORT_LIQUID_HANDLER, flowrate=PSD6_LOAD_FLOWRATE_UL_S))
    seq.add_command(PSD6SyringePumpInfuse(liquid_handler_pump, volume=PSD6_SECOND_PURGE_VOLUME_UL, valve_num=PSD6_PORT_LIQUID_HANDLER, flowrate=PSD6_PURGE_FLOWRATE_UL_S))

    ## move liquid dispenser to printing position ##
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Solution_1_Up_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Solution_Hotel_Ready_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Print_Ready_Angles"))
    
    ## move arm to Print_Dis_Left_Down position ##
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Print_Dis_Center_High_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Print_Dis_Left_Up_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Print_Dis_Left_Down_Angles", delay=5))
    
    ## move printer head to printing position(4,35) ##
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=2, position=40.0, speed=10.0)) # lowering printer head (79,40)
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=1, position=4.0, speed=10.0)) # printing up position (4,40)
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=2, position=35.0, speed=10.0)) # printing down position (4,35)
    
    ## add precursor solution using PSD6 pump ##
    seq.add_command(PSD6SyringePumpInfuse(liquid_handler_pump, volume=precursor_volume_ul, valve_num=PSD6_PORT_LIQUID_HANDLER, flowrate=PSD6_PURGE_FLOWRATE_UL_S))
    
    ## move to meniscus position ##
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=2, position=printing_ready_axis2_position, speed=10.0, delay='P')) # printing ready position adjusted by printing_gap (4,printing height)
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=1, position=2.0, speed=10.0)) # making meniscus stable (2,PH)
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=1, position=5.0, speed=10.0)) # making meniscus stable (5,PH)
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=1, position=3.0, speed=10.0)) # making meniscus stable (3,PH)
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=1, position=20, speed=printing_speed, delay=3)) # printing speed from MongoDB motor_speed (20, PH)
        
    ## move arm back to Liq_Handler ##
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Print_Ready_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Solution_Hotel_Ready_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Liq_Handler_Up_Angles", delay=1))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Liq_Handler_Down_Angles"))
    seq.add_command(KinovaArmOpenGripper(arm))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Liq_Handler_Down_Out_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Liq_Handler_Up_Out_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Print_Ready_Angles"))
    seq.add_command(KinovaArmExecuteAction(arm, action_name="Home"))

    ## end printing and move printer head to sonicator ##
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=2, position=10, speed=10.0)) # head up (20,10)
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=1, position=79, speed=10.0)) # sonicator up position (79,10)
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=2, position=70, speed=10.0)) # sonicator down position (79,70)

    ## add cleaning solvnet, sonicate ##
    for solvent_port, solvent_name in PSD6_CLEANING_SOLVENT_PORTS:
        seq.add_command(PSD6SyringePumpMoveAbsolute(solvent_pump, volume=0.0, valve_num=solvent_port, flowrate=PSD6_CLEANING_FLOWRATE_UL_S))
        seq.add_command(PSD6SyringePumpWithdraw(solvent_pump, volume=PSD6_CLEANING_VOLUME_UL, valve_num=solvent_port, flowrate=PSD6_CLEANING_FLOWRATE_UL_S))
        seq.add_command(PSD6SyringePumpInfuse(solvent_pump, volume=PSD6_CLEANING_VOLUME_UL, valve_num=PSD6_PORT_SONICATOR_RESERVOIR, flowrate=PSD6_CLEANING_FLOWRATE_UL_S))
    seq.add_command(SonicatorStartSonicating(sonicator))
    seq.add_command(SonicatorStopSonicating(sonicator, delay=SONICATION_TIME_S))

    ## mechanical cleaning ##
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=2, position=35, speed=10.0)) # head up (79,35)
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=1, position=45, speed=10.0)) # mechanical cleaning up position (45,35)
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=2, position=43, speed=10.0)) # mechanical cleaning down position (45,43)
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=1, position=79, speed=10.0)) # mechanical cleaning through linear movement (79,43)
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=2, position=70, speed=10.0)) # sonicator down position (79,70)
    seq.add_command(SonicatorStopSonicating(sonicator, delay=SONICATION_TIME_S)) # second sonication

    ## move to drying position (3,35) ##
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=2, position=10, speed=10.0)) # head up
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=1, position=3, speed=10.0)) # printing up position
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=2, position=35, speed=10.0)) # printing down position

    return seq


def main() -> None:
    params = load_recipe_params()
    printing_ready_axis2_position = printing_gap_to_axis2_position(float(params["printing_gap"]))

    print("\nLoaded MongoDB parameter set:")
    for key, value in params.items():
        print(f"  {key}: {value}")
    print(f"  printing_ready_axis2_position: {printing_ready_axis2_position:.4f} mm")

    seq = build_sequence(params)

    log_file = "logs/example_printing_recipe.log"
    invoker = CommandInvoker(seq, log_to_file=True, log_filename=log_file, alert_slack=False)

    print("\nPrinting recipe preview.")
    print("Sequence will use MongoDB motor_speed for axis 1 printing move and printing_gap for axis 2 ready position.")
    seq.print_command_names()
    userinput = input("\ntype 'y' to continue, type anything else to quit: ").strip().lower()
    if userinput == "y":
        result = invoker.invoke_commands()
        print(result)


if __name__ == "__main__":
    main()
