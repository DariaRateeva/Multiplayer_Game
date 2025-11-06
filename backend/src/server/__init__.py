"""
HTTP server for Memory Scramble game.

Serves REST API endpoints and the game UI.
Implements MIT spec endpoints for the web interface.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Dict, Optional

from src.game.board import Board
from src.commands.commands import GameManager

app = FastAPI(title="Memory Scramble Game")

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
            "looking_at": str(html_path),
            "try": "http://localhost:8080/docs for API documentation"
        }


# ==================== MIT SPEC ENDPOINTS ====================
# These match what the provided index.html expects

@app.post("/games/new")
async def games_new_post(spec: str = "random") -> Dict:
    """Create a new game."""
    global game_manager
    try:
        # 4x4 = 16 spaces = 8 pairs with emoji cards
        cards = {"🦄", "🌈", "🎨", "⭐", "🎪", "🎭", "🎬", "🎸"}
        board = Board(4, 4, cards)
        game_manager = GameManager(board)
        print(f"✅ Game created: {board.width}x{board.height} with emojis")
        return {"ok": True}
    except Exception as e:
        print(f"❌ Error creating game: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/look/{player_id}")
async def look_mit(player_id: str) -> Dict:
    """Get current board state."""
    global game_manager

    if game_manager is None:
        try:
            cards = {"🦄", "🌈", "🎨", "⭐", "🎪", "🎭", "🎬", "🎸"}
            board = Board(4, 4, cards)
            game_manager = GameManager(board)
            print(f"✅ Auto-created game for {player_id}")
        except Exception as e:
            print(f"❌ Error auto-creating game: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=400, detail="No active game")

    result = game_manager.look(player_id)
    return result


@app.get("/watch/{player_id}")
async def watch_mit(player_id: str) -> Dict:
    """Watch for board changes (long-polling)."""
    global game_manager

    if game_manager is None:
        try:
            cards = {"🦄", "🌈", "🎨", "⭐", "🎪", "🎭", "🎬", "🎸"}
            board = Board(4, 4, cards)
            game_manager = GameManager(board)
            print(f"✅ Auto-created game for watch by {player_id}")
        except Exception as e:
            print(f"❌ Error in watch: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=400, detail="No active game")

    result = game_manager.look(player_id)
    return result


@app.post("/flip/{player_id}")
async def flip_mit(player_id: str, x: int, y: int) -> Dict:
    """Flip a card on the board."""
    global game_manager

    if game_manager is None:
        print(f"❌ Flip failed: No active game")
        raise HTTPException(status_code=400, detail="No active game. Call /games/new first")

    print(f"📍 Flip request: {player_id} at ({x}, {y})")
    result = game_manager.flip(player_id, x, y)
    print(f"📊 Flip result: {result['ok']} - {result['message']}")
    return result


# ==================== CUSTOM API ENDPOINTS ====================
# Keep for backwards compatibility

@app.post("/api/games/new")
async def create_game(width: int = 3, height: int = 3) -> Dict:
    """Create a new game with specified dimensions."""
    global game_manager

    try:
        assert width > 0 and height > 0, "Width and height must be positive"
        assert (width * height) % 2 == 0, "Total spaces must be even"

        num_pairs = (width * height) // 2
        cards = {f"Card{i}" for i in range(num_pairs)}

        board = Board(width, height, cards)
        game_manager = GameManager(board)

        return {"ok": True, "message": "Game created", "width": width, "height": height}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/games/look")
async def look_custom(player_id: str) -> Dict:
    """Get current board state (custom API)."""
    global game_manager

    if game_manager is None:
        raise HTTPException(status_code=400, detail="No active game")
    return game_manager.look(player_id)


@app.post("/api/games/flip")
async def flip_custom(player_id: str, x: int, y: int) -> Dict:
    """Flip a card (custom API)."""
    global game_manager

    if game_manager is None:
        raise HTTPException(status_code=400, detail="No active game")
    return game_manager.flip(player_id, x, y)


# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health() -> Dict:
    """Health check endpoint."""
    return {"status": "ok", "game_active": game_manager is not None}


@app.get("/api")
async def api_info() -> Dict:
    """API information endpoint."""
    return {
        "name": "Memory Scramble Game",
        "version": "1.0",
        "endpoints": {
            "games_new": "POST /games/new",
            "look": "GET /look/{player_id}",
            "watch": "GET /watch/{player_id}",
            "flip": "POST /flip/{player_id}?x=0&y=0"
        }
    }
