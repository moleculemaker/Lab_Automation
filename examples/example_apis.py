# APIS imaging workflow example
# run from root using 'python -m examples.example_apis'

import os
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
from devices.apis import APIS
from commands.apis_commands import *


APIS_PORT = "COM8"
ROOT_SAVE_DIR = os.path.join("data", "imaging", "demo_campaign")
XPL_EXPOSURE_US = 50000
PPL_EXPOSURE_US = 18000
SAMPLE_ANGLES_DEG = [90, 60, 45, 30, 0]


def add_mode_capture_commands(seq, apis, mode_name, polarizer_angle, sample_angles, exposure_time, base_name, save_dir):
    seq.add_command(APISRotatePolarizer(apis, angle_deg=polarizer_angle))
    for angle in sample_angles:
        seq.add_command(APISRotateSample(apis, angle_deg=angle))
        filename = apis.build_mode_filename(base_name, mode_name, angle)
        raw16_path = os.path.join(save_dir, "raw16", filename + ".tif")
        rgb_path = os.path.join(save_dir, "rgb", filename + "_rgb.tif")
        seq.add_command(
            APISCaptureRaw16(
                apis,
                filename=filename,
                directory=save_dir,
                exposure_time=exposure_time,
                gain=0.0,
            )
        )
        seq.add_command(
            APISConvertRaw16ToRgb(
                apis,
                raw16_path=raw16_path,
                rgb_path=rgb_path,
            )
        )


def main() -> None:
    print("=== APIS Imaging Workflow ===")
    print("Enter parameter values using the MongoDB `sets` field names.")

    batch_input = input("Enter batch_no (for example: 1): ").strip()
    sample_input = input("Enter sample_no (for example: 1): ").strip()

    try:
        batch_no = int(batch_input)
    except ValueError:
        batch_no = batch_input

    try:
        sample_no = int(sample_input)
    except ValueError:
        sample_no = sample_input

    polymer_name = input("Enter polymer_name (for example: PProDOT): ").strip()
    solvent = input("Enter solvent (for example: CB): ").strip()
    concentration = int(input("Enter concentration (mg/ml): ").strip())
    motor_speed = float(input("Enter motor_speed (mm/s): ").strip())
    temperature = int(input("Enter temperature (C): ").strip())
    printing_gap = int(input("Enter printing_gap (um): ").strip())
    precursor_volume = int(input("Enter precursor_volume (ul): ").strip())

    params = {
        "campaign_name": "demo_campaign",
        "batch_no": batch_no,
        "sample_no": sample_no,
        "polymer_name": polymer_name,
        "temperature": temperature,
        "motor_speed": motor_speed,
        "printing_gap": printing_gap,
        "solvent": solvent,
        "concentration": concentration,
        "precursor_volume": precursor_volume,
    }

    print("\n=== Sample Parameters ===")
    for key, value in params.items():
        print(f"{key}: {value}")

    base_sample_name = APIS.build_sample_basename(
        round_num=params["batch_no"],
        sample_num=params["sample_no"],
        polymer=params["polymer_name"],
        solvent=params["solvent"],
        concentration=params["concentration"],
        speed=params["motor_speed"],
        temperature=params["temperature"],
        gap=params["printing_gap"],
        volume=params["precursor_volume"],
    )
    print(f"\nGenerated filename prefix: {base_sample_name}")
    print("Mode folders will use `xpl/` and `ppl/`.")
    print("Each capture will save RAW16 first, then convert that file to RGB.")

    confirm = input("\nProceed with imaging using these parameters? (y/n): ").strip().lower()
    if confirm != "y":
        print("Imaging cancelled.")
        return

    print("\nInitializing hardware...")
    apis = APIS(
        name="apis",
        port=APIS_PORT,
        baudrate=9600,
        timeout=0.5,
        connection_wait_s=2.0,
        settling_time_s=1.5,
        command_delay_s=0.05,
        max_retries=3,
        use_camera=True,
        camera_save_directory=ROOT_SAVE_DIR,
        camera_bayer_pattern="GBRG",
        camera_raw_max_value=1023.0,
    )
    xpl_dir = apis.resolve_mode_directory(ROOT_SAVE_DIR, params["polymer_name"], "xpl")
    ppl_dir = apis.resolve_mode_directory(ROOT_SAVE_DIR, params["polymer_name"], "ppl")

    seq = CommandSequence()
    seq.add_device(apis)

    seq.add_command(APISConnect(apis))
    seq.add_command(APISInitialize(apis))
    seq.add_command(APISHome(apis))

    print(f"\nStarting XPL capture ({len(SAMPLE_ANGLES_DEG)} angles)")
    add_mode_capture_commands(
        seq=seq,
        apis=apis,
        mode_name="xpl",
        polarizer_angle=90.0,
        sample_angles=SAMPLE_ANGLES_DEG,
        exposure_time=XPL_EXPOSURE_US,
        base_name=base_sample_name,
        save_dir=xpl_dir,
    )

    print(f"Starting PPL capture ({len(SAMPLE_ANGLES_DEG)} angles)")
    add_mode_capture_commands(
        seq=seq,
        apis=apis,
        mode_name="ppl",
        polarizer_angle=0.0,
        sample_angles=SAMPLE_ANGLES_DEG,
        exposure_time=PPL_EXPOSURE_US,
        base_name=base_sample_name,
        save_dir=ppl_dir,
    )

    seq.add_command(APISRotatePolarizer(apis, angle_deg=0.0))
    seq.add_command(APISRotateSample(apis, angle_deg=0.0))
    seq.add_command(APISDeinitialize(apis))

    print("\nRunning imaging sequence...")
    invoker = CommandInvoker(seq, False)
    result = invoker.invoke_commands()
    print(f"\nImaging finished. Result: {result}")


if __name__ == "__main__":
    main()
