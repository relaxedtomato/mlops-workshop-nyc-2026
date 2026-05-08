import os

import vastdb


def init_vastdb_client(ctx, secrets):
    ctx.vastdb_endpoint = os.environ.get("VASTDB_ENDPOINT", "")
    ctx.vastdb_bucket = os.environ.get("VASTDB_BUCKET", "")
    ctx.vastdb_schema = os.environ.get("VASTDB_SCHEMA", "video_embeddings")
    ctx.vastdb_table = os.environ.get("VASTDB_TABLE", "segments")
    ctx.vastdb_access_key = secrets.get("VASTDB_ACCESS_KEY", "")
    ctx.vastdb_secret_key = secrets.get("VASTDB_SECRET_KEY", "")
    ctx.logger.info(f"✅ VastDB: {ctx.vastdb_endpoint}/{ctx.vastdb_bucket}")


def connect_vastdb(ctx):
    return vastdb.connect(
        endpoint=ctx.vastdb_endpoint,
        access=ctx.vastdb_access_key,
        secret=ctx.vastdb_secret_key,
    )
