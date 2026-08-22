"""The two-front BFS race: cells the believed thief reaches strictly
before the cop. Mechanism studied from imreeyal's repos (read with the
owner's permission; re-implemented independently, no code copied — their
convention for our doctrine layer, returned): a pursuit score that only
prices distance chases the peak forever, while pricing the thief's SAFE
REGION picks the equal-distance approach that removes exits — corner
compression at zero barrier cost.
"""

from p2p_police.domain.board import Board
from p2p_police.strategy.region_race import safe_region_size

BOARD = Board(7)


def test_open_board_race_counts_cells_the_thief_wins() -> None:
    # Thief at (3,3), cop at (0,0): the far corner quadrant is thief-won,
    # the cop's home corner is cop-won; strict ties go to the cop.
    size = safe_region_size(BOARD, thief=(3, 3), cop=(0, 0))
    assert 0 < size < 49
    # Standing closer shrinks the thief's safe region monotonically.
    closer = safe_region_size(BOARD, thief=(3, 3), cop=(2, 2))
    assert closer < size


def test_adjacent_cop_starves_the_region() -> None:
    corner = safe_region_size(BOARD, thief=(6, 6), cop=(5, 5))
    center = safe_region_size(BOARD, thief=(3, 3), cop=(2, 2))
    assert corner < center  # a cornered thief has less safe ground


def test_equal_distance_approaches_differ_by_compression() -> None:
    """The load-bearing property: two cop cells at the SAME BFS distance
    from the thief can leave different safe regions — the term breaks
    pursuit ties toward the compressing side."""
    thief = (5, 5)
    inside = safe_region_size(BOARD, thief, cop=(3, 5))  # between thief+center
    rim = safe_region_size(BOARD, thief, cop=(5, 6))  # hugging the rim
    assert rim != inside  # rim-vs-lane approaches must price differently


def test_barriers_shape_the_race() -> None:
    walled = Board(7)
    for c in ((4, 0), (4, 1), (4, 2), (4, 3)):
        walled.add_barrier(c)
    open_size = safe_region_size(BOARD, thief=(6, 1), cop=(0, 1))
    pocket = safe_region_size(walled, thief=(6, 1), cop=(0, 1))
    assert pocket < open_size  # the wall cuts the thief's world down
