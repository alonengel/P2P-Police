# ADR-0003: Gatekeeper scope — metered third-party APIs, not the peer channel

Status: accepted · Date: 2026-07-13

The guidelines route ALL external API calls through the ApiGatekeeper. LLM
and Gmail calls do. The opponent MCP channel deliberately does NOT: it is the
game's turn pipeline with hard per-turn deadline semantics (rule 6) that a
throughput limiter must never delay — rate-limiting our own turns would
manufacture technical losses. It has its own bounded discipline instead:
per-call deadlines, persistent-session rebuild-on-failure, and retry backoff
from the SIGNED config. The gatekeeper therefore governs metered third-party
services (rate/quota/DOS protection of accounts); the peer channel is
governed by the deadline tracker + watchdog. Revisit if a league ever meters
peer traffic.
