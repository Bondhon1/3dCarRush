"""Collision detection and physics calculations"""

import math
from constants import CAR_LENGTH, CAR_WIDTH, COLLISION_TOLERANCE


class AABB:
    """Axis-Aligned Bounding Box for collision detection"""
    def __init__(self, x, y, width, length):
        self.x = x
        self.y = y
        self.width = width
        self.length = length
    
    def get_corners(self, angle_deg):
        """Get rotated corners of the AABB"""
        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        # Local corners before rotation
        local_corners = [
            (-self.width / 2, -self.length / 2),
            (self.width / 2, -self.length / 2),
            (self.width / 2, self.length / 2),
            (-self.width / 2, self.length / 2),
        ]
        
        # Rotate and translate
        corners = []
        for lx, ly in local_corners:
            rx = lx * cos_a - ly * sin_a + self.x
            ry = lx * sin_a + ly * cos_a + self.y
            corners.append((rx, ry))
        
        return corners
    
    def point_inside(self, px, py, angle_deg):
        """Check if a point is inside the rotated AABB"""
        angle_rad = math.radians(-angle_deg)  # Inverse rotation
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        # Translate to local space
        tx = px - self.x
        ty = py - self.y
        
        # Rotate to local space
        lx = tx * cos_a - ty * sin_a
        ly = tx * sin_a + ty * cos_a
        
        # Check bounds
        return (abs(lx) <= self.width / 2 and abs(ly) <= self.length / 2)


def sat_overlap(corners1, corners2, axis):
    """Test overlap along an axis using Separating Axis Theorem"""
    min1 = min(c[0] * axis[0] + c[1] * axis[1] for c in corners1)
    max1 = max(c[0] * axis[0] + c[1] * axis[1] for c in corners1)
    
    min2 = min(c[0] * axis[0] + c[1] * axis[1] for c in corners2)
    max2 = max(c[0] * axis[0] + c[1] * axis[1] for c in corners2)
    
    return not (max1 < min2 or max2 < min1)


def aabb_collision(pos1, angle1, size1_w, size1_l, pos2, angle2, size2_w, size2_l):
    """
    Check collision between two rotated AABBs using SAT (Separating Axis Theorem)
    Returns True if collision detected
    """
    aabb1 = AABB(pos1[0], pos1[1], size1_w, size1_l)
    aabb2 = AABB(pos2[0], pos2[1], size2_w, size2_l)
    
    corners1 = aabb1.get_corners(angle1)
    corners2 = aabb2.get_corners(angle2)
    
    # Test axes from both rectangles
    axes = []
    
    # Axes from first rectangle
    for i in range(4):
        c1 = corners1[i]
        c2 = corners1[(i + 1) % 4]
        edge = (c2[0] - c1[0], c2[1] - c1[1])
        # Perpendicular to edge (normal)
        normal = (-edge[1], edge[0])
        length = math.sqrt(normal[0]**2 + normal[1]**2)
        if length > 0:
            axes.append((normal[0] / length, normal[1] / length))
    
    # Axes from second rectangle
    for i in range(4):
        c1 = corners2[i]
        c2 = corners2[(i + 1) % 4]
        edge = (c2[0] - c1[0], c2[1] - c1[1])
        normal = (-edge[1], edge[0])
        length = math.sqrt(normal[0]**2 + normal[1]**2)
        if length > 0:
            axes.append((normal[0] / length, normal[1] / length))
    
    # Check all axes
    for axis in axes:
        if not sat_overlap(corners1, corners2, axis):
            return False  # Found separating axis, no collision
    
    return True  # No separating axis found, collision detected


def check_border_collision(x, y, angle_deg, car_width, car_length, border_positions):
    """
    Check collision with road borders
    Returns True if car is off the road
    """
    # Create car AABB
    car_aabb = AABB(x, y, car_width, car_length)
    corners = car_aabb.get_corners(angle_deg)
    
    # Check if any corner is near border
    for corner_x, corner_y in corners:
        for bx, by in border_positions:
            dist = math.sqrt((corner_x - bx)**2 + (corner_y - by)**2)
            if dist < 30:  # Within collision distance
                return True
    
    return False


def get_border_collision_normal(x, y, angle_deg, car_width, car_length, border_positions):
    """
    Get collision normal for pushing car away from border
    Returns (nx, ny) unit vector pointing away from border
    """
    car_aabb = AABB(x, y, car_width, car_length)
    corners = car_aabb.get_corners(angle_deg)
    
    closest_dist = float('inf')
    closest_nx, closest_ny = 0, 1
    
    for corner_x, corner_y in corners:
        for bx, by in border_positions:
            dx = corner_x - bx
            dy = corner_y - by
            dist = math.sqrt(dx**2 + dy**2)
            
            if dist < closest_dist and dist > 0:
                closest_dist = dist
                closest_nx = dx / dist
                closest_ny = dy / dist
    
    return (closest_nx, closest_ny)


def resolve_collision(pos1, vel1, mass1, pos2, vel2, mass2):
    """
    Resolve collision between two objects using simple physics
    Returns updated velocities
    """
    # Vector from object 1 to object 2
    dx = pos2[0] - pos1[0]
    dy = pos2[1] - pos1[1]
    dist = math.sqrt(dx**2 + dy**2)
    
    if dist == 0:
        return vel1, vel2
    
    # Normalize collision vector
    nx = dx / dist
    ny = dy / dist
    
    # Relative velocity
    dvx = vel2[0] - vel1[0]
    dvy = vel2[1] - vel1[1]
    
    # Relative velocity along collision normal
    dvn = dvx * nx + dvy * ny
    
    # Don't resolve if velocities are separating
    if dvn >= 0:
        return vel1, vel2
    
    # Impulse scalar (simplified)
    restitution = 0.3  # bounciness
    impulse = -(1 + restitution) * dvn / (1/mass1 + 1/mass2)
    
    # Apply impulse
    impulse_x = impulse * nx
    impulse_y = impulse * ny
    
    new_vel1 = (vel1[0] - impulse_x / mass1, vel1[1] - impulse_y / mass1)
    new_vel2 = (vel2[0] + impulse_x / mass2, vel2[1] + impulse_y / mass2)
    
    return new_vel1, new_vel2


def separate_overlapping_objects(pos1, pos2, min_distance):
    """
    Separate two overlapping objects along collision vector
    Returns updated positions
    """
    dx = pos2[0] - pos1[0]
    dy = pos2[1] - pos1[1]
    dist = math.sqrt(dx**2 + dy**2)
    
    if dist < 0.001:
        dist = min_distance
        dx = min_distance
        dy = 0
    
    # Push objects apart
    overlap = min_distance - dist
    nx = dx / dist
    ny = dy / dist
    
    push = overlap / 2 + 0.01  # Small extra push to prevent re-collision
    
    new_pos1 = (pos1[0] - push * nx, pos1[1] - push * ny, pos1[2])
    new_pos2 = (pos2[0] + push * nx, pos2[1] + push * ny, pos2[2])
    
    return new_pos1, new_pos2
