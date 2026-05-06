"""Send a rendered HTML+text email via SES with the logo embedded as a MIME
inline attachment (cid reference)."""

from __future__ import annotations

from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3

from src.notifications.assets import GITHUB_LOGO_CID, GITHUB_LOGO_PNG


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
        # multipart/related so HTML can reference inline assets via cid:
        root = MIMEMultipart("related")
        root["Subject"] = subject[:200]
        root["From"] = self._sender
        root["To"] = to_email

        # multipart/alternative inside it for text + html bodies.
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(text_body, "plain", "utf-8"))
        alt.attach(MIMEText(html_body, "html", "utf-8"))
        root.attach(alt)

        # Inline GitHub logo, referenced from HTML as src="cid:github-logo".
        img = MIMEImage(GITHUB_LOGO_PNG, _subtype="png")
        img.add_header("Content-ID", f"<{GITHUB_LOGO_CID}>")
        img.add_header("Content-Disposition", "inline", filename="github-logo.png")
        root.attach(img)

        resp = self._client.send_raw_email(
            Source=self._sender,
            Destinations=[to_email],
            RawMessage={"Data": root.as_string()},
        )
        return str(resp.get("MessageId", ""))
