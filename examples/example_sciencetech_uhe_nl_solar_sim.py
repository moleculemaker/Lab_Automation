# Sciencetech UHE-NL solar simulator smoke test
# run from root using 'python -m examples.example_sciencetech_uhe_nl_solar_sim'

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
from devices.sciencetech_uhe_nl_solar_sim import SciencetechUHENLSolarSim
from commands.sciencetech_uhe_nl_solar_sim_commands import *


def main() -> None:
    port = input("Enter the UHE-NL COM port (for example COM7): ").strip()
    if not port:
        print("No COM port provided. Exiting.")
        return

    confirm = input(
        "This test will ignite the lamp, move the shutter, and change the attenuator. Type 'y' to continue: "
    ).strip().lower()
    if confirm != "y":
        print("Smoke test cancelled.")
        return

    simulator = SciencetechUHENLSolarSim(
        name="uhe_nl",
        port=port,
        baudrate=9600,
        timeout=2.0,
        connect_delay_s=3.0,
        command_delay_s=8.0,
        status_timeout_s=8.0,
        default_current_percent=85.0,
        default_attenuator_percent=100,
        debug_io=False,
    )

    seq = CommandSequence()
    seq.add_device(simulator)
    seq.add_command(SciencetechUHENLSolarSimConnect(simulator))
    seq.add_command(SciencetechUHENLSolarSimInitialize(simulator))
    seq.add_command(SciencetechUHENLSolarSimGetStatus(simulator))
    seq.add_command(SciencetechUHENLSolarSimGetFeedback(simulator, feedback_type="cool"))
    seq.add_command(SciencetechUHENLSolarSimGetFeedback(simulator, feedback_type="lamp"))
    seq.add_command(SciencetechUHENLSolarSimGetFeedback(simulator, feedback_type="shutter"))
    seq.add_command(SciencetechUHENLSolarSimGetFeedback(simulator, feedback_type="attenuator"))
    seq.add_command(SciencetechUHENLSolarSimCloseShutter(simulator))
    seq.add_command(SciencetechUHENLSolarSimSetAttenuator(simulator, percent=75))
    seq.add_command(SciencetechUHENLSolarSimGetFeedback(simulator, feedback_type="attenuator"))
    seq.add_command(SciencetechUHENLSolarSimEnableArcLamp(simulator))
    seq.add_command(SciencetechUHENLSolarSimGetStatus(simulator))
    seq.add_command(SciencetechUHENLSolarSimGetFeedback(simulator, feedback_type="lamp"))
    seq.add_command(SciencetechUHENLSolarSimGetFeedback(simulator, feedback_type="output"))
    seq.add_command(SciencetechUHENLSolarSimGetFeedback(simulator, feedback_type="current"))
    seq.add_command(SciencetechUHENLSolarSimGetFeedback(simulator, feedback_type="voltage"))
    seq.add_command(SciencetechUHENLSolarSimGetFeedback(simulator, feedback_type="power"))
    seq.add_command(SciencetechUHENLSolarSimOpenShutter(simulator))
    seq.add_command(SciencetechUHENLSolarSimGetFeedback(simulator, feedback_type="shutter"))
    seq.add_command(SciencetechUHENLSolarSimCloseShutter(simulator))
    seq.add_command(SciencetechUHENLSolarSimOpenAttenuator(simulator))
    seq.add_command(SciencetechUHENLSolarSimGetFeedback(simulator, feedback_type="attenuator"))
    seq.add_command(SciencetechUHENLSolarSimDisableArcLamp(simulator))
    seq.add_command(SciencetechUHENLSolarSimGetFeedback(simulator, feedback_type="lamp"))
    seq.add_command(SciencetechUHENLSolarSimDeinitialize(simulator, close_serial=True))

    print("\nThis smoke test verifies the full UHE-NL control path.")
    print("Sequence: initialize with lamp OFF, close shutter, set attenuator to 75%, ignite lamp,")
    print("check output/current/voltage/power, open and close shutter, reopen attenuator to 100%,")
    print("turn lamp OFF, then deinitialize while leaving cooling on for cooldown.")

    invoker = CommandInvoker(seq, False)
    invoker.invoke_commands()


if __name__ == "__main__":
    main()
