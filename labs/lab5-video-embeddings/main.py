import base64
import os
import tempfile
from io import BytesIO

import pyarrow as pa
from moviepy.editor import VideoFileClip
from PIL import Image

from common.config_utils import validate_config
from common.s3_client import init_s3_client
from common.vastdb_client import init_vastdb_client, connect_vastdb
from common.vlm_client import init_vlm_client


def init(ctx):
    ctx.logger.info("🚀 Init: video embeddings")

    secrets = ctx.secrets.get("secrets", {})
    validate_config(
        ctx,
        required_envs=["S3_ENDPOINT_URL", "S3_REGION", "VLM_ENDPOINT", "VISION_MODEL", "EMBEDDING_MODEL"],
        required_secrets=["S3_ACCESS_KEY", "S3_SECRET_KEY", "LLM_API_KEY"],
        secrets=secrets,
    )

    ctx.s3_client = init_s3_client(ctx, secrets)
    ctx.vlm_client = init_vlm_client(ctx, secrets)
    init_vastdb_client(ctx, secrets)


def handler(ctx, event):
    data = event.data.get("data", event.data)
    status = data.get("status", "")

    if status != "success":
        ctx.logger.info(f"Upstream status={status} — skipping")
        return {"status": "skipped", "reason": f"Upstream status: {status}"}

    segment_keys = data.get("segment_keys", [])
    output_bucket = data.get("output_bucket", "")
    source_key = data.get("source_key", "")

    if not segment_keys:
        ctx.logger.warning("⚠️ No segment_keys in event")
        return {"status": "error", "reason": "No segment_keys in event"}

    ctx.logger.info(f"📦 Processing {len(segment_keys)} segments from {source_key}")

    results = process_segments(ctx, segment_keys, output_bucket, source_key, data)
    ctx.logger.info(f"✅ Result: {results}")

    return {
        "status": "success",
        "source_key": source_key,
        "segment_count": len(results),
    }


def process_segments(ctx, segment_keys, output_bucket, source_key, data):
    results = []

    for segment_key in segment_keys:
        ctx.logger.info(f"Processing: {segment_key}")

        # TODO (Step 1a): Download the segment from S3 as video_bytes.
        #                 Wrap in try/except and continue on error.

        # TODO (Step 1b): Write video_bytes to a tempfile, load with VideoFileClip,
        #                 extract 3 evenly spaced frames as JPEG bytes.
        #                 Use try/except/finally — finally removes the tempfile.

        # TODO (Step 2a): Build a multimodal request with the text prompt and base64 frames,
        #                 call the vision model, extract description.
        #                 Fall back to reasoning if content is empty.
        #                 Wrap in try/except and continue on error.

        # TODO (Step 2b): Call the embedding model with the description to get a 1024-dim vector.

        # TODO (Step 3): Connect to VastDB using connect_vastdb(ctx) and insert a row for this segment.
        #                See Step 3 in README for the full insert code.

        results.append(segment_key)

    return results
