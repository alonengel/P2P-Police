# PRD 05 — Public exposure (stage 5, delivered)

Goal: full game over the public internet (rule 10 legality condition).
Delivered: Cloudflare NAMED tunnel, one hostname per agent
(mcp.alon.website -> thief :8801, cop.mcp.alon.website -> police :8802);
persistent single MCP session per opponent (per-call sessions die through
proxies - field finding); in-flight timeouts; free-ngrok rejection rationale.
Milestone (met): 35-turn blind game over mcp.alon.website, identical digests
(results/public_tunnel_prd05_2026-07-13.json). Runbook: docs/DEPLOYMENT.md.
