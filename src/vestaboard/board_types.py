"""Vestaboard board type definitions."""

from enum import Enum


class BoardType(Enum):
    """Vestaboard board type with dimensions."""

    STANDARD = ("standard", 6, 22)  # Standard Vestaboard (6 rows x 22 columns)
    NOTE = ("note", 3, 15)           # Vestaboard Note (3 rows x 15 columns)

    def __init__(self, name: str, rows: int, cols: int):
        self._type_name = name
        self._rows = rows
        self._cols = cols

    @property
    def rows(self) -> int:
        """Number of rows on this board."""
        return self._rows

    @property
    def cols(self) -> int:
        """Number of columns on this board."""
        return self._cols

    @property
    def type_name(self) -> str:
        """String name of this board type."""
        return self._type_name

    @classmethod
    def from_string(cls, value: str) -> 'BoardType':
        """Parse board type from string.

        Args:
            value: Board type string ('standard' or 'note', case-insensitive)

        Returns:
            BoardType enum member

        Raises:
            ValueError: If value is not a valid board type

        Examples:
            >>> BoardType.from_string("standard")
            <BoardType.STANDARD: ('standard', 6, 22)>
            >>> BoardType.from_string("NOTE")
            <BoardType.NOTE: ('note', 3, 15)>
        """
        value_lower = value.lower().strip()

        if value_lower in ("standard", ""):
            return cls.STANDARD
        elif value_lower == "note":
            return cls.NOTE
        else:
            raise ValueError(f"Unknown board_type: '{value}'. Valid options: 'standard' or 'note'")

    def __str__(self) -> str:
        """String representation."""
        return f"{self.type_name} ({self.rows}x{self.cols})"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"BoardType.{self.name}"
