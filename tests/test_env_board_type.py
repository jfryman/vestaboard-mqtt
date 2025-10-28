"""Tests for board type environment variable parsing."""

import os
import pytest
from unittest.mock import patch
from src.vestaboard_client import (
    BoardType,
    create_vestaboard_client,
    VestaboardClient,
    LocalVestaboardClient,
)


class TestBoardTypeEnvironmentVariable:
    """Test VESTABOARD_BOARD_TYPE environment variable parsing."""

    def test_default_board_type_when_no_env_var(self):
        """Test that default is standard board when no env var set."""
        with patch.dict(os.environ, {"VESTABOARD_API_KEY": "test_key"}, clear=True):
            # Remove VESTABOARD_BOARD_TYPE if it exists
            os.environ.pop('VESTABOARD_BOARD_TYPE', None)
            client = create_vestaboard_client()
            assert client.board_rows == 6
            assert client.board_cols == 22

    def test_board_type_standard_lowercase(self):
        """Test VESTABOARD_BOARD_TYPE=standard."""
        with patch.dict(os.environ, {
            "VESTABOARD_API_KEY": "test_key",
            "VESTABOARD_BOARD_TYPE": "standard"
        }):
            client = create_vestaboard_client()
            assert client.board_rows == 6
            assert client.board_cols == 22

    def test_board_type_standard_uppercase(self):
        """Test VESTABOARD_BOARD_TYPE=STANDARD (case insensitive)."""
        with patch.dict(os.environ, {
            "VESTABOARD_API_KEY": "test_key",
            "VESTABOARD_BOARD_TYPE": "STANDARD"
        }):
            client = create_vestaboard_client()
            assert client.board_rows == 6
            assert client.board_cols == 22

    def test_board_type_note_lowercase(self):
        """Test VESTABOARD_BOARD_TYPE=note."""
        with patch.dict(os.environ, {
            "VESTABOARD_API_KEY": "test_key",
            "VESTABOARD_BOARD_TYPE": "note"
        }):
            client = create_vestaboard_client()
            assert client.board_rows == 3
            assert client.board_cols == 15

    def test_board_type_note_uppercase(self):
        """Test VESTABOARD_BOARD_TYPE=NOTE (case insensitive)."""
        with patch.dict(os.environ, {
            "VESTABOARD_API_KEY": "test_key",
            "VESTABOARD_BOARD_TYPE": "NOTE"
        }):
            client = create_vestaboard_client()
            assert client.board_rows == 3
            assert client.board_cols == 15

    def test_board_type_custom_dimensions(self):
        """Test VESTABOARD_BOARD_TYPE with custom dimensions (rows,cols)."""
        with patch.dict(os.environ, {
            "VESTABOARD_API_KEY": "test_key",
            "VESTABOARD_BOARD_TYPE": "4,20"
        }):
            client = create_vestaboard_client()
            assert client.board_rows == 4
            assert client.board_cols == 20

    def test_board_type_custom_dimensions_with_spaces(self):
        """Test custom dimensions with spaces around comma."""
        with patch.dict(os.environ, {
            "VESTABOARD_API_KEY": "test_key",
            "VESTABOARD_BOARD_TYPE": "3 , 15"
        }):
            client = create_vestaboard_client()
            assert client.board_rows == 3
            assert client.board_cols == 15

    def test_board_type_note_dimensions_match_constant(self):
        """Test that 'note' env var produces same dimensions as BoardType.NOTE."""
        with patch.dict(os.environ, {
            "VESTABOARD_API_KEY": "test_key",
            "VESTABOARD_BOARD_TYPE": "note"
        }):
            client = create_vestaboard_client()
            assert (client.board_rows, client.board_cols) == BoardType.NOTE

    def test_board_type_parameter_overrides_env_var(self):
        """Test that explicit board_type parameter overrides env var."""
        with patch.dict(os.environ, {
            "VESTABOARD_API_KEY": "test_key",
            "VESTABOARD_BOARD_TYPE": "note"  # Set to note
        }):
            # But pass standard explicitly
            client = create_vestaboard_client(board_type=BoardType.STANDARD)
            assert client.board_rows == 6
            assert client.board_cols == 22

    def test_invalid_board_type_raises_error(self):
        """Test that invalid board type string raises ValueError."""
        with patch.dict(os.environ, {
            "VESTABOARD_API_KEY": "test_key",
            "VESTABOARD_BOARD_TYPE": "invalid_type"
        }):
            with pytest.raises(ValueError, match="Unknown VESTABOARD_BOARD_TYPE"):
                create_vestaboard_client()

    def test_invalid_custom_dimensions_raises_error(self):
        """Test that invalid custom dimensions format raises ValueError."""
        with patch.dict(os.environ, {
            "VESTABOARD_API_KEY": "test_key",
            "VESTABOARD_BOARD_TYPE": "not_numbers,here"
        }):
            with pytest.raises(ValueError, match="Invalid VESTABOARD_BOARD_TYPE format"):
                create_vestaboard_client()

    def test_empty_board_type_defaults_to_standard(self):
        """Test that empty VESTABOARD_BOARD_TYPE defaults to standard."""
        with patch.dict(os.environ, {
            "VESTABOARD_API_KEY": "test_key",
            "VESTABOARD_BOARD_TYPE": ""
        }):
            client = create_vestaboard_client()
            assert client.board_rows == 6
            assert client.board_cols == 22


class TestBoardTypeWithLocalApi:
    """Test board type configuration with Local API mode."""

    def test_note_board_with_local_api(self):
        """Test Vestaboard Note with Local API."""
        with patch.dict(os.environ, {
            "VESTABOARD_API_KEY": "test_key",
            "VESTABOARD_BOARD_TYPE": "note",
            "USE_LOCAL_API": "true"
        }):
            client = create_vestaboard_client()
            assert isinstance(client, LocalVestaboardClient)
            assert client.board_rows == 3
            assert client.board_cols == 15

    def test_standard_board_with_local_api(self):
        """Test standard Vestaboard with Local API."""
        with patch.dict(os.environ, {
            "VESTABOARD_API_KEY": "test_key",
            "VESTABOARD_BOARD_TYPE": "standard",
            "USE_LOCAL_API": "true"
        }):
            client = create_vestaboard_client()
            assert isinstance(client, LocalVestaboardClient)
            assert client.board_rows == 6
            assert client.board_cols == 22

    def test_custom_board_with_cloud_api(self):
        """Test custom board dimensions with Cloud API."""
        with patch.dict(os.environ, {
            "VESTABOARD_API_KEY": "test_key",
            "VESTABOARD_BOARD_TYPE": "5,18"
        }):
            client = create_vestaboard_client(use_local_api=False)
            assert isinstance(client, VestaboardClient)
            assert client.board_rows == 5
            assert client.board_cols == 18


@pytest.mark.parametrize("env_value,expected_rows,expected_cols", [
    ("standard", 6, 22),
    ("STANDARD", 6, 22),
    ("note", 3, 15),
    ("NOTE", 3, 15),
    ("3,15", 3, 15),
    ("6,22", 6, 22),
    ("4,20", 4, 20),
    ("", 6, 22),  # Empty defaults to standard
])
def test_board_type_env_parsing_parametrized(env_value, expected_rows, expected_cols):
    """Parametrized test for various VESTABOARD_BOARD_TYPE values."""
    with patch.dict(os.environ, {
        "VESTABOARD_API_KEY": "test_key",
        "VESTABOARD_BOARD_TYPE": env_value
    }):
        client = create_vestaboard_client()
        assert client.board_rows == expected_rows
        assert client.board_cols == expected_cols


@pytest.mark.parametrize("invalid_value", [
    "invalid",
    "small",
    "large",
    "3x15",  # Wrong separator
    "3-15",  # Wrong separator
    "abc,def",  # Non-numeric
    "3",  # Only one dimension
    "3,15,2",  # Too many dimensions
])
def test_invalid_board_type_values(invalid_value):
    """Parametrized test for invalid VESTABOARD_BOARD_TYPE values."""
    with patch.dict(os.environ, {
        "VESTABOARD_API_KEY": "test_key",
        "VESTABOARD_BOARD_TYPE": invalid_value
    }):
        with pytest.raises(ValueError):
            create_vestaboard_client()
