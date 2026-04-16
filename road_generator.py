"""Procedural road generation for dynamic track creation"""

import random
import math
from constants import (
    ROAD_WIDTH, MIN_TRACK_LENGTH, MAX_TRACK_LENGTH,
    MIN_CURVE_RADIUS, MAX_CURVE_RADIUS
)


class RoadSegment:
    """Represents a single road segment"""
    def __init__(self, segment_type, **kwargs):
        self.type = segment_type  # 'straight', 'curve_left', 'curve_right', 'junction'
        self.properties = kwargs
        self.start_pos = None
        self.end_pos = None
        self.start_angle = 0
        self.end_angle = 0
        self.road_points = []
        self.border_points = []
    
    def to_dict(self):
        """Convert segment to dictionary for serialization"""
        return {
            'type': self.type,
            'properties': self.properties,
            'start_pos': self.start_pos,
            'end_pos': self.end_pos,
            'start_angle': self.start_angle,
            'end_angle': self.end_angle
        }


class RoadGenerator:
    """Generates procedural road tracks"""
    
    def __init__(self, seed=None):
        if seed is not None:
            random.seed(seed)
        self.segments = []
        self.total_length = 0
    
    def generate_track(self, num_segments=6, start_pos=(0, -600)):
        """Generate a complete track with multiple segments"""
        self.segments = []
        self.total_length = 0
        
        current_pos = list(start_pos) + [10]  # [x, y, z]
        current_angle = 90  # Start heading north
        
        for i in range(num_segments):
            segment_type = self._choose_segment_type(i, num_segments)
            segment = self._create_segment(
                segment_type, current_pos, current_angle
            )
            
            if segment:
                self.segments.append(segment)
                # Update position and angle for next segment
                current_pos = list(segment.end_pos) + [10]
                current_angle = segment.end_angle
                self.total_length += segment.properties.get('length', 0)
        
        # Add finish line
        self._add_finish_line()
        
        return self.segments
    
    def _choose_segment_type(self, index, total):
        """Choose segment type based on position in track"""
        if index == 0:
            return 'straight'  # First segment is always straight
        
        if index == total - 1:
            return 'straight'  # Last segment straight for finish
        
        # Randomly choose from available types
        types = ['straight', 'curve_left', 'curve_right']
        weights = [0.4, 0.3, 0.3]
        return random.choices(types, weights=weights)[0]
    
    def _create_segment(self, seg_type, start_pos, start_angle):
        """Create a specific type of road segment"""
        segment = RoadSegment(seg_type)
        segment.start_pos = start_pos
        segment.start_angle = start_angle
        
        if seg_type == 'straight':
            return self._create_straight(segment, start_pos, start_angle)
        elif seg_type == 'curve_left':
            return self._create_curve(segment, start_pos, start_angle, 'left')
        elif seg_type == 'curve_right':
            return self._create_curve(segment, start_pos, start_angle, 'right')
        
        return segment
    
    def _create_straight(self, segment, start_pos, angle):
        """Create a straight road segment"""
        length = random.uniform(MIN_TRACK_LENGTH, MAX_TRACK_LENGTH)
        
        # Calculate end position
        rad = math.radians(angle)
        end_x = start_pos[0] + length * math.cos(rad)
        end_y = start_pos[1] + length * math.sin(rad)
        
        segment.end_pos = (end_x, end_y, 10)
        segment.end_angle = angle
        segment.properties['length'] = length
        segment.properties['width'] = ROAD_WIDTH
        segment.properties['angle'] = angle
        
        return segment
    
    def _create_curve(self, segment, start_pos, start_angle, direction):
        """Create a curved road segment"""
        radius = random.uniform(MIN_CURVE_RADIUS, MAX_CURVE_RADIUS)
        angle_delta = random.uniform(30, 90)  # degrees
        
        if direction == 'left':
            center_offset_angle = start_angle + 90
            segment.properties['direction'] = 'left'
        else:
            center_offset_angle = start_angle - 90
            segment.properties['direction'] = 'right'
            angle_delta = -angle_delta
        
        # Calculate curve center
        rad = math.radians(center_offset_angle)
        center_x = start_pos[0] + radius * math.cos(rad)
        center_y = start_pos[1] + radius * math.sin(rad)
        
        # Calculate end position
        end_angle = start_angle + angle_delta
        rad = math.radians(end_angle)
        end_x = center_x + radius * math.cos(math.radians(end_angle - 90))
        end_y = center_y + radius * math.sin(math.radians(end_angle - 90))
        
        segment.end_pos = (end_x, end_y, 10)
        segment.end_angle = end_angle
        segment.properties['radius'] = radius
        segment.properties['angle_delta'] = angle_delta
        segment.properties['center'] = (center_x, center_y)
        segment.properties['width'] = ROAD_WIDTH
        segment.properties['length'] = abs(angle_delta) * radius * math.pi / 180
        
        return segment
    
    def _add_finish_line(self):
        """Add finish line position to the last segment"""
        if self.segments:
            last_segment = self.segments[-1]
            # Extend finish line position beyond the last segment
            rad = math.radians(last_segment.end_angle)
            finish_x = last_segment.end_pos[0] + 200 * math.cos(rad)
            finish_y = last_segment.end_pos[1] + 200 * math.sin(rad)
            
            self.finish_line = {
                'pos': (finish_x, finish_y),
                'angle': last_segment.end_angle,
                'width': ROAD_WIDTH
            }
    
    def get_finish_line(self):
        """Return finish line position and angle"""
        return getattr(self, 'finish_line', None)
    
    def get_road_points(self):
        """Get all road surface points for collision checking"""
        road_points = set()
        
        for segment in self.segments:
            if segment.type == 'straight':
                road_points.update(self._get_straight_road_points(segment))
            elif 'curve' in segment.type:
                road_points.update(self._get_curve_road_points(segment))
        
        return road_points
    
    def _get_straight_road_points(self, segment):
        """Get road points for a straight segment"""
        points = set()
        start = segment.start_pos
        end = segment.end_pos
        
        # Sample points along the straight line
        num_samples = int(segment.properties.get('length', 0) / 20)
        width = segment.properties.get('width', ROAD_WIDTH)
        
        for i in range(num_samples):
            t = i / max(1, num_samples - 1)
            x = start[0] + t * (end[0] - start[0])
            y = start[1] + t * (end[1] - start[1])
            
            # Add points across road width
            angle = segment.properties.get('angle', 90)
            rad = math.radians(angle)
            
            for w in range(int(-width/2), int(width/2), 20):
                px = x + w * math.cos(rad + math.pi/2)
                py = y + w * math.sin(rad + math.pi/2)
                points.add((int(px), int(py)))
        
        return points
    
    def _get_curve_road_points(self, segment):
        """Get road points for a curved segment"""
        points = set()
        radius = segment.properties.get('radius', 300)
        center = segment.properties.get('center', (0, 0))
        angle_delta = segment.properties.get('angle_delta', 45)
        width = segment.properties.get('width', ROAD_WIDTH)
        
        start_angle = segment.start_angle - 90
        num_samples = max(20, int(abs(angle_delta) * 2))
        
        for i in range(num_samples):
            t = i / max(1, num_samples - 1)
            current_angle = start_angle + t * angle_delta
            rad = math.radians(current_angle)
            
            x = center[0] + radius * math.cos(rad)
            y = center[1] + radius * math.sin(rad)
            
            # Add points across road width
            for w in range(int(-width/2), int(width/2), 20):
                px = x + w * math.cos(rad + math.pi/2)
                py = y + w * math.sin(rad + math.pi/2)
                points.add((int(px), int(py)))
        
        return points
    
    def get_border_points(self):
        """Get all border points for collision detection"""
        borders = set()
        
        for segment in self.segments:
            if segment.type == 'straight':
                borders.update(self._get_straight_borders(segment))
            elif 'curve' in segment.type:
                borders.update(self._get_curve_borders(segment))
        
        return borders
    
    def _get_straight_borders(self, segment):
        """Get border points for straight segment"""
        borders = set()
        start = segment.start_pos
        end = segment.end_pos
        width_half = segment.properties.get('width', ROAD_WIDTH) / 2
        
        angle = segment.properties.get('angle', 90)
        rad = math.radians(angle)
        perp_x = -math.sin(rad)
        perp_y = math.cos(rad)
        
        num_samples = int(segment.properties.get('length', 0) / 30)
        
        for i in range(num_samples):
            t = i / max(1, num_samples - 1)
            x = start[0] + t * (end[0] - start[0])
            y = start[1] + t * (end[1] - start[1])
            
            # Left and right borders
            for side in [-1, 1]:
                bx = x + side * width_half * perp_x
                by = y + side * width_half * perp_y
                borders.add((int(bx), int(by)))
        
        return borders
    
    def _get_curve_borders(self, segment):
        """Get border points for curved segment"""
        borders = set()
        radius = segment.properties.get('radius', 300)
        center = segment.properties.get('center', (0, 0))
        angle_delta = segment.properties.get('angle_delta', 45)
        width_half = segment.properties.get('width', ROAD_WIDTH) / 2
        
        start_angle = segment.start_angle - 90
        num_samples = max(20, int(abs(angle_delta) * 2))
        
        for i in range(num_samples):
            t = i / max(1, num_samples - 1)
            current_angle = start_angle + t * angle_delta
            
            for inner_outer in [-1, 1]:
                r = radius + inner_outer * width_half
                rad = math.radians(current_angle)
                bx = center[0] + r * math.cos(rad)
                by = center[1] + r * math.sin(rad)
                borders.add((int(bx), int(by)))
        
        return borders
