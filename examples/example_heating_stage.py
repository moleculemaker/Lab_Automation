# HeatingStage smoke test
# run from root using 'python -m examples.example_heating_stage'

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
AAMP_APP_DIR = ROOT_DIR / "aamp_app"
for path in (ROOT_DIR, AAMP_APP_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from command_sequence import CommandSequence
from command_invoker import CommandInvoker
from devices.heating_stage import HeatingStage
from commands.heating_stage_commands import *


HEATER_PORT = "COM16"
TARGET_TEMPERATURE_C = 40.0
ROOM_TEMPERATURE_C = 25.0


def main() -> None:
    seq = CommandSequence()

    heater = HeatingStage("heater", HEATER_PORT, 115200, timeout=0.1, heating_timeout=1200.0)
    seq.add_device(heater)

    seq.add_command(HeatingStageConnect(heater))
    seq.add_command(HeatingStageInitialize(heater))
    seq.add_command(HeatingStageSetSetPoint(heater, TARGET_TEMPERATURE_C))
    # Wait until the target temperature is held within ±1 C for 30 seconds.
    seq.add_command(HeatingStageWaitForTemperature(heater, target=TARGET_TEMPERATURE_C, tolerance=1.0, timeout=1200.0, poll_interval=1.0, hold_duration=30.0))
    seq.add_command(HeatingStageSetSetPoint(heater, ROOM_TEMPERATURE_C))
    seq.add_command(HeatingStageDeinitialize(heater))

    log_file = "logs/example_heating_stage.log"
    invoker = CommandInvoker(seq, log_to_file=True, log_filename=log_file, alert_slack=False)

    seq.print_command_names()
    print("\nThis smoke test changes the setpoint to the target temperature, then returns the setpoint to room temperature.")
    userinput = input("\ntype 'y' to continue, type anything else to quit: ").strip().lower()
    if userinput == "y":
        invoker.invoke_commands()


if __name__ == "__main__":
    main()
