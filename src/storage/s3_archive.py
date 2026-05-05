"""S3 access for raw GitHub payload archive and generated reports."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

import boto3

from src.collectors.normalizer import flatten_for_analytics
from src.common.dates import date_partition


class RawArchive:
    def __init__(self, bucket: str) -> None:
        self._bucket = bucket
        self._s3 = boto3.client("s3")

    def put_payload(
        self,
        when: datetime,
        repo_full_name: str,
        kind: str,
        payload: list[dict[str, Any]] | dict[str, Any],
    ) -> str:
        parts = date_partition(when)
        repo_safe = repo_full_name.replace("/", "_")
        key = (
            f"github/year={parts['year']}/month={parts['month']}/day={parts['day']}"
            f"/repo={repo_safe}/{kind}.json"
        )
        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=json.dumps(payload).encode("utf-8"),
            ContentType="application/json",
        )
        return key


class ProcessedArchive:
    """Writes flattened activity records as newline-delimited JSON for Athena.

    Records are grouped by (activity_date, repo) so each S3 object lands in the
    correct date partition - critical for Athena partition pruning.
    """

    PREFIX = "processed/github/activity"

    def __init__(self, bucket: str) -> None:
        self._bucket = bucket
        self._s3 = boto3.client("s3")

    def put_records(self, records: list[dict[str, Any]]) -> dict[str, str]:
        if not records:
            return {}

        # Group by (activity_date, repo) so each S3 object stays small and
        # belongs to one logical batch. Partition path uses only date keys -
        # `repo` is kept as a data column so it doesn't collide with a Hive
        # partition column of the same name (Athena rejects that as a
        # duplicate-column schema).
        groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for r in records:
            groups[(r["activity_date"], r["repo"])].append(r)

        keys_written: dict[str, str] = {}
        for (date, repo), group in groups.items():
            year, month, day = date.split("-")
            key = (
                f"{self.PREFIX}/year={year}/month={month}/day={day}"
                f"/activity-{uuid.uuid4().hex[:8]}.jsonl"
            )
            body = "\n".join(
                json.dumps(flatten_for_analytics(r)) for r in group
            ).encode("utf-8")
            self._s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=body,
                ContentType="application/x-ndjson",
            )
            keys_written[f"{date}#{repo}"] = key
        return keys_written


class ReportsArchive:
    def __init__(self, bucket: str) -> None:
        self._bucket = bucket
        self._s3 = boto3.client("s3")

    def put_weekly(
        self,
        username: str,
        end_date: str,
        report_json: dict[str, Any],
        report_markdown: str,
    ) -> tuple[str, str]:
        year = end_date[:4]
        prefix = f"reports/user={username}/year={year}/end={end_date}"
        json_key = f"{prefix}/report.json"
        md_key = f"{prefix}/report.md"
        self._s3.put_object(
            Bucket=self._bucket,
            Key=json_key,
            Body=json.dumps(report_json, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        self._s3.put_object(
            Bucket=self._bucket,
            Key=md_key,
            Body=report_markdown.encode("utf-8"),
            ContentType="text/markdown",
        )
        return json_key, md_key
