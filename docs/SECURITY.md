# SECURITY — threat model one-pager

(Adapted from Renat Karimov's parallel scaffold, merged with our controls.)

## Trust boundaries

| Input | Trust | Control |
|---|---|---|
| Opponent MCP messages | NONE | strict parsing (kind/turn/actor/fields), dedup, deadline-bounded waits; malformed = protocol failure, never guessed around |
| Opponent hints | HOSTILE by design | belief-weighted only; lie detector + honesty profiler; never touches rule enforcement |
| LLM output | UNTRUSTED TEXT | renders hint prose only; word-capped; NEVER influences moves, rules or crypto (rule 25); parse failures -> template fallback |
| Shared config | agreed, then LOCKED | JSON Schema (config/game.schema.json) + Appendix-VI validators + SHA-256 byte-identity at negotiation |
| Own secrets | — | credentials/token/.env outside repo + gitignored; gitleaks in CI; send-only OAuth scope; rotate on any leak |

## Principles

- Never trust a peer's claims about our hidden state; everything checkable is
  recomputed locally (replicated engine, commit-reveal, mutual audit).
- Nonces + intent flags stay secret until the audit (dictionary-attack and
  deception-leak protection).
- Public endpoints expose exactly four dumb tools; all game logic runs behind
  the SDK; the gatekeeper triad (bucket/quota/DOS) guards outbound accounts.
- Fail loud and report: every game end - including our own crashes - emits
  the four artifacts and the league email (rules 32/35).
