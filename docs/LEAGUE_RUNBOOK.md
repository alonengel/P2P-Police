# LEAGUE RUNBOOK — manual duties for every counted game

Code automates the game; these steps are HUMAN duties. Skipping any of them
costs points or disqualifies (rule numbers from the rulebook's Appendix ה/ו).

## Before the series (per opponent)

1. **Coordinate out-of-band** (WhatsApp): agree schedule, exchange public URLs
   (ours: thief `https://mcp.alon.website/mcp`, cop `https://cop.mcp.alon.website/mcp`).
2. **Negotiate the shared game.json** — any change to negotiable values, and
   minimums may only go UP (rule 12). Both sides must load a byte-identical
   file (rule 11; the code verifies the sha and refuses otherwise).
3. **Exchange + lock the scent model** (rule 23): share our scent spec
   including the numeric example AND the re-emission clamp at 0.9 — the clamp
   EXTENDS the book's literal formula; an opponent without it will fail audit.
4. **Warm-up games are allowed and wise** (uncounted); declare which game is
   the counted one BEFORE it starts.
5. **Truthful game-count declaration** (rules 37-38): the lecturer
   cross-verifies from every team's reports — lying disqualifies.
6. **Re-mint the Gmail token if >5 days old** (Testing-mode tokens die at ~7):
   `uv run python scripts/gmail_auth.py ../secrets/credentials.json`.
7. Set `[email] mode = "send"`; update `sub_game_number`; commit everything.

## Per counted game

1. **EMAIL THE LECTURER THE COMMIT ID** used for this game (rule 53 + App ו
   §2.5) — to rmisegal@gmail.com, manually. The declaration artifact records
   the hash; the email is OUR duty, not the code's.
2. Start `cloudflared tunnel run copthief`, then the peer
   (`uv run p2p-police peer --gui`).
3. After the game: confirm the audit verdict is "Verified OK" on BOTH sides
   and the digests match (mutual audit, rules 35-36) BEFORE agreeing on the
   result.
4. Verify the automatic report email went to rmisegal+uoh26finalgame@gmail.com
   (rule 51) — EACH team sends its own (rule 35; we always send).
5. Verify the game's config artifact landed in `config/games/` and commit it
   (rules 3-4) with the log + result artifacts in `results/`.
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
