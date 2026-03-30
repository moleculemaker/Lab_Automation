# UV-Vis film absorbance degradation example
# run from root using 'python -m examples.example_uvvis_film_absorbance_degradation'

import sys
import time
from pathlib import Path
from typing import Dict, Iterable, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
AAMP_APP_DIR = ROOT_DIR / "aamp_app"
for path in (ROOT_DIR, AAMP_APP_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from devices.newport_esp301 import NewportESP301
from devices.stellarnet_spectrometer import StellarNetSpectrometer


ESP301_PORT = "COM6"
ESP301_AXIS_NUMBER = 3
ESP301_SPEED = 20.0

ESP301_AXIS_CONFIGS = {
    3: {
        "stage_model": "PR50PP",
        "motion_type": "rotary",
        "units": "deg",
        "home_mode": "OR1",
        "zero_position": 0.0,
        "default_speed": ESP301_SPEED,
    },
}

SAVE_DIRECTORY = "data/spectroscopy/"
SPEC_KEYS = ["UV-Vis"]
DEFAULT_INTEGRATION_TIMES = (100,)
SCANS_TO_AVG = (100,)
SMOOTHINGS = (3,)
XTIMINGS = (3,)
TARGET_MAX_COUNT = 52000
TARGET_TOLERANCE = 2000

ACTIVE_SLOTS = (1, 2, 3, 4, 5, 6, 7, 8)
SAMPLE_NAMES: Dict[int, str] = {
    1: "sample_1",
    2: "sample_2",
    3: "sample_3",
    4: "sample_4",
    5: "sample_5",
    6: "sample_6",
    7: "sample_7",
    8: "sample_8",
}

NUM_CYCLES = 1
DWELL_BETWEEN_CYCLES_S = 0.0
SAVE_PHOTON_COUNTS = True


def sample_angle_deg(slot: int) -> float:
    return float((slot - 1) * 45.0)


def dark_angle_deg() -> float:
    return 15.0


def blank_angle_deg(slot: int) -> float:
    return float(sample_angle_deg(slot) + 22.5)


def validate_slots(active_slots: Iterable[int], sample_names: Dict[int, str]) -> Tuple[bool, str]:
    active_slots = tuple(active_slots)
    if not active_slots:
        return False, "ACTIVE_SLOTS is empty."
    for slot in active_slots:
        if slot < 1 or slot > 8:
            return False, f"Slot {slot} is invalid. Valid slots are 1 through 8."
        if slot not in sample_names or not str(sample_names[slot]).strip():
            return False, f"Slot {slot} is active but has no sample name."
    return True, "Slot configuration is valid."


def move_axis3(esp301: NewportESP301, angle_deg: float) -> bool:
    ok, message = esp301.move_speed_absolute(
        axis_number=ESP301_AXIS_NUMBER,
        position=angle_deg,
        speed=ESP301_SPEED,
    )
    print(f"move axis3 -> {ok}, {message}")
    return ok


def prompt_continue(message: str) -> bool:
    response = input(f"{message} Press ENTER to continue or type anything else to cancel: ").strip()
    return response == ""


def main() -> None:
    ok, message = validate_slots(ACTIVE_SLOTS, SAMPLE_NAMES)
    if not ok:
        print(message)
        return

    print("=== UV-Vis Film Absorbance Degradation Example ===")
    print("This example uses ESP301 axis 3 for rotary positioning and StellarNet UV-Vis for repeated absorbance acquisition.")
    print("Workflow:")
    print("1. Move to 22.5 deg for initial blank-based integration-time adjustment.")
    print("2. Move to 15.0 deg for a one-time dark measurement.")
    print("3. For each loop, measure blank before every sample and append absorbance by sample name.")
    print("4. Photon counts can be saved alongside absorbance.")
    print("")
    print(f"Active slots: {ACTIVE_SLOTS}")
    for slot in ACTIVE_SLOTS:
        print(
            f"  slot {slot}: sample={SAMPLE_NAMES[slot]}, "
            f"sample_angle={sample_angle_deg(slot):.1f} deg, "
            f"blank_angle={blank_angle_deg(slot):.1f} deg"
        )
    print(f"Dark angle: {dark_angle_deg():.1f} deg")
    print(f"Configured loop count: {NUM_CYCLES}")
    print(f"Dwell between cycles: {DWELL_BETWEEN_CYCLES_S} s")
    print(f"Photon counts enabled: {SAVE_PHOTON_COUNTS}")

    if not prompt_continue("Confirm the chamber is clear and the spectrometer optical path is ready."):
        print("Cancelled before initialization.")
        return

    esp301 = NewportESP301(
        name="uvvis_stage",
        port=ESP301_PORT,
        axis_list=(ESP301_AXIS_NUMBER,),
        default_speed=ESP301_SPEED,
        poll_interval=0.1,
        axis_configs=ESP301_AXIS_CONFIGS,
    )
    spec = StellarNetSpectrometer(
        name="spec",
        spec_keys=SPEC_KEYS,
        save_directory=SAVE_DIRECTORY,
        default_integration_time=DEFAULT_INTEGRATION_TIMES,
    )

    esp_initialized = False
    spec_initialized = False

    try:
        ok, message = esp301.connect()
        print(f"esp301 connect -> {ok}, {message}")
        if not ok:
            return

        ok, message = esp301.initialize()
        print(f"esp301 initialize -> {ok}, {message}")
        if not ok:
            return
        esp_initialized = True

        ok, message = spec.initialize()
        print(f"spectrometer initialize -> {ok}, {message}")
        if not ok:
            return
        spec_initialized = True

        if not move_axis3(esp301, 22.5):
            return
        ok, message = spec.adjust_default_integration_time(
            scans_to_avg=SCANS_TO_AVG,
            smoothings=SMOOTHINGS,
            xtimings=XTIMINGS,
            target_max_count=TARGET_MAX_COUNT,
            tolerance=TARGET_TOLERANCE,
        )
        print(f"adjust_default_integration_time -> {ok}, {message}")
        print(f"default_integration_time -> {spec.default_integration_time}")
        if not ok:
            return

        if not move_axis3(esp301, dark_angle_deg()):
            return
        ok, message = spec.update_all_dark_spectra(
            integration_times=spec.default_integration_time,
            scans_to_avg=SCANS_TO_AVG,
            smoothings=SMOOTHINGS,
            xtimings=XTIMINGS,
        )
        print(f"update_dark -> {ok}, {message}")
        if not ok:
            return

        if NUM_CYCLES < 1:
            print("NUM_CYCLES must be at least 1.")
            return

        for cycle_index in range(NUM_CYCLES):
            print("")
            print(f"=== Begin cycle {cycle_index + 1} / {NUM_CYCLES} ===")
            for slot in ACTIVE_SLOTS:
                sample_name = SAMPLE_NAMES[slot]
                current_blank_angle = blank_angle_deg(slot)
                current_sample_angle = sample_angle_deg(slot)

                if not move_axis3(esp301, current_blank_angle):
                    return
                ok, message = spec.update_all_blank_spectra(
                    integration_times=spec.default_integration_time,
                    scans_to_avg=SCANS_TO_AVG,
                    smoothings=SMOOTHINGS,
                    xtimings=XTIMINGS,
                )
                print(f"update_blank slot {slot} -> {ok}, {message}")
                if not ok:
                    return

                if not move_axis3(esp301, current_sample_angle):
                    return
                ok, message = spec.get_all_absorbance_byname(
                    sample_name=sample_name,
                    save_to_file=True,
                    repeat_measure=True,
                    integration_times=spec.default_integration_time,
                    scans_to_avg=SCANS_TO_AVG,
                    smoothings=SMOOTHINGS,
                    xtimings=XTIMINGS,
                )
                print(f"get_absorbance_byname slot {slot} -> {ok}, {message}")
                if not ok:
                    return

                if SAVE_PHOTON_COUNTS:
                    ok, message = spec.get_all_counts_byname(
                        sample_name=sample_name,
                        save_to_file=True,
                        repeat_measure=True,
                        integration_times=spec.default_integration_time,
                        scans_to_avg=SCANS_TO_AVG,
                        smoothings=SMOOTHINGS,
                        xtimings=XTIMINGS,
                    )
                    print(f"get_photoncounts_byname slot {slot} -> {ok}, {message}")
                    if not ok:
                        return

            print(f"=== End cycle {cycle_index + 1} / {NUM_CYCLES} ===")
            if cycle_index < NUM_CYCLES - 1 and DWELL_BETWEEN_CYCLES_S > 0:
                print(f"Sleeping for {DWELL_BETWEEN_CYCLES_S} s before next cycle.")
                time.sleep(DWELL_BETWEEN_CYCLES_S)

    finally:
        if spec_initialized:
            ok, message = spec.deinitialize()
            print(f"spectrometer deinitialize -> {ok}, {message}")
        if esp_initialized:
            ok, message = esp301.deinitialize()
            print(f"esp301 deinitialize -> {ok}, {message}")


if __name__ == "__main__":
    main()
