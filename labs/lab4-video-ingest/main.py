import gc
import math
import os
import tempfile

from common.handler_utils import parse_s3_event
from common.config_utils import validate_config
from common.s3_client import init_s3_client, download_object


def init(ctx):
    ctx.logger.info("🚀 Init: video segmenter")

    secrets = ctx.secrets.get("secrets", {})
    validate_config(
        ctx,
        required_envs=["S3_ENDPOINT_URL", "S3_REGION", "SEGMENT_DURATION"],
        required_secrets=["S3_ACCESS_KEY", "S3_SECRET_KEY"],
        secrets=secrets,
    )

    ctx.s3_client = init_s3_client(ctx, secrets)

    ctx.segment_duration = int(os.environ.get("SEGMENT_DURATION", "5"))
    ctx.output_bucket = os.environ.get("OUTPUT_BUCKET", "")
    ctx.logger.info(f"✅ Segment duration: {ctx.segment_duration}s")


def handler(ctx, event):
    ctx.logger.info("ℹ️ Handler invoked")

    s3_bucket, s3_key = parse_s3_event(event)
    if not s3_bucket:
        ctx.logger.warning("⚠️ No records found in event")
        return {"status": "error", "reason": "No Records in event"}

    filename = os.path.basename(s3_key)
    ctx.logger.info(f"📦 Bucket: {s3_bucket} | 📄 Key: {s3_key}")

    if not s3_key.lower().endswith(".mp4"):
        ctx.logger.info(f"Skipping non-mp4 file: {s3_key}")
        return {"status": "skipped", "reason": f"Not a .mp4 file: {s3_key}"}

    if "_segment_" in s3_key.lower():
        ctx.logger.info(f"Skipping already-segmented file: {s3_key}")
        return {"status": "skipped", "reason": f"Already a segment: {s3_key}"}

    # TODO (Step 1): Add idempotency check — set output_bucket, base, segment_prefix,
    #                list objects, and return early if segments already exist.

    video_bytes = download_object(ctx.s3_client, s3_bucket, s3_key)

    segment_keys = segment_and_upload(ctx, video_bytes, filename, output_bucket)

    # TODO (Step 4): Build and return the result dict.


def segment_and_upload(ctx, video_bytes, filename, output_bucket):
    base = os.path.splitext(filename)[0]
    segment_keys = []

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
        tmp_in.write(video_bytes)
        tmp_in_path = tmp_in.name

    try:
        # TODO (Step 2a): Load the clip with VideoFileClip, calculate total_duration
        #                 and total_segments, and log the video info.

        # TODO (Step 2b): Add the slice loop — subclip, write to tempfile,
        #                 read bytes.
        #                 Note: os.unlink(tmp_out_path) and gc.collect() are
        #                 already called after each iteration.

        # TODO (Step 3): Upload each segment to S3 with put_object and metadata.
        #                Append segment_key to segment_keys.

        clip.close()
        gc.collect()
    finally:
        if os.path.exists(tmp_in_path):
            os.unlink(tmp_in_path)

    return segment_keys
