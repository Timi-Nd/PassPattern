"""Immutable key positions and physical adjacency for US QWERTY."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class KeyboardLayout:
    """A fixed physical keyboard coordinate map.

    Coordinates use quarter-key horizontal units and one row per vertical unit.
    Same-row keys are adjacent at one-key spacing; adjacent rows are neighbors
    when their horizontal centers differ by at most three quarter-key units.
    """

    name: str
    positions: Mapping[str, tuple[int, int]]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("layout name must be a non-empty string.")
        if not isinstance(self.positions, Mapping) or not self.positions:
            raise ValueError("positions must be a non-empty mapping.")
        copied: dict[str, tuple[int, int]] = {}
        for key, position in self.positions.items():
            if (
                not isinstance(key, str)
                or len(key) != 1
                or not (("a" <= key <= "z") or ("0" <= key <= "9"))
            ):
                raise ValueError("layout keys must be single lowercase ASCII letters or digits.")
            if (
                not isinstance(position, tuple)
                or len(position) != 2
                or any(
                    isinstance(coordinate, bool) or not isinstance(coordinate, int)
                    for coordinate in position
                )
            ):
                raise ValueError("key positions must be pairs of integer coordinates.")
            copied[key] = position
        object.__setattr__(self, "positions", MappingProxyType(copied))

    def are_neighbors(self, first: str, second: str) -> bool:
        """Return whether two distinct keys touch under the documented model."""
        first_position = self.positions.get(first)
        second_position = self.positions.get(second)
        if first_position is None or second_position is None or first == second:
            return False
        dx = abs(first_position[0] - second_position[0])
        dy = abs(first_position[1] - second_position[1])
        if dy == 0:
            return dx == 4
        return dy == 1 and dx <= 3

    def direction(self, first: str, second: str) -> tuple[int, int]:
        """Return the eight-way compass direction between neighboring keys."""
        first_position = self.positions[first]
        second_position = self.positions[second]
        dx = second_position[0] - first_position[0]
        dy = second_position[1] - first_position[1]
        return _sign(dx), _sign(dy)


def _qwerty_positions() -> dict[str, tuple[int, int]]:
    positions: dict[str, tuple[int, int]] = {}
    rows = (
        ("1234567890", 0, 0),
        ("qwertyuiop", 2, 1),
        ("asdfghjkl", 3, 2),
        ("zxcvbnm", 5, 3),
    )
    for characters, offset, row in rows:
        for index, character in enumerate(characters):
            positions[character] = (offset + index * 4, row)
    return positions


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


US_QWERTY = KeyboardLayout("us_qwerty", _qwerty_positions())
