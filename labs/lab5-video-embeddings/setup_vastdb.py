#!/usr/bin/env python3
import os
import pyarrow as pa
import vastdb

session = vastdb.connect(
    endpoint=os.environ.get("VASTDB_ENDPOINT", ""),
    access=os.environ.get("VASTDB_ACCESS_KEY", ""),
    secret=os.environ.get("VASTDB_SECRET_KEY", ""),
)
print("Connected to VastDB.")

BUCKET_NAME = os.environ.get("VASTDB_BUCKET", "")
SCHEMA_NAME = "video_embeddings"
TABLE_NAME = os.environ.get("VASTDB_TABLE", "segments")

segment_schema = pa.schema([
    ("segment_key",      pa.utf8()),
    ("source_video",     pa.utf8()),
    ("segment_number",   pa.int32()),
    ("total_segments",   pa.int32()),
    ("segment_duration", pa.float32()),
    ("description",      pa.utf8()),
    ("embedding",        pa.list_(pa.field("item", pa.float32(), nullable=False), 1024)),
])

with session.transaction() as tx:
    bucket = tx.bucket(BUCKET_NAME)
    print(f"Bucket '{bucket.name}' accessed")

    try:
        schema = bucket.create_schema(SCHEMA_NAME)
        print(f"Schema '{SCHEMA_NAME}' created")
    except Exception:
        schema = bucket.schema(SCHEMA_NAME)
        print(f"Schema '{SCHEMA_NAME}' accessed (already exists)")

    try:
        table = schema.create_table(TABLE_NAME, segment_schema)
        print(f"Table '{TABLE_NAME}' created")
    except Exception:
        table = schema.table(TABLE_NAME)
        print(f"Table '{TABLE_NAME}' accessed (already exists)")

    result = table.select().read_all()
    print(f"Verified: {len(result)} row(s) in table.")

print("VastDB setup complete.")
