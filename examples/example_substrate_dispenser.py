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

from devices.substrate_dispenser import SubstrateDispenser
from commands.substrate_dispenser_commands import *


def main():
    port = input("Enter substrate dispenser COM port [example: COM7]: ").strip() or "COM7"

    dispenser = SubstrateDispenser("dispenser", port)

    seq = CommandSequence()
    seq.add_device(dispenser)
    seq.add_command(SubstrateDispenserConnect(dispenser))
    seq.add_command(SubstrateDispenserInitialize(dispenser))
    seq.add_command(SubstrateDispenserMoveToPosition(dispenser, position_mm=25.0, speed_mm_per_s=10.0, delay=2.0))
    seq.add_command(SubstrateDispenserHome(dispenser, delay=2.0))
    seq.add_command(SubstrateDispenserDeinitialize(dispenser, close_serial=True))

    invoker = CommandInvoker(seq, log_to_file=False)
    print(invoker.invoke_commands())


if __name__ == "__main__":
    main()
