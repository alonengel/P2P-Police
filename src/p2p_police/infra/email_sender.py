"""Gmail reporting (rulebook ch. 9 + Appendix A, rules 30/32-34).

Send-only by design: our OAuth flow requests ONLY gmail.send (least
privilege); the sender never reads a mailbox. Implemented over the REST API
with stdlib MIME + httpx (no heavyweight SDK): refresh the access token, then
POST the base64url message. Every call passes the gatekeeper's 'email'
service (5 rpm, daily quota, DOS lock). Secrets live OUTSIDE the repo.
"""

import base64
import json
import os
from email.message import EmailMessage
from pathlib import Path

import httpx

from p2p_police.shared.gatekeeper import ApiGatekeeper, TransientProviderError

SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"  # the ONLY scope we mint
TOKEN_URL = "https://oauth2.googleapis.com/token"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


class EmailError(Exception):
    """Report email could not be sent (auth or API failure)."""


def _load_token() -> dict:
    path = Path(os.environ.get("GMAIL_TOKEN_PATH", "token.json"))
    if not path.is_file():
        raise EmailError(f"Gmail token file not found: {path} (see Appendix A setup)")
    return json.loads(path.read_text(encoding="utf-8"))


def _access_token(token: dict) -> str:
    """Exchange the long-lived refresh token for a fresh access token."""
    try:
        response = httpx.post(
            TOKEN_URL,
            data={
                "client_id": token["client_id"],
                "client_secret": token["client_secret"],
                "refresh_token": token["refresh_token"],
                "grant_type": "refresh_token",
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except (httpx.HTTPError, KeyError) as error:
        raise TransientProviderError(f"gmail token refresh failed: {error}") from error


def _build_mime(recipient: str, subject: str, body: str, attachments: list[Path]) -> str:
    message = EmailMessage()
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    for path in attachments:
        message.add_attachment(
            path.read_bytes(), maintype="application", subtype="json", filename=path.name
        )
    return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")


def send_report(
    gatekeeper: ApiGatekeeper,
    recipient: str,
    subject: str,
    body: str,
    attachments: list[Path],
) -> str:
    """Send the machine-readable report (JSON attached, rule 33-34).

    Returns the Gmail message id. 429s surface as transient errors so the
    gatekeeper's bounded backoff handles them (never blind-retry, ch. 9).
    """

    def call() -> str:
        access = _access_token(_load_token())
        raw = _build_mime(recipient, subject, body, attachments)
        try:
            response = httpx.post(
                SEND_URL,
                json={"raw": raw},
                headers={"Authorization": f"Bearer {access}"},
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("id", "")
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 429:
                raise TransientProviderError("gmail 429 - backing off") from error
            raise EmailError(f"gmail send failed: {error}") from error
        except httpx.HTTPError as error:
            raise TransientProviderError(f"gmail network failure: {error}") from error

    return str(gatekeeper.execute("email", call))
