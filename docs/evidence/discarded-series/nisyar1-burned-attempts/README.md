# Burned nis-yar1 friendly attempts (2026-08-09 → 2026-08-10) — technical, uncounted

**Every file here is from a FRIENDLY (uncounted) attempt that never played a
single turn.** No counter moved, no league report was sent, nothing entered the
rule-52 ledger. Kept under the evidence guardrail (archived, never deleted).

All records show the same signature: `outcome: technical_loss`,
`turns_completed: 0`, `opponent_group_id: "unknown"`,
`failure: DeadlineExpiredError: deadline expired while waiting for opponent agreement`.
"unknown" is honest, not a bug: the opponent's signed declaration is the only
place their group_id crosses the wire, and it never arrived.

Root cause (established 2026-08-10, evidence in
`docs/docsVersusNisYar1/` at the workspace root): the reference handshake is a
bidirectional push — each peer POSTs its signed agreement to the rival's
`negotiate` tool. Our pushes into nis-yar1's ngrok path-split endpoints were
accepted (HTTP 200 every ~7.3 s for the full 180 s window, both directions),
but zero requests from their side ever reached our tunnel: cloudflared's
`cloudflared_tunnel_total_requests` counter read **0** across both game windows
(16:02:31Z–16:08:40Z), and a two-probe control immediately after moved it 0→2,
proving the counter counts. Their routed local repro passed because both of
their peers dial their *own* domain — the outbound dial to a *remote* opponent
URL is the untested path that fails.

The g03/g05 files are the 2026-08-09 attempts (same class, pre-dating their
path-proxy fix); g01 is 2026-08-10 post-fix. Sibling repo holds the even
windows (g02/g04/g06).

`seed3820-scent-mismatch/` is the 2026-08-10 19:52 series (fourth failure
generation): their crash-on-contact bug was FIXED — full declarations arrived
both directions within seconds — but their declared `scent_model_sha256`
(`81ebee59…`) contradicted the mutually-locked `934c220d…`
(multiplicative_book_v1), so every window refused fatally in ~6 s under the
both-declare rule. Refusal is mandatory: a mismatched scent model is
divergent physics and would break the end-of-game audit.
