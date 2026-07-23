"""Hidden-wire disqualification guards: rules 8-9, 18, 21-22, 25.

Every rule-sensitive surface the reference-v3 mode adds gets a
machine-checked invariant - a violating edit fails CI with the rule number
in the message instead of failing the project at audit.
"""

import ast
import json
import random
from pathlib import Path

import pytest

from p2p_police.domain.primitives import Outcome, Role
from p2p_police.domain.rules import RuleSet
from p2p_police.infra.mcp_server import PeerInboxes
from p2p_police.peer.perception import Perception
from p2p_police.shared.config import Config
from p2p_police.strategy.brain_base import RandomBrain
from p2p_police.wire import codec, hidden_turns
from p2p_police.wire.hidden_exchange import HiddenExchange
from p2p_police.wire.hidden_runtime import HiddenRuntime
from p2p_police.wire.own_state import OwnState

WIRE = Path("src/p2p_police/wire")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = {name.name for node in ast.walk(tree)
             if isinstance(node, ast.Import) for name in node.names}
    found |= {node.module for node in ast.walk(tree)
              if isinstance(node, ast.ImportFrom) and node.module}
    return found


def test_rule_25_no_llm_reachable_from_wire_modules():
    """Moves stay pure Python: no wire module may import the LLM provider,
    and only the runtime (hint chain assembly, like peer/runtime.py) may
    even see the talk providers."""
    for path in sorted(WIRE.glob("*.py")):
        found = _imports(path)
        assert "p2p_police.infra.llm_provider" not in found, f"rule 25: {path.name}"
        if path.name != "hidden_runtime.py":
            assert "p2p_police.strategy.talk_providers" not in found, \
                f"rule 25: {path.name} touches the talk chain"


def test_rules_8_9_snapshot_shows_local_truth_only():
    """The live view fed from a hidden game can only ever show MY cell,
    belief and public barriers - OwnState has no rival cell to leak."""
    own = OwnState(Role.POLICE, 7, (0, 0), RuleSet(14, 35, 35))
    perception = Perception(Role.POLICE, 7)
    seen = {}
    perception.on_snapshot = seen.update
    perception.emit(own, 1)
    assert seen["my_cell"] == (0, 0)
    assert Role.THIEF not in own.positions  # rules 8-9: structurally absent
    with pytest.raises(KeyError):
        _ = own.positions[Role.THIEF]


def test_rule_18_live_wire_carries_commit_only():
    """Neither the nonce, the action, nor the intent verdict rides a live
    TurnMessage - reveals happen at the audit boundary, together."""
    exchange = HiddenExchange(Role.POLICE, 1, lambda _m: None, None, turn_timeout=5)
    commit = exchange.seal_step("d" * 64, 1, {"type": "move", "move": "E"}, "a hint", False)
    message = codec.build_turn_message(
        1, "police", "a hint", {"0,0": 0.9}, commit, capture_claim=[0, 1])
    record = exchange.own_records[0]
    blob = json.dumps(message, ensure_ascii=False)
    assert record["nonce"] not in blob, "rule 18: nonce leaked pre-audit"
    for secret in ("nonce", "action", "verdict", "payload", "move"):
        assert secret not in message, f"rule 18/deception: {secret} on the live wire"
    assert '"E"' not in blob  # the move itself stays sealed until audit


def _thief_runtime(config_dir, sent):
    config = Config.load(config_dir)
    config.private["network"]["wire_shape"] = "reference"

    class StubTransport:
        def send_turn(self, payload, _deadline):
            sent.append(payload)
            return {"accepted": True}

    inboxes = PeerInboxes()
    own = OwnState(Role.THIEF, config.grid_size, config.thief_start, config.rule_set())
    runtime = HiddenRuntime(Role.THIEF, config, own, StubTransport(), inboxes,
                            RandomBrain(Role.THIEF, random.Random(1)))
    # Mid-round posture: the thief opened (its step 1 is out), the police
    # holds the token — its message is the one under test.
    runtime.own.next_actor = Role.POLICE
    runtime.my_step = 1
    return runtime, inboxes


def test_rules_21_22_hit_claim_forces_an_immediate_honest_concession(config_dir):
    sent = []
    runtime, inboxes = _thief_runtime(config_dir, sent)
    inboxes.turns.put(codec.build_turn_message(
        1, "police", "got you now", {}, "c" * 64, capture_claim=[3, 3]))
    hidden_turns.their_half_turn(runtime)
    assert runtime.own.outcome is Outcome.CAPTURE
    assert sent[-1]["claim_response"] == {"claim": [3, 3], "caught": True}
    assert sent[-1]["step"] == 2  # the concede is OUR next own step


def test_rules_21_22_missed_claim_answered_truthfully_false(config_dir):
    sent = []
    runtime, inboxes = _thief_runtime(config_dir, sent)
    inboxes.turns.put(codec.build_turn_message(
        1, "police", "hmm where", {}, "c" * 64, capture_claim=[0, 0]))
    hidden_turns.their_half_turn(runtime)
    assert runtime.own.outcome is Outcome.ONGOING
    assert runtime.pending_claim_response == {"claim": [0, 0], "caught": False}
    assert sent == []  # the answer rides our NEXT turn message


def test_rules_21_22_barrier_on_our_cell_forces_the_concession(config_dir):
    sent = []
    runtime, inboxes = _thief_runtime(config_dir, sent)
    inboxes.turns.put(codec.build_turn_message(
        1, "police", "walls closing in", {}, "c" * 64, barrier_placed=[3, 3]))
    hidden_turns.their_half_turn(runtime)
    assert runtime.own.outcome is Outcome.CAPTURE
    assert sent[-1]["claim_response"] == {"claim": [3, 3], "caught": True}


def _police_runtime(config_dir, sent):
    config = Config.load(config_dir)
    config.private["network"]["wire_shape"] = "reference"

    class StubTransport:
        def send_turn(self, payload, _deadline):
            sent.append(payload)
            return {"accepted": True}

    inboxes = PeerInboxes()
    own = OwnState(Role.POLICE, config.grid_size, config.cop_start, config.rule_set())
    runtime = HiddenRuntime(Role.POLICE, config, own, StubTransport(), inboxes,
                            RandomBrain(Role.POLICE, random.Random(1)))
    return runtime, inboxes


def test_demo_style_final_reusing_the_last_step_is_consumed_not_deduped(config_dir):
    """Reference interop: the demo's send_final re-uses the sender's LAST
    step number (no apply_move before it). Our receiver keys any caught=True
    final to its LIVE expectation, so the concession we are owed lands
    instead of being dropped as an at-least-once duplicate of step 1."""
    sent = []
    runtime, inboxes = _police_runtime(config_dir, sent)
    inboxes.turns.put(codec.build_turn_message(1, "thief", "catch me", {}, "a" * 64))
    hidden_turns.their_half_turn(runtime)  # thief's step 1 consumed
    hidden_turns.my_half_turn(runtime)     # our step 1 + landing claim out
    inboxes.turns.put(codec.build_turn_message(
        1, "thief", codec.FINAL_CAUGHT_HINT, {}, "b" * 64,
        claim_response={"claim": [3, 3], "caught": True}))
    hidden_turns.their_half_turn(runtime)  # expects thief 2; final says 1
    assert runtime.own.outcome is Outcome.CAPTURE
    assert [r["commit"] for r in runtime.exchange.their_records] == ["a" * 64, "b" * 64]


def test_our_own_echoed_message_is_dropped_never_fatal(config_dir):
    """Per-sender numbering makes MY step N collide with the rival's step N
    in the (kind, turn) keyspace — an echo of OUR OWN message is transport
    noise the wait adapter drops; the rival's real message still lands."""
    sent = []
    runtime, inboxes = _police_runtime(config_dir, sent)
    inboxes.turns.put(codec.build_turn_message(1, "police", "echo of us", {}, "e" * 64))
    inboxes.turns.put(codec.build_turn_message(1, "thief", "the real one", {}, "a" * 64))
    hidden_turns.their_half_turn(runtime)
    assert runtime.own.outcome is Outcome.ONGOING
    assert [r["commit"] for r in runtime.exchange.their_records] == ["a" * 64]
