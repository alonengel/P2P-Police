"""Foreign-conformance: our bytes reproduce the official reference's forms.

Vectors from the ImreEyal interop kit (MIT — see tests/vectors/foreign/_README.md)
pin the reference implementation's constructions. If any test here fails, a game
against a reference-derived team dies at negotiation or audits as TAMPERED
(ADR-0004). Scent vectors are deliberately excluded: we follow the BOOK's model.
"""

import hashlib
import json
from pathlib import Path

import pytest

from p2p_police.domain import game_ids
from p2p_police.domain.crypto import canonical, commit_hash
from p2p_police.domain.negotiation import canonical_terms
from p2p_police.report.artifacts import consensus_signature

FOREIGN = Path(__file__).parents[1] / "vectors" / "foreign"


def _load(name: str) -> dict:
    return json.loads((FOREIGN / f"{name}.json").read_text(encoding="utf-8"))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestCanonicalJson:
    def test_all_vectors_reproduce_exact_string_and_hash(self):
        for case in _load("canonical_json")["vectors"]:
            assert canonical(case["object"]) == case["canonical"], case["note"]
            assert _sha(case["canonical"]) == case["sha256"], case["note"]


class TestCommitReveal:
    def test_reference_commit_construction(self):
        for case in _load("commit_reveal")["vectors"]:
            material = f"{canonical(case['payload'])}|{case['nonce']}"
            assert _sha(material) == case["commit"], case["note"]

    def test_our_commit_hash_is_the_reference_construction(self):
        payload = {
            "step": 1, "role": "police", "sub_game": 1, "state_digest": "d" * 64,
            "action": {"type": "move", "direction": "N"}, "hint": "רמז בעברית",
            "verdict": True,
        }
        nonce = "0f1e2d3c4b5a69788796a5b4c3d2e1f0"
        assert commit_hash(payload, nonce) == _sha(f"{canonical(payload)}|{nonce}")

    def test_divergent_forms_are_rejected_not_matched(self):
        case = _load("commit_reveal")["divergent_forms"]
        ours = _sha(f"{canonical(case['payload'])}|{case['nonce']}")
        assert ours == case["reference_form"]
        assert ours != case["book_ch5_listing_form"]
        assert ours != case["book_audit_snippet_form"]


class TestGameUid:
    def test_derived_uid_matches_reference(self):
        for case in _load("game_uid")["vectors"]:
            uid = game_ids.derive_game_uid(case["terms"], case["group_a"], case["group_b"])
            assert uid == case["game_uid"], case["note"]

    def test_uid_is_order_independent(self):
        case = _load("game_uid")["vectors"][0]
        assert game_ids.derive_game_uid(
            case["terms"], case["group_b"], case["group_a"]
        ) == case["game_uid"]


class TestTermsSignature:
    def test_signature_construction_over_terms(self):
        for case in _load("terms_signature")["vectors"]:
            material = f"{canonical_terms(case['terms'])}|{case['nonce']}"
            assert _sha(material) == case["signature"]


class TestReportConsensus:
    def test_spaced_signature_matches_reference(self):
        for case in _load("report_consensus")["vectors"]:
            assert consensus_signature(case["report"]) == case["signature"], case["note"]

    def test_sign_then_insert_roundtrip(self):
        data = _load("report_consensus")
        key = data["signature_key"]
        for case in data["vectors"]:
            signed = dict(case["signed_report"])
            popped = signed.pop(key)
            assert popped == case["signature"]
            assert consensus_signature(signed) == popped

    def test_compact_form_is_a_different_hash(self):
        for case in _load("report_consensus")["vectors"]:
            compact = _sha(canonical(case["report"]))
            assert compact == case["compact_form_sha256"]
            assert compact != case["signature"]


@pytest.mark.parametrize("excluded", ["pheromone", "derive_starts", "joint_seed"])
def test_excluded_vector_families_stay_excluded(excluded):
    """Scent follows the BOOK, not the reference (ADR-0004); opt-in kit
    features were not adopted. Their vectors must not silently appear."""
    assert not (FOREIGN / f"{excluded}.json").exists()
