# Festo solenoid valve smoke test
# run from repo root with:
#   python -m examples.example_festo_solenoid_valve

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
from devices.festo_solenoid_valve import FestoSolenoidValve
from commands.festo_solenoid_valve_commands import (
    FestoCloseAll,
    FestoConnect,
    FestoDeinitialize,
    FestoInitialize,
    FestoValveClosed,
    FestoValveOpen,
)

DEFAULT_PORT = "COM9"
PIN8_VALVE_NUM = 2
PIN4_VALVE_NUM = 3


def main() -> None:
    port = input(
        f"Enter the Arduino COM port for the Festo valve controller [{DEFAULT_PORT}]: "
    ).strip()
    if not port:
        port = DEFAULT_PORT

    confirm = input(
        f"This test will use {port}, then close both valves, open valve_num={PIN8_VALVE_NUM} (pin 8), close it, open valve_num={PIN4_VALVE_NUM} (pin 4), close it, then deinitialize. Type 'y' to continue: "
    ).strip().lower()
    if confirm != "y":
        print("Smoke test cancelled.")
        return

    valve = FestoSolenoidValve(
        name="festo_valve",
        port=port,
        baudrate=9600,
        timeout=0.5,
    )

    seq = CommandSequence()
    seq.add_device(valve)
    seq.add_command(FestoConnect(valve))
    seq.add_command(FestoInitialize(valve))
    seq.add_command(FestoCloseAll(valve))
    seq.add_command(FestoValveOpen(valve, valve_num=PIN8_VALVE_NUM, delay=5.0))
    seq.add_command(FestoValveClosed(valve, valve_num=PIN8_VALVE_NUM, delay=60))
    # seq.add_command(FestoValveOpen(valve, valve_num=PIN4_VALVE_NUM, delay=45.0))
    # seq.add_command(FestoValveClosed(valve, valve_num=PIN4_VALVE_NUM, delay=15))
    seq.add_command(FestoCloseAll(valve))
    seq.add_command(FestoDeinitialize(valve))

    print("\nAssumptions:")
    print("- Arduino sketch: to_implement/festo_solenoid_valve_multiple/Festo_Multiple.ino")
    print("- With the current sketch, valve_num=2 uses Arduino pin D8 and valve_num=3 uses D4.") 
    print("- valve_num=1 is still mapped to D12 unless you remap the sketch.")
    print("- The Arduino pin must drive a MOSFET/relay/driver board, not the valve coil directly.")
    print("- The valve coil power must come from an external supply with flyback protection.")

    invoker = CommandInvoker(
        seq,
        log_to_file=True,
        log_filename="logs/example_festo_solenoid_valve.log",
        alert_slack=False,
    )
    invoker.invoke_commands()


if __name__ == "__main__":
    main()
