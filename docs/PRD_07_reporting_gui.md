# PRD 07 — Reporting & observability (stage 7, delivered)

Goal: the four Table-20 artifacts, automatic Gmail reporting, live GUI and
replay witness (rules 8-9, 20, 30, 32-34, 50-54).
Delivered: declaration/config/log/result with shared game_uid (config
archived to config/games/); watchdog (rule 7) with state persistence;
send-only Gmail over httpx behind the gatekeeper email service, auto-send
when [email].mode=send, REAL delivery verified; verify-log CLI + Tk replay
witness (Verified OK / TAMPERED banners); live belief-map GUI via the
Perception local-truth gate. Evidence: assets/*.png, results/*.json.
