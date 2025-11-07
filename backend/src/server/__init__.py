"""
HTTP server for Memory Scramble with async support for concurrent players.

Implements MIT spec endpoints:
- POST /games/new - create new game
- GET /look/{player_id} - get board state
- GET /watch/{player_id} - long-polling
- POST /flip/{player_id}?x=0&y=0 - flip card
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Dict, Optional
import asyncio

from src.game.board import Board
from src.commands.commands import GameManager

app = FastAPI(title="Memory Scramble Game (Async)")

# Enable CORS for web browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global game session
game_manager: Optional[GameManager] = None


# ==================== SERVE HTML ====================

@app.get("/")
async def serve_index():
    """Serve the game UI HTML file."""
    project_root = Path(__file__).parent.parent.parent.parent
    html_path = project_root / "public" / "index.html"

    if html_path.exists():
        return FileResponse(html_path, media_type="text/html")
    else:
        return {
            "error": "index.html not found",
            "looking_at": str(html_path)
        }


# ==================== MIT SPEC ENDPOINTS ====================

@app.post("/games/new")
async def games_new_post(spec: str = "random") -> Dict:
    """
    Create a new game.

    POSTCONDITION: game_manager initialized with new Board
    """
    global game_manager
    try:
        cards = {"🦄", "🌈", "🎨", "⭐", "🎪", "🎭", "🎬", "🎸"}
        board = Board(4, 4, cards)
        game_manager = GameManager(board)
        print(f"✅ Game created: {board.width}x{board.height}")
        return {"ok": True}
    except Exception as e:
        print(f"❌ Error creating game: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/look/{player_id}")
async def look_mit(player_id: str) -> Dict:
    """
    Get current board state (non-blocking).

    POSTCONDITION: returns board with all card states
    """
    global game_manager

    if game_manager is None:
        try:
            cards = {"🦄", "🌈", "🎨", "⭐", "🎪", "🎭", "🎬", "🎸"}
            board = Board(4, 4, cards)
            game_manager = GameManager(board)
            print(f"✅ Auto-created game for {player_id}")
        except Exception as e:
            print(f"❌ Error: {e}")
            raise HTTPException(status_code=400, detail="No active game")

    result = await game_manager.look(player_id)
    return result


@app.get("/watch/{player_id}")
async def watch_mit(player_id: str) -> Dict:
    """
    Watch for board changes (long-polling).

    POSTCONDITION: returns current board state
    """
    global game_manager

    if game_manager is None:
        try:
            cards = {"🦄", "🌈", "🎨", "⭐", "🎪", "🎭", "🎬", "🎸"}
            board = Board(4, 4, cards)
            game_manager = GameManager(board)
            print(f"✅ Auto-created game for watch by {player_id}")
        except Exception as e:
            print(f"❌ Error: {e}")
            raise HTTPException(status_code=400, detail="No active game")

    result = await game_manager.look(player_id)
    return result


@app.post("/flip/{player_id}")
async def flip_mit(player_id: str, x: int, y: int) -> Dict:
    """
    Flip a card on the board (async - may wait for other players).

    PRECONDITION: 0 <= x < 4, 0 <= y < 4
    POSTCONDITION: card is flipped and controlled by player
    """
    global game_manager

    if game_manager is None:
        print(f"❌ Flip failed: No active game")
        raise HTTPException(status_code=400, detail="No active game")

    print(f"📍 Flip request: {player_id} at ({x}, {y})")
    result = await game_manager.flip(player_id, x, y)
    print(f"📊 Result: {result}")
    return result


# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health() -> Dict:
    """Health check endpoint."""
    return {"status": "ok", "game_active": game_manager is not None}


@app.get("/api")
async def api_info() -> Dict:
    """API information endpoint."""
    return {
        "name": "Memory Scramble Game (Async)",
        "version": "2.0",
        "endpoints": {
            "games_new": "POST /games/new",
            "look": "GET /look/{player_id}",
            "watch": "GET /watch/{player_id}",
            "flip": "POST /flip/{player_id}?x=0&y=0"
        }
    }


@app.post("/reset/{player_id}")
async def reset_cards(player_id: str, x1: int, y1: int, x2: int, y2: int) -> Dict:
    """Reset two mismatched cards back to face-down."""
    global game_manager
    if game_manager is None:
        raise HTTPException(status_code=400, detail="No active game")

    try:
        game_manager.board.flip_card(x1, y1)
        game_manager.board.flip_card(x2, y2)
        game_manager.board.set_control(x1, y1, None)
        game_manager.board.set_control(x2, y2, None)
        return {"ok": True, "message": "Cards reset"}
    except Exception as e:
        return {"ok": False, "message": str(e)}

    @app.post("/map/{player_id}")
    async def map_endpoint(player_id: str, transformer_type: str = "emoji") -> Dict:
        """
        Apply a transformer to all cards.

        Query param: transformer_type=emoji|uppercase|reverse
        """
        global game_manager
        if game_manager is None:
            raise HTTPException(status_code=400, detail="No active game")

        # Define some example transformers
        transformers = {
            "emoji": emoji_transformer,
            "uppercase": uppercase_transformer,
            "reverse": reverse_transformer,
        }

        transformer = transformers.get(transformer_type)
        if not transformer:
            raise HTTPException(status_code=400, detail=f"Unknown transformer: {transformer_type}")

        try:
            result = await game_manager.map_game(player_id, transformer)
            return result
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Example async transformers
    async def emoji_transformer(card: str) -> str:
        """Transform emoji to emoji (for testing)."""
        emoji_map = {
            "🦄": "🌈",
            "🌈": "🦄",
            "🎨": "🎭",
            "🎭": "🎨",
            "⭐": "🎪",
            "🎪": "⭐",
            "🎬": "🎸",
            "🎸": "🎬",
        }
        # Simulate async operation (e.g., API call)
        await asyncio.sleep(0.01)
        return emoji_map.get(card, card)

    async def uppercase_transformer(card: str) -> str:
        """Transform to uppercase (for string cards)."""
        await asyncio.sleep(0.01)
        return card.upper()

    async def reverse_transformer(card: str) -> str:
        """Reverse the card string."""
        await asyncio.sleep(0.01)
        return card[::-1]

    @app.get("/watch/{player_id}")
    async def watch_endpoint(player_id: str) -> Dict:
        """
        Wait for board to change, then return updated state.

        This endpoint blocks until a change occurs.
        """
        global game_manager
        if game_manager is None:
            raise HTTPException(status_code=400, detail="No active game")

        try:
            result = await game_manager.watch(player_id)
            return result
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
