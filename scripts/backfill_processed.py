"""One-shot: read every activity record out of DynamoDB and write it to the
processed S3 tier. Use this once after first deploy; regular collector runs
keep the tier in sync going forward.

Usage:
    cd github-logs
    source .venv/bin/activate
    AWS_REGION=us-east-2 \
    ACTIVITY_TABLE=github-logs-activity \
    RAW_ARCHIVE_BUCKET=$(aws cloudformation describe-stacks \
        --stack-name github-logs --region us-east-2 \
        --query "Stacks[0].Outputs[?OutputKey=='RawArchiveBucketName'].OutputValue" \
        --output text) \
    GITHUB_USERNAME=iviraa \
    python -m scripts.backfill_processed
"""

from __future__ import annotations

import os
import sys
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from src.storage.s3_archive import ProcessedArchive


def _scan_user_activity(table_name: str, username: str) -> list[dict[str, Any]]:
    table = boto3.resource("dynamodb").Table(table_name)
    items: list[dict[str, Any]] = []
    kwargs: dict[str, Any] = {
        "KeyConditionExpression": Key("PK").eq(f"USER#{username}"),
    }
    while True:
        resp = table.query(**kwargs)
        items.extend(resp.get("Items", []))
        lek = resp.get("LastEvaluatedKey")
        if not lek:
            return items
        kwargs["ExclusiveStartKey"] = lek


def main() -> int:
    table_name = os.environ.get("ACTIVITY_TABLE")
    bucket = os.environ.get("RAW_ARCHIVE_BUCKET")
    username = os.environ.get("GITHUB_USERNAME")
    if not (table_name and bucket and username):
        print(
            "missing env vars: ACTIVITY_TABLE, RAW_ARCHIVE_BUCKET, GITHUB_USERNAME",
            file=sys.stderr,
        )
        return 1

    print(f"scanning {table_name} for USER#{username}")
    records = _scan_user_activity(table_name, username)
    print(f"found {len(records)} records")
    if not records:
        return 0

    # DynamoDB returns Decimal for numeric fields; cast back to int/float
    # so the JSON serializer in ProcessedArchive doesn't choke.
    cleaned = [_decimals_to_native(r) for r in records]

    archive = ProcessedArchive(bucket)
    keys = archive.put_records(cleaned)
    print(f"wrote {len(keys)} processed partitions to s3://{bucket}/{archive.PREFIX}/")
    for k, v in sorted(keys.items()):
        print(f"  {k}  ->  {v}")
    return 0


def _decimals_to_native(obj: Any) -> Any:
    from decimal import Decimal

    if isinstance(obj, list):
        return [_decimals_to_native(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _decimals_to_native(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    return obj


if __name__ == "__main__":
    sys.exit(main())
