import os
import boto3


def init_s3_client(ctx, secrets):
    s3_access_key = secrets.get("S3_ACCESS_KEY", "")
    s3_secret_key = secrets.get("S3_SECRET_KEY", "")

    client = boto3.client(
        "s3",
        use_ssl=False,
        endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
        aws_access_key_id=s3_access_key,
        aws_secret_access_key=s3_secret_key,
        region_name=os.environ.get("S3_REGION", "us-east-1"),
        config=boto3.session.Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )
    ctx.logger.info("✅ S3 client initialized")
    return client


def download_object(s3_client, bucket, key):
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()
