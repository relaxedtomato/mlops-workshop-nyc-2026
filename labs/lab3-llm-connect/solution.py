import os
import boto3
from common.handler_utils import parse_s3_event
from common.llm_client import LLMClient
from common.config_utils import validate_config


def init(ctx):
    secrets = ctx.secrets.get("secrets", {})

    validate_config(
        ctx,
        required_envs=["S3_ENDPOINT_URL", "S3_REGION", "LLM_ENDPOINT", "MODEL_NAME"],
        required_secrets=["S3_ACCESS_KEY", "S3_SECRET_KEY", "LLM_API_KEY"],
        secrets=secrets,
    )

    s3_access_key = secrets.get("S3_ACCESS_KEY", "")
    s3_secret_key = secrets.get("S3_SECRET_KEY", "")

    ctx.s3_client = boto3.client(
        's3',
        use_ssl=False,
        endpoint_url=os.environ.get('S3_ENDPOINT_URL'),
        aws_access_key_id=s3_access_key,
        aws_secret_access_key=s3_secret_key,
        region_name=os.environ.get('S3_REGION'),
        config=boto3.session.Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'}
        )
    )
    ctx.logger.info("✅ S3 client initialized")

    # LLM client
    ctx.llm_client = LLMClient(
        endpoint=os.environ.get('LLM_ENDPOINT'),
        api_key=secrets.get("LLM_API_KEY", ""),
        model=os.environ.get('MODEL_NAME', 'nvidia/llama-3.1-8b-instruct'),
        max_tokens=int(os.environ.get('MAX_TOKENS', '512')),
    )
    ctx.logger.info(f"✅ LLM client initialized → {os.environ.get('LLM_ENDPOINT')}")

def handler(ctx, event):
    ctx.logger.info("ℹ️ Handler invoked")

    s3_bucket, s3_key = parse_s3_event(event)
    if not s3_bucket:
        ctx.logger.warning("No records found in event")
        return

    ctx.logger.info(f"📦 Bucket: {s3_bucket}")
    ctx.logger.info(f"📄 Key: {s3_key}")

    ctx.logger.info("⬇️ Fetching file from S3...")
    response = ctx.s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
    content = response['Body'].read().decode('utf-8')
    ctx.logger.info(f"✅ File fetched — size: {response['ContentLength']} bytes, type: {response['ContentType']}")

    ctx.logger.info("🤖 Calling LLM for summary...")
    summary = llm_summary(ctx, content)
    ctx.logger.info(f"✅ Summary: {summary}")
    return {"bucket": s3_bucket, "key": s3_key, "summary": summary}


def llm_summary(ctx, content):
    return ctx.llm_client.summarize(content)
