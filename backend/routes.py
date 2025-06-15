from . import app
import os
import json
import pymongo
import logging
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route("/health", methods=["GET"])
def health():
    try:
        # Verify MongoDB connection
        client.admin.command('ping')
        return jsonify({"status": "OK", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "Error", "error": str(e)}), 500

@app.route("/count")
def count():
    """return length of data"""
    count = db.songs.count_documents({})
    return jsonify({"count": count}), 200

@app.route("/song", methods=["GET"])
def songs():
    """Return all songs from the database"""
    songs_list = list(db.songs.find({}))
    return jsonify({"songs": parse_json(songs_list)}), 200


@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    song = db.songs.find_one({"id": id})
    if song is None:
        return jsonify({"message": "song with id not found"}), 404
    return jsonify(parse_json(song)), 200

@app.route("/song", methods=["POST"])
def create_song():
    try:
        song = request.get_json()
        if not song:
            return jsonify({"message": "Invalid JSON"}), 400
        if "id" not in song:
            return jsonify({"message": "Missing id field"}), 400

        existing = db.songs.find_one({"id": song["id"]})
        if existing:
            response = make_response(
                jsonify({"Message": f"song with id {song['id']} already present"}),
                302
            )
            response.headers['Location'] = url_for('get_song_by_id', id=song["id"])
            return response

        db.songs.insert_one(song)
        # Fetch the inserted document (including _id)
        inserted_song = db.songs.find_one({"id": song["id"]})
        return jsonify(parse_json(inserted_song)), 201

    except Exception as e:
        return jsonify(f"Error in create_song: {str(e)}")
        # return jsonify({"message": "Internal server error"}), 500

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    # Get update data from request
    update_data = request.get_json()
    if not update_data:
        return jsonify({"message": "Invalid input"}), 400
    
    # Check if song exists
    existing_song = db.songs.find_one({"id": id})
    if not existing_song:
        return jsonify({"message": "song not found"}), 404
    
    # Perform update
    db.songs.update_one(
        {"id": id},
        {"$set": update_data}
    )
    
    # Return updated song
    updated_song = db.songs.find_one({"id": id})
    return jsonify(parse_json(updated_song)), 200

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    # Delete the song from the database
    result = db.songs.delete_one({"id": id})
    
    if result.deleted_count == 0:
        return jsonify({"message": "song not found"}), 404
    
    return "", 204

    
