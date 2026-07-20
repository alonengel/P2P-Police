# COST — token & cost analysis (guidelines §11)

## Measured (all games to date)

| Run | Provider | Input tok | Output tok | Cost |
|---|---|---|---|---|
| All dev games + both counted-format series | `template` | 0 | 0 | $0.00 |
| Cross-repo public-tunnel game (PRD-05) | `template` | 0 | 0 | $0.00 |

The token meter (rule 54) seals totals into every result artifact
(`tokens_total`); every game so far reports 0.

## Projections per 6-sub-game series (~210 hints/side)

| Provider | Model | $/M in / $/M out | Est. tokens | Est. cost |
|---|---|---|---|---|
| template | — | — | 0 | $0.00 |
| ollama | llama3.2 (local) | 0 / 0 | 0 API | $0.00 |
| claude_api | claude-haiku-4-5 | 1.00 / 5.00 | ~21k in / ~6k out | ~$0.05 |
| openrouter | gpt-4o-mini | 0.15 / 0.60 | ~21k in / ~6k out | ~$0.007 |
| claude_cli | subscription | plan quota | n/a | $0 marginal |

Assumptions: ~100-token prompt + ~30-token reply per hint; `every_n_steps`
divides these linearly (e.g. =3 → a third).

## Optimization strategy (implemented)

1. **Default to zero**: template provider plays complete series at 0 tokens —
   the competition then rides on the movement algorithm (Appendix ו Table 21).
2. **Throttle**: `every_n_steps` caps LLM turns; template fills the gaps.
3. **Never block**: any provider failure falls back to template — worst case
   costs 0, not a technical loss.
4. **Budget guard**: series budget 200k tokens (signed config); the meter's
   sealed totals prove compliance in every report.

## Double-proof token accounting

Token claims are provable two independent ways, so a 0-token series is
auditable rather than asserted: (1) the per-provider meter aggregated into
every result artifact (`tokens_total`, rule 54), and (2) the gatekeeper's
timestamped call log (one instance per run) — a series claiming zero
tokens must show BOTH an empty LLM call log and a zero meter, and the
template provider's 0-token path is the shipped default.
