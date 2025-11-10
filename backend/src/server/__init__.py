from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sys

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

# Paths
public_dir = Path(__file__).parent.parent.parent.parent / "public"
boards_dir = Path(__file__).parent.parent.parent / "boards"

# ✅ DEFAULT BOARD - but can be recreated with different size
_shared_board: Board = None
_game_manager: GameManager = None
connected_clients = []


def create_board(width: int = 4, height: int = 4) -> Board:
    """Create a new board with given dimensions."""
    num_cards = (width * height) // 2
    available_cards = ["🎮", "🌈", "🎨", "⭐", "🎪", "🎭", "🎬", "🎸",
                       "🎯", "🎲", "🎺", "🎻", "🎹", "🎤", "🎧", "🎼"]

    # Use only the cards we need
    cards = set(list(available_cards)[:num_cards])
    return Board(width, height, cards)


# Initialize default board
_shared_board = create_board(4, 4)
_game_manager = GameManager(_shared_board)
print(f"🎮 Game started with {_shared_board.width}x{_shared_board.height} board")

# Serve static files
try:
    if public_dir.exists():
        app.mount("/static", StaticFiles(directory=str(public_dir)), name="static")
except Exception as e:
    print(f"⚠️  Could not mount static files: {e}")


@app.get("/")
async def serve_game():
    """Serve the game UI."""
    index_file = public_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"error": "Frontend not found"}


@app.get("/api/look")
async def look(playerId: str):
    """Get current board state for a player."""
    try:
        result = await _game_manager.look(playerId)
        return result
    except Exception as e:
        print(f"❌ Error in /api/look: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/flip")
async def flip(playerId: str, row: int, column: int):
    """Flip a card and notify all connected clients."""
    try:
        print(f"🎯 Player {playerId} flipping card at ({row}, {column})")
        result = await _game_manager.flip(playerId, row, column)

        # Notify all WebSocket clients
        if connected_clients:
            board_state = await _game_manager.look(playerId)
            for client in connected_clients[:]:
                try:
                    await client.send_json({"type": "board_update", "data": board_state})
                except:
                    connected_clients.remove(client)

        return result
    except Exception as e:
        print(f"❌ Error in /api/flip: {e}")
        return {"ok": False, "message": str(e)}


@app.post("/api/newgame")
async def newgame(playerId: str, width: int = 4, height: int = 4):
    """
    Create a new game board with specified dimensions.
    This resets the board for ALL players!
    """
    global _shared_board, _game_manager

    try:
        print(f"🎮 Creating new {width}x{height} board for all players")

        # Create new board
        _shared_board = create_board(width, height)
        _game_manager = GameManager(_shared_board)

        # Notify all connected clients
        board_state = await _game_manager.look(playerId)
        for client in connected_clients[:]:
            try:
                await client.send_json({"type": "board_update", "data": board_state})
            except:
                connected_clients.remove(client)

        return {
            "ok": True,
            "message": f"New {width}x{height} game created!",
            **board_state
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time board updates."""
    await websocket.accept()
    connected_clients.append(websocket)
    print(f"✅ WebSocket connected. Total clients: {len(connected_clients)}")

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        print(f"❌ WebSocket disconnected. Remaining: {len(connected_clients)}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "board_size": f"{_shared_board.width}x{_shared_board.height}",
        "websocket_connections": len(connected_clients)
    }
