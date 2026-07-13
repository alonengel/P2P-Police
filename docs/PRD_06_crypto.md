# PRD 06 — Commit-reveal integrity (stage 6, delivered)

Goal: the four-phase protocol + mutual audit (rules 17-24).
Delivered: canonical JSON over the pinned 7-field sealed record (step, role,
sub_game, state_digest, action, hint, verdict); secrets nonces, secret until
the end audit; SealedExchange (commit -> ack-as-lock -> reveal -> audit);
binary verdicts; FSM wired with TECHNICAL_LOSS exits; negotiation locks the
scent model incl. the re-emission clamp (rule 23) and seals the hardware
disclosure (rule 24). Milestone (met): 35 sealed steps, audit Verified OK
both sides; tamper injection -> TAMPERED (test + live verify-log demo).
