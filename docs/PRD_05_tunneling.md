# PRD 05 — Public exposure & tunneling

## Scope & non-goals

Rule 10: the local FastMCP server must be reachable from the public
internet. Scope: the named-tunnel production path, its hardening, and the
dev fallbacks. Non-goals: authentication beyond the MCP layer (the book's
threat model is the audit, not the transport).

## Design

- **Cloudflare named tunnel** `copthief` on the team domain: police
  `https://cop-mcp.alon.website/mcp`, thief `https://thief-mcp.alon.website/mcp`
  (`mcp.alon.website` remains a legacy thief alias). Stable URLs — the
  opponent_url is the ONLY thing a rival knows about us.
- **Hostname discipline**: single-level names only (sub-subdomains break
  the universal *.alon.website certificate — hit live, documented).
- **Ingress pins**: `127.0.0.1:<port>` (cloudflared resolves `localhost`
  to ::1 while the servers bind IPv4) + `originRequest.httpHostHeader`
  (FastMCP's version-dependent DNS-rebinding protection 421-rejects
  tunneled Hosts; observed live against the unmodified reference peer).
- **Transport client**: ONE persistent MCP session per opponent on a
  dedicated loop thread, rebuilt only on connection-flavored failures
  ("Session terminated" through proxies — field finding); 502/503/504
  retryable; every call deadline-bounded (rule 6).

## Decisions & alternatives rejected

- **Free ngrok**: rejected on ex6 field data — connection-rate caps and
  idle drops stalled real matches. Quick Cloudflare tunnels remain the
  ad-hoc fallback; the named tunnel is the league path.
- **Auth tokens on the endpoint**: deferred — the mutual audit, not
  transport secrecy, is the book's integrity mechanism; complexity cut.

## Test plan / acceptance (all met)

Full public bidirectional 35-turn sealed games over the tunnel with
identical digests and mutual Verified-OK audits — re-run after every
behavior-changing slice; pre-match probe step (runbook 2b) added after the
421 finding. Evidence: `docs/evidence/public-games.md`, DEPLOYMENT.md.
