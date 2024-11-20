from mongodb_helper import MongoDBHelper
import os

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


solution_dict = {
    "metadata": {
        "solvent": "string",
        "concentration": 0.3,
    },
    "result": {
        "uv_vis": None,
        "t80": 0.3,
    },
}



json_schema = {
    "bsonType": "object",
    "title": "Solution Object Validation",
    "required": ["metadata", "result"],
    "properties": {
        "metadata": {
            "bsonType": "object",
            "title": "Metadata Object Validation",
            "required": ["solvent", "concentration"],
            "properties": {
                "solvent": {
                    "bsonType": "string",
                    "description": "'solvent' must be a string and is required",
                },
                "concentration": {
                    "bsonType": "double",
                    "description": "'concentration' must be a double and is required",
                },
            },
        },
        "result": {
            "bsonType": "object",
            "title": "Result Object Validation",
            "required": ["uv_vis", "t80"],
            "properties": {
                "uv_vis": {
                    "bsonType": ["objectId", "null"],
                    "description": "'uv_vis' must be an objectId and is required",
                },
                "t80": {
                    "bsonType": ["double", "null"],
                    "description": "'t80' must be a double and is required",
                },
            },
        },
    },
}



collection_name = "solutions"
collection_options = {"validator": {"$jsonSchema": json_schema}}
db.create_collection(collection_name, **collection_options)
quit()
