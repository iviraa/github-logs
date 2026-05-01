"""DynamoDB access for activity records and generated reports."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from src.collectors.normalizer import to_ddb_keys


class ActivityStore:
    def __init__(self, table_name: str) -> None:
        self._table = boto3.resource("dynamodb").Table(table_name)

    def put_activity_batch(self, username: str, records: Iterable[dict[str, Any]]) -> int:
        count = 0
        with self._table.batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
            for record in records:
                keys = to_ddb_keys(username, record)
                item = {**keys, "username": username, **record}
                batch.put_item(Item=item)
                count += 1
        return count

    def query_range(
        self, username: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Inclusive of start, exclusive of end+1day. Both dates as YYYY-MM-DD."""
        pk = f"USER#{username}"
        sk_lo = f"ACTIVITY#{start_date}"
        sk_hi = f"ACTIVITY#{end_date}~"  # '~' sorts after digits and '#'
        items: list[dict[str, Any]] = []
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key("PK").eq(pk) & Key("SK").between(sk_lo, sk_hi),
        }
        while True:
            resp = self._table.query(**kwargs)
            items.extend(resp.get("Items", []))
            lek = resp.get("LastEvaluatedKey")
            if not lek:
                return items
            kwargs["ExclusiveStartKey"] = lek


class ReportStore:
    def __init__(self, table_name: str) -> None:
        self._table = boto3.resource("dynamodb").Table(table_name)

    def put_weekly(
        self,
        username: str,
        start_date: str,
        end_date: str,
        report_json_s3_key: str,
        report_md_s3_key: str,
        metrics: dict[str, int],
    ) -> None:
        self._table.put_item(
            Item={
                "PK": f"USER#{username}",
                "SK": f"REPORT#weekly#{start_date}#{end_date}",
                "username": username,
                "report_type": "weekly",
                "start_date": start_date,
                "end_date": end_date,
                "report_json_s3_key": report_json_s3_key,
                "report_markdown_s3_key": report_md_s3_key,
                "metrics": metrics,
            }
        )
