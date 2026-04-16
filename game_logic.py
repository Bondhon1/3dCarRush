"""Core game logic and state management"""

import math
import time
import random
from constants import CAR_LENGTH, CAR_WIDTH
from physics import aabb_collision, separate_overlapping_objects, resolve_collision
from road_generator import RoadGenerator
from players import PlayerCar, EnemyCar


class GameMode:
    """Enumeration for game modes"""
    RACING = 'racing'
    TIME_ATTACK = 'time_attack'
    SURVIVAL = 'survival'
    DEATHMATCH = 'deathmatch'


class GameState:
    """Manages the complete game state"""
    
    def __init__(self, num_players=1, mode=GameMode.RACING, seed=None):
        self.num_players = num_players
        self.mode = mode
        self.seed = seed
        self.paused = False
        self.game_over = False
        self.start_time = time.time()
        
        # Track generation
        self.road_generator = RoadGenerator(seed=seed)
        self.road_generator.generate_track(num_segments=8)
        
        self.road_points = self.road_generator.get_road_points()
        self.border_points = self.road_generator.get_border_points()
        self.finish_line = self.road_generator.get_finish_line()
        
        # Players
        self.players = []
        start_pos = (0, -600, 10)
        for i in range(num_players):
            color = self._get_player_color(i)
            player = PlayerCar(player_id=i, start_pos=start_pos, color=color)
            self.players.append(player)
        
        # Enemy cars
        self.enemy_cars = []
        self._spawn_enemies()
        
        # Game state
        self.round_winners = []
        self.collisions_this_frame = []
    
    def _get_player_color(self, player_id):
        """Get color for player based on ID"""
        colors = [
            (0.2, 0.8, 0.9),   # Cyan
            (1.0, 0.8, 0.0),   # Yellow
            (0.8, 0.2, 1.0),   # Magenta
            (0.2, 1.0, 0.3)    # Green
        ]
        return colors[player_id % len(colors)]
    
    def _spawn_enemies(self):
        """Create enemy cars with paths"""
        self.enemy_cars = []
        
        # Generate paths for enemies based on road segments
        num_enemies = 2
        for i in range(num_enemies):
            color = (0.9, 0.3, 0.3)
            speed = random.uniform(12, 18)
            
            # Create simple waypoint path from segments
            path = self._generate_enemy_path(offset=50 * (i - num_enemies/2))
            
            enemy = EnemyCar(
                enemy_id=i,
                color=color,
                path_points=path,
                speed=speed
            )
            self.enemy_cars.append(enemy)
    
    def _generate_enemy_path(self, offset=0):
        """Generate waypoint path for enemy from road segments"""
        waypoints = [(0, -600, 10)]  # Start position
        
        current_x, current_y = 0, -600
        
        for segment in self.road_generator.segments:
            if segment.type == 'straight':
                # Add waypoint at end of straight
                end_x = segment.end_pos[0] + offset
                end_y = segment.end_pos[1]
                waypoints.append((end_x, end_y, 10))
            
            elif 'curve' in segment.type:
                # Add multiple waypoints along curve
                center = segment.properties.get('center', (0, 0))
                radius = segment.properties.get('radius', 300)
                angle_delta = segment.properties.get('angle_delta', 45)
                start_angle = segment.start_angle - 90
                
                num_points = 5
                for i in range(1, num_points + 1):
                    t = i / num_points
                    current_angle = start_angle + t * angle_delta
                    rad = math.radians(current_angle)
                    
                    wx = center[0] + radius * math.cos(rad) + offset
                    wy = center[1] + radius * math.sin(rad)
                    waypoints.append((wx, wy, 10))
        
        # Add finish line waypoint
        if self.finish_line:
            waypoints.append(self.finish_line['pos'] + (10,))
        
        return waypoints
    
    def update(self, dt=0.016):
        """Update game state"""
        if self.paused or self.game_over:
            return
        
        # Update players
        for player in self.players:
            player.update(dt)
        
        # Update enemies
        for enemy in self.enemy_cars:
            enemy.update(dt)
        
        # Check collisions
        self._check_collisions()
        
        # Check finish line
        self._check_finish_line()
        
        # Check game over conditions
        self._check_game_over()
    
    def _check_collisions(self):
        """Detect and resolve collisions"""
        self.collisions_this_frame = []
        
        # Player-to-border collisions with proper response
        for player in self.players:
            if self._check_border_collision(player):
                self._handle_border_collision(player)
        
        # Enemy-to-border collisions
        for enemy in self.enemy_cars:
            if self._check_border_collision(enemy):
                self._handle_border_collision(enemy)
        
        # Player-to-player collisions
        for i, player1 in enumerate(self.players):
            for player2 in self.players[i+1:]:
                if self._check_car_collision(player1, player2):
                    self._resolve_car_collision(player1, player2)
        
        # Player-to-enemy collisions
        for player in self.players:
            for enemy in self.enemy_cars:
                if self._check_car_collision(player, enemy):
                    if player.collision_cooldown <= 0:
                        self.collisions_this_frame.append((player, enemy))
                        
                        if self.mode == GameMode.DEATHMATCH:
                            player.lives -= 1
                        else:
                            player.apply_collision_damage(1)
                        
                        self._resolve_car_collision(player, enemy)
        
        # Enemy-to-enemy collisions
        for i, enemy1 in enumerate(self.enemy_cars):
            for enemy2 in self.enemy_cars[i+1:]:
                if self._check_car_collision(enemy1, enemy2):
                    self._resolve_car_collision(enemy1, enemy2)
    
    def _check_border_collision(self, car):
        """Check if car collided with border"""
        from physics import check_border_collision
        
        # Sample borders for performance
        border_sample = list(self.border_points)[:100]
        
        return check_border_collision(
            car.position[0], car.position[1],
            car.angle,
            CAR_WIDTH, CAR_LENGTH,
            border_sample
        )
    
    def _handle_border_collision(self, car):
        """Handle car hitting border - push back"""
        from physics import get_border_collision_normal
        
        # Get direction away from border
        border_sample = list(self.border_points)[:100]
        nx, ny = get_border_collision_normal(
            car.position[0], car.position[1],
            car.angle, CAR_WIDTH, CAR_LENGTH,
            border_sample
        )
        
        # Push car away
        push_distance = 50
        car.position[0] += nx * push_distance
        car.position[1] += ny * push_distance
        
        # Reduce velocity in direction of wall
        vel_dot = car.velocity[0] * nx + car.velocity[1] * ny
        if vel_dot < 0:  # Moving into wall
            car.velocity[0] -= vel_dot * nx * 0.8
            car.velocity[1] -= vel_dot * ny * 0.8
    
    def _check_car_collision(self, car1, car2):
        """Check if two cars collide using AABB"""
        bb1 = car1.get_bounding_box()
        bb2 = car2.get_bounding_box()
        
        return aabb_collision(
            (bb1['x'], bb1['y']), bb1['angle'],
            bb1['width'], bb1['length'],
            (bb2['x'], bb2['y']), bb2['angle'],
            bb2['width'], bb2['length']
        )
    
    def _resolve_car_collision(self, car1, car2):
        """Resolve collision between two cars"""
        min_dist = CAR_WIDTH + 5
        new_pos1, new_pos2 = separate_overlapping_objects(
            car1.position, car2.position, min_dist
        )
        
        car1.position = list(new_pos1)
        car2.position = list(new_pos2)
    
    def _check_finish_line(self):
        """Check if players crossed finish line"""
        if not self.finish_line:
            return
        
        finish_x, finish_y = self.finish_line['pos']
        finish_width = self.finish_line.get('width', 400)
        
        for player in self.players:
            if not player.finished:
                # Simple rectangular collision check for finish line
                if abs(player.position[0] - finish_x) < finish_width / 2 and \
                   abs(player.position[1] - finish_y) < 50:
                    player.finished = True
                    self.round_winners.append(player)
    
    def _check_game_over(self):
        """Check win/lose conditions based on game mode"""
        if self.mode == GameMode.RACING:
            # Someone finished
            if self.round_winners:
                self.game_over = True
        
        elif self.mode == GameMode.SURVIVAL:
            # Only one player left alive
            alive_count = sum(1 for p in self.players if p.lives > 0)
            if alive_count <= 1:
                self.game_over = True
        
        elif self.mode == GameMode.DEATHMATCH:
            # Time-based or point-based scoring
            pass
    
    def toggle_pause(self):
        """Toggle pause state"""
        self.paused = not self.paused
    
    def reset(self):
        """Reset game state"""
        for player in self.players:
            player.reset()

        self._spawn_enemies()
        
        self.round_winners = []
        self.collisions_this_frame = []
        self.game_over = False
        self.start_time = time.time()

    def get_elapsed_time(self):
        """Get time elapsed since game start"""
        return time.time() - self.start_time
    
    def get_game_status(self):
        """Get human-readable game status"""
        if self.paused:
            return "PAUSED"
        elif self.game_over:
            if self.round_winners:
                winner = self.round_winners[0]
                if isinstance(winner, PlayerCar):
                    return f"PLAYER {winner.player_id + 1} FINISHED!"
            return "GAME OVER"
        else:
            return "RACING"
    
    def get_player_stats(self, player_idx):
        """Get stats for a specific player"""
        if player_idx >= len(self.players):
            return {}
        
        player = self.players[player_idx]
        return {
            'position': player.position,
            'angle': player.angle,
            'speed': player.speed,
            'lives': max(0, player.lives),
            'finished': player.finished,
            'mode': self.mode
        }
    
    def get_game_info(self):
        """Get overall game information"""
        return {
            'mode': self.mode,
            'elapsed_time': self.get_elapsed_time(),
            'num_players': self.num_players,
            'paused': self.paused,
            'game_over': self.game_over,
            'winners': [(w.player_id if isinstance(w, PlayerCar) else -1) for w in self.round_winners]
        }
