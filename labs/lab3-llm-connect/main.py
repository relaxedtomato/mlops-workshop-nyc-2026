import os
import boto3
from common.config_utils import validate_config
from common.handler_utils import parse_s3_event
from common.llm_client import LLMClient


def init(ctx):
    secrets = ctx.secrets.get("secrets", {})

    # TODO (Step 2a): Call validate_config() from common.config_utils to check required
    #                env vars and secrets are set. Then initialize the S3 client using
    #                credentials from ctx.secrets and env vars S3_ENDPOINT_URL, S3_REGION.
    #                Store as ctx.s3_client.

    # TODO (Step 3a): Initialize the LLM client using LLMClient.
    #                Use LLM_ENDPOINT, MODEL_NAME, MAX_TOKENS, and LLM_API_KEY.
    #                Store as ctx.llm_client.


def handler(ctx, event):
    ctx.logger.info("ℹ️ Handler invoked")

    # TODO (Step 1a): Parse the S3 event using parse_s3_event(event).
    #                Log the bucket and key. Return early if no records found.

    # TODO (Step 2b): Fetch the file from S3 using ctx.s3_client.get_object().
    #                Decode the body content to utf-8.

    # TODO (Step 3c): Call llm_summary(ctx, content), log the result, and return.


def llm_summary(ctx, content):
    # TODO (Step 3b): Return ctx.llm_client.summarize(content).
    pass
