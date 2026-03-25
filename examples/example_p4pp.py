# P4PP smoke test
# run from root using 'python -m examples.example_p4pp'

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
from devices.p4pp import P4PP
from commands.p4pp_commands import *


P4PP_PORT = "COM19"


def main() -> None:
    seq = CommandSequence()

    p4pp = P4PP(
        name="p4pp",
        port=P4PP_PORT,
        baudrate=115200,
        timeout=0.2,
        startup_delay=2.0,
        command_timeout=10.0,
        motion_timeout=60.0,
        home_timeout=60.0,
        measure_timeout=30.0,
        poll_interval=0.2,
        rotation_safety_linear_mm=45.0,
        measurement_resistor_ohms=681.0,
        save_directory="data/resistance/",
    )
    seq.add_device(p4pp)

    seq.add_command(P4PPConnect(p4pp))
    seq.add_command(P4PPInitialize(p4pp))
    seq.add_command(P4PPSetMeasurementResistor(p4pp, resistor_ohms=681.0))
    seq.add_command(P4PPHomeAll(p4pp))
    seq.add_command(P4PPMoveLinearAbsolute(p4pp, position_mm=5.0))
    seq.add_command(P4PPMoveRotationalAbsolute(p4pp, position_deg=30.0))
    seq.add_command(P4PPRefreshPosition(p4pp))
    seq.add_command(P4PPMoveRotationalAbsolute(p4pp, position_deg=0.0))
    seq.add_command(P4PPMoveLinearAbsolute(p4pp, position_mm=0.0))
    # Uncomment when the probe/sample path is ready for measurement.
    # seq.add_command(P4PPMeasure(p4pp, cycles=20))
    # seq.add_command(P4PPSaveMeasurementCsv(p4pp, sample_id="demo_sample"))
    seq.add_command(P4PPDeinitialize(p4pp))

    log_file = "logs/example_p4pp.log"
    invoker = CommandInvoker(seq, log_to_file=True, log_filename=log_file, alert_slack=False)

    print("This smoke test uses the Python-side P4PP integration.")
    print("Measurement resistor selection is explicit. Default is 681 ohm.")
    print("Firmware and hardware details should be referenced from https://github.com/polyprintillinois/P4PP .")
    seq.print_command_names()
    userinput = input("\ntype 'y' to continue, type anything else to quit: ").strip().lower()
    if userinput == "y":
        invoker.invoke_commands()


if __name__ == "__main__":
    main()
