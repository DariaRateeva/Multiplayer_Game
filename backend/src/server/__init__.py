"""Memory Scramble Game Server - Integrated with Board/GameManager"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from game.board import Board
from commands.commands import GameManager

app = FastAPI(title="Memory Scramble API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Find public directory
public_dir = Path(__file__).parent.parent.parent.parent / "public"

# Store active games
games = {}

@app.get("/")
async def serve_game():
    """Serve the main game page."""
    index_file = public_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"error": "Frontend not found"}

# Mount static files
if public_dir.exists():
    app.mount("/static", StaticFiles(directory=str(public_dir)), name="static")

@app.post("/games/new")
async def create_new_game():
    """Create a new game with actual Board."""
    cards = {"🎮", "🌈", "🎨", "⭐", "🎪", "🎭", "🎬", "🎸"}
    board = Board(4, 4, cards)
    game = GameManager(board)

    game_id = f"game_{len(games)}"
    games[game_id] = game

    return {"success": True, "gameId": game_id}

@app.get("/look/{player_id}")
async def look(player_id: str):
    """Get board state using GameManager."""
    # Use first game for now (single player)
    if games:
        game = list(games.values())[0]
        state = await game.look(player_id)
        return state

    # Fallback for no game
    return {"ok": False, "error": "No active game"}


@app.post("/flip/{player_id}")
async def flip_card(player_id: str, x: int, y: int):
    """Flip a card and return its state."""
    if not games:
        return {"ok": False, "message": "No active game"}

    game = list(games.values())[0]

    # Get board state BEFORE flip to see what card we're flipping
    board_before = await game.look(player_id)

    # Perform the flip
    flip_result = await game.flip(player_id, y, x)  # NOTE: y,x order for row,col

    # Get updated board state AFTER flip
    board_after = await game.look(player_id)

    # Return the flipped card's info
    return {
        **flip_result,
        "board": board_after.get("board"),
        "scores": board_after.get("scores", {})
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy", "games": len(games)}
