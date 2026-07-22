"""Third-party PAIR verification (league tooling, offline over saved files).

Given BOTH teams' log artifacts of the same game, verify each side alone
(the ch. 7 replay engine: commits + physics recompute) and then cross-check
that the two sealed views describe ONE game: same game_uid, same end-state
digest, same outcome, and every record one side sealed byte-equal to what
the other side received (commit equality is the cryptographic anchor).
Never touches a live game - input is files, output is a verdict dict.
"""

import json
from pathlib import Path

_EXCLUDED = ("verdict",)  # intent flags may be absent pre-audit on the rival's copy


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _by_key(records: list[dict]) -> dict:
    """Payload-carrying records only: on the hidden wire a failed/absent
    audit leaves commit-only opponent records — those surface as 'missing
    from the rival's view' problems instead of crashing the verifier."""
    return {(r["payload"]["step"], r["payload"]["role"]): r
            for r in records if "payload" in r}


def _public(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k not in _EXCLUDED}


def cross_check(doc_a: dict, doc_b: dict) -> list[str]:
    """Consistency problems between the two logs ([] = one coherent game)."""
    problems = []
    if doc_a.get("game_uid") != doc_b.get("game_uid"):
        problems.append("game_uid differs - these logs are not the same game")
    sum_a, sum_b = doc_a.get("summary", {}), doc_b.get("summary", {})
    if sum_a.get("end_state_digest") != sum_b.get("end_state_digest"):
        problems.append("end_state_digest differs - the sides ended in different worlds")
    if sum_a.get("outcome") != sum_b.get("outcome"):
        problems.append(f"outcome differs: {sum_a.get('outcome')!r} vs {sum_b.get('outcome')!r}")
    for own_doc, other_doc, label in ((doc_a, doc_b, "A"), (doc_b, doc_a, "B")):
        own = _by_key(own_doc.get("records", []))
        seen = _by_key(other_doc.get("opponent_records", []))
        for key, record in own.items():
            other = seen.get(key)
            if other is None:
                problems.append(f"side {label} step {key[0]}: missing from the rival's view")
            elif other["commit"] != record["commit"]:
                problems.append(f"side {label} step {key[0]}: commit differs across the logs")
            elif _public(other["payload"]) != _public(record["payload"]):
                problems.append(f"side {label} step {key[0]}: payload differs under one commit")
    return problems


def verify_pair(path_a: str | Path, path_b: str | Path) -> dict:
    """Full pair verdict. overall: Verified OK | TAMPERED | CROSS-MISMATCH."""
    from p2p_police.sdk.sdk import SimulationSdk  # local: sdk composes report

    doc_a, doc_b = _load(path_a), _load(path_b)
    verdict_a = SimulationSdk.verify_log(str(path_a))
    verdict_b = SimulationSdk.verify_log(str(path_b))
    problems = cross_check(doc_a, doc_b)
    if "TAMPERED" in (verdict_a, verdict_b):
        overall = "TAMPERED"
    else:
        overall = "CROSS-MISMATCH" if problems else "Verified OK"
    return {
        "game_uid": doc_a.get("game_uid"),
        "sides": [doc.get("summary", {}).get("group_id", "?") for doc in (doc_a, doc_b)],
        "verdict_a": verdict_a,
        "verdict_b": verdict_b,
        "problems": problems,
        "overall": overall,
    }
