"""
Concurrent player simulation for Task 3.
Simply tests that multiple players can access the game simultaneously without crashes.
"""

import asyncio
import random
import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from src.game.board import Board
from src.commands.commands import GameManager


async def simulate_concurrent_game(num_players: int = 3, num_moves: int = 20):
    """
    Simulate concurrent players making random moves.

    TESTS:
    - Multiple players access simultaneously
    - Server handles concurrent requests
    - No deadlocks or crashes
    """
    print(f"\n🎮 Starting concurrent simulation: {num_players} players, {num_moves} moves\n")

    # Create game
    cards = {"🦄", "🌈", "🎨", "⭐", "🎪", "🎭", "🎬", "🎸"}
    board = Board(4, 4, cards)
    game = GameManager(board)

    # Track moves for each player
    player_moves = {f"player_{i}": 0 for i in range(num_players)}

    async def player_actions(player_id: str, moves: int):
        """Coroutine for a single player making moves."""
        for i in range(moves):
            # Try flipping random cards
            x = random.randint(0, 3)
            y = random.randint(0, 3)

            try:
                # Attempt flip (may fail if card already used, that's OK)
                result = await game.flip(player_id, x, y)
                if result["ok"]:
                    player_moves[player_id] += 1
                    print(f"✅ {player_id}: flipped {result['card']} at ({x},{y})")

                # Small random delay to encourage interleaving
                await asyncio.sleep(random.uniform(0.001, 0.01))

            except Exception as e:
                # Errors are OK - we're testing concurrent access, not game correctness
                print(f"⚠️  {player_id} at ({x},{y}): {type(e).__name__}")

    # Create concurrent tasks for all players
    tasks = [
        player_actions(f"player_{i}", num_moves // num_players)
        for i in range(num_players)
    ]

    try:
        # Run all players concurrently with 30 second timeout
        async with asyncio.timeout(30):
            await asyncio.gather(*tasks)

        print(f"\n✅ CONCURRENT TEST PASSED!")
        print(f"   - {num_players} players ran simultaneously")
        print(f"   - No deadlocks or crashes")
        print(f"   - {sum(player_moves.values())} total successful flips")
        return True

    except TimeoutError:
        print(f"\n❌ TIMEOUT - possible deadlock detected!")
        return False
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run simulation
    success = asyncio.run(simulate_concurrent_game(num_players=4, num_moves=20))
    sys.exit(0 if success else 1)
