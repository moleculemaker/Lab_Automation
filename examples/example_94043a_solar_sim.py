# Newport 94043A solar simulator smoke test via 69920 power supply
# run from root using 'python -m examples.example_94043a_solar_sim'

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
from devices.newport_94043a_solar_sim import Newport94043ASolarSim
from commands.newport_94043a_solar_sim_commands import *


POWER_SUPPLY_PORT = "COM11"
POWER_PRESET_WATTS = 400


def main() -> None:
    seq = CommandSequence()

    power_supply = Newport94043ASolarSim(
        name="newport_94043a_solar_sim",
        port=POWER_SUPPLY_PORT,
        baudrate=9600,
        timeout=1.0,
        default_power_watts=400,
        max_power_watts=450,
    )
    seq.add_device(power_supply)

    seq.add_command(Newport94043ASolarSimConnect(power_supply))
    seq.add_command(Newport94043ASolarSimIdentify(power_supply))
    seq.add_command(Newport94043ASolarSimInitialize(power_supply))
    seq.add_command(Newport94043ASolarSimStatusByte(power_supply))
    seq.add_command(Newport94043ASolarSimEventStatus(power_supply))
    seq.add_command(Newport94043ASolarSimGetLampHours(power_supply))
    seq.add_command(Newport94043ASolarSimGetWatts(power_supply))
    seq.add_command(Newport94043ASolarSimGetCurrentLimit(power_supply))
    seq.add_command(Newport94043ASolarSimGetPowerLimit(power_supply))
    seq.add_command(Newport94043ASolarSimSetPowerPreset(power_supply, watts=POWER_PRESET_WATTS))
    seq.add_command(Newport94043ASolarSimGetPowerPreset(power_supply))
    seq.add_command(Newport94043ASolarSimLampStart(power_supply))
    seq.add_command(Newport94043ASolarSimGetWatts(power_supply))
    seq.add_command(Newport94043ASolarSimSetPowerPreset(power_supply, watts=420))
    seq.add_command(Newport94043ASolarSimGetPowerPreset(power_supply))
    seq.add_command(Newport94043ASolarSimGetWatts(power_supply))
    seq.add_command(Newport94043ASolarSimSetPowerPreset(power_supply, watts=380))
    seq.add_command(Newport94043ASolarSimGetPowerPreset(power_supply))
    seq.add_command(Newport94043ASolarSimGetWatts(power_supply))
    seq.add_command(Newport94043ASolarSimLampStop(power_supply))

    seq.add_command(Newport94043ASolarSimDeinitialize(power_supply))

    log_file = "logs/example_94043a_solar_sim.log"
    invoker = CommandInvoker(seq, log_to_file=True, log_filename=log_file, alert_slack=False)

    seq.print_command_names()
    print("\nThis smoke test communicates with the 94043A solar simulator through the 69920 power supply in power mode.")
    print("Sequence: initialize at 400 W, lamp start, set 420 W, set 380 W, lamp stop.")
    print("Software blocks presets above 450 W.")
    userinput = input("\ntype 'y' to continue, type anything else to quit: ").strip().lower()
    if userinput == "y":
        invoker.invoke_commands()


if __name__ == "__main__":
    main()
