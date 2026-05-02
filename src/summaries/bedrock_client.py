"""Thin Bedrock InvokeModel wrapper that returns parsed JSON."""

from __future__ import annotations

import json
from typing import Any

import boto3


class BedrockClient:
    def __init__(self, model_id: str, region: str | None = None) -> None:
        self._model_id = model_id
        self._client = boto3.client("bedrock-runtime", region_name=region)

    def invoke_json(
        self,
        system_prompt: str,
        user_payload: dict[str, Any],
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": json.dumps(user_payload, indent=2)},
                    ],
                }
            ],
        }
        resp = self._client.invoke_model(
            modelId=self._model_id,
            body=json.dumps(body).encode("utf-8"),
            contentType="application/json",
            accept="application/json",
        )
        raw = json.loads(resp["body"].read())
        text = _extract_text(raw)
        return _parse_json_strict(text)


def _extract_text(raw: dict[str, Any]) -> str:
    content = raw.get("content", [])
    for block in content:
        if block.get("type") == "text":
            return str(block.get("text", ""))
    return ""


def _parse_json_strict(text: str) -> dict[str, Any]:
    text = text.strip()
    # Strip code fences if the model added them despite instructions.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)
