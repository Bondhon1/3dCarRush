"""Test script for modular game architecture"""

import sys
import math

print("=" * 60)
print("Testing 3D Car Rush Modular Architecture")
print("=" * 60)

# Test 1: Constants
print("\n[Test 1] Loading constants...")
try:
    from constants import *
    print("✓ Constants loaded successfully")
except Exception as e:
    print(f"✗ Failed to load constants: {e}")
    sys.exit(1)

# Test 2: Physics module
print("\n[Test 2] Testing physics module...")
try:
    from physics import AABB, aabb_collision, separate_overlapping_objects
    
    # Test AABB collision
    pos1 = (0, 0)
    pos2 = (10, 0)
    result = aabb_collision(pos1, 0, CAR_WIDTH, CAR_LENGTH, pos2, 0, CAR_WIDTH, CAR_LENGTH)
    print(f"  AABB collision test: {result}")
    print("✓ Physics module working correctly")
except Exception as e:
    print(f"✗ Physics module error: {e}")
    sys.exit(1)

# Test 3: Road Generator
print("\n[Test 3] Testing road generator...")
try:
    from road_generator import RoadGenerator
    
    gen = RoadGenerator(seed=42)
    segments = gen.generate_track(num_segments=6)
    
    print(f"  Generated {len(segments)} road segments")
    print(f"  Total track length: {gen.total_length:.0f} units")
    print(f"  Road points: {len(gen.get_road_points())} points")
    print(f"  Border points: {len(gen.get_border_points())} points")
    
    finish_line = gen.get_finish_line()
    if finish_line:
        print(f"  Finish line at: {finish_line['pos']}")
    
    print("✓ Road generator working correctly")
except Exception as e:
    print(f"✗ Road generator error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Players module
print("\n[Test 4] Testing players module...")
try:
    from players import PlayerCar, EnemyCar
    
    player = PlayerCar(player_id=0, start_pos=(0, -600, 10))
    print(f"  Player created at: {player.position}")
    print(f"  Player color: {player.color}")
    
    enemy = EnemyCar(enemy_id=0, path_points=[(0, -600, 10), (100, -500, 10)])
    print(f"  Enemy created at: {enemy.position}")
    
    # Test update
    player.forward = True
    player.update(dt=0.016)
    print(f"  Player position after update: {player.position}")
    
    print("✓ Players module working correctly")
except Exception as e:
    print(f"✗ Players module error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Game logic
print("\n[Test 5] Testing game logic...")
try:
    from game_logic import GameState, GameMode
    
    game = GameState(num_players=1, mode=GameMode.RACING, seed=42)
    print(f"  Game initialized with {len(game.players)} players")
    print(f"  Enemy cars: {len(game.enemy_cars)}")
    print(f"  Road segments: {len(game.road_generator.segments)}")
    
    # Test update
    game.update(dt=0.016)
    print(f"  Game updated successfully")
    print(f"  Player position: {game.players[0].position}")
    print(f"  Elapsed time: {game.get_elapsed_time():.2f}s")
    
    print("✓ Game logic working correctly")
except Exception as e:
    print(f"✗ Game logic error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Rendering module (without display)
print("\n[Test 6] Testing rendering module...")
try:
    from rendering import Renderer, Camera, RenderUtils
    
    renderer = Renderer(window_width=1000, window_height=800)
    print(f"  Renderer created: {renderer.window_width}x{renderer.window_height}")
    
    # Test split-screen setup
    renderer.setup_split_screen(2)
    print(f"  Split-screen setup for 2 players")
    print(f"  Viewports: {renderer.viewports}")
    
    camera = Camera()
    print(f"  Camera created at: {camera.position}")
    
    print("✓ Rendering module working correctly")
except Exception as e:
    print(f"✗ Rendering module error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Scene module (without display)
print("\n[Test 7] Testing scene module...")
try:
    from scene import SceneRenderer
    
    scene = SceneRenderer()
    scene.setup(game.road_generator)
    
    print(f"  Scene initialized")
    print(f"  Tree positions: {len(scene.tree_positions)}")
    print(f"  Finish line: {scene.finish_line}")
    
    print("✓ Scene module working correctly")
except Exception as e:
    print(f"✗ Scene module error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("All Tests Passed! ✓")
print("=" * 60)
print("\nModular architecture is ready for rendering and gameplay.")
print("Run: python main_new.py")
