# Lab 4: Segment a Video (25 min)

## Overview

Build a DataEngine function that receives an S3 event when a video file is uploaded, downloads it, slices it into fixed-duration segments using moviepy, and uploads each segment back to S3, ready for downstream VLM processing.

```
  S3 Bucket
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
  S3 Bucket  (base/base_segment_001_of_N.mp4 ...)
      │
      ▼
  {"segment_keys": [...]}  ->  Lab 5 VLM
```

## Scenario

At **FrameIQ**, video files land in S3 continuously from field cameras. Before the VLM can reason about their contents, each file needs to be broken into short, manageable clips. 

In this lab you'll implement the segmentation function that sits at the front of the video pipeline: validate the incoming file, slice it into 5-second segments, upload each one back to S3 with metadata, and return a structured result dict that the downstream VLM function can consume directly via function-to-function chaining.

> All commands run on the **workshop VM** via the terminal in your browser. Nothing runs on your laptop.

## Steps

### Step 1: Add the idempotency check

Your first task is to add an idempotency guard so the function skips a video if its segments already exist, preventing duplicate work when the same file triggers the function more than once.

#### 1a. Add the skip check in `handler()`

Before the video download, add a check to skip processing if segments for this video already exist in the output bucket:

```python
output_bucket = ctx.output_bucket or bucket
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
clip = VideoFileClip(tmp_in_path)
total_duration = clip.duration
total_segments = math.ceil(total_duration / ctx.segment_duration)
ctx.logger.info(f"Video: {total_duration:.2f}s -> {total_segments} x {ctx.segment_duration}s segments")
```

#### 2b. Add the slice loop

Iterate over each segment, extract a subclip, write it to a temp file, and read the bytes:

```python
for i in range(total_segments):
    start = i * ctx.segment_duration
    end = min(start + ctx.segment_duration, total_duration)
    segment_key = f"{base}/{base}_segment_{i+1:03d}_of_{total_segments:03d}.mp4"

    sub = clip.subclip(start, end)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_out:
        tmp_out_path = tmp_out.name
    sub.write_videofile(tmp_out_path, codec="libx264", audio=False, logger=None)
    sub.close()

    with open(tmp_out_path, "rb") as f:
        segment_bytes = f.read()
```

---

### Step 3: Upload each segment to S3

For each segment, once the bytes are written to a temp file, upload it to S3 with metadata and append the key to the results list:

```python
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
result = {
    "status": "success",
    "source_bucket": bucket,
    "source_key": key,
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
docker tag $USER-s3-segment-video:latest $DE_REG_HOST/$DE_REG_USER/$USER-s3-segment-video:v1
docker push $DE_REG_HOST/$DE_REG_USER/$USER-s3-segment-video:v1
```

Create the function:

```sh
vastde functions create \
  --name $USER-s3-segment-video \
  --container-registry $DE_REG_NAME \
  --artifact-source $DE_REG_USER/$USER-s3-segment-video \
  --image-tag v1
```

Create a new S3 element trigger. Navigate to **DataEngine UI > Triggers > Create Trigger** and fill in:

| Field | Example value |
|---|---|
| **Name** | `$USER-s3-segment-video-trigger` |
| **Trigger Type** | `Element` |
| **Source View** | select your S3 bucket |
| **Element Type** | `Element Created` |

Then create and deploy the pipeline from the UI using `pipeline-config.yaml` as a reference (same flow before to deploy pipelines).

#### 4c. Upload a video and tail the logs

> **Note:** `sample.mp4` is not included in this repository. Video files are excluded from version control for licensing and distribution reasons. Do not commit or share video files publicly. A sample video is pre-loaded on your workshop VM for testing purposes only.

> **TODO:** Source a few short, royalty-free video clips to recommend to attendees or pre-load in the workshop environment

Upload the sample video to your S3 bucket:

```sh
s3cmd put sample.mp4 s3://<your-bucket>/sample.mp4
```

Tail the logs:

```sh
vastde logs tail $USER-s3-segment-video-pipeline \
  --function $USER-s3-segment-video \
  --since 5m
```

You should see:

```
2026-05-11 09:00:04.23 [alice-s3-segment-video] [INFO]  [user] Video: 30.00s -> 6 x 5s segments
2026-05-11 09:00:25.81 [alice-s3-segment-video] [INFO]  [user] ✅ Result: {'status': 'success', 'source_bucket': 'alice-videos', 'source_key': 'sample.mp4', 'output_bucket': 'alice-videos', 'segment_keys': ['sample/sample_segment_001_of_006.mp4', 'sample/sample_segment_002_of_006.mp4', 'sample/sample_segment_003_of_006.mp4', 'sample/sample_segment_004_of_006.mp4', 'sample/sample_segment_005_of_006.mp4', 'sample/sample_segment_006_of_006.mp4'], 'segment_count': 6, 'segment_duration': 5}
```

#### 4d. Confirm segments in S3

Verify the segments were uploaded correctly:

```sh
s3cmd ls s3://<your-output-bucket>/sample/ --recursive
```

> **TODO** Need to confirm output bucket creation and what to insert, could be simple as $USER-output-bucket and part of the environment variables shared

You should see segment files in the following format: `sample_segment_001_of_006.mp4`.

---

## Key Takeaways

- **Idempotency matters**: checking for existing segments before processing prevents duplicate uploads when the same S3 event fires more than once
- **Tempfiles for video processing**: moviepy needs a real file path, not a byte stream; writing to a tempfile and cleaning up after each segment keeps memory bounded
- **S3 metadata**: each segment carries `original-video`, `segment-number`, and `total-segments` as object metadata, making it queryable without reading the file
- **Function-to-function chaining**: the structured return dict (`segment_keys`, `segment_count`) is the contract for Lab 5; what this function returns is what the VLM function receives as input
- **Segment key layout**: `{base}/{base}_segment_001_of_006.mp4` groups all segments under a per-video prefix, making it easy to list or delete a full set with one S3 command

---

**Next up: [Lab 5: VLM + VastDB](../lab5-vlm-vastdb/)**
