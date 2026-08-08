# Artifact formats — the four JSON kinds, what each is for, and which one gets emailed

Reference for opponents (and graders) diffing artifacts against ours. Everything
below is read from the files we actually ship, not from intent. The four kinds
follow the rulebook's Table 20; filenames derive from `game_id` + sub-game
number so files from different games can never mix.

## Naming and location

| Kind | Filename | Lives in |
|---|---|---|
| Config | `config_<game_id>_gNN.json` | `config/games/` |
| Log | `log_<game_id>_gNN.json` | `results/` |
| Declaration | `declaration_<game_id>.json` | `results/` |
| Result (series) | `result_<game_id>.json` | `results/` |

`game_id = <first-sorted-group>-vs-<second>` (alphabetical). One config + one
log per sub-game, one declaration + one result per series. All four kinds are
committed and pushed to GitHub per game; **only the result is emailed** (below).

## Shared conventions

- **Canonical JSON** everywhere a hash or signature is involved:
  `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
- **Commit** (sealed record): `SHA256(canonical(payload) + "|" + nonce)`; the
  nonce is revealed only at the end-of-game audit.
- **game_uid**: `UUID(SHA256(canonical(terms) + "|" + "|".join(sorted(group_pair)))[:16])`
  over the flat 14-key terms — both peers derive it independently; every
  artifact of the series carries the same uid.
- **Cells** are `[row, col]`, origin top-left, index 0.
- **Step counting** is per-side: a full survival shows 35 thief steps and 34
  cop steps — same game, different chairs. The agreed game length is the
  thief's count.

## 1. Config — `config_<game_id>_gNN.json`

The signed shared constitution as it applied to ONE sub-game. Top level:

`_schema, agreed_between, board_and_agents, config_name, config_sha256,
game_id, game_uid, links, movement_and_barriers, network_and_league,
pheromones, rate_limiter_gatekeeper, report_type, schema_version, scoring,
sub_game_number, world`

The five parameter sections mirror game.json exactly (board/agents, movement +
barriers incl. `max_barriers 14` / `survival_threshold 35`, pheromones
0.9/0.1/5×5, scoring 20/5/5/10/tie 2, world = setting + hint cap).
`config_sha256` is the canonical hash both sides verified at negotiation;
`agreed_between` names the two groups.

## 2. Log — `log_<game_id>_gNN.json`

One sub-game's full sealed history, from the reporting side's chair:

- `records[]` — OUR sealed half-turns: `{commit, nonce, payload}` where
  `payload = {step, role, sub_game, state_digest, action, hint, verdict}`
  (the pinned 7-field set; `records[0]` is the step-zero declaration carrying
  our `github_commit` — rule 53 rides here).
- `opponent_records[]` — the rival's messages as received: their `commit`,
  their `declared` block (`hint`, `capture_claim`, `barrier_placed`, …) and,
  post-audit, their revealed `payload` (move/intent/position per their reveal).
- `summary` — the settled verdict: `outcome` (capture/survival), `audit`
  ("Verified OK" only when the commit-reveal replay checks out), `end_state_digest`,
  `digest_match`, `disputed_capture`, `turns_completed`, `steps_sealed`,
  `github_commit`, `group_id`/`opponent_group_id`, `opponent_info` (their
  declared identity at handshake), `opponent_step_zero`, `scent_readings_refused`,
  `started_at`/`ended_at`, `gatekeeper` counters.
- `wire_shape` — the negotiated wire (reference-v3 in our pairings).

## 3. Declaration — `declaration_<game_id>.json`

The series' identity record (rules 37-38, 45, 49, 53). Top level:

`_schema, consensus_signature, declaration_type, declared_at, game_ended_at,
game_id, game_started_at, game_uid, groups, links, max_tokens_per_game,
num_sub_games, report_type, schema_version, timezone, token_budget_per_series`

Each `groups` entry declares one team: `group_id, group_name, members
("Name:student-id"), counted_games_played, github_commit, code_version,
llm_model, mcp_servers, repos (BOTH repos, rule 49), hardware_spec +
hardware_spec_sha256, signature`. What a team declares here is what gets
filed — nobody invents the other side's identity values.

## 4. Result — `result_<game_id>.json` — THE emailed report

`report_type: "final_game_result"`, one per series per team, written by the
runner that settles the last window. Top level:

`_schema, final_result, game_id, game_uid, groups, links, mutual_agreement,
num_sub_games, report_type, schema_version, sub_games, timezone`

- `sub_games[]` — one row per game: `sub_game_number, roles, result
  (capture/survival), winner_group, tie, score, tokens, audit
  {log_verified, tampered}, log_files, github_commit (per team, per game),
  started_at, ended_at`.
- `final_result` — the aggregate: `total_score, sub_games_won, ties,
  series_tie, winner_group, tokens_total_series, games_played_including_this
  (per-team counted counters, rules 37-38), first_meeting_between_groups,
  diversity_reward_applied`.
- `mutual_agreement` — `{sha256, confirmed}`: the canonical hash both sides
  computed over the agreed series facts; compare it string-to-string before
  arguing about anything else.
- `links.github` carries both teams' repos (rule 49); `links.log`/`config`
  name the sibling artifacts.

**Email protocol**: the body is the exact canonical bytes of this JSON and the
one attachment is the same bytes under the artifact's filename — so
`sha256(attachment) == sha256(body)` and either can be verified on receipt.
Subject carries the game_id, final score, and winner/series_tie. Friendlies go
to the two teams' own inboxes only; the league address is armed exclusively
for counted games (config + CLI interlock, both halves required).

A per-window sibling (`report_type: "result"`) exists transiently inside a
repo while its runner hasn't seen the full series; the canonical series
artifact is always the `final_game_result` form above. If a field here and a
file we shipped ever disagree, the file wins — tell us and we fix the doc.
