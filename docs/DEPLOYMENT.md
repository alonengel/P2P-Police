# DEPLOYMENT — from localhost to the public league

## Levels

1. **Local dev** (default): two processes, two repos — thief `:8801`, police `:8802`.
   `powershell -File ../run_cross_match.ps1` runs a full verified match.
2. **Public play**: expose YOUR server with a tunnel; the opponent's URL goes in
   `config/game.toml [network].opponent_url`. That URL is the only thing either
   side knows about the other.

## Cloudflare named tunnel (our production path — verified)

One tunnel (`copthief`, from ex6) carries both agents on separate hostnames:

| Agent | Public URL | Local service |
|---|---|---|
| Thief | `https://thief-mcp.alon.website/mcp` | `http://localhost:8801` |
| Police | `https://cop-mcp.alon.website/mcp` | `http://localhost:8802` |

(`mcp.alon.website` remains a legacy alias for the thief — older evidence
artifacts reference it; the symmetric `thief-mcp`/`cop-mcp` pair is canonical.)

Setup (already done on this machine; for a new one):
```bash
cloudflared tunnel login                       # browser auth
cloudflared tunnel create copthief
cloudflared tunnel route dns copthief thief-mcp.alon.website
cloudflared tunnel route dns copthief cop-mcp.alon.website
# ~/.cloudflared/config.yml: ingress mapping the two hostnames to
#   http://127.0.0.1:8801 / 8802  (NOT 'localhost' - cloudflared resolves it
#   to IPv6 ::1 while the servers bind IPv4; also: sub-subdomains like
#   cop.mcp.* break the universal *.alon.website certificate - stay one level)
# Each ingress entry MUST also rewrite the Host header:
#     originRequest:
#       httpHostHeader: 127.0.0.1:<port>
#   FastMCP's DNS-rebinding protection (version-dependent) answers 421
#   Misdirected Request to any Host that isn't the bind address - which is
#   every tunneled request. Observed live against the unmodified official
#   reference peer; the rewrite makes the origin always see itself.
#   (ngrok equivalent: --host-header=rewrite)
cloudflared tunnel run copthief                # keep running during games
```
Credentials JSON + cert.pem live in `~/.cloudflared/` — NEVER in a repo.

**Verified evidence:** `results/dev-history/results/public_tunnel_prd05_2026-07-13.json` — full
35-turn blind game over `mcp.alon.website`, identical digests.

## Why not free ngrok

Tested in ex6: new-connection rate cap (~20/min) + idle drops stalled real
matches. Quick Cloudflare tunnels (`cloudflared tunnel --url http://localhost:8801`)
work for ad-hoc games; the named tunnel gives stable URLs for the league.

## Hard-won lesson (keep!)

MCP sessions MUST be persistent per opponent: per-call sessions get
"Session terminated" through proxies. `McpTransport` holds one session and
rebuilds it only on failure — do not "simplify" this away.

## Gmail reporting (Appendix A)

- Mint a SEND-ONLY token: `uv run python scripts/gmail_auth.py <credentials.json>`
  (browser consent; writes `token.json` next to the credentials).
- Point `GMAIL_TOKEN_PATH` at it (default: `token.json` in the CWD; we keep
  secrets in `../secrets/`, outside both repos).
- **Google Testing-mode refresh tokens EXPIRE after ~7 days** — re-mint before
  league day; a dead token fails fast with a clear error.
- League games: set `[email] mode = "send"` in `game.toml`; dev default is
  `disabled`. Test to your own inbox first by overriding the recipient.
