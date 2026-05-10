import gc
import math
import os
import tempfile

from moviepy.editor import VideoFileClip
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

    output_bucket = ctx.output_bucket or s3_bucket
    base = os.path.splitext(filename)[0]
    segment_prefix = f"{base}/"

    resp = ctx.s3_client.list_objects_v2(Bucket=output_bucket, Prefix=segment_prefix, MaxKeys=1)
    
    if resp.get("Contents"):
        return {"status": "skipped", "reason": "Segments already exist"}

    video_bytes = download_object(ctx.s3_client, s3_bucket, s3_key)

    segment_keys = segment_and_upload(ctx, video_bytes, filename, output_bucket)

    result = {
        "status": "success",
        "source_bucket": s3_bucket,
        "source_key": s3_key,
        "output_bucket": output_bucket,
        "segment_keys": segment_keys,
        "segment_count": len(segment_keys),
        "segment_duration": ctx.segment_duration,
    }
    ctx.logger.info(f"Result: {result}")
    return result


def segment_and_upload(ctx, video_bytes, filename, output_bucket):
    base = os.path.splitext(filename)[0]
    segment_keys = []

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
        tmp_in.write(video_bytes)
        tmp_in_path = tmp_in.name

    try:
        clip = VideoFileClip(tmp_in_path)
        total_duration = clip.duration
        total_segments = math.ceil(total_duration / ctx.segment_duration)
        ctx.logger.info(f"Video: {total_duration:.2f}s -> {total_segments} x {ctx.segment_duration}s segments")

        for i in range(total_segments):
            start = i * ctx.segment_duration
            end = min(start + ctx.segment_duration, total_duration)
            segment_key = f"{base}/{base}_segment_{i+1:03d}_of_{total_segments:03d}.mp4"

            try:
                sub = clip.subclip(start, end)
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_out:
                    tmp_out_path = tmp_out.name
                sub.write_videofile(tmp_out_path, codec="libx264", audio=False, logger=None)
                sub.close()
            except Exception as e:
                ctx.logger.warning(f"⚠️ Segment {i+1}/{total_segments}: {str(e)[:80]}")
                gc.collect()
                continue

            with open(tmp_out_path, "rb") as f:
                segment_bytes = f.read()
            os.unlink(tmp_out_path)
            gc.collect()

            ctx.s3_client.put_object(
                Bucket=output_bucket,
                Key=segment_key,
                Body=segment_bytes,
                Metadata={
                    "original-video": filename,
                    "segment-number": str(i + 1),
                    "total-segments": str(total_segments),
                    "segment-duration": str(ctx.segment_duration),
                },
            )

            segment_keys.append(segment_key)

        clip.close()
        gc.collect()
    finally:
        if os.path.exists(tmp_in_path):
            os.unlink(tmp_in_path)

    return segment_keys
