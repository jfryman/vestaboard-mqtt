"""Utility functions for Vestaboard client operations."""

from typing import List

from .board_types import BoardType
from .constants import CHAR_CODE_MAP, DEFAULT_PREVIEW_ROWS, TEXT_TO_CODE_MAP


def format_log_suffix(label: str) -> str:
    """Format an optional log message suffix for API type labels.

    Args:
        label: API type label (e.g., "Local API")

    Returns:
        Formatted suffix string or empty string
    """
    return f" - {label}" if label else ""


def debug_layout_preview(
    layout: List[List[int]], logger, max_preview_rows: int = DEFAULT_PREVIEW_ROWS
) -> None:
    """Generate a readable preview of the layout array for debugging.

    Args:
        layout: Layout array (any dimensions)
        logger: Logger instance for output
        max_preview_rows: Maximum number of rows to preview
    """
    try:
        if not layout:
            logger.debug("Empty layout")
            return

        rows = len(layout)
        cols = len(layout[0]) if layout else 0

        preview_lines = []
        for row_idx, row in enumerate(layout[:max_preview_rows]):
            line = "".join(CHAR_CODE_MAP.get(code, f"[{code}]") for code in row)
            preview_lines.append(f"Row {row_idx + 1}: '{line.strip()}'")

        if rows > max_preview_rows:
            preview_lines.append(f"... ({rows} total rows)")

        logger.debug(f"Layout preview ({rows}x{cols}):")
        for line in preview_lines:
            logger.debug(line)

    except Exception as e:
        logger.warning(f"Preview generation failed: {e}")
        try:
            logger.debug(f"Raw layout dimensions: {len(layout)}x{len(layout[0]) if layout else 0}")
        except Exception:
            logger.debug("Unable to determine layout dimensions")


def text_to_layout(text: str, board_type: BoardType) -> List[List[int]]:
    """Convert text string to layout array.

    This is a simplified conversion that centers text on the first row.
    For production use, consider using Vestaboard's text-to-layout service
    or implementing more sophisticated text wrapping.

    Args:
        text: Text string to convert
        board_type: BoardType enum specifying board dimensions

    Returns:
        Layout array matching board dimensions

    Examples:
        >>> # Standard Vestaboard
        >>> text_to_layout("HELLO", BoardType.STANDARD)  # Returns 6x22 array
        >>> # Vestaboard Note
        >>> text_to_layout("HELLO", BoardType.NOTE)  # Returns 3x15 array
    """
    # Create empty layout
    layout = [[0 for _ in range(board_type.cols)] for _ in range(board_type.rows)]

    # Simple centering on first row
    text_upper = text.upper()[: board_type.cols]  # Truncate to fit width
    start_col = max(0, (board_type.cols - len(text_upper)) // 2)

    for i, char in enumerate(text_upper):
        if start_col + i < board_type.cols:
            layout[0][start_col + i] = TEXT_TO_CODE_MAP.get(char, 0)

    return layout
