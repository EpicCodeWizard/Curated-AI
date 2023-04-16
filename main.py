from replit.database.database import ObservedList, ObservedDict
from flask_cors import CORS, cross_origin
from replit import db
from flask import *
import validators
import html2text
import requests
import openai
import numpy
import json
import uuid
import os

app = Flask(__name__)
cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"
class db_raw:
  def items(self):
    findata = {}
    for key in db.keys():
      findata[key] = json.loads(db.get_raw(key)) if type(db[key]) == ObservedList or type(db[key]) == ObservedDict else db[key]
    return findata.items()
  def __getitem__(self, key):
    return json.loads(db.get_raw(key)) if type(db[key]) == ObservedList or type(db[key]) == ObservedDict else db[key]
db_raw = db_raw()
openai.api_key = os.environ["OPENAI_KEY"]

def proccess_data(url):
  return html2text.html2text(requests.get(url).text)

def get_embedding(text):
  result = openai.Embedding.create(model="text-embedding-ada-002", input=text)
  return result["data"][0]["embedding"]

def vector_similarity(x, y):
  return numpy.dot(numpy.array(x), numpy.array(y))

@app.route("/api/create", methods=["POST"])
@cross_origin()
def create_bookmark():
  if request.json["userId"] not in db:
    db[request.json["userId"]] = []
  if "url" in request.json:
    text = proccess_data(request.json["url"])
    url = request.json["url"]
  else:
    text = request.json["text"]
    url = None
  daid = str(uuid.uuid4())
  db["embeddings"][daid] = get_embedding(text)
  db[request.json["userId"]].append({"title": request.json["title"], "url": url, "text": text, "id": daid})
  return daid

@app.route("/api/bookmarks", methods=["GET"])
@cross_origin()
def get_bookmarks():
  try:
    return jsonify(db_raw[request.args.get("userId")])
  except:
    return jsonify([])

@app.route("/api/bookmark", methods=["GET"])
@cross_origin()
def get_bookmark():
  index = 0
  for i, x in enumerate(db_raw[request.args.get("userId")]):
    if x["id"] == request.args.get("id"):
      index += i
  return jsonify(db_raw[request.args.get("userId")][index])

@app.route("/api/delete", methods=["POST"])
@cross_origin()
def delete_bookmark():
  index = 0
  for i, x in enumerate(db_raw[request.json["userId"]]):
    if x["id"] == request.json["id"]:
      index += i
  del db[request.json["userId"]][index]
  return ""

@app.route("/api/query", methods=["GET"])
@cross_origin()
def query_bookmark():
  search = request.args.get("q")
  bookmarks = db_raw[request.args.get("userId")]
  query_embedding = get_embedding(search)
  document_similarities = {}
  for bookmark in bookmarks:
    document_similarities[bookmark["id"]] = vector_similarity(query_embedding, db_raw["embeddings"][bookmark["id"]])
  document_similarities = dict(sorted(document_similarities.items(), key=lambda item: item[1]))
  index = 0
  special_id = next(iter(document_similarities.keys()))
  for i, x in enumerate(bookmarks):
    if x["id"] == special_id:
      index += i
  return jsonify(dict(**bookmarks[index], confidence=next(iter(document_similarities.values()))))

app.run(host="0.0.0.0")
