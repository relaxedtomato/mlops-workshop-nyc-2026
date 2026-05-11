# Lab 6: Search Video (15 min)

## Overview

Run a semantic search against the VastDB segments table populated in Lab 5. A standalone Python script embeds your natural language query and ranks all stored segments by cosine similarity.

```
  Natural language query
      │
      ▼
  ┌──────────────────────────────────────┐
  │   search_vastdb.py (CLI)             │
  │                                      │
  │   embed_query() → vector[1024]       │
  │   cosine_similarity() per segment    │
  │   filter score >= 0.4                │
  └──────────────────────────────────────┘
      │
      ▼
  Top 3 matching segments (JSON)
```

## Scenario

You have ingested video, segmented it, and stored embeddings in VastDB through Labs 4 and 5. Now it is time to query. In this lab you will run `search_vastdb.py` to search segments by meaning, not metadata.

> All commands run on the **workshop VM** via the terminal in your browser. Nothing runs on your laptop.

## Steps

### Step 1: Set up the environment

Navigate to the lab directory and install dependencies:

```sh
# labs/lab6-video-search/
cd labs/lab6-video-search
pip install -r requirements.txt
```

Copy the environment template. Skip this step if `.env` already exists (created by `setup.py`):

```sh
cp -n example.env .env
```

Open `.env` and fill in your credentials. The embedding and VastDB endpoints are the same ones used in Lab 5:

```sh
# labs/lab6-video-search/.env
EMBEDDING_ENDPOINT=http://<embedding-endpoint>
EMBEDDING_MODEL=qwen/qwen3-embedding-4b
LLM_API_KEY=<your-llm-key>

VASTDB_ENDPOINT=http://<vastdb-endpoint>
VASTDB_BUCKET=<your-vastdb-bucket>
VASTDB_ACCESS_KEY=<your-access-key>
VASTDB_SECRET_KEY=<your-secret-key>
```

Load the variables:

```sh
export $(grep -v '^#' .env | xargs)
```

### Step 2: Run a search query

Run the script with a natural language query:

```sh
python3 search_vastdb.py "pine tree"
```

```json
Using the number of endpoints as a heuristic for concurrency.
[
  {
    "segment_key": "sample_30s/sample_30s_segment_006_of_007.mp4",
    "source_video": "sample_30s.mp4",
    "description": "The title \"Big Buck Bunny\" is displayed in large white letters over a grassy landscape featuring a burrow in the center.",
    "score": 0.5079
  },
  {
    "segment_key": "sample_30s/sample_30s_segment_002_of_007.mp4",
    "source_video": "sample_30s.mp4",
    "description": "A panning shot reveals a lush, green landscape with stylized trees and changing foreground details, starting with a clear view of the trees, then a small bush moving left, and finally displaying more foreground grass in a slow pan or zoom out.",
    "score": 0.4931
  },
  {
    "segment_key": "sample_30s/sample_30s_segment_003_of_007.mp4",
    "source_video": "sample_30s.mp4",
    "description": "The video features a serene computer-generated landscape that transitions from a wide view of a grassy field with pine trees to a close-up of a peaceful stream bank.",
    "score": 0.4897
  }
]
```

Results with a score below `0.4` are filtered out. If nothing matches your query you will see an empty array (`[]`).

### Step 3: Try different queries

Try a few more queries and compare the scores:

```sh
python3 search_vastdb.py "bunny in a field"
python3 search_vastdb.py "close-up of an animal"
python3 search_vastdb.py "bird flying"
```

Scores closer to `1.0` indicate stronger semantic similarity. A score below `0.4` typically means the segment has little relation to the query.

## Key Takeaways

- Semantic search matches meaning, not keywords
- A higher score means stronger semantic similarity; a lower score means less relation
