"""Loads station metadata, alerts and model metadata into MongoDB (document store for flexible JSON data;
view it in MongoDB Compass).  pip install pymongo"""
import os, json, glob, sqlite3, pandas as pd
from pymongo import MongoClient, GEOSPHERE
db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017"))["earthscape"]
st = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "stations.csv"))
db.stations.delete_many({})
db.stations.insert_many([{**r, "location": {"type": "Point", "coordinates": [r["longitude"], r["latitude"]]}} for r in st.to_dict("records")])
db.stations.create_index([("location", GEOSPHERE)])
sample = pd.read_json(os.path.join(os.path.dirname(__file__), "..", "data", "sample_stream.json"))
db.readings_stream.delete_many({}); db.readings_stream.insert_many(json.loads(sample.to_json(orient="records")))
db.readings_stream.create_index([("station_id", 1), ("date", -1)])
for f in glob.glob(os.path.join(os.path.dirname(__file__), "..", "ml", "registry", "v*.json")):
    db.model_registry.replace_one({"version": json.load(open(f))["version"]}, json.load(open(f)), upsert=True)
print("MongoDB loaded:", db.stations.count_documents({}), "stations,", db.readings_stream.count_documents({}), "stream readings")
# Example query in Mongo Shell:  db.stations.find({location:{$near:{$geometry:{type:"Point",coordinates:[67,24.8]},$maxDistance:300000}}})
