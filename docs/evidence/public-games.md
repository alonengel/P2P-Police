# Evidence — public-internet games (the legality condition, exercised)

> Status: complete; re-run after every behavior-changing slice.

## Setup

| Item | Value |
|---|---|
| Tunnel | Cloudflare named tunnel `copthief`, hostnames `cop-mcp.alon.website` / `thief-mcp.alon.website` (single-level: sub-subdomains break the universal cert), ingress pinned to 127.0.0.1 with `originRequest.httpHostHeader` (FastMCP 421 hardening) |
| Transport | ONE persistent MCP session per opponent, rebuilt only on failure ("Session terminated" through proxies — field finding) |
| Email | `[email] mode = "disabled"` during ALL test games — nothing was ever sent |

## Observed

- **2026-07-13** — first fully public bidirectional 35-turn sealed game
  over the tunnel: identical end-state digests, audits Verified OK both
  directions (`results/public_bidirectional_e2e_2026-07-13.json`).
- **2026-07-18** — repeated on the reference-aligned bytes AND the new
  symmetric hostnames, through the Host-header-rewriting ingress: same
  verdicts; the report now carries the gatekeeper monitoring view; the
  physics-recomputing `verify-log` re-validates the committed log
  (`results/public_bidirectional_e2e_2026-07-18.json`).
- Edge routing observed via Frankfurt + Tel Aviv Cloudflare POPs; the
  runbook's step 2b (probe your OWN public URL before declaring a counted
  game) exists because the 421 failure mode was observed live against the
  unmodified reference peer by the rival team and hardened here.

## What this does NOT prove

These are self-play games (both peers ours, both roles exercised over the
real internet). The first cross-TEAM public game happens as a league
warm-up; the interop-alignment evidence covers the byte-level risk it
would otherwise carry.
