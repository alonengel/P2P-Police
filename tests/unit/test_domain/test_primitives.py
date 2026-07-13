"""Primitives encode the rulebook's coordinate convention: top-left origin,
zero-indexed, rows grow downward (N = row-1). Diagonals do not exist."""

from p2p_police.domain.primitives import Move, Role


def test_move_set_is_exactly_four_orthogonals_plus_stay() -> None:
    assert {m.name for m in Move} == {"N", "S", "E", "W", "STAY"}


def test_north_decreases_row_in_top_left_origin() -> None:
    assert Move.N.applied_to((3, 3)) == (2, 3)


def test_south_increases_row() -> None:
    assert Move.S.applied_to((3, 3)) == (4, 3)


def test_east_increases_col_and_west_decreases() -> None:
    assert Move.E.applied_to((3, 3)) == (3, 4)
    assert Move.W.applied_to((3, 3)) == (3, 2)


def test_stay_keeps_the_cell() -> None:
    assert Move.STAY.applied_to((0, 0)) == (0, 0)


def test_no_move_changes_both_axes() -> None:
    """A move touching both row and col would be a diagonal — forbidden."""
    for move in Move:
        row_delta, col_delta = move.delta
        assert row_delta == 0 or col_delta == 0


def test_roles_are_mutual_rivals() -> None:
    assert Role.POLICE.rival is Role.THIEF
    assert Role.THIEF.rival is Role.POLICE
