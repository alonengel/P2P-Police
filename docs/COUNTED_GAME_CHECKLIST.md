# COUNTED game vs vibecode — the complete procedure, before / during / after

Operational checklist for our second counted series (first: imreeyal, filed
2026-08-04). Everything here is verified against the code and the six vibecode
friendlies of 2026-08-08; generic background lives in `LEAGUE_RUNBOOK.md` —
this file is the execution order.

**League state going in**: `counted_games_played = 1` (imreeyal). This series
is counted game #2, vs a DIFFERENT team → satisfies `min_games_to_pass = 2`
(rule 52: one counted game per rival, max 10 total). First counted meeting
with vibecode → the winner takes the `diversity_reward` (10) in the standings;
`final_result.diversity_reward_applied` records it.

**Protocol state (all converged 2026-08-08, nothing left open)**: shared
constitution `agreed_between [anrbj666, vibecode]`, `config_sha256 9ed3b2e9…`;
scent `multiplicative_book_v1 934c220d…`; wire reference-v3 `229ae648…`;
mutual_agreement = ADR-0012 symmetric-outcome scope (spaced serialization);
step-0 sealed AND on the wire both directions; declarations span the series.

## Contacts

| Who | Address | Role |
|---|---|---|
| League / lecturer | `rmisegal+uoh26finalgame@gmail.com` | THE report address (rule 51) — counted only |
| vibecode operators | `agentsorch@gmail.com` (Ron Marom, Amit Kuperminz) | coordination + artifact swap |
| Us | `alonisrael.engel@gmail.com` | our own copy of everything |

## BEFORE (T-minus, in order)

1. **Declare it counted, in writing, both operators, BEFORE T** (rule 52 +
   both teams' safety frame). Keep the message — it is the authorization
   artifact. Nothing counts without it.
2. **Gmail token freshness**: if the token is >5 days old it will die mid-day
   — re-mint: `uv run python scripts/gmail_auth.py ../secrets/credentials.json`.
   The runner's preflight refuses the whole series (zero games played) if the
   mail rail is dead — better to fix it now.
3. **Arm the counted posture — BOTH repos, `config/game.toml`**:
   - `[email] mode = "send"`
   - `[email] counted = true` (config half of the lecturer-address interlock)
   - `[email] recipient = "alonisrael.engel@gmail.com, rmisegal+uoh26finalgame@gmail.com"`
     (league restored per rule 51; keep our copy)
   - `counted_games_played` STAYS `1` — it means games played BEFORE this one
     (rules 37-38; the lecturer cross-checks every team's declared count).
4. **Check the overlay** (`config/game.local.toml`, both repos): it must NOT
   override `[email] recipient` or `mode` (a stale friendly override silently
   redirects the league report). Keep only: `opponent_group_id = "vibecode"`,
   `[network] opponent_url`, and the police `[strategy.claim]` threshold.
5. **Commit + push BOTH repos** (rule 53: play a pushed commit — every sealed
   step-zero and result row must carry a hash the lecturer can rev-parse).
   Archive leftover pairing artifacts first so the tree and results dir are
   clean (the runner's series-start archive backs this up).
6. **Endpoints up + cross-probe, both directions, confirmed in writing**:
   `cloudflared tunnel run copthief`, then a real MCP `list_tools` against
   their two URLs and theirs against ours. No green probe, no T.

## LAUNCH (at T, both repos in parallel)

```bash
# police repo                                            # thief repo
uv run python scripts/league_series.py \                 uv run python scripts/league_series.py \
    --sub-games "1,3,5" --seed <S> --counted                 --sub-games "2,4,6" --seed <S> --counted
```

`--counted` is the CLI half of the interlock — league mail is possible only
with BOTH halves armed; a friendly posture structurally cannot address the
lecturer, and a counted run without the flag refuses to mail. The preflight
proves deliverability BEFORE window 1. Pick any `<S>`; record it.

## DURING

- Touch nothing. The runners interleave g01..g06 strictly sequentially; each
  window is settled by mutual audit before the next opens.
- A FAILED window is logged honestly and skipped — re-run ONLY that window by
  hand afterwards (`uv run p2p-police peer --sub-game N --seed S+N --counted`)
  until it settles. The settlement guard refuses aggregation (and email) while
  any window is unsettled — nothing is ever fabricated.
- Keep the terminal logs; screenshot anything unusual (dispute evidence).

## AFTER (the part that gets graded)

1. **Verify the series settled honestly**: 6/6 `audit: Verified OK`, result
   rows complete, `mutual_agreement.confirmed: true` with the hash matching
   vibecode's file string-for-string.
2. **Verify THE report email went out** — exactly ONE per team, result JSON as
   body + the same bytes as the single attachment, to the league address
   (check the sent box; the runner prints `emailed: <message-id>`). vibecode
   sends their own copy — rule 35: a missing or contradictory report
   disqualifies the game, so confirm with them that theirs left too.
3. **Commit + push ALL artifacts, both repos** (configs in `config/games/`,
   declaration + logs + result in `results/`): uncommitted artifacts are
   invisible to the lecturer's audit and rule-53 hashes must resolve.
4. **Verify the counted tracker**: `results/counted_series.json` (both repos)
   gains the `anrbj666-vs-vibecode` entry with the report's message id.
5. **Bump the counter FOR THE FUTURE**: `counted_games_played 1 → 2` in BOTH
   repos' game.toml, commit (`chore(config): counted #2 filed — vibecode`).
   From now on every handshake declares 2.
6. **Restore the friendly posture** in game.toml, both repos:
   `counted = false`, recipient back to
   `"alonisrael.engel@gmail.com, agentsorch@gmail.com"` — so no stray dev run
   can ever mail the league. Commit.
7. **Artifact swap with vibecode**: full four-kind set + byte-exact manifest,
   both directions, field-by-field diff (the friendly #5/#6 standard: sealed
   commits recompute, step-0s byte-identical to the wire, configs at
   `9ed3b2e9…`, mutual_agreement equal). File the diff summary in
   `docs/docsVersusAmitAndRon/`.
8. **League accounting sanity**: our declared count now 2 (≥ min 2, vs two
   different teams); diversity reward applied to the winner of this first
   counted meeting; tokens 0 as always.

## Known play-state going in (from the six friendlies, 2026-08-08)

Ledger 6-0 in series for us (75-35, 90-30, 85-45, 75-35, 70-50 + the aborted
first attempt), but the last one was the closest: their SW-corner anti-phase
dance beats our chaser (3/3 escapes) while their NE line always dies (~17s
captures), and their barrier-wall trap has caught our thief twice. If we want
the margin back before the counted six: the STAY parity-break endgame for the
cop is the one known counter to the SW dance; barrier-aware escape planning is
the counter to the wall. Neither is protocol — both are strategy, and the
series is winnable as-is. Their operators fix fast; assume their best.
