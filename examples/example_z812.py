# Z812 smoke test
# run from root using 'python -m examples.example_z812'

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
from devices.z812 import Z812
from commands.z812_commands import *


STAGE_PORT = "COM12"


def main() -> None:
    seq = CommandSequence()

    stage = Z812(
        name="z812",
        port=STAGE_PORT,
        baudrate=115200,
        timeout=0.1,
        destination=0x50,
        source=0x01,
        channel=1,
    )
    seq.add_device(stage)

    seq.add_command(Z812Connect(stage))
    seq.add_command(Z812Initialize(stage))
    seq.add_command(Z812MoveAbsolute(stage, position=8.0))
    seq.add_command(Z812MoveRelative(stage, distance=3.0))
    seq.add_command(Z812MoveAbsolute(stage, position=0.0))
    seq.add_command(Z812Deinitialize(stage))

    log_file = "logs/example_z812.log"
    invoker = CommandInvoker(seq, log_to_file=True, log_filename=log_file, alert_slack=False)

    seq.print_command_names()
    userinput = input("\ntype 'y' to continue, type anything else to quit: ").strip().lower()
    if userinput == "y":
        invoker.invoke_commands()


if __name__ == "__main__":
    main()
