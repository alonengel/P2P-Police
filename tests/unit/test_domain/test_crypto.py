"""Crypto tests encode ch. 5: canonical determinism, nonce uniqueness,
bit-sensitive verification, and the binary tamper verdict (rules 17-19)."""

import pytest

from p2p_police.domain.crypto import (
    audit_records,
    build_step_payload,
    canonical,
    commit_hash,
    new_nonce,
    verify_commit,
)


def make_payload(step: int = 1, hint: str = "Going north!") -> dict:
    return build_step_payload(step, "police", 1, "d" * 8, {"type": "move", "move": "N"}, hint, True)


def test_canonical_is_key_order_independent() -> None:
    assert canonical({"b": 1, "a": [2, 3]}) == canonical({"a": [2, 3], "b": 1})
    assert canonical({"a": 1}) == '{"a":1}'


def test_nonces_are_unique_and_hex() -> None:
    nonces = {new_nonce() for _ in range(100)}
    assert len(nonces) == 100
    assert all(len(n) == 32 and int(n, 16) >= 0 for n in nonces)


def test_commit_verifies_with_right_nonce_only() -> None:
    payload, nonce = make_payload(), new_nonce()
    sealed = commit_hash(payload, nonce)
    assert verify_commit(payload, nonce, sealed)
    assert not verify_commit(payload, new_nonce(), sealed)


def test_single_bit_of_payload_breaks_the_seal() -> None:
    payload, nonce = make_payload(), new_nonce()
    sealed = commit_hash(payload, nonce)
    tampered = dict(payload, hint="Going south!")
    assert not verify_commit(tampered, nonce, sealed)


def test_incomplete_payload_is_rejected_at_sealing() -> None:
    with pytest.raises(ValueError, match="missing fields"):
        commit_hash({"step": 1}, new_nonce())


def test_audit_verifies_clean_log() -> None:
    records, nonces = [], []
    for step in range(1, 4):
        payload, nonce = make_payload(step), new_nonce()
        records.append({"payload": payload, "commit": commit_hash(payload, nonce)})
        nonces.append(nonce)
    assert audit_records(records, nonces) == "Verified OK"


def test_audit_flags_one_tampered_record() -> None:
    """One forged step voids the whole match — no appeal (ch. 7)."""
    records, nonces = [], []
    for step in range(1, 4):
        payload, nonce = make_payload(step), new_nonce()
        records.append({"payload": payload, "commit": commit_hash(payload, nonce)})
        nonces.append(nonce)
    records[1]["payload"]["action"] = {"type": "move", "move": "S"}  # rewrite history
    assert audit_records(records, nonces) == "TAMPERED"


def test_audit_flags_nonce_count_mismatch() -> None:
    payload, nonce = make_payload(), new_nonce()
    records = [{"payload": payload, "commit": commit_hash(payload, nonce)}]
    assert audit_records(records, []) == "TAMPERED"
