"""S3-compatible storage abstraction.
Swap providers by changing S3_ENDPOINT_URL, S3_ACCESS_KEY, S3_SECRET_KEY in env."""

import boto3
from botocore.config import Config as BotoConfig
from app.core.config import settings


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )


def _ensure_bucket():
    client = _get_s3_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
    except Exception:
        client.create_bucket(Bucket=settings.S3_BUCKET_NAME)


async def upload_file_to_s3(file_bytes: bytes, key: str, content_type: str) -> str:
    _ensure_bucket()
    client = _get_s3_client()
    client.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}/{key}"


async def get_file_from_s3(key: str) -> bytes:
    client = _get_s3_client()
    response = client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
    return response["Body"].read()
