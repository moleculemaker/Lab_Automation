# P4PP rotation sweep measurement
# run from root using 'python -m examples.example_p4pp_rotation_sweep'

import csv
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
from commands.command import CommandResult
from commands.p4pp_commands import (
    P4PPConnect,
    P4PPDeinitialize,
    P4PPHomeAll,
    P4PPInitialize,
    P4PPMeasure,
    P4PPMoveLinearAbsolute,
    P4PPMoveRotationalAbsolute,
    P4PPParentCommand,
    P4PPRefreshPosition,
    P4PPSaveMeasurementCsv,
    P4PPSetMeasurementResistor,
)
from devices.p4pp import P4PP


P4PP_PORT = "COM19"
SAMPLE_NAME = "sample_name"
SAVE_DIRECTORY = "data/resistance"
MEASUREMENT_CYCLES = 25
MEASUREMENT_RESISTOR_OHMS = 681.0
RETRACT_LINEAR_MM = 40.0
MEASURE_LINEAR_MM = 47.0
ANGLE_START_DEG = 0
ANGLE_STOP_DEG = 180
ANGLE_STEP_DEG = 5


class P4PPSaveRotationSweepSummary(P4PPParentCommand):
    """Append the latest P4PP rotation sweep average/std result to a merged CSV."""

    def __init__(self, receiver: P4PP, angle_deg: float, sample_id: str, csv_path: str, notes: str = "", **kwargs):
        super().__init__(receiver, **kwargs)
        self._params["angle_deg"] = angle_deg
        self._params["sample_id"] = sample_id
        self._params["csv_path"] = csv_path
        self._params["notes"] = notes

    def execute(self) -> None:
        if self._receiver.latest_result is None:
            self._result = CommandResult(False, "No P4PP measurement result is available to summarize.")
            return

        csv_path = self._params["csv_path"]
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        file_exists = Path(csv_path).is_file()
        resistor_info = self._receiver.get_measurement_resistor_info()
        _, linear_position_mm = self._receiver.get_linear_position_mm()
        _, rotational_position_deg = self._receiver.get_rotational_position_deg()
        cycle_results = self._receiver.cycle_results

        row = {
            "sample_id": self._params["sample_id"],
            "angle_deg": self._params["angle_deg"],
            "linear_position_mm": linear_position_mm,
            "rotational_position_deg": rotational_position_deg,
            "cycles": len(cycle_results) if cycle_results else 1,
            "r_set_ohms": resistor_info["R_set"],
            "r_sheet_avg": self._receiver.latest_result,
            "r_sheet_std": self._receiver.latest_std if self._receiver.latest_std is not None else "",
            "notes": self._params["notes"],
        }

        with open(csv_path, "a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

        self._result = CommandResult(True, "Successfully saved P4PP rotation sweep summary to " + csv_path)


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
        measure_timeout=60.0,
        poll_interval=0.2,
        rotation_safety_linear_mm=45.0,
        measurement_resistor_ohms=MEASUREMENT_RESISTOR_OHMS,
        save_directory=SAVE_DIRECTORY,
    )
    seq.add_device(p4pp)

    sample_dir = Path(SAVE_DIRECTORY) / SAMPLE_NAME
    measurement_csv_path = sample_dir / f"{SAMPLE_NAME}_p4pp_rotation_sweep_measurements.csv"
    merged_csv_path = sample_dir / f"{SAMPLE_NAME}_p4pp_rotation_sweep_merged.csv"
    angles_deg = list(range(ANGLE_START_DEG, ANGLE_STOP_DEG, ANGLE_STEP_DEG))

    seq.add_command(P4PPConnect(p4pp))
    seq.add_command(P4PPInitialize(p4pp))
    seq.add_command(P4PPHomeAll(p4pp))
    seq.add_command(P4PPSetMeasurementResistor(p4pp, resistor_ohms=MEASUREMENT_RESISTOR_OHMS))

    for angle_deg in angles_deg:
        # Retract below the rotation safety limit before changing angle.
        sample_id = f"{SAMPLE_NAME}_{angle_deg}deg"
        seq.add_command(P4PPMoveLinearAbsolute(p4pp, position_mm=RETRACT_LINEAR_MM))
        seq.add_command(P4PPMoveRotationalAbsolute(p4pp, position_deg=float(angle_deg)))
        seq.add_command(P4PPMoveLinearAbsolute(p4pp, position_mm=MEASURE_LINEAR_MM))
        seq.add_command(P4PPMeasure(p4pp, cycles=MEASUREMENT_CYCLES))
        seq.add_command(
            P4PPSaveMeasurementCsv(
                p4pp,
                sample_id=sample_id,
                csv_path=str(measurement_csv_path),
                notes="P4PP 0:180:5 rotation sweep at 47 mm linear position",
            )
        )
        seq.add_command(
            P4PPSaveRotationSweepSummary(
                p4pp,
                angle_deg=float(angle_deg),
                sample_id=sample_id,
                csv_path=str(merged_csv_path),
                notes="P4PP 0:180:5 rotation sweep avg/std summary",
            )
        )

    seq.add_command(P4PPMoveLinearAbsolute(p4pp, position_mm=RETRACT_LINEAR_MM))
    seq.add_command(P4PPRefreshPosition(p4pp))
    seq.add_command(P4PPDeinitialize(p4pp))

    log_file = "logs/example_p4pp_rotation_sweep.log"
    invoker = CommandInvoker(seq, log_to_file=True, log_filename=log_file, alert_slack=False)

    print("This P4PP example homes the axes, selects the 681 ohm resistor,")
    print(f"then measures {len(angles_deg)} angles from 0 to 175 deg in 5 deg steps.")
    print(f"Each angle is measured with {MEASUREMENT_CYCLES} cycles at {MEASURE_LINEAR_MM} mm.")
    print(f"Detailed results will be appended to {measurement_csv_path}.")
    print(f"Merged avg/std results will be appended to {merged_csv_path}.")
    seq.print_command_names()
    userinput = input("\ntype 'y' to continue, type anything else to quit: ").strip().lower()
    if userinput == "y":
        invoker.invoke_commands()


if __name__ == "__main__":
    main()
