# RISK REGISTER (L=likelihood, I=impact; adopted format from Renat Karimov)

| ID | Risk | L | I | Mitigation (status) |
|---|---|---|---|---|
| RK-01 | Twin physics drift | L | H | golden vectors + parity script + paired commits (ACTIVE) |
| RK-02 | Cross-team hashing non-determinism | M | H | INTEROP_HASHING.md contract + scent-code offer + schema (ACTIVE) |
| RK-03 | Tunnel drops mid-game | M | M | persistent session rebuild + retryable 5xx + deadlines (PROVEN in E2E) |
| RK-04 | Duplicate message delivery | M | H | sealed-exchange dedup by (kind, turn) (TESTED) |
| RK-05 | Opponent schema/interpretation drift | M | H | game.schema.json pre-validation + negotiation disclosures (ACTIVE) |
| RK-06 | Gmail token expiry on league day | H | H | runbook re-mint step (<7-day Testing tokens) (DOCUMENTED) |
| RK-07 | Unreported forfeit | L | H | catch-all reporting funnel; technical loss still emits (TESTED) |
| RK-08 | Forged opponent log | L | H | commit-reveal + both-halves verification + TAMPERED void (TESTED) |
| RK-09 | GUI failure abandons game | L | M | worker failures -> reported technical loss (TESTED) |
| RK-10 | 429 / account suspension | L | H | bucket+quota+DOS triad; email 5rpm (TESTED) |
| RK-11 | Config mismatch at negotiation | M | L | sha refusal BEFORE first move; schema validation (TESTED) |
| RK-12 | Forgetting a league-day human duty | M | H | LEAGUE_RUNBOOK.md checklists (DOCUMENTED) |
| RK-13 | Intent-flag leak to opponent | - | H | CLOSED: verdicts secret until audit (fixed + tested) |
