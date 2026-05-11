# Lab 4: Segment a Video (25 min)

## Overview

Build a function that receives an S3 event when a video file is uploaded, downloads it, slices it into fixed-duration segments using `moviepy`, and uploads each segment back to S3, ready for downstream VLM processing.

```
  S3 Bucket [s3://$USER-video]
      │ (.mp4 upload)
      ▼
  Element Trigger
      │ (CloudEvent)
      ▼
  ┌────────────────────────────────────┐
  │   DataEngine Function              │
  │                                    │
  │  handler()                         │
  │   ├─ validate .mp4 + skip guard    │
  │   ├─ download video bytes          │
  │   └─ segment_and_upload()          │
  │        ├─ moviepy slice loop       │
  │        └─ put_object per segment   │
  └────────────────────────────────────┘
      │
      ▼
  S3 Bucket [s3://$USER-video-segments] (base/base_segment_001_of_N.mp4 ...)
      │
      ▼
  {"segment_keys": [...]}  ->  Lab 5 VLM
```

## Scenario

At **FrameIQ**, video files land in S3 continuously from field cameras. Before the VLM can reason about their contents, each file needs to be broken into short, manageable clips.

In this lab you'll implement the segmentation function that sits at the front of the video ingestion pipeline: validate the incoming file, slice it into 5-second segments, upload each one back to S3 with metadata, and return that the downstream function can consume directly via function-to-function chaining.


## Steps

> All commands run on the **workshop VM** via the terminal in your browser. Nothing runs on your laptop.

### Step 1: Add the idempotency check

Your first task is to add a check so the function skips a video if its segments already exist, preventing duplicate work when the same file triggers the function more than once.

#### Add the skip check in `handler()`

Before the video download, add a check to skip processing if segments for this video already exist in the output bucket:

```python
# labs/lab4-video-ingest/main.py
output_bucket = ctx.output_bucket or s3_bucket
base = os.path.splitext(filename)[0]
segment_prefix = f"{base}/"

resp = ctx.s3_client.list_objects_v2(Bucket=output_bucket, Prefix=segment_prefix, MaxKeys=1)

if resp.get("Contents"):
    return {"status": "skipped", "reason": "Segments already exist"}
```

---

### Step 2: Implement the moviepy slice loop in `segment_and_upload()`

The starter provides a `segment_and_upload()` function with file setup and cleanup already handled.

Your task is to load the video, calculate how many segments to create, and slice it into clips.

#### 2a. Load the clip and calculate segment count

Load the video from the temp file, calculate its total duration, and determine how many fixed-length segments it will produce:

```python
# labs/lab4-video-ingest/main.py
clip = VideoFileClip(tmp_in_path)
total_duration = clip.duration
total_segments = math.ceil(total_duration / ctx.segment_duration)
ctx.logger.info(f"Video: {total_duration:.2f}s -> {total_segments} x {ctx.segment_duration}s segments")
```

#### 2b. Add the slice loop

Iterate over each segment, extract a subclip, write it to a temp file, and read the bytes:

```python
# labs/lab4-video-ingest/main.py
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
```

---

### Step 3: Upload each segment to S3

For each segment, once the bytes are written to a temp file, upload it to S3 with metadata and append the key to the results list:

```python
# labs/lab4-video-ingest/main.py
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
```

---

### Step 4: Return the structured result and verify end to end

#### 4a. Return the result dict from `handler()`

After `segment_and_upload()` returns, add:

```python
# labs/lab4-video-ingest/main.py
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
```

#### 4b. Build and deploy

Follow the same pattern as previous labs. Build, tag, and push:

```sh
vastde functions build $USER-s3-segment-video
```

```sh
docker tag $USER-s3-segment-video:latest $DE_REG_HOST/$DE_REG_USER/$USER-s3-segment-video:v1
```

```sh
docker push $DE_REG_HOST/$DE_REG_USER/$USER-s3-segment-video:v1
```

⏱️ This step takes a moment.

Create the function:

```sh
vastde functions create \
  --name $USER-s3-segment-video \
  --container-registry $DE_REG_NAME \
  --artifact-source $DE_REG_USER/$USER-s3-segment-video \
  --image-tag v1
```

Create a new S3 element trigger. Navigate to **DataEngine UI > Manage Elements > Triggers > Create Trigger** and fill in:

| Field | Value |
|---|---|
| **Name** | `$USER-s3-segment-video-trigger` |
| **Trigger Type** | `Element` |
| **Source View** | select your `$USER-video` bucket |
| **Element Type** | `Element Created` |
| **Description** | fires when a new video file is uploaded |

Before deploying, set up your config and secrets using `$USER-mlops-config.yaml`. Skip any file that already exists (created by `setup.py`):

```sh
cp -n config.example.yaml config.yaml
cp -n secrets.example.yaml secrets.yaml
```

In `config.yaml`:

```yaml
# config.yaml

# S3
S3_ENDPOINT_URL: "http://<your-s3-endpoint>"
S3_REGION: "<your-region>"
OUTPUT_BUCKET: "$USER-video-segments"
SEGMENT_DURATION: "5"

# VLM (used in Lab 5 — set now so the pipeline does not need reconfiguring)
VLM_ENDPOINT: "<your-vlm-endpoint>"
VISION_MODEL: "<your-vision-model>"
EMBEDDING_MODEL: "<your-embedding-model>"
SUMMARY_MODEL: ""
MAX_TOKENS: "512"

# VastDB (used in Lab 5 — set now so the pipeline does not need reconfiguring)
VASTDB_ENDPOINT: "<your-vastdb-endpoint>"
VASTDB_BUCKET: "<your-vastdb-bucket>"
VASTDB_SCHEMA: "video_embeddings"
VASTDB_TABLE: "segments"
```

In `secrets.yaml`:

```yaml
# secrets.yaml
secrets:
  S3_ACCESS_KEY: "<your-s3-access-key>"
  S3_SECRET_KEY: "<your-s3-secret-key>"
  VLM_API_KEY: "<your-vlm-api-key>"
  VASTDB_ACCESS_KEY: "<your-vastdb-access-key>"
  VASTDB_SECRET_KEY: "<your-vastdb-secret-key>"
```

Then create and deploy the pipeline from the UI using `pipeline-config.yaml` as a reference. Fill in:

| Field | Value |
|---|---|
| **Name** | `$USER-video-ingest-pipeline` |
| **Description** | S3-triggered pipeline that segments uploaded .mp4 files into 5-second clips |

Add the environment variables from `config.yaml` under `Environment Variables` and upload `secrets.yaml` under `Secrets`.

> **Note:** If the `.yaml` file upload does not work in the UI, copy the values manually.

Once configured, $USER-s3-segment-video-trigger --> $USER-s3-segment-video connected, click Deploy and wait for pipeline changes from `In Progress` --> `Running` status before proceeding.

⏱️ This step takes a moment.

#### 4c. Upload a video and tail the logs

Download a sample video using one of the following (Pexels, free to use):

> **Note:** Keep videos under 30 seconds, 640x360 or lower resolution, H.264 MP4 format. Each segment requires a VLM call in Lab 5 — longer or higher-resolution videos mean more segments, more memory, and more wait time.

```sh
# Option 1
# in /lab4-video-ingest
curl -L -o sample.mp4 "https://www.pexels.com/download/video/29598934/?fps=30.0&h=360&w=640"

# Option 2
# in /lab4-video-ingest
curl -L -o sample.mp4 "https://www.pexels.com/download/video/29825273/?fps=30.0&h=360&w=640"
```

Before uploading, confirm the pipeline is in `Ready` status:

```sh
vastde pipelines list | grep $USER
```

Upload the sample video to your S3 bucket:

```sh
# in /lab4-video-ingest
s3cmd put sample.mp4 s3://$USER-video/sample.mp4
```

> **Tip:** To re-run the pipeline with the same video, remove the existing segments first so the idempotency check does not skip it:

```sh
s3cmd rm s3://$USER-video-segments/sample/ --recursive
```

Tail the logs:

```sh
vastde logs tail $USER-video-ingest-pipeline \
  --function $USER-s3-segment-video \
  --since 5m
```

⏱️ This step takes a moment.

You should see:

```
2026-05-11 09:00:04.23 [alice-s3-segment-video] [INFO]  [user] Video: 30.00s -> 6 x 5s segments
2026-05-11 09:00:25.81 [alice-s3-segment-video] [INFO]  [user] ✅ Result: {'status': 'success', 'source_bucket': 'alice-videos', 'source_key': 'sample.mp4', 'output_bucket': 'alice-videos', 'segment_keys': ['sample/sample_segment_001_of_006.mp4', 'sample/sample_segment_002_of_006.mp4', 'sample/sample_segment_003_of_006.mp4', 'sample/sample_segment_004_of_006.mp4', 'sample/sample_segment_005_of_006.mp4', 'sample/sample_segment_006_of_006.mp4'], 'segment_count': 6, 'segment_duration': 5}
```

#### 4d. Confirm segments in S3

Verify the segments were uploaded correctly:

```sh
s3cmd ls s3://$USER-video-segments/
```

Expected output:

```
DIR  s3://$USER-video-segments/sample/
```

Drill into the prefix to see the individual segments:

```sh
s3cmd ls s3://$USER-video-segments/sample/
```

Expected output:

```
2026-05-09 11:55        71705  s3://$USER-video-segments/sample_30s/sample_30s_segment_001_of_007.mp4
2026-05-09 11:55       106846  s3://$USER-video-segments/sample_30s/sample_30s_segment_002_of_007.mp4
2026-05-09 11:55       172550  s3://$USER-video-segments/sample_30s/sample_30s_segment_003_of_007.mp4
2026-05-09 11:55        86565  s3://$USER-video-segments/sample_30s/sample_30s_segment_004_of_007.mp4
2026-05-09 11:55       101016  s3://$USER-video-segments/sample_30s/sample_30s_segment_005_of_007.mp4
2026-05-09 11:55       164014  s3://$USER-video-segments/sample_30s/sample_30s_segment_006_of_007.mp4
```

---

## Key Takeaways

- Check for existing output before processing as a precaution if the same S3 event fires more than once
- Video processing needs real file paths: write to a tempfile, process, clean up
- The return value of your function is the input to the next function in the pipeline

---

**Next up: [Lab 5: VLM + VastDB](../lab5-video-embeddings/)**
