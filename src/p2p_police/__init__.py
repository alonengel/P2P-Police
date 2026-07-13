"""P2P-Police: the Cop agent of the distributed Cops-and-Robbers game.

Public API is exposed through the SDK layer (single business entry point);
everything else is an implementation detail.
"""

from p2p_police.shared.version import CODE_VERSION

__version__ = CODE_VERSION
__all__ = ["__version__"]
