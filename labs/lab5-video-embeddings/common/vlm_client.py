import os

from openai import OpenAI


def init_vlm_client(ctx, secrets):
    vlm_api_key = secrets.get("LLM_API_KEY", "")
    ctx.vision_model = os.environ.get("VISION_MODEL", "")
    ctx.embedding_model = os.environ.get("EMBEDDING_MODEL", "")
    ctx.summary_model = os.environ.get("SUMMARY_MODEL", "")
    ctx.max_tokens = int(os.environ.get("MAX_TOKENS", "512"))

    client = OpenAI(
        base_url=os.environ.get("VLM_ENDPOINT"),
        api_key=vlm_api_key or "none",
    )
    ctx.logger.info(f"✅ VLM client initialized | vision={ctx.vision_model} | embedding={ctx.embedding_model}")
    return client
