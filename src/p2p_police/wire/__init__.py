"""Hidden-information (reference-v3) wire layer — an ADDITIONAL mode.

The bookletter lockstep runtime (peer/) stays the untouched default; this
package arms only when game.toml sets [network] wire_shape = "reference"
and both peers' negotiation declares the same registry lock-doc hash.
No module here lives in domain/ — the parity-locked physics is imported,
never modified.
"""
