"""Tonight's REAL cross-team game logs must verify clean (2026-07-24).

These are the actual working-tree artifacts of the first full games against
a foreign-schema rival: 35 completed turns, every live commit recorded, and
the old audit still rendered TAMPERED/digest_match=false because it judged
the rival's half by OUR payload schema and OUR digest construction. After
the fix, the ch. 7 replay verifier must render every such log Verified OK —
commit-clean, foreign schema tolerated, no team named here (the artifacts
speak for themselves)."""

import json
from pathlib import Path

from p2p_police.sdk.sdk import SimulationSdk

RESULTS = Path(__file__).resolve().parents[3] / "docs/evidence/discarded-series"


def foreign_reference_logs() -> list[Path]:
    """Hidden-wire logs of games against a FOREIGN group (not self-play)."""
    found = []
    for path in sorted(RESULTS.glob("log_*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        summary = doc.get("summary", {})
        if doc.get("wire_shape") == "reference" and \
                summary.get("opponent_group_id") not in (summary.get("group_id"), None):
            found.append(path)
    return found


def test_the_full_cross_team_game_logs_exist() -> None:
    """Non-vacuity: at least one foreign game reached the audit with the
    rival's live commits on record (the 35-turn games this fix is for)."""
    played = [path for path in foreign_reference_logs()
              if json.loads(path.read_text(encoding="utf-8"))["opponent_records"]]
    assert played, "no cross-team hidden-wire log with live rival commits found"


def test_foreign_schema_rival_game_logs_verify_ok() -> None:
    """The fix, proven on tonight's actual files: our side of a real foreign
    game replays Verified OK — never TAMPERED for the rival's schema."""
    for path in foreign_reference_logs():
        # startswith: absent their config artifact the verdict carries the
        # named seals-only qualifier — still never TAMPERED for the schema
        assert SimulationSdk.verify_log(str(path)).startswith("Verified OK"), path.name


def test_forging_our_half_of_the_real_log_still_reads_tampered(tmp_path) -> None:
    """Fairness is not laxity: flip one sealed byte of the SAME real log and
    the commit criterion must still convict."""
    source = max(foreign_reference_logs(),
                 key=lambda p: bool(json.loads(p.read_text(encoding="utf-8"))["records"]))
    doc = json.loads(source.read_text(encoding="utf-8"))
    doc["records"][0]["payload"]["hint"] = "forged after the fact"
    forged = tmp_path / source.name
    forged.write_text(json.dumps(doc), encoding="utf-8")
    assert SimulationSdk.verify_log(str(forged)) == "TAMPERED"
