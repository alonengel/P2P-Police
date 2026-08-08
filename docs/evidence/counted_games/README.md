# Counted-game evidence archive

One directory per rival team, holding this repo's half of the FULL four-kind
artifact set (config / log / declaration / result) for the one counted series
against that pairing (rule 52), exactly as filed with the league. Nothing in
here is ever overwritten — the canonical working paths (`results/`,
`config/games/`) hold whatever series played last; THIS is the permanent
record of the ones that count.

MANIFEST.txt in each directory hashes the exact bytes committed. Third-party
verification (interop kit): point `tools/check_artifacts.py` at a directory
here — each holds all four kinds, which is the layout the kit expects; the
kit's two-directory join across the police and thief repos' copies prints the
full-series agreement.
