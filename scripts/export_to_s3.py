"""
NexaPlay Dashboard Exporter
---------------------------
Uploads the Grafana dashboard JSON to an S3 bucket so it is backed up
outside the local Docker environment and can be retrieved by any team
member or CI pipeline.

Credentials and bucket name are read from environment variables (or a
.env file in the project root). Never hard-code credentials here.

Usage:
    python scripts/export_to_s3.py

Required environment variables (set in .env or the shell):
    AWS_ACCESS_KEY_ID       — access key for the nexaplay-dashboard-exporter IAM user
    AWS_SECRET_ACCESS_KEY   — secret key for the same user
    AWS_REGION              — e.g. us-east-1
    S3_BUCKET_NAME          — e.g. j0nes-osei-nexaplay-dashboards
"""

import os
import sys
import json
import pathlib

# Load .env file if python-dotenv is available; silently skip if not installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import boto3
from botocore.exceptions import BotoCoreError, ClientError

# ── Configuration ─────────────────────────────────────────────────────────────

DASHBOARD_PATH = pathlib.Path(__file__).parent.parent / "grafana" / "dashboards" / "nexaplay-overview.json"
S3_KEY         = "dashboards/nexaplay-overview.json"

REQUIRED_ENV = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "S3_BUCKET_NAME"]


def check_env() -> dict:
    """Validate all required environment variables are present."""
    missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
    if missing:
        print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        print("        Set them in your .env file or export them in your shell.")
        sys.exit(1)
    return {k: os.environ[k] for k in REQUIRED_ENV}


def validate_json(path: pathlib.Path) -> None:
    """Confirm the dashboard file is valid JSON before uploading."""
    try:
        with open(path) as f:
            json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Dashboard file is not valid JSON: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"[ERROR] Dashboard file not found: {path}")
        sys.exit(1)


def upload(env: dict) -> None:
    """Upload the dashboard JSON to S3."""
    bucket = env["S3_BUCKET_NAME"]
    region = env["AWS_REGION"]

    s3 = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=env["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=env["AWS_SECRET_ACCESS_KEY"],
    )

    print(f"[INFO] Uploading {DASHBOARD_PATH.name} → s3://{bucket}/{S3_KEY}")

    try:
        s3.upload_file(
            Filename=str(DASHBOARD_PATH),
            Bucket=bucket,
            Key=S3_KEY,
            ExtraArgs={"ContentType": "application/json"},
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        msg  = e.response["Error"]["Message"]
        print(f"[ERROR] S3 upload failed ({code}): {msg}")
        sys.exit(1)
    except BotoCoreError as e:
        print(f"[ERROR] AWS connection error: {e}")
        sys.exit(1)

    print(f"[OK]   Upload complete.")
    print(f"       Verify with: aws s3 ls s3://{bucket}/dashboards/")


def main():
    print("=== NexaPlay Dashboard Exporter ===")
    env = check_env()
    validate_json(DASHBOARD_PATH)
    upload(env)


if __name__ == "__main__":
    main()
