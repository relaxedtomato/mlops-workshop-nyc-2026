#!/usr/bin/env python3
"""
Search VastDB segments by semantic similarity.

Usage:
  python3 search_vastdb.py "cars driving on a highway"

Environment variables:
  VASTDB_ENDPOINT, VASTDB_BUCKET, VASTDB_ACCESS_KEY, VASTDB_SECRET_KEY
  VASTDB_SCHEMA, VASTDB_TABLE
  EMBEDDING_ENDPOINT, EMBEDDING_MODEL, LLM_API_KEY
"""
import json
import os
import sys

import numpy as np
import vastdb
from openai import OpenAI

ENDPOINT   = os.environ.get("VASTDB_ENDPOINT", "")
ACCESS_KEY = os.environ.get("VASTDB_ACCESS_KEY", "")
SECRET_KEY = os.environ.get("VASTDB_SECRET_KEY", "")
BUCKET     = os.environ.get("VASTDB_BUCKET", "")
SCHEMA     = os.environ.get("VASTDB_SCHEMA", "video_embeddings")
TABLE      = os.environ.get("VASTDB_TABLE", "segments")
TOP_K      = 3
MIN_SCORE  = 0.4

query = " ".join(sys.argv[1:])
if not query:
    raise SystemExit("Usage: python3 search_vastdb.py <search prompt>")

client = OpenAI(
    base_url=os.environ.get("EMBEDDING_ENDPOINT", ""),
    api_key=os.environ.get("LLM_API_KEY", "ollama"),
)
response = client.embeddings.create(
    model=os.environ.get("EMBEDDING_MODEL", ""),
    input=query,
    dimensions=1024,
)
query_embedding = np.array(response.data[0].embedding)

session = vastdb.connect(endpoint=ENDPOINT, access=ACCESS_KEY, secret=SECRET_KEY)
with session.transaction() as tx:
    table = tx.bucket(BUCKET).schema(SCHEMA).table(TABLE)
    rows = table.select().read_all()

results = []
for i in range(len(rows)):
    embedding = np.array(rows["embedding"][i].as_py())
    norm = np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
    score = float(np.dot(query_embedding, embedding) / norm) if norm else 0.0
    results.append({
        "segment_key":  rows["segment_key"][i].as_py(),
        "source_video": rows["source_video"][i].as_py(),
        "description":  rows["description"][i].as_py(),
        "score":        round(score, 4),
    })

results.sort(key=lambda r: r["score"], reverse=True)
top = [r for r in results if r["score"] >= MIN_SCORE][:TOP_K]
print(json.dumps(top, indent=2))
