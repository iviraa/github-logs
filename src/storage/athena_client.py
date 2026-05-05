"""Thin Athena client: run a query, poll to completion, return rows as dicts."""

from __future__ import annotations

import time
from typing import Any

import boto3


class AthenaClient:
    def __init__(self, workgroup: str, database: str, region: str | None = None) -> None:
        self._workgroup = workgroup
        self._database = database
        self._client = boto3.client("athena", region_name=region)

    def query(self, sql: str, max_wait_seconds: int = 90) -> list[dict[str, Any]]:
        resp = self._client.start_query_execution(
            QueryString=sql,
            WorkGroup=self._workgroup,
            QueryExecutionContext={"Database": self._database},
        )
        qid = resp["QueryExecutionId"]

        deadline = time.time() + max_wait_seconds
        while time.time() < deadline:
            time.sleep(1.0)
            r = self._client.get_query_execution(QueryExecutionId=qid)
            state = r["QueryExecution"]["Status"]["State"]
            if state == "SUCCEEDED":
                break
            if state in ("FAILED", "CANCELLED"):
                reason = r["QueryExecution"]["Status"].get("StateChangeReason", "")
                raise RuntimeError(f"athena query {state}: {reason}")
        else:
            self._client.stop_query_execution(QueryExecutionId=qid)
            raise TimeoutError(f"athena query did not complete within {max_wait_seconds}s")

        return self._collect_rows(qid)

    def _collect_rows(self, qid: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        cols: list[str] | None = None
        next_token: str | None = None
        while True:
            kwargs: dict[str, Any] = {"QueryExecutionId": qid, "MaxResults": 1000}
            if next_token:
                kwargs["NextToken"] = next_token
            resp = self._client.get_query_results(**kwargs)
            data = resp["ResultSet"]
            if cols is None:
                cols = [c["Name"] for c in data["ResultSetMetadata"]["ColumnInfo"]]
                # First row of the first page is the header; skip it.
                page_rows = data["Rows"][1:]
            else:
                page_rows = data["Rows"]
            for row in page_rows:
                values = [c.get("VarCharValue") for c in row.get("Data", [])]
                rows.append(dict(zip(cols, values, strict=False)))
            next_token = resp.get("NextToken")
            if not next_token:
                return rows
