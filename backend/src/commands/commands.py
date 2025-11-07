"""
Commands module for Memory Scramble - Simple glue code for Board operations.

Implements the commands specification:
- look() - returns current board state
- flip() - flips a card and returns result

Async version supports concurrent players.
"""

from typing import Dict, Any, Optional
import asyncio
from src.game.board import Board


class GameManager:
    """
    Manages a single game session.

    Tracks board state, player control, and scores.
    Thread-safe for concurrent player moves.
    """

    def __init__(self, board: Board) -> None:
        """
        Create a new game manager.

        PRECONDITION: board is initialized Board
        POSTCONDITION: game manager ready to handle requests
        """
        self.board = board
        self.scores: Dict[str, int] = {}
        self.pending_cards: Dict[str, list] = {}
        print(f"✅ GameManager initialized: {board.width}x{board.height} board")

    async def look(self, player_id: str) -> Dict[str, Any]:
        """
        Get current board state.

        PRECONDITION: player_id is valid string
        POSTCONDITION: returns JSON-serializable board state

        Returns:
            dict with:
            - board: 2D array of spaces
            - width, height: board dimensions
            - scores: player scores
            - ok: success flag
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
            return {"ok": False, "error": str(e)}

    async def flip(self, player_id: str, x: int, y: int) -> Dict[str, Any]:
        """
        Flip a card at position (x, y).

        PRECONDITION: 0 <= x < width, 0 <= y < height
        POSTCONDITION: card at (x, y) is flipped and controlled by player_id

        Returns:
            dict with:
            - ok: success flag
            - message: status message
            - card: flipped card value (if successful)
        """
        try:
            # Validate bounds
            if x < 0 or x >= self.board.width or y < 0 or y >= self.board.height:
                return {
                    "ok": False,
                    "message": f"Position ({x}, {y}) out of bounds ({self.board.width}x{self.board.height})"
                }

            # Get the space
            space = self.board.get_space(x, y)

            # Can't flip empty space
            if space.card is None:
                return {
                    "ok": False,
                    "message": f"No card at ({x}, {y})"
                }

            # Store card value BEFORE flipping
            card_value = space.card

            # Flip the card and take control (may wait for async)
            if hasattr(self.board, 'wait_for_flip'):
                # Async version available
                await self.board.wait_for_flip(x, y, player_id)
            else:
                # Fallback to sync version
                self.board.flip_card(x, y)
                self.board.set_control(x, y, player_id)

            # Track pending cards for this player
            if player_id not in self.pending_cards:
                self.pending_cards[player_id] = []
            self.pending_cards[player_id].append((x, y, card_value))

            return {
                "ok": True,
                "message": f"Flipped {card_value} at ({x}, {y})",
                "card": card_value
            }

        except Exception as e:
            print(f"❌ Error in flip: {e}")
            import traceback
            traceback.print_exc()
            return {
                "ok": False,
                "message": f"Error: {str(e)}"
            }

    async def check_match(self, player_id: str) -> Dict[str, Any]:
        """
        Check if player's last two flipped cards match.

        PRECONDITION: player has flipped at least 2 cards
        POSTCONDITION: matched cards removed or reset

        Returns:
            dict with:
            - ok: success flag
            - matched: boolean indicating match
            - card: matched card value (if match)
        """
        try:
            if player_id not in self.pending_cards or len(self.pending_cards[player_id]) < 2:
                return {"ok": False, "message": "No two cards to check"}

            # Get the two most recent cards
            (x1, y1, card1) = self.pending_cards[player_id][-2]
            (x2, y2, card2) = self.pending_cards[player_id][-1]

            if card1 == card2:
                # Match! Remove cards
                self.board.set_control(x1, y1, None)
                self.board.set_control(x2, y2, None)
                self.board.flip_card(x1, y1)
                self.board.flip_card(x2, y2)
                self.scores[player_id] = self.scores.get(player_id, 0) + 1
                self.pending_cards[player_id] = []
                print(f"🎉 {player_id} matched {card1}!")
                return {"ok": True, "matched": True, "card": card1}
            else:
                # No match - reset cards
                self.board.flip_card(x1, y1)
                self.board.flip_card(x2, y2)
                self.board.set_control(x1, y1, None)
                self.board.set_control(x2, y2, None)
                self.pending_cards[player_id] = []
                print(f"❌ {player_id} didn't match: {card1} vs {card2}")
                return {"ok": True, "matched": False}

        except Exception as e:
            print(f"❌ Error checking match: {e}")
            return {"ok": False, "message": f"Error: {str(e)}"}

    def _serialize_board(self) -> list:
        """
        Convert board to 2D JSON-serializable list.

        POSTCONDITION: returns [[{card, is_face_up, controlled_by}, ...], ...]
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

    async def map_game(self, player_id: str, transformer: callable) -> Dict[str, Any]:
        """
        Apply a transformation function to all cards on the board.

        PRECONDITION: transformer is async function mapping card to card
        POSTCONDITION: board transformed, game state unchanged

        Returns: board state with all cards transformed
        """
        try:
            result = await self.board.map_cards(player_id, transformer)
            print(f"✅ Map completed for {player_id}")
            return result
        except Exception as e:
            print(f"❌ Map error: {e}")
            return {"ok": False, "error": str(e)}

    async def watch(self, player_id: str) -> Dict[str, Any]:
        """
        Wait for the next board change.

        PRECONDITION: player_id is valid string
        POSTCONDITION: returns board state after change occurs

        Returns: board state when change happens
        """
        try:
            result = await self.board.wait_for_change()
            print(f"🔔 Watcher {player_id} notified of change")
            return result
        except Exception as e:
            print(f"❌ Watch error: {e}")
            return {"ok": False, "error": str(e)}
