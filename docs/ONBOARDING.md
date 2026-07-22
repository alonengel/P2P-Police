# Play against us in 30 minutes — team anrbj666

This repo is the **cop** agent of team `anrbj666` (Alon Engel, Renat Karimov);
the sibling thief lives at <https://github.com/alonengel/P2P-Thief>. This page
is everything another team needs to set up a game against us — warm-ups first,
counted series when both sides are ready.

Contact: `engel.alon@gmail.com`.

## Endpoints

| Agent | Public MCP URL | Port (local) |
|---|---|---|
| Cop | `https://cop-mcp.alon.website/mcp` | 8802 |
| Thief | `https://thief-mcp.alon.website/mcp` | 8801 |

FastMCP over HTTP, four tools: `negotiate`, `receive_turn`, `submit_audit`,
`receive_control`. Our transport retries connection-flavored failures
(including tunnel-edge 502-504/530) up to the turn budget, and our receiver
**tolerates duplicate deliveries** of the same step — a lost HTTP ack never
becomes a technical loss on our side. We recommend you dedup too.

## Before any game (the 30 minutes)

1. **Shared constitution**: we exchange and byte-match `config/game.json`
   (all Appendix-F fixed values verbatim; minimums negotiable upward only)
   and lock it via `config_sha256`.
2. **Scent model lock** (rule 23): we declare the book's multiplicative model
   as a league-envelope document — `scent_model_sha256 =
   934c220d5bf62acaa3297c6c9d723ea954c220260b02292ca17f6d5daef9f4d9`
   (`multiplicative_book_v1`). The full doc is committed at
   `config/scent_model_lock.json`; a hash mismatch refuses the game, so
   compare before scheduling.
3. **Byte-form contract**: canonical JSON, commitment construction, game-uid
   derivation, and the consensus signature are pinned in
   [`docs/INTEROP_HASHING.md`](INTEROP_HASHING.md). Reproduce our golden
   vectors (`tests/vectors/physics_vectors.json`) to verify your physics
   matches ours byte-for-byte before the first handshake.
4. **Negotiated terms** stated in the agreement: intra-turn commit order,
   information mode, wire shape (per pair), plus identity (group ids — 8
   chars, no spaces — repos, MCP URLs, counted-games-played declaration).

## Warm-ups (recommended, uncounted)

We will happily play as many uncounted warm-up games as you need: end-of-game
reports go to the two teams only, nothing is emailed to the league, and both
sides get full audit logs to debug against. Bring a flaky tunnel on purpose —
we drill failure modes (see `docs/evidence/chaos-drills.md`) and would rather
find interop issues before anything counts.

### Sparring posture (optional)

Warm-ups run our normal configuration with email reporting disabled (the
committed default) — nothing reaches the league before a counted game. A
committed generic posture also exists — `config/sparring.toml`, launched with
`uv run p2p-police peer --sparring [--wire-shape reference]` — baseline brain,
no tuned terms, for teams that prefer strategy-neutral warm-ups; we are happy
to play either way, your choice. The wire shape stays selectable so either
protocol (bookletter lockstep or hidden reference-v3) can be warmed up.

## Counted series

One counted series per pair: 6 sub-games, roles alternating, `num_games = 6`
in the signed config, game-count declared at start, mutual audit after every
sub-game, and **each team emails its own JSON report** — we always send, and
we verify result agreement with you before sending.

## What we need from you

Your `group_id`, both repo links, your two public MCP URLs, your scent-model
lock hash, and a proposed time window. Everything else is negotiated in the
handshake itself.

## Third-party verification

After any game — warm-up or counted — either side (or any third party) can
check the pair of logs: `uv run python scripts/verify_pair.py <log_a> <log_b>`
verifies both logs independently (commits + physics recompute) and their
mutual consistency (same game_uid, same end digest, record-for-record match).
