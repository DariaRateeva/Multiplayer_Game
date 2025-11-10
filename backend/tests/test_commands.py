"""
Tests for GameManager class.
"""

import pytest
from src.game.board import Board
from src.commands.commands import GameManager


class TestGameManager:
    @pytest.fixture
    def game(self):
        """Create a fresh game for each test."""
        available_cards = {'🎮', '🌈', '🎨'}
        board = Board(3, 2, available_cards)
        return GameManager(board)

    @pytest.mark.asyncio
    async def test_look_returns_board_state(self, game):
        """Test that look() returns correct board state."""
        result = await game.look("Player1")

        assert result["ok"] == True
        assert "width" in result
        assert "height" in result
        assert "board" in result
        assert result["width"] == 3
        assert result["height"] == 2

    @pytest.mark.asyncio
    async def test_look_includes_scores(self, game):
        """Test that look() includes scores."""
        result = await game.look("Player1")

        assert "scores" in result
        assert isinstance(result["scores"], dict)

    @pytest.mark.asyncio
    async def test_flip_face_down_card(self, game):
        """Test flipping a face-down card."""
        result = await game.flip("Player1", 0, 0)

        assert result["ok"] == True
        assert "board" in result
        # ✅ Check for 'state' instead of 'is_face_up'
        assert result["board"][0][0]["state"] in ["my", "up"]  # Should be face-up now
        assert result["board"][0][0]["card"] is not None

    @pytest.mark.asyncio
    async def test_flip_empty_space_fails(self, game):
        """Test flipping an empty space fails."""
        # First remove a card to create empty space
        await game.flip("Player1", 0, 0)
        await game.flip("Player1", 0, 1)

        # If they match, flip again to remove them
        result = await game.look("Player1")
        if result["board"][0][0]["state"] == "my":
            # Cards matched, flip another to trigger removal
            await game.flip("Player1", 1, 0)

            # Now try to flip the removed card
            result = await game.flip("Player1", 0, 0)
            assert result["ok"] == False
            assert "message" in result

    @pytest.mark.asyncio
    async def test_flip_updates_board_state(self, game):
        """Test that flip updates the board state correctly."""
        # Flip first card
        result1 = await game.flip("Player1", 0, 0)
        assert result1["ok"] == True

        # Flip second card
        result2 = await game.flip("Player1", 0, 1)
        assert result2["ok"] == True

        # Check that board is returned with both flips
        assert "board" in result2
        assert "width" in result2
        assert "height" in result2

    def test_serialize_board(self, game):
        """Test board serialization with player_id."""
        # ✅ Call with player_id argument
        board_json = game._serialize_board("Player1")

        assert isinstance(board_json, list)
        assert len(board_json) == 2  # height = 2
        assert len(board_json[0]) == 3  # width = 3

        # Check structure of each cell
        for row in board_json:
            for cell in row:
                assert "state" in cell
                assert cell["state"] in ["down", "up", "my", "none"]
                assert "card" in cell
                assert "controlled_by" in cell
