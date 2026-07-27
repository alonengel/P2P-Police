"""Information regimes: what a brain is ALLOWED to know (ADR-0006/0010).

One table, one resolver, one view function. Adding a regime is a row plus a
branch in `brain_view` - not edits scattered through config, runtime and the
handshake, which is what this module exists to prevent.

Each regime declares the wire shapes that can honour it, because legality is
not a matter of taste: `exact` needs replicated engines to read a rival cell
from, and the reference wire structurally has none (`OwnState` holds a
single-key positions dict). Asking for a regime the wire cannot serve is a
configuration error, and it is refused LOUDLY at startup rather than silently
downgraded - a peer that thinks it agreed to one regime and plays another is
the failure this whole seam is meant to make impossible.
"""

BOOKLETTER, REFERENCE = "bookletter", "reference"


class InfoModeError(ValueError):
    """Configured regime is not in the registry, or illegal for this wire."""


class InfoMode:
    """Input: registry row. Output: a legality answer. Setup: frozen at import."""

    def __init__(self, name: str, summary: str, wire_shapes: tuple,
                 needs_peer_agreement: bool) -> None:
        self.name, self.summary = name, summary
        self.wire_shapes = frozenset(wire_shapes)
        self.needs_peer_agreement = needs_peer_agreement

    def serves(self, wire_shape: str) -> bool:
        return wire_shape in self.wire_shapes


MODES: dict[str, InfoMode] = {
    "belief": InfoMode(
        "belief",
        "Dec-POMDP posture: the brain sees only the scent/hint posterior.",
        (BOOKLETTER, REFERENCE), needs_peer_agreement=False),
    "exact": InfoMode(
        "exact",
        "Replicated-engine truth: every position arrived through the agreed "
        "protocol, so it is shared local knowledge (ADR-0006).",
        (BOOKLETTER,), needs_peer_agreement=True),
    # A third regime is designed but deliberately NOT shipped: "derived" would
    # invert the transmitted scent field to the sender's exact cell on the
    # reference wire (ADR-0010). It is a row and a branch away, gated on a
    # both-declare acceptance, and stays unbuilt while belief mode measures at
    # ceiling under league conditions.
}


def resolve(name: str, wire_shape: str | None = None) -> InfoMode:
    """The regime for `name`, checked against the wire that must serve it."""
    mode = MODES.get(name)
    if mode is None:
        raise InfoModeError(
            f"unknown [strategy] info_mode {name!r}; known regimes: "
            f"{', '.join(sorted(MODES))}")
    if wire_shape is not None and not mode.serves(wire_shape):
        raise InfoModeError(
            f"info_mode {name!r} cannot be honoured on the {wire_shape!r} wire "
            f"(it serves: {', '.join(sorted(mode.wire_shapes))})")
    return mode


def brain_view(mode: InfoMode, perception):
    """What the brain is handed this turn: None means 'read the engine'.

    The single extension point. A new regime returns whatever view it grants -
    a posterior, a sharpened posterior, or None for replicated truth.
    """
    if mode.name == "exact":
        return None
    return perception.belief
