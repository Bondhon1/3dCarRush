"""Player car management and control"""

import math
from constants import CAR_LENGTH, CAR_WIDTH, NORMAL_SPEED, TURN_SPEED, BOOST_SPEED


class PlayerCar:
    """Represents a player-controlled car"""
    
    def __init__(self, player_id=0, start_pos=(0, -600, 10), color=(0.2, 0.8, 0.9)):
        self.player_id = player_id
        self.position = list(start_pos)
        self.velocity = [0, 0, 0]
        self.angle = 90.0  # Heading direction in degrees
        self.color = color
        self.lives = 10
        
        # Control inputs
        self.forward = False
        self.backward = False
        self.turn_left = False
        self.turn_right = False
        self.boost_active = False
        self.shield_active = False
        
        # State
        self.speed = NORMAL_SPEED
        self.finished = False
        self.collision_cooldown = 0
    
    def update(self, dt=0.016):
        """Update car physics and position"""
        if self.finished:
            return

        # Update angle based on turning inputs
        if self.turn_left:
            self.angle += TURN_SPEED
        if self.turn_right:
            self.angle -= TURN_SPEED
        
        # Normalize angle
        self.angle %= 360
        
        # Calculate target speed
        target_speed = 0
        if self.forward:
            target_speed = BOOST_SPEED if self.boost_active else NORMAL_SPEED
        elif self.backward:
            target_speed = -NORMAL_SPEED * 0.5
        
        # Smooth speed transition
        self.speed += (target_speed - self.speed) * 0.1
        
        # Update velocity based on angle and speed
        rad = math.radians(self.angle)
        self.velocity[0] = self.speed * math.cos(rad)
        self.velocity[1] = self.speed * math.sin(rad)
        
        # Update position
        self.position[0] += self.velocity[0]
        self.position[1] += self.velocity[1]
        
        # Apply gravity (simple Z movement)
        if self.position[2] > 10:
            self.velocity[2] -= 0.5  # Gravity
            self.position[2] += self.velocity[2]
        else:
            self.position[2] = 10
            self.velocity[2] = 0
        
        # Update collision cooldown
        if self.collision_cooldown > 0:
            self.collision_cooldown -= dt
    
    def set_input(self, key, pressed):
        """Handle keyboard input"""
        if isinstance(key, bytes):
            try:
                key = key.decode("utf-8")
            except UnicodeDecodeError:
                key = key.decode("latin1", errors="ignore")

        key_lower = key.lower() if isinstance(key, str) else key
        if key_lower == " ":
            key_lower = "space"
        
        if key_lower in ('w', 'up'):
            self.forward = pressed
        elif key_lower in ('s', 'down'):
            self.backward = pressed
        elif key_lower in ('a', 'left'):
            self.turn_left = pressed
        elif key_lower in ('d', 'right'):
            self.turn_right = pressed
        elif key_lower == 'space':
            self.boost_active = pressed
    
    def apply_collision_damage(self, damage=1):
        """Apply damage from collision"""
        if not self.shield_active:
            self.lives -= damage
            self.collision_cooldown = 0.5
    
    def apply_boost(self):
        """Activate boost effect"""
        self.speed = BOOST_SPEED
    
    def apply_shield(self):
        """Activate shield"""
        self.shield_active = True
    
    def get_bounding_box(self):
        """Get AABB for collision detection"""
        return {
            'x': self.position[0],
            'y': self.position[1],
            'width': CAR_WIDTH,
            'length': CAR_LENGTH,
            'angle': self.angle
        }
    
    def reset(self, start_pos=(0, -600, 10)):
        """Reset car to starting position"""
        self.position = list(start_pos)
        self.velocity = [0, 0, 0]
        self.angle = 90.0
        self.lives = 10
        self.speed = NORMAL_SPEED
        self.finished = False
        self.boost_active = False
        self.shield_active = False


class EnemyCar:
    """Represents an AI-controlled enemy car"""
    
    def __init__(self, enemy_id=0, color=(0.9, 0.3, 0.3), path_points=None, speed=15.0):
        self.enemy_id = enemy_id
        self.position = list(path_points[0]) if path_points else [0, -600, 10]
        self.velocity = [0, 0, 0]
        self.angle = 90.0
        self.color = color
        self.speed = speed
        self.lives = 4
        
        # Pathfinding
        self.path_points = path_points or []
        self.current_waypoint = 0
        self.finished = False
    
    def update(self, dt=0.016):
        """Update enemy car movement"""
        if self.finished or not self.path_points:
            return
        
        # Get current target waypoint
        if self.current_waypoint >= len(self.path_points):
            self.finished = True
            return
        
        target = self.path_points[self.current_waypoint]
        dx = target[0] - self.position[0]
        dy = target[1] - self.position[1]
        dist = math.sqrt(dx**2 + dy**2)
        
        # Reached waypoint, move to next
        if dist < 50:
            self.current_waypoint += 1
            if self.current_waypoint >= len(self.path_points):
                self.finished = True
                return
            target = self.path_points[self.current_waypoint]
            dx = target[0] - self.position[0]
            dy = target[1] - self.position[1]
            dist = math.sqrt(dx**2 + dy**2)
        
        # Calculate target angle
        if dist > 0:
            target_angle = math.degrees(math.atan2(dy, dx))
            
            # Smoothly turn toward target
            angle_diff = (target_angle - self.angle) % 360
            if angle_diff > 180:
                angle_diff -= 360
            
            max_turn = TURN_SPEED * 2
            self.angle += max(min(angle_diff, max_turn), -max_turn)
            self.angle %= 360
        
        # Move forward
        rad = math.radians(self.angle)
        self.velocity[0] = self.speed * math.cos(rad)
        self.velocity[1] = self.speed * math.sin(rad)
        
        self.position[0] += self.velocity[0]
        self.position[1] += self.velocity[1]
        
        # Gravity
        if self.position[2] > 10:
            self.velocity[2] -= 0.5
            self.position[2] += self.velocity[2]
        else:
            self.position[2] = 10
            self.velocity[2] = 0
    
    def get_bounding_box(self):
        """Get AABB for collision detection"""
        return {
            'x': self.position[0],
            'y': self.position[1],
            'width': CAR_WIDTH,
            'length': CAR_LENGTH,
            'angle': self.angle
        }
    
    def apply_damage(self, damage=1):
        """Apply damage to enemy car"""
        self.lives -= damage
