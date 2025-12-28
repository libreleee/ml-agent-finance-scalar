import os

import boto3


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL_S3", "http://seaweedfs-s3:8333"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "seaweedfs_access_key"),
        aws_secret_access_key=os.getenv(
            "AWS_SECRET_ACCESS_KEY", "seaweedfs_secret_key"
        ),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        verify=False,
    )


def parse_s3_path(s3_path: str):
    if s3_path.startswith("s3a://"):
        s3_path = s3_path[len("s3a://") :]
    elif s3_path.startswith("s3://"):
        s3_path = s3_path[len("s3://") :]
    else:
        raise ValueError(f"Unsupported S3 path: {s3_path}")

    bucket, _, key = s3_path.partition("/")
    if not bucket or not key:
        raise ValueError(f"Incomplete S3 path: {s3_path}")

    return bucket, key


def fetch_object_bytes(s3_path: str):
    bucket, key = parse_s3_path(s3_path)
    client = get_s3_client()
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()
