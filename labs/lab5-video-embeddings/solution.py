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

        try:
            response = ctx.s3_client.get_object(Bucket=output_bucket, Key=segment_key)
            video_bytes = response["Body"].read()
            ctx.logger.info(f"Downloaded s3://{output_bucket}/{segment_key} ({len(video_bytes):,} bytes)")
        except Exception as e:
            ctx.logger.error(f"Failed to download {segment_key}: {e}")
            continue

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        try:
            clip = VideoFileClip(tmp_path)
            num_frames = 3
            frame_times = [clip.duration * (i + 1) / (num_frames + 1) for i in range(num_frames)]
            frames = []
            for t in frame_times:
                frame = clip.get_frame(t)
                buf = BytesIO()
                Image.fromarray(frame).save(buf, format="JPEG")
                frames.append(buf.getvalue())
            clip.close()
            ctx.logger.info(f"Extracted {len(frames)} frames from {segment_key}")
        except Exception as e:
            ctx.logger.error(f"Failed to extract frames from {segment_key}: {e}")
            continue
        finally:
            os.unlink(tmp_path)

        try:
            content = [{"type": "text", "text": "Describe what is happening in these video frames in 1 sentence."}]
            for frame_bytes in frames:
                frame_b64 = base64.b64encode(frame_bytes).decode("utf-8")
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"}})

            response = ctx.vlm_client.chat.completions.create(
                model=ctx.vision_model,
                messages=[
                    {"role": "system", "content": "/no_think"},
                    {"role": "user", "content": content},
                ],
                max_tokens=ctx.max_tokens,
                extra_body={"think": False},
            )
            msg = response.choices[0].message
            description = msg.content or getattr(msg, "reasoning", "")
            description = description.split("\n\n")[-1].strip()
            if ": " in description:
                parts = description.split(": ", 1)
                if len(parts[0]) < 60:
                    description = parts[1].strip()
            if not description:
                ctx.logger.warning(f"Empty description for {segment_key} — skipping embedding")
                continue
            if not msg.content and ctx.summary_model:
                summary_response = ctx.vlm_client.chat.completions.create(
                    model=ctx.summary_model,
                    messages=[{"role": "user", "content": f"Summarize this in one sentence: {description}"}],
                    max_tokens=128,
                )
                description = summary_response.choices[0].message.content
                description = description.split("\n\n")[-1].strip() if description else ""
            ctx.logger.info(f"Description: {description}")
        except Exception as e:
            ctx.logger.error(f"Vision model failed for {segment_key}: {e}")
            continue

        try:

            embed_response = ctx.vlm_client.embeddings.create(
                model=ctx.embedding_model,
                input=description,
                dimensions=1024,
            )
            embedding = embed_response.data[0].embedding
        except Exception as e:
            ctx.logger.error(f"Embedding failed for {segment_key}: {e}")
            continue

        ctx.logger.info(f"Embedding: {len(embedding)} dimensions")

        if not embedding:                                                                                                     
            ctx.logger.warning(f"Empty embedding for {segment_key} — skipping")
            continue
        if len(embedding) != 1024:                                                                           
            ctx.logger.warning(f"Embedding has {len(embedding)} dimensions — truncating/padding to 1024")
            embedding = (embedding + [0.0] * 1024)[:1024]

        try:
            vastdb_session = connect_vastdb(ctx)
            with vastdb_session.transaction() as tx:
                table = tx.bucket(ctx.vastdb_bucket).schema(ctx.vastdb_schema).table(ctx.vastdb_table)
                
                existing = table.select().read_all()                                                                                                                                        
                existing_keys = existing["segment_key"].to_pylist() if len(existing) > 0 else []                                                                                            
                if segment_key in existing_keys:                                                                                                                                            
                    ctx.logger.info(f"Segment already in VastDB, skipping: {segment_key}")                                                                                                  
                    results.append(segment_key)                                                                                                                                             
                    continue

                row = pa.table({
                    "segment_key":      [segment_key],
                    "source_video":     [source_key],
                    "segment_number":   pa.array([segment_keys.index(segment_key) + 1], type=pa.int32()),
                    "total_segments":   pa.array([len(segment_keys)], type=pa.int32()),
                    "segment_duration": pa.array([float(data.get("segment_duration", 5))], type=pa.float32()),
                    "description":      [description],
                    "embedding":        [embedding],
                }, schema=pa.schema([
                    ("segment_key",      pa.utf8()),
                    ("source_video",     pa.utf8()),
                    ("segment_number",   pa.int32()),
                    ("total_segments",   pa.int32()),
                    ("segment_duration", pa.float32()),
                    ("description",      pa.utf8()),
                    ("embedding",        pa.list_(pa.field("item", pa.float32(), nullable=False), 1024)),
                ]))
                table.insert(row)
                ctx.logger.info(f"Written to VastDB: {segment_key}")

        except Exception as e:
            ctx.logger.error(f"VastDB write failed for {segment_key}: {e}")
            continue

        results.append(segment_key)
    return results
