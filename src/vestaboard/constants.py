"""Vestaboard character code mappings and constants."""

# Vestaboard character code mapping (shared across all clients)
# Official mapping from https://docs.vestaboard.com/docs/charactercodes/
CHAR_CODE_MAP = {
    0: ' ',   # blank
    **{i: chr(ord('A') + i - 1) for i in range(1, 27)},  # A-Z (1-26)
    27: '1', 28: '2', 29: '3', 30: '4', 31: '5', 32: '6',  # 1-9 (27-35)
    33: '7', 34: '8', 35: '9', 36: '0',                    # 0 is 36
    37: '!', 38: '@', 39: '#', 40: '$', 41: '(', 42: ')',  # punctuation
    44: '-', 46: '+', 47: '&', 48: '=', 49: ';', 50: ':',  # punctuation continued
    52: "'", 53: '"', 54: '%', 55: ',', 56: '.', 59: '/',  # punctuation continued
    60: '?', 62: '♥',  # question mark, heart (Note) / degree (Flagship)
    # Color codes
    63: '🟥', 64: '🟧', 65: '🟨', 66: '🟩', 67: '🟦', 68: '🟪',  # red, orange, yellow, green, blue, violet
    69: '⬜', 70: '⬛', 71: '⬛'  # white, black, filled
}

# Reverse mapping for text-to-code conversion
TEXT_TO_CODE_MAP = {
    ' ': 0,
    **{chr(ord('A') + i): i + 1 for i in range(26)},  # A-Z -> 1-26
    '1': 27, '2': 28, '3': 29, '4': 30, '5': 31,       # 1-9 -> 27-35
    '6': 32, '7': 33, '8': 34, '9': 35, '0': 36,       # 0 -> 36
    '!': 37, '@': 38, '#': 39, '$': 40, '(': 41, ')': 42,  # punctuation
    '-': 44, '+': 46, '&': 47, '=': 48, ';': 49, ':': 50,  # punctuation continued
    "'": 52, '"': 53, '%': 54, ',': 55, '.': 56, '/': 59,  # punctuation continued
    '?': 60, '♥': 62, '❤': 62,  # question mark, heart (both ♥ and ❤ map to same code)
    # Color codes (emoji to code mapping)
    '🟥': 63, '🟧': 64, '🟨': 65, '🟩': 66, '🟦': 67, '🟪': 68,  # red, orange, yellow, green, blue, violet
    '⬜': 69, '⬛': 70, '■': 71  # white, black, filled
}

# Default preview rows for debug output
DEFAULT_PREVIEW_ROWS = 3

# Queue processing delay
QUEUE_PROCESSING_DELAY = 0.1  # seconds between immediate queue processing attempts
