# LEAGUE RUNBOOK — manual duties for every counted game

Code automates the game; these steps are HUMAN duties. Skipping any of them
costs points or disqualifies (rule numbers from the rulebook's Appendix ה/ו).

## Before the series (per opponent)

1. **Coordinate out-of-band** (WhatsApp): agree schedule, exchange public URLs
   (ours: thief `https://thief-mcp.alon.website/mcp`, cop `https://cop-mcp.alon.website/mcp`;
   `mcp.alon.website` still routes to the thief as a legacy alias).
2. **Negotiate the shared game.json** - for a counted series set
   `network_and_league.num_games = 6` (Table 18 fixed: 6 sub-games per
   series; the dev default 1 is for single-game testing) - any change to negotiable values, and
   minimums may only go UP (rule 12). Both sides must load a byte-identical
   file (rule 11; the code verifies the sha and refuses otherwise).
3. **Exchange + lock the scent model** (rule 23) — and OFFER OUR CODE
   (book ch. 4.5: "permitted and even recommended"). Attach two files:
   `src/p2p_police/domain/scent.py` and `tests/vectors/physics_vectors.json`.
   Ready-to-paste message: *"Our scent model incl. the re-emission clamp at
   0.9 (extends the book's literal formula — without it you fail our audit).
   Either run this exact file or verify your implementation reproduces the
   attached golden vectors bit-for-bit; our negotiation checks
   scent_model_sha256 before move one either way."*
   Scent physics is pure dice — zero strategy inside; sharing it eliminates
   the divergent-float technical-loss class for both teams.
3b. **Disclose interpretation edge cases** (docs/INTEROP_HASHING.md item 7:
   trapped-thief reading, max_moves-as-survival) and offer the JSON Schema
   (`config/game.schema.json`) so they can pre-validate their game.json.
4. **Warm-up games are allowed and wise** (uncounted); declare which game is
   the counted one BEFORE it starts.
4b. **Warm-ups run the sparring posture** — `uv run p2p-police peer --sparring`
   loads `config/sparring.toml` (shipped baseline brain, deception disarmed,
   no email) so uncounted games never feed our tuned play to a rival's
   cross-game profiler; counted games use the committed game.toml as usual.
   `--wire-shape bookletter|reference` selects the warm-up protocol.
5. **Truthful game-count declaration** (rules 37-38): the lecturer
   cross-verifies from every team's reports — lying disqualifies.
6. **Re-mint the Gmail token if >5 days old** (Testing-mode tokens die at ~7):
   `uv run python scripts/gmail_auth.py ../secrets/credentials.json`.
7. Set `[email] mode = "send"` AND restore the league recipient (see
   "Running the counted series" step 1); update `sub_game_number`; commit
   everything.

## Running the counted series (end to end)

A counted series is ONE continuous run that ends in its series report:
six sub-games, roles alternating per the book — this police repo plays the
ODD windows (1,3,5), the thief repo the EVEN ones (2,4,6).

1. **Arm the counted posture** (per repo, per counted game): set
   `[email] mode = "send"` and RESTORE the recipient to the league address
   `rmisegal+uoh26finalgame@gmail.com` (rule 51). The committed game.toml
   deliberately ships the warm-up posture — recipient = our own addresses
   (`alonisrael.engel@gmail.com, Imree.c@gmail.com`), `mode = "disabled"` —
   so a stray dev run can never mail the league; flipping both back is a
   HUMAN duty. Commit the armed config.
2. **T-protocol launch**: at the agreed start time, tunnels up and probed
   (see "Per counted game" 2/2b), then each of OUR repos starts ITS window
   runner:
   - police repo (here): `uv run python scripts/league_series.py --sub-games "1,3,5" --seed 900`
   - thief repo: `uv run python scripts/league_series.py --sub-games "2,4,6" --seed 900`
   Each runner launches the committed CLI per window (`peer --sub-game N
   --seed base+N`), strictly sequentially, logging every window honestly
   to stdout. A runner refuses windows of the wrong parity.
3. **Single-instance lock**: the runner writes
   `results/local/league_series.lock` (its pid inside); a second instance
   REFUSES to start — our orchestration-layer half of the double-instance
   guard (the wire's game_uid/sub_game_number checks are the other half).
   If a runner died hard, verify that pid is gone before deleting the lock.
4. **A failed window is logged, never fabricated.** The runner continues to
   the next window and exits non-zero; re-run ONLY the failed window by
   hand (`uv run p2p-police peer --sub-game N --seed base+N`) until it
   settles.
5. **Aggregate across BOTH role repos** (a team's series record spans them):
   `uv run p2p-police series-result --game-id <ours-vs-theirs>
   --results-dir results --results-dir ../P2P-Thief/results --email`
6. **The settlement guard (rule 35)** is why aggregation may print REFUSED:
   every sub-game 1..num_games needs a settled, audit-clean log — the
   report never invents or completes a missing game. A refused series
   emails NOTHING; settle the missing window, then re-aggregate.
7. **`--email` auto-fire**: on a successful emit only, ONE email goes out —
   the result JSON as body plus the result file as THE attachment
   (result-only per the course bot's ruling, ADR-0012 second addendum;
   the other three template types reach the lecturer via GitHub — commit
   and push them per game, step 5 below) — through shared/gatekeeper,
   recipient from config, and only when `[email] mode = "send"`. The
   subject carries the game_id, the final score and series_tie/winner.
8. **Rule 53 stays manual**: email the lecturer the commit id used for each
   counted game (see "Per counted game" step 1) — the code never does this.

## Per counted game

1. **EMAIL THE LECTURER THE COMMIT ID** used for this game (rule 53 + App ו
   §2.5) — to rmisegal@gmail.com, manually. The declaration artifact records
   the hash; the email is OUR duty, not the code's.
2. Start `cloudflared tunnel run copthief`, then the peer
   (`uv run p2p-police peer --gui`).
2b. **Probe your OWN public URL before declaring the counted game** — one
   tool call against `https://cop-mcp.alon.website/mcp` (not localhost) and
   confirm it answers. Catches tunnel breakage — especially FastMCP's
   version-dependent 421 Host-header rejection (see DEPLOYMENT.md) — in
   seconds instead of mid-game.
3. After the game: confirm the audit verdict is "Verified OK" on BOTH sides
   and the digests match (mutual audit, rules 35-36) BEFORE agreeing on the
   result.
4. NO per-sub-game email exists (book §9.3.3, p. 79: the result file is THE
   mandated report email, one per series from each team). Verify the ONE
   series email after "Running the counted series" step 5-7 — to
   rmisegal+uoh26finalgame@gmail.com (rule 51).
5. Verify the game's config artifact landed in `config/games/` — then
   COMMIT AND PUSH it (rules 3-5 + App ו §2) with the log + result
   artifacts in `results/`; artifacts left uncommitted are invisible to the
   lecturer's audit.
6. Screenshot anything unusual; keep logs — they are the only accepted
   dispute evidence.

## Counting rules (don't burn games)

- Only ONE counted game per rival team (rule 52); 6 sub-games per series;
  minimum 2 counted games vs DIFFERENT teams to pass; max 10 counted total.
- Tie across a pairing → both sides get tie_score 2.

## Submission day (checklist pointer)

Both repos: academic README complete + cross-links; screenshots in assets/;
`git tag -a v1.0-submission -m "Final submission: Police-Thief P2P, group anrbj666"`
+ push the tag; Moodle form PDF (fields unaltered), EACH member submits
separately, team code `anrbj666`.

### Counted-day additions (2026-07-25)

- **Preflight before window 1**: with `[email] mode = "send"`, the runner
  verifies deliverability first (token loads/refreshes against the OAuth
  endpoint only, recipient non-empty) and refuses the whole run with zero
  games played if the report could not be sent — never discover a dead mail
  rail after the sixth settle.
- **League-address interlock**: sending to the league requires BOTH
  `[email] counted = true` and the `--counted` flag. Rehearsals and
  friendlies structurally cannot address the lecturer.
- **Auto-close**: when the runner's last window settles and all num_games
  logs are visible across both repos' results dirs, the series result is
  aggregated and the ONE report email fires; any missing sub-game is named
  and nothing is aggregated (a report must never invent a game).
- **Orphan guard**: peer startup connect-probes its role port (refuses if
  anything answers) and verifies its own server listens after start.

### Clean-commit note (2026-08-03 friendly finding; updated same day)

The declared commit id is the bare `git rev-parse HEAD` (no dirty
qualifier — pair decision with imreeyal, see report/code_identity.py),
so artifact churn can no longer stain the declared hash. The pre-window
ritual still carries the honesty burden the qualifier used to: archive
the previous window's artifacts, COMMIT, PUSH, and only then launch —
the declared hash claims "this pushed commit is what played", and a
clean launch tree is what makes that claim true (rule 53: the lecturer
must be able to rev-parse it).
