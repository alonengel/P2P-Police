"""Pairing-vs-fatal refusal classes on the negotiate declarations: a wrong
sub-game window or a role collision is a BYSTANDER (PairingRefusalError,
tolerated by the repush wait); locked-model divergence stays plain-fatal."""

import pytest

from p2p_police.domain.errors import GameRuleError
from p2p_police.wire import terms as wire_terms


def test_pairing_class_refusals_are_bystanders_not_violations():
    """Wrong-window and role-equal refusals classify as PairingRefusalError
    (the repush wait tolerates them: wrong game, not you); they still remain
    GameRuleError so an escape would fail safe as a technical loss."""
    assert issubclass(wire_terms.PairingRefusalError, GameRuleError)
    with pytest.raises(wire_terms.PairingRefusalError):
        wire_terms.verify_declarations({"sub_game_number": 2}, {"sub_game_number": 5})
    with pytest.raises(wire_terms.PairingRefusalError):
        wire_terms.verify_declarations({"role": "police"}, {"role": "police"})


@pytest.mark.parametrize(("field", "ours", "others"), [
    ("scent_model_sha256", "a" * 64, "b" * 64),
    ("info_mode", "belief", "exact"),
])
def test_locked_model_mismatches_stay_plain_fatal_never_pairing(field, ours, others):
    """A locked-model divergence is a genuine violation by our REAL
    counterpart - it must never classify as a tolerable bystander."""
    with pytest.raises(GameRuleError) as caught:
        wire_terms.verify_declarations({field: ours}, {field: others})
    assert not isinstance(caught.value, wire_terms.PairingRefusalError)
