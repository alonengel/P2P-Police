"""The shared game.json must validate against the published interop schema
(adapted from Renat Karimov's parallel scaffold) - and the schema must
reject Appendix-VI violations independently of the Python validators."""

import json
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).parents[3]
SCHEMA = json.loads((REPO / "config" / "game.schema.json").read_text(encoding="utf-8"))


def test_shipped_config_validates() -> None:
    config = json.loads((REPO / "config" / "game.json").read_text(encoding="utf-8"))
    jsonschema.validate(config, SCHEMA)


def test_schema_rejects_fixed_value_drift(shared_terms: dict) -> None:
    shared_terms["scoring"]["capture_cop"] = 25
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(shared_terms, SCHEMA)


def test_schema_rejects_lowered_minimum(shared_terms: dict) -> None:
    shared_terms["board_and_agents"]["grid_size"] = 5
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(shared_terms, SCHEMA)


def test_schema_rejects_diagonal_move_set(shared_terms: dict) -> None:
    shared_terms["movement_and_barriers"]["move_set"] = ["N", "S", "E", "W", "NE", "STAY"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(shared_terms, SCHEMA)
