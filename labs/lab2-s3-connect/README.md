# Lab 2: Connect to S3 (15 min)

## Overview

Swap your schedule trigger for an S3 element trigger, explore the DataEngine UI, and watch your function fire when a file lands in your bucket. No code changes, just wiring and observation.

```
  S3 Bucket
      │ (file upload via S3 UI)
      ▼
  Element Trigger
      │ (fires on ObjectCreated)
      ▼
  ┌─────────────────────────┐
  │   DataEngine Pipeline   │
  │  ┌─────────────────────┐│
  │  │  Function           ││
  │  │  handler(ctx, event)││ ← logs CloudEvent payload
  │  └─────────────────────┘│
  └─────────────────────────┘
      │
      ▼
   vastde logs tail
   (CloudEvent with bucket + key)
```

## Scenario

At **FrameIQ**, pipelines don't run on a clock, they react to data. A new video file lands in a bucket and the pipeline wakes up. In this lab you'll rewire your pipeline from a schedule trigger to an S3 element trigger, which is the foundation for every data pipeline you'll build in Labs 3 onwards. You'll also get a guided tour of the DataEngine UI so you know where to look when things need debugging.

> All commands run on the **workshop VM** via the terminal in your browser. Nothing runs on your laptop.

## Steps

### Step 1: Explore the DataEngine UI

Before making any changes, orient yourself in the DataEngine UI.

#### 1a. Functions view

Navigate to **DataEngine UI > Functions**. You should see your `$USER-hello-world` function from Lab 1. Spend a few minutes clicking around: open the function, look at its details, and see what information is available:

![DataEngine Functions view](function.png)

- Under `Revision Details`, the function version can be updated by changing the `Image Tag` (e.g. v1, v2, v3)

#### 1b. Pipelines view

Navigate to **DataEngine UI > Pipelines**. Click into your pipeline to see the graph, trigger linked to function. Spend a few minutes exploring the pipeline graph and the configuration panels.

![DataEngine Pipelines view](pipeline-config.png)

- Under `Function Deployment`, the function version can be updated by changing the `Revision Number` (e.g. 1, 2, 3)
- Explore the `Deployment Resources` in the configuration panel
- Check out the `YAML` to see the pipeline configuration
- The `Deploy` button will deploy the pipeline to capture any relevant changes (e.g. new trigger, function version)

#### 1c. Logs view

Navigate to **DataEngine UI > Logs**. This is where invocation traces live, you'll use this throughout the workshop. Click into a past invocation from Lab 1 and see what was logged.

![DataEngine Logs view](pipeline-logs.png)

- Click on a specific log to see what information is available
- Navigate to a specific log and view the trace details

---

### Step 2: Create an S3 element trigger

Navigate to **DataEngine UI > Triggers > Create Trigger** and fill in:

| Field | Example value |
|---|---|
| **Name** | `$USER-s3-trigger` |
| **Trigger Type** | `Element` |
| **Source View** | select your S3 bucket |
| **Element Type** | `Element Created` |

Verify via CLI:

```sh
vastde triggers list | grep $USER
```

Expected output:

```
Trigger Name               Status        Type        Description      GUID                        Updated at
------------------------------------------------------------------------------------------------------------------
$USER-s3-trigger           Ready         0xc0006...                   4d32fd72-7961-4b00-940b...  2026-03-29 21:23
```

---

### Step 3: Update the pipeline to use the new trigger

Navigate to **DataEngine UI > Pipelines** and click into your pipeline.

Remove the existing schedule trigger link and connect your new S3 trigger to the function.

Once updated, redeploy the pipeline from the UI.

---

### Step 4: What is a CloudEvent?

When a file is uploaded to your S3 bucket, a **CloudEvent** is passed to your function's `handler()`. Here's what it looks like:

```json
{
  "id": "59e46a1b-b060-49e8-8438-3dc03095a0da",
  "source": "vastdata.com:trigger1.7c99196c-6c16-4c84-b87d-c1d7861d0ba4",
  "specversion": "1.0",
  "type": "vastdata.com:Element.ObjectCreated",
  "time": "2025-10-10T13:38:09Z",
  "subject": "vastdata.com:kafka-view.default-topic",
  "datacontenttype": "application/json",
  "dataschema": null,
  "triggerext1": "cli-generated",
  "triggerext2": "test-event",
  "data": {
    "Records": [
      {
        "s3": {
          "bucket": { "name": "your-bucket-name" },
          "object": { "key": "sample.txt" }
        }
      }
    ]
  }
}

```

In Lab 3 you'll parse this payload to extract the bucket name and object key and act on the file.

---

### Step 5: Upload a file and verify

#### 5a. Upload a file

> **TODO:** Confirm how attendees access the S3 bucket in the workshop environment (portal link, credentials).

Upload the sample file to your S3 bucket:

```sh
s3cmd put ./test.md s3://<your-bucket>/test.md
```

Expected output:

```
upload: './test.md' -> 's3://<your-bucket>/test.md'  [1 of 1]
 15 of 15   100% in    0s  1548.79 B/s  done
```

#### 5b. Check the logs

Tail the pipeline logs to see the CloudEvent your function received:

```sh
vastde logs tail $USER-hello-world-pipeline \
  --function $USER-hello-world \
  --since 5m
```

You should see the CloudEvent payload:

```
2026-04-08 15:41:29.67 [$USER-hello-world] [INFO]  [user] Handler {'attributes': {'source': 'vastdata.com:$USER-s3-trigger...', 'type': 'vastdata.com:Element.ElementCreated', ...}, 'data': {'Records': [{'s3': {'bucket': {'name': 'your-bucket-name'}, 'object': {'key': 'test.md', ...}}}]}}
```

---

## Key Takeaways

- **Element triggers** fire on S3 object events (`ObjectCreated`, `ObjectDeleted`); more efficient than polling on a schedule
- **CloudEvents** are a standard envelope DataEngine uses to pass event metadata to your function; always contains the bucket name and object key
- **DataEngine UI** is your primary tool for wiring triggers to functions, monitoring pipeline status, and inspecting invocation logs
- **Event-driven vs schedule-driven**: schedules are useful for periodic jobs; event triggers are the right model when you want to react to data as it arrives

---

**Next up: [Lab 3: Read from S3 and Summarize with an LLM](../lab3-llm-connect/)**
