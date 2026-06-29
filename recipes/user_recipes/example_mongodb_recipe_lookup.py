"""Minimal recipe example that reads a parameter set from MongoDB.

Run from the repository root:
    python ./recipes/user_recipes/example_mongodb_recipe_lookup.py

Expected .env entries:
    MONGO_URI=mongodb://...
    MONGO_DB_NAME=...
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


ROOT_DIR = Path(__file__).resolve().parents[2]
AAMP_APP_DIR = ROOT_DIR / "aamp_app"
for path in (ROOT_DIR, AAMP_APP_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from command_sequence import CommandSequence
from mongodb_helper import MongoDBHelper


DEFAULT_CAMPAIGN_NAME = ""


def load_env(file_paths=(ROOT_DIR / ".env", AAMP_APP_DIR / ".env")) -> None:
    for file_path in file_paths:
        if not file_path.exists():
            continue
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


def get_mongo_helper() -> MongoDBHelper:
    mongo_uri = os.environ.get("MONGO_URI")
    mongo_db_name = os.environ.get("MONGO_DB_NAME")
    if not mongo_uri or not mongo_db_name:
        raise RuntimeError("MONGO_URI and MONGO_DB_NAME must be set in .env.")
    return MongoDBHelper(mongo_uri, mongo_db_name)


def fetch_campaign(mongo: MongoDBHelper, campaign_name: str) -> dict:
    campaign_doc = mongo.db["campaigns"].find_one({"campaign_name": campaign_name})
    if campaign_doc is None:
        available_campaigns = sorted(mongo.db["campaigns"].distinct("campaign_name"))
        preview = available_campaigns[:20]
        suffix = " ..." if len(available_campaigns) > len(preview) else ""
        raise LookupError(
            f"Campaign '{campaign_name}' was not found. Available campaigns: {preview}{suffix}"
        )
    return campaign_doc


def list_batch_numbers(mongo: MongoDBHelper, campaign_doc: dict) -> List[int]:
    return sorted(mongo.db["sets"].distinct("batch_no", {"campaign_id": campaign_doc["_id"]}))


def list_sample_numbers(mongo: MongoDBHelper, campaign_doc: dict, batch_no: int) -> List[int]:
    return sorted(
        mongo.db["sets"].distinct(
            "sample_no",
            {
                "campaign_id": campaign_doc["_id"],
                "batch_no": batch_no,
            },
        )
    )


def prompt_choice(prompt: str, options: List[int]) -> int:
    if not options:
        raise LookupError(f"No options available for {prompt}.")

    print(f"\nAvailable {prompt}: {options}")
    default = options[0]
    while True:
        raw_value = input(f"Choose {prompt} [{default}]: ").strip()
        value = default if not raw_value else int(raw_value)
        if value in options:
            return value
        print(f"{value} is not available. Choose one of: {options}")


def fetch_parameter_set(
    mongo: MongoDBHelper,
    campaign_doc: dict,
    batch_no: int,
    sample_no: int,
) -> Tuple[dict, dict]:
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
                f"No set found for campaign='{campaign_doc['campaign_name']}', batch_no={batch_no}, "
                f"sample_no={sample_no}. Available sample_no values: {available_samples}"
            )

        available_batches = list_batch_numbers(mongo, campaign_doc)
        raise LookupError(
            f"No set found for campaign='{campaign_doc['campaign_name']}', batch_no={batch_no}, "
            f"sample_no={sample_no}. Available batch_no values: {available_batches}"
        )

    return campaign_doc, set_doc


def display_value(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def build_recipe_params(batch_no: int, sample_no: int, set_doc: dict) -> Dict[str, object]:
    return {
        "campaign_name": display_value(set_doc.get("campaign_name", "")),
        "batch_no": batch_no,
        "sample_no": sample_no,
        "polymer_name": display_value(set_doc["polymer_name"]),
        "temperature": display_value(set_doc["temperature"]),
        "motor_speed": float(set_doc["motor_speed"]),
        "printing_gap": display_value(set_doc["printing_gap"]),
        "solvent": display_value(set_doc["solvent"]),
        "concentration": display_value(set_doc["concentration"]),
        "precursor_volume": display_value(set_doc["precursor_volume"]),
    }


def sanitize_path_component(value: object) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*]+', "_", str(value).strip())
    return sanitized or "unnamed"


def build_sample_name(params: Dict[str, object]) -> str:
    speed = f"{params['motor_speed']:.4f}".rstrip("0").rstrip(".")
    parts = [
        f"R{params['batch_no']}",
        f"S{params['sample_no']}",
        params["polymer_name"],
        params["solvent"],
        f"{params['concentration']}mgml",
        f"{speed}mms",
        f"{params['temperature']}C",
        f"{params['printing_gap']}um",
        f"{params['precursor_volume']}ul",
    ]
    return sanitize_path_component("_".join(str(part) for part in parts))


def build_sequence(params: Dict[str, object]) -> CommandSequence:
    seq = CommandSequence()

    # Add devices and commands here using values from params.
    # Example:
    #   volume_ul = float(params["precursor_volume"])
    #   speed_mm_s = float(params["motor_speed"])
    #   gap_um = float(params["printing_gap"])
    #
    #   seq.add_device(...)
    #   seq.add_command(...)

    return seq


def prompt_with_default(prompt: str, default: object) -> str:
    raw_value = input(f"{prompt} [{default}]: ").strip()
    return raw_value if raw_value else str(default)


def main() -> None:
    load_env()
    mongo = get_mongo_helper()

    campaign_name = prompt_with_default("Campaign name", DEFAULT_CAMPAIGN_NAME)
    if not campaign_name:
        raise ValueError("Campaign name is required.")

    campaign_doc = fetch_campaign(mongo, campaign_name)
    batch_no = prompt_choice("batch_no values", list_batch_numbers(mongo, campaign_doc))
    sample_no = prompt_choice("sample_no values", list_sample_numbers(mongo, campaign_doc, batch_no))

    campaign_doc, set_doc = fetch_parameter_set(mongo, campaign_doc, batch_no, sample_no)
    params = build_recipe_params(batch_no, sample_no, set_doc)
    params["campaign_name"] = campaign_doc["campaign_name"]

    print("\nLoaded MongoDB parameter set:")
    for key, value in params.items():
        print(f"  {key}: {value}")

    print(f"\nSuggested sample name: {build_sample_name(params)}")

    seq = build_sequence(params)
    print("\nRecipe command sequence preview:")
    if seq.command_list:
        seq.print_command_names()
    else:
        print("  No commands yet. Add devices/commands in build_sequence().")


if __name__ == "__main__":
    main()
