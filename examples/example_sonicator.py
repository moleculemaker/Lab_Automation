# Sonicator smoke test
# run from root using 'python -m examples.example_sonicator'

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
from devices.sonicator import Sonicator
from commands.sonicator_commands import *


def main() -> None:
    port = input("Enter the Sonicator Arduino COM port (for example COM13): ").strip()
    if not port:
        print("No COM port provided. Exiting.")
        return

    confirm = input(
        "This test will stop sonication if it is already running, then start and stop it once. Type 'y' to continue: "
    ).strip().lower()
    if confirm != "y":
        print("Smoke test cancelled.")
        return

    sonicator = Sonicator(
        name="sonicator",
        port=port,
        baudrate=9600,
        timeout=0.5,
        connect_delay_s=3.0,
        response_timeout_s=3.0,
        power_probe_timeout_s=5.0,
        line_terminator="\n",
        command_prefix=">",
        debug_io=False,
    )

    seq = CommandSequence()
    seq.add_device(sonicator)
    seq.add_command(SonicatorConnect(sonicator))
    seq.add_command(SonicatorInitialize(sonicator))
    seq.add_command(SonicatorGetStatus(sonicator))
    seq.add_command(SonicatorStartSonicating(sonicator))
    seq.add_command(SonicatorGetStatus(sonicator, delay=2.0))
    seq.add_command(SonicatorStopSonicating(sonicator, delay=5.0))
    seq.add_command(SonicatorGetStatus(sonicator))
    seq.add_command(SonicatorDeinitialize(sonicator, close_serial=True))

    print("\nThis smoke test assumes an Arduino Uno R3 wrapper wired to 5V, GND, D7, and D8.")
    print("The explicit power-probe command is not part of this example because it is intrusive.")
    print("Sequence: connect, initialize to idle, read status, start sonication, wait briefly, stop, read status, deinitialize.")

    invoker = CommandInvoker(
        seq,
        log_to_file=True,
        log_filename="logs/example_sonicator.log",
        alert_slack=False,
    )
    invoker.invoke_commands()


if __name__ == "__main__":
    main()
