"""Runtime configuration: env vars + cached secret fetch."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache

import boto3


@dataclass(frozen=True)
class Config:
    github_username: str
    activity_table: str
    reports_table: str
    raw_archive_bucket: str
    reports_bucket: str
    bedrock_model_id: str
    github_secret_arn: str
    sender_email: str
    recipient_email: str
    region: str


def load() -> Config:
    return Config(
        github_username=_require("GITHUB_USERNAME"),
        activity_table=_require("ACTIVITY_TABLE"),
        reports_table=_require("REPORTS_TABLE"),
        raw_archive_bucket=_require("RAW_ARCHIVE_BUCKET"),
        reports_bucket=_require("REPORTS_BUCKET"),
        bedrock_model_id=_require("BEDROCK_MODEL_ID"),
        github_secret_arn=_require("GITHUB_SECRET_ARN"),
        sender_email=_require("SENDER_EMAIL"),
        recipient_email=_require("RECIPIENT_EMAIL"),
        region=os.environ.get("AWS_REGION", "us-east-1"),
    )


def _require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"missing required env var: {key}")
    return value


@lru_cache(maxsize=1)
def github_token(secret_arn: str) -> str:
    """Fetch the GitHub PAT from Secrets Manager. Cached per warm Lambda."""
    # Local dev shortcut: if GITHUB_TOKEN is set, use it directly.
    direct = os.environ.get("GITHUB_TOKEN")
    if direct:
        return direct

    client = boto3.client("secretsmanager")
    resp = client.get_secret_value(SecretId=secret_arn)
    raw = resp["SecretString"]
    # Accept either a JSON object {"token": "..."} or a bare string.
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "token" in parsed:
            return str(parsed["token"])
    except json.JSONDecodeError:
        pass
    return raw
