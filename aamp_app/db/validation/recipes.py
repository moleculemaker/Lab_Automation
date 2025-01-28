from mongodb_helper import MongoDBHelper
from pymongo.errors import CollectionInvalid
import os

def init_collection():
    def load_env(file_path=".env"):
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value

    load_env()

    mongo_uri = os.environ.get("MONGO_URI")
    mongo_db_name = os.environ.get("MONGO_DB_NAME")

    mongo = MongoDBHelper(
        mongo_uri,
        mongo_db_name,
    )

    db = mongo.db


    film_dict = {
        "metadata": {
            "solvent": "string",
            "concentration": "float",
            "printing_speed": "float",
            "printing_temperature": "float",
        },
        "result": {
            "uv_vis": ["object_id", "null"],
            "t80": ["float", "null"],
        },
    }


    recipe_dict_schema = {
        "bsonType": "object",
        "title": "Recipe Object Validation",
        "required": ["file_name", "recipe_dict", "dash_friendly", "executions"],
        "properties": {
            "file_name": {
                "bsonType": "string",
                "description": "'file_name' must be a string and is required"
            },
            "recipe_dict": {
                "bsonType": "object",
                "title": "Recipe Dictionary Validation",
                "required": ["devices", "commands", "execution_options"],
                "properties": {
                    "devices": {
                        "bsonType": "array",
                        "description": "'devices' must be an array and is required"
                    },
                    "commands": {
                        "bsonType": "array",
                        "description": "'commands' must be an array and is required"
                    },
                    "execution_options": {
                        "bsonType": "object",
                        "required": ["output_files", "default_execution_record_name"],
                        "properties": {
                            "output_files": {
                                "bsonType": "array",
                                "description": "'output_files' must be an array"
                            },
                            "default_execution_record_name": {
                                "bsonType": "string",
                                "description": "'default_execution_record_name' must be a string"
                            }
                        }
                    }
                }
            },
            "dash_friendly": {
                "bsonType": "bool",
                "description": "'dash_friendly' must be a boolean and is required"
            },
            "executions": {
                "bsonType": "array",
                "description": "'executions' must be an array and is required"
            }
        }
    }



    collection_name = "recipes"
    collection_options = {"validator": {"$jsonSchema": recipe_dict_schema}}
    try:
        db.create_collection(collection_name, **collection_options)
    except CollectionInvalid:
        print("recipes collection already exists")