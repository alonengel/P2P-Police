# UI — interface documentation (guidelines §10)

## Screens & states (all captured from real games)

| State | Evidence | What the user sees |
|---|---|---|
| Live — YOUR TURN | green banner (see live view) | act-enabled; belief heatmap current |
| Live — LOCKED | gray banner "LOCKED - opponent moving" | input frozen; prevents race conditions (the async FSM made visible) |
| Live — GAME OVER | `assets/live_belief_map.png` | purple banner + final belief state |
| Replay — Verified OK | `assets/replay_verified_ok.png` | green banner, step controls, hint per step |
| Replay — TAMPERED | `assets/replay_tampered_demo.png` | red "TAMPERED - game void" (one rewritten move) |

## Typical workflow

1. `uv run p2p-police peer --gui` → negotiation, then the live window opens.
2. Watch the belief heatmap sharpen as scent + hints arrive; the banner tells
   you whose half-turn it is (YOUR TURN / LOCKED).
3. Game ends → GAME OVER banner; artifacts land in `results/`.
4. `uv run p2p-police replay --log results/log_<id>.json` → step through the
   sealed history with the cryptographic verdict always visible.

## Nielsen's 10 heuristics

1. **Visibility of system status** — the tri-state banner + turn counter + belief peak readout.
2. **Match to the real world** — "YOUR TURN", chase-map metaphor, red = suspicion.
3. **User control & freedom** — replay steps forward/back/first/last freely.
4. **Consistency** — same board renderer, palette and banner across live+replay.
5. **Error prevention** — LOCKED state swallows out-of-turn input; port-busy fails fast with the fix in the message.
6. **Recognition over recall** — hints displayed verbatim; verdict text, not codes.
7. **Flexibility** — GUI optional (headless CLI for automation/CI), `--screenshot` for evidence.
8. **Aesthetic & minimalist** — one board, one banner, one info line; LOCAL truth only (also rule 8-9).
9. **Error recognition & recovery** — TAMPERED names the condition and the consequence ("game void"); ConfigError messages say which file/key.
10. **Help & documentation** — README manual, `--help` on every command, runbooks in docs/.

## Accessibility

High-contrast palette on dark background; color never the sole signal (banner
TEXT states the mode); keyboard-free replay via large buttons; window scales
from `[gui]`-configurable cell size; DPI-aware rendering on Windows.
