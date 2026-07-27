"""Information-regime registry: legality is checked, never assumed.

The failure this guards is specific: a peer that believes it agreed to one
regime and plays another. A typo used to degrade silently to belief on the
reference wire, and an `exact` request on a wire with no rival positions was
ignored rather than refused. Both are now startup errors.
"""

import pytest

from p2p_police.shared.config import Config, ConfigError
from p2p_police.shared.info_modes import (
    BOOKLETTER,
    MODES,
    REFERENCE,
    InfoModeError,
    brain_view,
    resolve,
)


def test_the_shipped_default_serves_every_wire() -> None:
    assert resolve("belief", BOOKLETTER).name == "belief"
    assert resolve("belief", REFERENCE).name == "belief"
    assert MODES["belief"].needs_peer_agreement is False


def test_exact_is_refused_on_a_wire_that_cannot_serve_it() -> None:
    """`exact` reads a rival cell from replicated engines; the reference wire
    structurally has none, so asking for it is a configuration error and not a
    silent downgrade."""
    assert resolve("exact", BOOKLETTER).name == "exact"
    with pytest.raises(InfoModeError, match="cannot be honoured"):
        resolve("exact", REFERENCE)
    assert MODES["exact"].needs_peer_agreement is True  # ADR-0006 both-declare


def test_an_unknown_regime_names_the_known_ones() -> None:
    with pytest.raises(InfoModeError, match="belief, exact"):
        resolve("exakt", BOOKLETTER)


def test_brain_view_is_the_single_extension_point() -> None:
    """Exact hands the brain nothing (it reads the engine); every posterior
    regime hands it a view. A new regime is a row plus a branch here."""
    class _Perception:
        belief = "posterior"

    assert brain_view(resolve("exact"), _Perception()) is None
    assert brain_view(resolve("belief"), _Perception()) == "posterior"


def test_config_surfaces_a_bad_regime_as_a_config_error(config_dir) -> None:
    toml_path = config_dir / "game.toml"
    toml_path.write_text(
        toml_path.read_text(encoding="utf-8") + '\n[strategy]\ninfo_mode = "radar"\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="info_mode"):
        Config.load(config_dir).info_mode()


def test_the_reference_wire_refuses_a_regime_it_cannot_serve(config_dir) -> None:
    """Startup, not mid-game. Asking for replicated-engine truth on the wire
    that structurally has no rival position used to be ignored silently; the
    peer would then declare 'belief' while its config said 'exact'."""
    from p2p_police.shared.info_modes import BOOKLETTER, REFERENCE

    toml_path = config_dir / "game.toml"
    toml_path.write_text(
        toml_path.read_text(encoding="utf-8") + '\n[strategy]\ninfo_mode = "exact"\n',
        encoding="utf-8",
    )
    config = Config.load(config_dir)
    assert config.info_mode(BOOKLETTER) == "exact"
    with pytest.raises(ConfigError, match="cannot be honoured"):
        config.info_mode(REFERENCE)
