"""Publish a Markdown summary to SNS as an email."""

from __future__ import annotations

import boto3


class SnsNotifier:
    def __init__(self, topic_arn: str) -> None:
        self._topic_arn = topic_arn
        self._client = boto3.client("sns")

    def publish(self, subject: str, body: str) -> str:
        # SNS subjects are limited to 100 chars and printable ASCII.
        safe_subject = subject[:100]
        resp = self._client.publish(
            TopicArn=self._topic_arn,
            Subject=safe_subject,
            Message=body,
        )
        return str(resp.get("MessageId", ""))
