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

from devices.substrate_hotel import SubstrateHotel
from commands.substrate_hotel_commands import *


def main():
    port = input("Enter substrate hotel COM port [example: COM10]: ").strip() or "COM10"

    hotel = SubstrateHotel(
        "hotel",
        port,
        home_timeout_s=300.0,
        move_timeout_s=300.0,
    )

    seq = CommandSequence()
    seq.add_device(hotel)
    seq.add_command(SubstrateHotelConnect(hotel))
    seq.add_command(SubstrateHotelInitialize(hotel))
    seq.add_command(SubstrateHotelMoveToPosition(hotel, position_mm=405.0, speed_mm_per_s=10.0, delay=2.0))
    # seq.add_command(SubstrateHotelHome(hotel, delay=2.0))
    seq.add_command(SubstrateHotelDeinitialize(hotel, close_serial=True))

    invoker = CommandInvoker(seq, log_to_file=False)
    print(invoker.invoke_commands())


if __name__ == "__main__":
    main()
