# PRD 04 — Language + scent: belief under uncertainty (ch. 4+6, stage 4 of 7)

## Goal

The heart of the game: agents stop seeing each other. Each side builds a
Bayesian belief map over the rival's location from (a) the rival's decaying
scent field, (b) movement diffusion (one orthogonal step or stay per turn),
and (c) the rival's ≤15-word verbal hint — which may be a lie, detected by
comparing the claim against the scent evidence (expected fresh trail
(1−ρ)·0.9 ≈ 0.81, book's worked example).

## Modules

| Module | Contract |
|---|---|
| domain/belief (parity-locked) | uniform prior → per-turn: diffuse (movement model) × scent likelihood × hint likelihood → normalized posterior; argmax cell; lie detector: claimed-region max scent vs LIE_EVIDENCE_FLOOR |
| shared/rate_limiter | token bucket tokens←min(C, tokens+r·Δt), allow ⟺ tokens≥1; daily quota safety threshold; DOS lock (consecutive-denial circuit breaker) — values from rate_limits.json |
| shared/gatekeeper | ApiGatekeeper.execute(): the SINGLE doorway for every external call — limiter check, bounded retries, call log |
| strategy/hints | truth/lie intent policy; template sentences (0 tokens, book default); ≤hint_max_words enforced on EVERY provider path; claim parsing (our own deterministic templates) |
| infra/llm_provider | provider registry: template (shipped, default) + ollama/claude_api/claude_cli/openrouter seams behind the gatekeeper (full clients arrive with league prep) |

## Binding requirements encoded as tests

- Belief mass concentrates near fresh scent; silent regions decay toward the
  movement-diffusion prior; posterior always sums to 1; barriers hold zero mass.
- Hint "moved north" with dead-silent north (τ=0) and hot south-east → hint
  weighted as a LIE; belief re-aims at the scent source (book p. 30 example).
- Truthful hints sharpen the posterior toward the claimed region.
- Token bucket: burst up to C, then blocked; refill over time (fake clock).
- Quota: daily safety threshold blocks before provider limits (429 protection).
- DOS lock: sustained denial storm trips the circuit breaker (rules 28-29).
- Hint text NEVER exceeds hint_max_words (rule: applies to template AND LLM).

## Milestone

Blind arena: a belief-driven cop (argmax-belief pursuit, never reading the
thief's true position) still captures a random thief in most games — proving
the belief map, not luck, drives the moves.
