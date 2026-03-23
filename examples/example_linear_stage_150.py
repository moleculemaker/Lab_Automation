# LinearStage150 smoke test
# run from root using 'python -m examples.example_linear_stage_150'

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
from devices.linear_stage_150 import LinearStage150
from commands.linear_stage_150_commands import *


STAGE_PORT = "COM15"


def main() -> None:
    seq = CommandSequence()

    stage = LinearStage150(
        name="linear_stage_150",
        port=STAGE_PORT,
        baudrate=115200,
        timeout=0.1,
        destination=0x50,
        source=0x01,
        channel=1,
    )
    seq.add_device(stage)

    seq.add_command(LinearStage150Connect(stage))
    seq.add_command(LinearStage150Initialize(stage))
    seq.add_command(LinearStage150MoveAbsolute(stage, position=100.0))
    seq.add_command(LinearStage150MoveRelative(stage, distance=5.0))
    seq.add_command(LinearStage150MoveAbsolute(stage, position=0.0))
    seq.add_command(LinearStage150Deinitialize(stage))

    log_file = "logs/example_linear_stage_150.log"
    invoker = CommandInvoker(seq, log_to_file=True, log_filename=log_file, alert_slack=False)

    seq.print_command_names()
    userinput = input("\ntype 'y' to continue, type anything else to quit: ").strip().lower()
    if userinput == "y":
        invoker.invoke_commands()


if __name__ == "__main__":
    main()
