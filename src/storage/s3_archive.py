"""S3 access for raw GitHub payload archive and generated reports."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import boto3

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
