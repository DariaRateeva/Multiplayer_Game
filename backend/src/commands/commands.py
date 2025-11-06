"""
Commands module for Memory Scramble game.

This module provides the interface for the HTTP API to interact with the Board.
All game logic stays in the Board ADT.
"""

from typing import Dict, Any, Optional
from src.game.board import Board


class GameManager:
    """
    Manages a single game session with a board.

    Tracks:
    - The board state
    - Player scores
    """

    def __init__(self, board: Board) -> None:
        """Initialize a game session with a board."""
        self.board = board
        self.scores: Dict[str, int] = {}
        print(f"✅ GameManager initialized: {board.width}x{board.height} board")

    def look(self, player_id: str) -> Dict[str, Any]:
        """
        Look at the current board state.

        Returns:
        {
            "board": [[{"card": str|None, "is_face_up": bool, "controlled_by": str|None}, ...]],
            "width": int,
            "height": int,
            "scores": {player_id: score}
        }
        """
        try:
            board_grid = self._serialize_board()
            result = {
                "board": board_grid,
                "width": self.board.width,
                "height": self.board.height,
                "scores": self.scores,
                "ok": True
            }
            print(f"✅ Look for {player_id}: board is {self.board.width}x{self.board.height}")
            return result
        except Exception as e:
            print(f"❌ Error in look(): {e}")
            import traceback
            traceback.print_exc()
            raise

    def flip(self, player_id: str, x: int, y: int) -> Dict[str, Any]:
        """
        Flip a card at position (x, y).

        Returns:
        {
            "ok": bool,
            "message": str,
            "board": [[...]],
            "scores": {...}
        }
        """
        try:
            # Validate bounds
            if x < 0 or x >= self.board.width or y < 0 or y >= self.board.height:
                return {
                    "ok": False,
                    "message": f"Position ({x}, {y}) out of bounds ({self.board.width}x{self.board.height})",
                    "board": self._serialize_board(),
                    "scores": self.scores
                }

            # Get the space
            space = self.board.get_space(x, y)

            # Can't flip empty space
            if space.card is None:
                return {
                    "ok": False,
                    "message": f"No card at ({x}, {y})",
                    "board": self._serialize_board(),
                    "scores": self.scores
                }

            # If card is already face-up and controlled by someone else, reject
            if space.is_face_up and space.controlled_by is not None and space.controlled_by != player_id:
                return {
                    "ok": False,
                    "message": f"Card already controlled by {space.controlled_by}",
                    "board": self._serialize_board(),
                    "scores": self.scores
                }

            # Store card value BEFORE flipping
            card_value = space.card

            # Flip the card and take control
            self.board.flip_card(x, y)
            self.board.set_control(x, y, player_id)

            return {
                "ok": True,
                "message": f"Flipped {card_value} at ({x}, {y})",
                "board": self._serialize_board(),
                "scores": self.scores,
                "card": card_value
            }

        except Exception as e:
            print(f"❌ Error in flip: {e}")
            import traceback
            traceback.print_exc()
            return {
                "ok": False,
                "message": f"Error: {str(e)}",
                "board": self._serialize_board() if self.board else [],
                "scores": self.scores
            }

    # ==================== PRIVATE HELPERS ====================

    def _serialize_board(self) -> list:
        """
        Convert board to 2D JSON-serializable list.

        Returns: [[{card, is_face_up, controlled_by}, ...], ...]
        """
        try:
            grid = []
            for y in range(self.board.height):
                row = []
                for x in range(self.board.width):
                    space = self.board.get_space(x, y)
                    row.append({
                        "card": space.card,
                        "is_face_up": space.is_face_up,
                        "controlled_by": space.controlled_by
                    })
                grid.append(row)
            return grid
        except Exception as e:
            print(f"❌ Error serializing board: {e}")
            import traceback
            traceback.print_exc()
            return []
