import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from gridfs import GridFS

CWD = Path.cwd().resolve()
ROOT_DIR = CWD.parent if CWD.name == "aamp_app" else CWD
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


CAMPAIGN_NAME = "${campaign_name}"
BATCH_NO = ${batch_no}
SAMPLE_NO = ${sample_no}
APIS_PORT = "COM8"
ROOT_SAVE_DIR = ROOT_DIR / "data" / "imaging"
XPL_EXPOSURE_US = 50000
PPL_EXPOSURE_US = 18000
SAMPLE_ANGLES_DEG = [90, 60, 45, 30, 0]


def load_env(file_path=ROOT_DIR / ".env"):
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value


def sanitize_path_component(value: str) -> str:
    sanitized = re.sub(r'[<>:"/\\\\|?*]+', "_", value.strip())
    return sanitized or "unnamed_campaign"


def get_mongo():
    mongo_uri = os.environ.get("MONGO_URI")
    mongo_db_name = os.environ.get("MONGO_DB_NAME")
    if not mongo_uri or not mongo_db_name:
        raise RuntimeError("MONGO_URI and MONGO_DB_NAME must be set in .env.")
    return MongoDBHelper(mongo_uri, mongo_db_name)


def fetch_parameter_set(mongo, campaign_name, batch_no, sample_no):
    campaign_doc = mongo.db["campaigns"].find_one({"campaign_name": campaign_name})
    if campaign_doc is None:
        raise LookupError(f"Campaign '{campaign_name}' was not found.")
    set_doc = mongo.db["sets"].find_one(
        {
            "campaign_id": campaign_doc["_id"],
            "batch_no": batch_no,
            "sample_no": sample_no,
        }
    )
    if set_doc is None:
        raise LookupError(
            f"No parameter set found for campaign='{campaign_name}', batch_no={batch_no}, sample_no={sample_no}."
        )
    return campaign_doc, set_doc


def build_sample_params(batch_no, sample_no, set_doc):
    return {
        "polymer": set_doc["polymer_name"],
        "round_num": batch_no,
        "sample_num": sample_no,
        "temperature": set_doc["temperature"],
        "speed": float(set_doc["motor_speed"]),
        "gap": set_doc["printing_gap"],
        "solvent": set_doc["solvent"],
        "concentration": set_doc["concentration"],
        "volume": set_doc["precursor_volume"],
    }


def add_mode_capture_commands(seq, apis, mode_name, polarizer_angle, sample_angles, exposure_time, base_name, save_dir, capture_records):
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


def upload_capture_records_to_mongodb(mongo, campaign_doc, set_doc, capture_records):
    fs = GridFS(mongo.db)
    uploaded_count = 0
    for record in capture_records:
        local_path = record["local_path"]
        if not os.path.isfile(local_path):
            continue
        with open(local_path, "rb") as file_obj:
            file_id = fs.put(file_obj, filename=os.path.basename(local_path))
        metadata = {
            "campaign_id": campaign_doc["_id"],
            "campaign_name": campaign_doc["campaign_name"],
            "set_id": set_doc["_id"],
            "batch_no": set_doc["batch_no"],
            "sample_no": set_doc["sample_no"],
            "polymer_name": set_doc["polymer_name"],
            "solvent": set_doc["solvent"],
            "concentration": set_doc["concentration"],
            "motor_speed": set_doc["motor_speed"],
            "temperature": set_doc["temperature"],
            "printing_gap": set_doc["printing_gap"],
            "precursor_volume": set_doc["precursor_volume"],
            "mode": record["mode"],
            "image_kind": record["image_kind"],
            "sample_angle_deg": record["sample_angle_deg"],
            "file_id": file_id,
            "filename": os.path.basename(local_path),
            "relative_local_path": os.path.relpath(local_path, ROOT_DIR),
            "measurement_type": "apis_imaging",
            "source": "ch_apis_imaging_recipe",
            "uploaded_at": datetime.now(timezone.utc),
        }
        mongo.db["images"].insert_one(metadata)
        uploaded_count += 1
    return uploaded_count


load_env()
mongo = get_mongo()
campaign_doc, set_doc = fetch_parameter_set(mongo, CAMPAIGN_NAME, BATCH_NO, SAMPLE_NO)
params = build_sample_params(BATCH_NO, SAMPLE_NO, set_doc)

base_sample_name = APIS.build_sample_basename(
    round_num=params["round_num"],
    sample_num=params["sample_num"],
    polymer=params["polymer"],
    solvent=params["solvent"],
    concentration=params["concentration"],
    speed=params["speed"],
    temperature=params["temperature"],
    gap=params["gap"],
    volume=params["volume"],
)

root_save_dir = os.path.join(str(ROOT_SAVE_DIR), sanitize_path_component(CAMPAIGN_NAME))
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

xpl_dir = apis.resolve_mode_directory(root_save_dir, params["polymer"], "xpl")
ppl_dir = apis.resolve_mode_directory(root_save_dir, params["polymer"], "ppl")
capture_records = []

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

invoker = CommandInvoker(seq, False)
result = invoker.invoke_commands()
print(f"APIS imaging finished for campaign={CAMPAIGN_NAME}, batch_no={BATCH_NO}, sample_no={SAMPLE_NO}. Result={result}")

if result:
    uploaded_count = upload_capture_records_to_mongodb(mongo, campaign_doc, set_doc, capture_records)
    print(f"Uploaded {uploaded_count} APIS image files to GridFS and inserted metadata into images collection.")

mongo.close_connection()
