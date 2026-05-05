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
| Lab 5 | VLM + VastDB |
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

## Resources

- [Event page](https://luma.com/h8muplvs)
- [VSS Blueprint](https://github.com/vast-data/vss-blueprint)
- [VAST Community](https://community.vastdata.com/)
