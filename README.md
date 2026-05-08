# MLOps Workshop Lab Guide — NYC, May 11, 2026

**VAST DataEngine** — serverless functions, S3 event triggers, LLM/VLM integration, VastDB, and video semantic search (VSS).

## What You'll Build

An end-to-end video semantic search (VSS) pipeline on VAST DataEngine:
- S3-triggered video ingestion (segmentation → VLM reasoning → embedding → VastDB write)
- FastAPI search endpoint (embed query → vector search → LLM synthesis)
- Optionally: one of three autonomous agents (triage, Q&A, or pipeline health monitor)

## Schedule

| Lab | Title |
|-----|-------|
| [Lab 1](labs/lab1-hello-world/) | Hello Vast Data |
| [Lab 2](labs/lab2-s3-connect/) | Connect to S3 |
| [Lab 3](labs/lab3-llm-connect/) | Read from S3 + LLM Summarize |
| [Lab 4](labs/lab4-video-ingest/) | Video Ingest |
| [Lab 5](labs/lab5-video-embeddings/) | VLM + VastDB |
| Lab 6 | Search Endpoint |
| CYOA | Agent Offramp |

## What You'll Learn

1. Write and deploy a DataEngine serverless function (init/handler model)
2. Connect a function to S3 event triggers using CloudEvents
3. Call external LLM APIs from a DataEngine function with secret management
4. Build a video ingestion pipeline (segment → embed → reason)
5. Write structured data to VastDB from a pipeline function
6. Expose a semantic video search endpoint via FastAPI

## Prerequisites

- Python (intermediate)
- Basic S3/object storage concepts
- Familiarity with REST APIs and API keys
- No prior DataEngine experience required

> **The lab environment is provided** — no local installs required. All tools (`vastde` CLI, Docker, Python 3.10+) are pre-configured on your workshop VM.

## Verify Setup
1. Load the workshop environment in your browser
2. Open the terminal and run the following commands to ensure everything is connected:

```sh
vastde --version #returns a value, so its defined

vastde config view # returns configs, not empty
Tenant Name: mlops
Username: mlops-admin
Password: ***
Builder Image URL: docker.selab.vastdata.com:5000/vast-builder:latest
VMS URL: https://10.143.12.208/

vastde functions list # call is successful, `No functions available` returned
No functions available
```

3. Let's check other connections to ensure everything else is working
```sh
  s3cmd ls # lists all available buckets
```

4. Retrieve all environment variables to use within the labs.

> **TODO:** Provide a pre-filled `env.yaml` (or similar) that attendees can load into their shell session to set all required environment variables in one step. Sourcing a single file is easier than setting variables one by one.

> **TODO:** Add a per-lab env var checklist to each lab's README so attendees can confirm the variables they need are set before starting that lab.

## Resources

- [Event page](https://luma.com/h8muplvs)
- [VSS Blueprint](https://github.com/vast-data/vss-blueprint)
- [VAST Community](https://community.vastdata.com/)
