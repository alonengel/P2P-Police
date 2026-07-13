"""Mint token.json with the SEND-ONLY Gmail scope (Appendix A, rule 30).

Standard OAuth installed-app flow, stdlib + httpx only: opens the consent
page, catches the redirect on localhost, exchanges the code for tokens.
Writes token.json next to the given credentials.json. BOTH files are secrets
and must stay gitignored (they are).

Usage: uv run python scripts/gmail_auth.py <path-to-credentials.json>
"""

import json
import secrets
import socket
import sys
import urllib.parse
import webbrowser
from pathlib import Path

import httpx

SCOPE = "https://www.googleapis.com/auth/gmail.send"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def wait_for_code(port: int, state: str) -> str:
    """One-shot localhost HTTP listener for the OAuth redirect."""
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", port))
        server.listen(1)
        connection, _ = server.accept()
        with connection:
            request = connection.recv(65536).decode("utf-8", "replace")
            connection.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
                b"<h2>Token minted - you can close this tab.</h2>"
            )
    query = urllib.parse.urlparse(request.split(" ")[1]).query
    params = urllib.parse.parse_qs(query)
    if params.get("state", [""])[0] != state:
        raise SystemExit("OAuth state mismatch - aborting")
    return params["code"][0]


def main(credentials_path: str) -> None:
    creds = json.loads(Path(credentials_path).read_text(encoding="utf-8"))["installed"]
    port = 8765
    redirect = f"http://127.0.0.1:{port}"
    state = secrets.token_urlsafe(16)
    url = AUTH_URL + "?" + urllib.parse.urlencode(
        {
            "client_id": creds["client_id"],
            "redirect_uri": redirect,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    print("Opening browser for consent (send-only scope)...")
    webbrowser.open(url)
    code = wait_for_code(port, state)
    response = httpx.post(
        TOKEN_URL,
        data={
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect,
        },
        timeout=30,
    )
    response.raise_for_status()
    tokens = response.json()
    out = Path(credentials_path).parent / "token.json"
    out.write_text(
        json.dumps(
            {
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"],
                "refresh_token": tokens["refresh_token"],
                "scopes": [SCOPE],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"token.json written to {out} (scope: gmail.send only)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "credentials.json")
