# APIS imaging workflow example backed by MongoDB parameter sets.
# Run from repo root using:
#   python -m examples.example_apis_from_mongodb

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from gridfs import GridFS

ROOT_DIR = Path(__file__).resolve().parents[1]
AAMP_APP_DIR = ROOT_DIR / "aamp_app"
for path in (ROOT_DIR, AAMP_APP_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from command_invoker import CommandInvoker
from command_sequence import CommandSequence
from commands.apis_commands import *
from devices.apis import APIS
from mongodb_helper import MongoDBHelper


APIS_PORT = "COM8"
ROOT_SAVE_DIR = os.path.join("data", "imaging")
XPL_EXPOSURE_US = 50000
PPL_EXPOSURE_US = 18000
SAMPLE_ANGLES_DEG = [90, 60, 45, 30, 0]


def load_env(file_path: Path = ROOT_DIR / ".env") -> None:
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value


def sanitize_path_component(value: str) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*]+', "_", value.strip())
    return sanitized or "unnamed_campaign"


def format_display_value(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def get_mongo_helper() -> MongoDBHelper:
    mongo_uri = os.environ.get("MONGO_URI")
    mongo_db_name = os.environ.get("MONGO_DB_NAME")
    if not mongo_uri or not mongo_db_name:
        raise RuntimeError("MONGO_URI and MONGO_DB_NAME must be set in .env to use this example.")
    return MongoDBHelper(mongo_uri, mongo_db_name)


def fetch_parameter_set(
    mongo: MongoDBHelper,
    campaign_name: str,
    batch_no: int,
    sample_no: int,
) -> Tuple[dict, dict]:
    campaign_doc = mongo.db["campaigns"].find_one({"campaign_name": campaign_name})
    if campaign_doc is None:
        raise LookupError(f"Campaign '{campaign_name}' was not found in the campaigns collection.")

    set_doc = mongo.db["sets"].find_one(
        {
            "campaign_id": campaign_doc["_id"],
            "batch_no": batch_no,
            "sample_no": sample_no,
        }
    )
    if set_doc is None:
        available_samples = sorted(
            mongo.db["sets"].distinct(
                "sample_no",
                {
                    "campaign_id": campaign_doc["_id"],
                    "batch_no": batch_no,
                },
            )
        )
        if available_samples:
            raise LookupError(
                f"No parameter set found for campaign='{campaign_name}', batch_no={batch_no}, "
                f"sample_no={sample_no}. Available sample_no values for that round: {available_samples}"
            )
        available_rounds = sorted(
            mongo.db["sets"].distinct(
                "batch_no",
                {"campaign_id": campaign_doc["_id"]},
            )
        )
        raise LookupError(
            f"No parameter set found for campaign='{campaign_name}', batch_no={batch_no}, "
            f"sample_no={sample_no}. Available rounds(batch_no): {available_rounds}"
        )
    return campaign_doc, set_doc


def build_set_params(batch_no: int, sample_no: int, set_doc: dict) -> Dict[str, object]:
    return {
        "campaign_name": format_display_value(set_doc.get("campaign_name", "")),
        "batch_no": batch_no,
        "sample_no": sample_no,
        "polymer_name": format_display_value(set_doc["polymer_name"]),
        "temperature": format_display_value(set_doc["temperature"]),
        "motor_speed": float(set_doc["motor_speed"]),
        "printing_gap": format_display_value(set_doc["printing_gap"]),
        "solvent": format_display_value(set_doc["solvent"]),
        "concentration": format_display_value(set_doc["concentration"]),
        "precursor_volume": format_display_value(set_doc["precursor_volume"]),
    }


def add_mode_capture_commands(
    seq: CommandSequence,
    apis: APIS,
    mode_name: str,
    polarizer_angle: float,
    sample_angles: List[float],
    exposure_time: int,
    base_name: str,
    save_dir: str,
    capture_records: List[dict],
) -> None:
    seq.add_command(APISRotatePolarizer(apis, angle_deg=polarizer_angle))
    for angle in sample_angles:
        seq.add_command(APISRotateSample(apis, angle_deg=angle))
        filename = apis.build_mode_filename(base_name, mode_name, angle)
        raw16_path = os.path.join(save_dir, "raw16", filename + ".tif")
        rgb_path = os.path.join(save_dir, "rgb", filename + "_rgb.tif")
        capture_records.append(
            {
                "mode": mode_name,
                "image_kind": "raw16",
                "sample_angle_deg": angle,
                "local_path": raw16_path,
            }
        )
        capture_records.append(
            {
                "mode": mode_name,
                "image_kind": "rgb",
                "sample_angle_deg": angle,
                "local_path": rgb_path,
            }
        )
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


def upload_capture_records_to_mongodb(
    mongo: MongoDBHelper,
    campaign_doc: dict,
    set_doc: dict,
    capture_records: List[dict],
) -> Tuple[int, int]:
    fs = GridFS(mongo.db)
    uploaded_count = 0
    skipped_count = 0
    for record in capture_records:
        local_path = record["local_path"]
        if not os.path.isfile(local_path):
            skipped_count += 1
            continue

        with open(local_path, "rb") as file_obj:
            file_id = fs.put(file_obj, filename=os.path.basename(local_path))

        metadata = {
            "campaign_id": campaign_doc["_id"],
            "campaign_name": campaign_doc["campaign_name"],
            "set_id": set_doc["_id"],
            "batch_no": set_doc.get("batch_no"),
            "sample_no": set_doc.get("sample_no"),
            "polymer_name": set_doc.get("polymer_name"),
            "solvent": set_doc.get("solvent"),
            "concentration": set_doc.get("concentration"),
            "motor_speed": set_doc.get("motor_speed"),
            "temperature": set_doc.get("temperature"),
            "printing_gap": set_doc.get("printing_gap"),
            "precursor_volume": set_doc.get("precursor_volume"),
            "mode": record["mode"],
            "image_kind": record["image_kind"],
            "sample_angle_deg": record["sample_angle_deg"],
            "file_id": file_id,
            "filename": os.path.basename(local_path),
            "relative_local_path": os.path.relpath(local_path, ROOT_DIR),
            "measurement_type": "apis_imaging",
            "uploaded_at": datetime.now(timezone.utc),
            "source": "example_apis_from_mongodb",
        }
        mongo.db["images"].insert_one(metadata)
        uploaded_count += 1

    return uploaded_count, skipped_count


def main() -> None:
    print("=== APIS Imaging From MongoDB Parameter Sets ===")
    print("This example resolves sample parameters from MongoDB using campaign name, round number, and sample number.")
    print("Round number is matched to MongoDB field `batch_no`.")
    print("Sample number is matched to MongoDB field `sample_no`.")

    load_env()
    mongo = get_mongo_helper()

    campaign_name = input("Enter campaign name: ").strip()
    batch_no = int(input("Enter batch_no: ").strip())
    sample_no = int(input("Enter sample_no: ").strip())

    try:
        campaign_doc, set_doc = fetch_parameter_set(mongo, campaign_name, batch_no, sample_no)
    except LookupError as exc:
        print(f"\nParameter lookup failed: {exc}")
        mongo.close_connection()
        return

    params = build_set_params(batch_no, sample_no, set_doc)

    print("\n=== Resolved Sample Parameters ===")
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
    root_save_dir = os.path.join(ROOT_SAVE_DIR, sanitize_path_component(campaign_name))
    print(f"\nGenerated filename prefix: {base_sample_name}")
    print(f"Local save root: {root_save_dir}")
    print("Mode folders will use `xpl/` and `ppl/`.")
    print("Each capture will save RAW16 first, then convert that file to RGB.")

    upload_after_capture = (
        input("\nUpload captured files to MongoDB GridFS after local imaging? (y/n): ").strip().lower() == "y"
    )
    confirm = input("Proceed with imaging using these parameters? (y/n): ").strip().lower()
    if confirm != "y":
        print("Imaging cancelled.")
        mongo.close_connection()
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
        camera_save_directory=root_save_dir,
        camera_bayer_pattern="GBRG",
        camera_raw_max_value=1023.0,
    )
    xpl_dir = apis.resolve_mode_directory(root_save_dir, params["polymer_name"], "xpl")
    ppl_dir = apis.resolve_mode_directory(root_save_dir, params["polymer_name"], "ppl")

    capture_records: List[dict] = []
    seq = CommandSequence()
    seq.add_device(apis)

    seq.add_command(APISConnect(apis))
    seq.add_command(APISInitialize(apis))
    seq.add_command(APISHome(apis))

    add_mode_capture_commands(
        seq=seq,
        apis=apis,
        mode_name="xpl",
        polarizer_angle=90.0,
        sample_angles=SAMPLE_ANGLES_DEG,
        exposure_time=XPL_EXPOSURE_US,
        base_name=base_sample_name,
        save_dir=xpl_dir,
        capture_records=capture_records,
    )
    add_mode_capture_commands(
        seq=seq,
        apis=apis,
        mode_name="ppl",
        polarizer_angle=0.0,
        sample_angles=SAMPLE_ANGLES_DEG,
        exposure_time=PPL_EXPOSURE_US,
        base_name=base_sample_name,
        save_dir=ppl_dir,
        capture_records=capture_records,
    )

    seq.add_command(APISRotatePolarizer(apis, angle_deg=0.0))
    seq.add_command(APISRotateSample(apis, angle_deg=0.0))
    seq.add_command(APISDeinitialize(apis))

    print("\nRunning imaging sequence...")
    invoker = CommandInvoker(seq, False)
    result = invoker.invoke_commands()
    print(f"\nImaging finished. Result: {result}")

    if result and upload_after_capture:
        uploaded_count, skipped_count = upload_capture_records_to_mongodb(
            mongo=mongo,
            campaign_doc=campaign_doc,
            set_doc=set_doc,
            capture_records=capture_records,
        )
        print(
            f"Uploaded {uploaded_count} files to GridFS and inserted matching metadata into `images`."
        )
        if skipped_count:
            print(f"Skipped {skipped_count} expected files because they were not found on disk.")
    elif upload_after_capture:
        print("Skipping MongoDB upload because imaging did not complete successfully.")

    mongo.close_connection()


if __name__ == "__main__":
    main()
