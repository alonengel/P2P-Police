# Crash-resume (E6): per-half-turn snapshots + resume path

## What was built

- `src/p2p_police/peer/resume.py`: after every applied half-turn the runtime
  checkpoints an **atomic** snapshot (tmp file + `os.replace`) holding the
  turn index, both sealed-record logs **including our own nonces** (they never
  cross the wire before the audit), the applied-action log, the consumed-message
  dedup keys and the verified opponent agreement. An integrity SHA-256 covers
  the whole document; a tampered or truncated snapshot is rejected cleanly
  (`ResumeError`), never replayed.
- Snapshots live under `results/local/resume_*.json` — **gitignored mutable
  state, never evidence, never committed**. Recording is **ON by default**
  (`[resume] enabled` in `config/game.toml`): it is pure local persistence
  with zero wire-protocol change, so there is no reason to play without it.
- Resume path (`p2p-police peer --resume`, or `SimulationSdk.run_peer(resume=True)`):
  the snapshot's actions are replayed through the one true application path
  (`protocol.apply_action`) on a fresh engine, the replayed digest must equal
  the snapshot's recorded digest, the `SealedExchange` is re-armed with its
  records — commit-reveal chain intact — and `play(resume_from=turn)` continues
  from the next expected step. Opponent hints are re-fed to perception during
  replay so the belief map is rebuilt from the recorded evidence.

## The control-channel handshake — a per-pair courtesy, not a rule change

On resume we send `{kind: "resume_offer", turn, group_id}` through the existing
`receive_control` tool. A peer that receives it re-sends its **last sealed
commit+reveal pair** (if any); the sealing layer's at-least-once dedup absorbs
the duplicate wherever it already arrived. Honoring a resume offer is a
**negotiated courtesy between the pair**: the rulebook's deadline rules keep
running throughout — a lapsed wait is still failure (rule 6), so a resume only
succeeds if it completes **inside the opponent's turn budget**. Nothing here
weakens any book rule; a peer that ignores the offer simply wins on deadline
as before.

## Known limitation (documented, deliberate)

Snapshots are written at half-turn boundaries. A crash in the middle of our own
commit/reveal send can lose that half-turn's nonce; the resumed peer must not
re-commit a different action for a step the rival already consumed, so recovery
is only guaranteed from the last completed half-turn. The deception policy's
in-memory cooldown state also restarts on resume; the sealed intent trail
(what the audit checks) is fully preserved.

## Drill evidence (really observed)

`docs/evidence/drills/resume_recovery_2026-07-21.jsonl` — in-process
kill-and-resume over real HTTP MCP: crash after 6 half-turns (transport closed,
undelivered inbox mail dropped, runtime discarded), resume from snapshot in
**0.045 s**, 6 half-turns recovered by replay, game finished `capture` with
`digest_match=true` and **mutual audits `Verified OK`**. Re-run:
`uv run python scripts/resume_drill.py`; the slow test
`tests/integration/test_resume_drill.py` repeats it with evidence in tmp.
