from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.commands.commands import GameManager
from src.game.board import Board

app = FastAPI()

# ✅ CREATE ONE SHARED BOARD AT SERVER STARTUP
_shared_board: Board = Board.parse_from_file("boards/perfect.txt")
_game_manager: GameManager = GameManager(_shared_board)

connected_clients = []

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="public"), name="static")


@app.get("/")
async def index():
    """Serve the game UI."""
    return FileResponse("public/index.html")


@app.get("/look")
async def look_endpoint(player_id: str):
    """Get current board state."""
    return await _game_manager.look(player_id)


@app.post("/flip")
async def flip_endpoint(player_id: str, row: int, column: int):
    """Flip a card."""
    result = await _game_manager.flip(player_id, row, column)

    # Notify all connected WebSocket clients
    for client in connected_clients:
        try:
            await client.send_json({
                "event": "update",
                "board": _game_manager._serialize_board()
            })
        except:
            pass  # Client disconnected

    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates."""
    await websocket.accept()
    connected_clients.append(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
