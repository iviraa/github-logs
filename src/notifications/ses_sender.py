"""Send a rendered HTML+text email via SES."""

from __future__ import annotations

import boto3


class SesSender:
    def __init__(self, sender_email: str, region: str | None = None) -> None:
        self._sender = sender_email
        self._client = boto3.client("ses", region_name=region)

    def send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> str:
        resp = self._client.send_email(
            Source=self._sender,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject[:200], "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                },
            },
        )
        return str(resp.get("MessageId", ""))
