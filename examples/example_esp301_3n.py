# ESP301-3N smoke test
# run from root using 'python -m examples.example_esp301_3n'

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
from devices.newport_esp301 import NewportESP301
from commands.newport_esp301_commands import *


ESP301_PORT = "COM6"

AXIS_CONFIGS = {
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
    3: {
        "stage_model": "PR50PP",
        "motion_type": "rotary",
        "units": "deg",
        "home_mode": "OR1",
        "zero_position": 0.0,
        "default_speed": 10.0,
    },
}


def main() -> None:
    seq = CommandSequence()

    esp301 = NewportESP301(
        name="esp301_3n",
        port=ESP301_PORT,
        axis_list=(1, 2, 3),
        default_speed=10.0,
        poll_interval=0.1,
        axis_configs=AXIS_CONFIGS,
    )
    seq.add_device(esp301)

    seq.add_command(NewportESP301Connect(esp301))
    seq.add_command(NewportESP301Initialize(esp301))

    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=1, position=20.0, speed=5.0))
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=1, position=5.0, speed=5.0))
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=2, position=20.0, speed=5.0))
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=2, position=5.0, speed=5.0))
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=3, position=45.0, speed=10.0))
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=3, position=120.0, speed=10.0))
    seq.add_command(NewportESP301MoveSpeedAbsolute(esp301, axis_number=3, position=15.0, speed=10.0))

    # Re-run initialization at the end to confirm all three axes can home again.
    seq.add_command(NewportESP301Initialize(esp301))

    log_file = "logs/example_esp301_3n.log"
    invoker = CommandInvoker(seq, log_to_file=True, log_filename=log_file, alert_slack=False)

    seq.print_command_names()
    print("\nBefore running, place axes 1 and 2 away from the negative limit and make sure axis 3 has clearance for a full home search.")
    userinput = input("\ntype 'y' to continue, type anything else to quit: ").strip().lower()
    if userinput == "y":
        invoker.invoke_commands()


if __name__ == "__main__":
    main()
