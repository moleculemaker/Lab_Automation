from mongodb_helper import MongoDBHelper
from gridfs import GridFS
from bson import ObjectId
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

fs = GridFS(db, collection="recipes")

# Open and store the CSV file using GridFS
with open("data.csv", "rb") as file:
    file_id = fs.put(file, filename="data.csv")
    # create ObjectId(file_id) in document to point to csv

# Retrieve the CSV file from GridFS
gridfs_file = fs.find_one({"_id": ObjectId("64c2d215255f257ee66d30e9")})

# Read the CSV data from the file
csv_data = gridfs_file.read()

# Print the CSV data
print(csv_data)
# print(csv_data.decode())
