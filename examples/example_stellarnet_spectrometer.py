# StellarNet UV-Vis calibration and absorbance example
# run from root using 'python -m examples.example_stellarnet_spectrometer'

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
AAMP_APP_DIR = ROOT_DIR / "aamp_app"
for path in (ROOT_DIR, AAMP_APP_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from devices.stellarnet_spectrometer import StellarNetSpectrometer


SAVE_DIRECTORY = "data/spectroscopy/"
SPEC_KEYS = ["UV-Vis"]
DEFAULT_INTEGRATION_TIMES = (100,)
SCANS_TO_AVG = (100,)
SMOOTHINGS = (3,)
XTIMINGS = (3,)
TARGET_MAX_COUNT = 52000
TARGET_TOLERANCE = 2000


def prompt_continue(message: str) -> bool:
    response = input(f"{message} Press ENTER to continue or type anything else to cancel: ").strip()
    return response == ""


def main() -> None:
    print("=== StellarNet UV-Vis Calibration Example ===")
    print("This example initializes the UV-Vis spectrometer, adjusts the default integration time at the blank position,")
    print("records dark and blank references, and then captures absorbance and photon counts by sample name.")

    spec = StellarNetSpectrometer(
        name="spec",
        spec_keys=SPEC_KEYS,
        save_directory=SAVE_DIRECTORY,
        default_integration_time=DEFAULT_INTEGRATION_TIMES,
    )

    ok, message = spec.initialize()
    print(f"initialize -> {ok}, {message}")
    if not ok:
        return

    print(f"Connected spectrometers: {list(spec.spectrometer_dict.keys())}")
    print(f"Save directory: {spec.save_directory}")
    print(f"Initial default integration time: {spec.default_integration_time}")

    if not prompt_continue("Set the optical path to BLANK/reference for integration-time adjustment."):
        spec.deinitialize()
        print("Cancelled before integration-time adjustment.")
        return

    ok, message = spec.adjust_default_integration_time(
        scans_to_avg=SCANS_TO_AVG,
        smoothings=SMOOTHINGS,
        xtimings=XTIMINGS,
        target_max_count=TARGET_MAX_COUNT,
        tolerance=TARGET_TOLERANCE,
    )
    print(f"adjust_default_integration_time -> {ok}, {message}")
    print(f"Updated default integration time: {spec.default_integration_time}")
    if not ok:
        spec.deinitialize()
        return

    if not prompt_continue("Set the optical path to DARK."):
        spec.deinitialize()
        print("Cancelled before dark capture.")
        return

    ok, message = spec.update_all_dark_spectra(
        integration_times=spec.default_integration_time,
        scans_to_avg=SCANS_TO_AVG,
        smoothings=SMOOTHINGS,
        xtimings=XTIMINGS,
    )
    print(f"update_dark -> {ok}, {message}")
    if not ok:
        spec.deinitialize()
        return

    if not prompt_continue("Set the optical path to BLANK/reference."):
        spec.deinitialize()
        print("Cancelled before blank capture.")
        return

    ok, message = spec.update_all_blank_spectra(
        integration_times=spec.default_integration_time,
        scans_to_avg=SCANS_TO_AVG,
        smoothings=SMOOTHINGS,
        xtimings=XTIMINGS,
    )
    print(f"update_blank -> {ok}, {message}")
    if not ok:
        spec.deinitialize()
        return

    if not prompt_continue("Load the SAMPLE for absorbance acquisition."):
        spec.deinitialize()
        print("Cancelled before sample acquisition.")
        return

    sample_name = input("Enter sample name for the saved absorbance file prefix: ").strip()
    if not sample_name:
        sample_name = "uvvis_sample"

    repeat_measure = input(
        "Append this measurement to an existing sample time series if matching files are found? [Y/N]: "
    ).strip().lower() == "y"

    ok, message = spec.get_all_absorbance_byname(
        sample_name=sample_name,
        save_to_file=True,
        repeat_measure=repeat_measure,
        integration_times=spec.default_integration_time,
        scans_to_avg=SCANS_TO_AVG,
        smoothings=SMOOTHINGS,
        xtimings=XTIMINGS,
    )
    print(f"get_absorbance_byname -> {ok}, {message}")

    if ok:
        save_counts = input("Save photon counts for the same sample name as well? [Y/N]: ").strip().lower()
        if save_counts != "n":
            ok_counts, message_counts = spec.get_all_counts_byname(
                sample_name=sample_name,
                save_to_file=True,
                repeat_measure=repeat_measure,
                integration_times=spec.default_integration_time,
                scans_to_avg=SCANS_TO_AVG,
                smoothings=SMOOTHINGS,
                xtimings=XTIMINGS,
            )
            print(f"get_photoncounts_byname -> {ok_counts}, {message_counts}")

        calc_decay = input(
            "Compute spectral decay now if repeated absorbance data and reference/am15g_spectrum.csv are available? [Y/N]: "
        ).strip().lower() == "y"
        if calc_decay:
            ok_decay, message_decay = spec.get_spec_decay(sample_name=sample_name, save_to_file=True)
            print(f"get_spec_decay -> {ok_decay}, {message_decay}")

    ok, message = spec.deinitialize()
    print(f"deinitialize -> {ok}, {message}")


if __name__ == "__main__":
    main()
