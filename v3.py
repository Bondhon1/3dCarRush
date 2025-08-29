import sys
import math
import random
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

# Camera and constants
camera_offset = [0, -10, 5]  # Camera offset relative to car
car_pos = [0, -600, 30]      # Start car at y = -GRID_LENGTH, slightly above ground
car_angle = 0.0              # Angle in degrees
fovY = 60                   # Reduced for better focus
GRID_LENGTH = 600
selected_layout = None

lives = 3
collision_cooldown = 0  # To avoid multiple life losses per frame

# Global constants for borders
BORDER_HEIGHT = 30.0
BORDER_THICKNESS = 12.0


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def draw_vertical_borders(x_left, x_right, y_start, y_end, height=BORDER_HEIGHT, thickness=BORDER_THICKNESS):
    glColor3f(0.6, 0.6, 0.2)
    glBegin(GL_QUADS)
    glVertex3f(x_left, y_start, height)
    glVertex3f(x_left + thickness, y_start, 0.1)
    glVertex3f(x_left + thickness, y_end, 0.1)
    glVertex3f(x_left, y_end, height)
    glEnd()
    glBegin(GL_QUADS)
    glVertex3f(x_right - thickness, y_start, height)
    glVertex3f(x_right, y_start, 0.1)
    glVertex3f(x_right, y_end, 0.1)
    glVertex3f(x_right - thickness, y_end, height)
    glEnd()


def draw_horizontal_borders(y_left, y_right, x_start, x_end, height=BORDER_HEIGHT, thickness=BORDER_THICKNESS):
    glColor3f(0.6, 0.6, 0.2)
    glBegin(GL_QUADS)
    glVertex3f(x_start, y_left, 0.1)
    glVertex3f(x_end, y_left, 0.1)
    glVertex3f(x_end, y_left - thickness, height)
    glVertex3f(x_start, y_left - thickness, height)
    glEnd()
    glBegin(GL_QUADS)
    glVertex3f(x_start, y_right, 0.1)
    glVertex3f(x_end, y_right, 0.1)
    glVertex3f(x_end, y_right + thickness, height)
    glVertex3f(x_start, y_right + thickness, height)
    glEnd()


def draw_curved_border(center_x, center_y, radius, half_width, start_angle, end_angle, height=BORDER_HEIGHT, thickness=BORDER_THICKNESS):
    segments = 32
    glColor3f(0.6, 0.6, 0.2)
    radii = [radius - half_width, radius + half_width]
    for r in radii:
        for i in range(segments):
            angle1 = start_angle + i * (end_angle - start_angle) / segments
            angle2 = start_angle + (i+1) * (end_angle - start_angle) / segments
            x1 = center_x + r * math.cos(angle1)
            y1 = center_y + r * math.sin(angle1)
            x2 = center_x + r * math.cos(angle2)
            y2 = center_y + r * math.sin(angle2)
            x1_in = center_x + (r - (thickness if r < radius else -thickness)) * math.cos(angle1)
            y1_in = center_y + (r - (thickness if r < radius else -thickness)) * math.sin(angle1)
            x2_in = center_x + (r - (thickness if r < radius else -thickness)) * math.cos(angle2)
            y2_in = center_y + (r - (thickness if r < radius else -thickness)) * math.sin(angle2)
            glBegin(GL_QUADS)
            glVertex3f(x1_in, y1_in, 0.1)
            glVertex3f(x1, y1, 0.1)
            glVertex3f(x2, y2, height)
            glVertex3f(x2_in, y2_in, height)
            glEnd()


def draw_straight_road(center_x, start_y, length, road_width=400):
    half_width = road_width // 2
    end_y = start_y + length
    glColor3f(0.1, 0.1, 0.1)
    glBegin(GL_QUADS)
    glVertex3f(center_x - half_width, start_y, 0.1)
    glVertex3f(center_x + half_width, start_y, 0.1)
    glVertex3f(center_x + half_width, end_y, 0.1)
    glVertex3f(center_x - half_width, end_y, 0.1)
    glEnd()
    draw_vertical_borders(center_x - half_width, center_x + half_width, start_y, end_y)
    glColor3f(1, 1, 1)
    for lane_x in [center_x - 100, center_x, center_x + 100]:
        for y in range(int(start_y) + 20, int(end_y), 80):
            glBegin(GL_QUADS)
            glVertex3f(lane_x - 5, y, 1)
            glVertex3f(lane_x + 5, y, 1)
            glVertex3f(lane_x + 5, y + 40, 1)
            glVertex3f(lane_x - 5, y + 40, 1)
            glEnd()


def draw_horizontal_road(center_y, start_x, length, road_width=400):
    half_width = road_width // 2
    end_x = start_x + length
    glColor3f(0.1, 0.1, 0.1)
    glBegin(GL_QUADS)
    glVertex3f(start_x, center_y - half_width, 0.1)
    glVertex3f(end_x, center_y - half_width, 0.1)
    glVertex3f(end_x, center_y + half_width, 0.1)
    glVertex3f(start_x, center_y + half_width, 0.1)
    glEnd()
    draw_horizontal_borders(center_y - half_width, center_y + half_width, start_x, end_x)
    glColor3f(1, 1, 1)
    for lane_y in [center_y - 100, center_y, center_y + 100]:
        for x in range(int(start_x) + 20, int(end_x), 80):
            glBegin(GL_QUADS)
            glVertex3f(x, lane_y - 5, 1)
            glVertex3f(x + 40, lane_y - 5, 1)
            glVertex3f(x + 40, lane_y + 5, 1)
            glVertex3f(x, lane_y + 5, 1)
            glEnd()


def draw_curved_road(center_x, center_y, curve_radius, road_width=400, angle_start=0, angle_end=math.pi / 2, x_shift=0):
    half_width = road_width // 2
    segments = 32
    glColor3f(0.1, 0.1, 0.1)
    for i in range(segments):
        angle1 = angle_start + i * (angle_end - angle_start) / segments
        angle2 = angle_start + (i + 1) * (angle_end - angle_start) / segments
        inner_x1 = center_x + x_shift + (curve_radius - half_width) * math.cos(angle1)
        inner_y1 = center_y + (curve_radius - half_width) * math.sin(angle1)
        outer_x1 = center_x + x_shift + (curve_radius + half_width) * math.cos(angle1)
        outer_y1 = center_y + (curve_radius + half_width) * math.sin(angle1)
        inner_x2 = center_x + x_shift + (curve_radius - half_width) * math.cos(angle2)
        inner_y2 = center_y + (curve_radius - half_width) * math.sin(angle2)
        outer_x2 = center_x + x_shift + (curve_radius + half_width) * math.cos(angle2)
        outer_y2 = center_y + (curve_radius + half_width) * math.sin(angle2)
        glBegin(GL_QUADS)
        glVertex3f(inner_x1, inner_y1, 0.1)
        glVertex3f(outer_x1, outer_y1, 0.1)
        glVertex3f(outer_x2, outer_y2, 0.1)
        glVertex3f(inner_x2, inner_y2, 0.1)
        glEnd()
    draw_curved_border(center_x + x_shift, center_y, curve_radius, half_width, angle_start, angle_end)
    glColor3f(1, 1, 1)
    lane_offsets = [-100, 0, 100]
    for lane_offset in lane_offsets:
        lane_r = curve_radius + lane_offset
        lane_segments = 16
        for i in range(0, lane_segments, 2):
            ang1 = angle_start + i * (angle_end - angle_start) / lane_segments
            ang2 = angle_start + (i + 1) * (angle_end - angle_start) / lane_segments
            center_x1 = center_x + x_shift + lane_r * math.cos(ang1)
            center_y1 = center_y + lane_r * math.sin(ang1)
            center_x2 = center_x + x_shift + lane_r * math.cos(ang2)
            center_y2 = center_y + lane_r * math.sin(ang2)
            line_width = 5
            perp_angle1 = ang1 + math.pi / 2
            perp_angle2 = ang2 + math.pi / 2
            line_x1_1 = center_x1 + line_width * math.cos(perp_angle1)
            line_y1_1 = center_y1 + line_width * math.sin(perp_angle1)
            line_x1_2 = center_x1 - line_width * math.cos(perp_angle1)
            line_y1_2 = center_y1 - line_width * math.sin(perp_angle1)
            line_x2_1 = center_x2 + line_width * math.cos(perp_angle2)
            line_y2_1 = center_y2 + line_width * math.sin(perp_angle2)
            line_x2_2 = center_x2 - line_width * math.cos(perp_angle2)
            line_y2_2 = center_y2 - line_width * math.sin(perp_angle2)
            glBegin(GL_QUADS)
            glVertex3f(line_x1_1, line_y1_1, 1)
            glVertex3f(line_x1_2, line_y1_2, 1)
            glVertex3f(line_x2_2, line_y2_2, 1)
            glVertex3f(line_x2_1, line_y2_1, 1)
            glEnd()


def draw_road():
    selected_layout()


def draw_cube(size):
    glBegin(GL_QUADS)
    # Front face
    glVertex3f(-size, -size, size)
    glVertex3f(size, -size, size)
    glVertex3f(size, size, size)
    glVertex3f(-size, size, size)
    # Back face
    glVertex3f(-size, -size, -size)
    glVertex3f(size, -size, -size)
    glVertex3f(size, size, -size)
    glVertex3f(-size, size, -size)
    # Top face
    glVertex3f(-size, size, -size)
    glVertex3f(size, size, -size)
    glVertex3f(size, size, size)
    glVertex3f(-size, size, size)
    # Bottom face
    glVertex3f(-size, -size, -size)
    glVertex3f(size, -size, -size)
    glVertex3f(size, -size, size)
    glVertex3f(-size, -size, size)
    # Left face
    glVertex3f(-size, -size, -size)
    glVertex3f(-size, -size, size)
    glVertex3f(-size, size, size)
    glVertex3f(-size, size, -size)
    # Right face
    glVertex3f(size, -size, -size)
    glVertex3f(size, -size, size)
    glVertex3f(size, size, size)
    glVertex3f(size, size, -size)
    glEnd()


def draw_cylinder(radius, height, slices=20):
    quad = gluNewQuadric()
    gluCylinder(quad, radius, radius, height, slices, 1)
    # Top disk
    glPushMatrix()
    glTranslatef(0, 0, height)
    gluDisk(quad, 0, radius, slices, 1)
    glPopMatrix()
    # Bottom disk
    glPushMatrix()
    glRotatef(180, 1, 0, 0)
    gluDisk(quad, 0, radius, slices, 1)
    glPopMatrix()
    gluDeleteQuadric(quad)


def draw_player_car(x=0, y=0, z=30, car_angle=0, gun_angle=0):
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(car_angle - 90, 0, 0, 1)

    # Main body - lighter blue
    glPushMatrix()
    glScalef(2.5, 1.2, 0.6)
    glColor3f(0.4, 0.5, 0.9)  # Light sky blue
    draw_cube(1.0)
    glPopMatrix()

    # Cabin - light grey
    glPushMatrix()
    glTranslatef(0.0, 0.0, 0.65)
    glScalef(1.2, 0.9, 0.55)
    glColor3f(0.0, 0.85, 0.9)  # Light grey-blue
    draw_cube(1.0)
    glPopMatrix()

    # Gun mount platform - pale yellow
    glPushMatrix()
    glTranslatef(0.6, 0.0, 1.1)
    glScalef(0.5, 0.5, 0.1)
    glColor3f(0.5, 0.2, 0.5)  # Pale yellow
    draw_cube(1.0)
    glPopMatrix()

    # Gun barrel - light silver
    glPushMatrix()
    glTranslatef(0.6, 0.0, 1.2)
    glRotatef(gun_angle, 0, 0, 1)
    glRotatef(90, 0, 1, 0)
    glColor3f(0.2, 0.2, 0.2)  # Light silver
    draw_cylinder(0.1, 1.0)
    glPopMatrix()

    # Wheels - black cylinders
    wheel_positions = [(-1.4, 1.3, 0.0), (-1.4, -1.3, 0.0), (1.4, 1.3, 0.0), (1.4, -1.3, 0.0)]
    for wx, wy, wz in wheel_positions:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glRotatef(90, 1, 0, 0)
        glColor3f(0.05, 0.05, 0.05)  # Near black tires
        draw_cylinder(0.3, 0.2)
        glPopMatrix()

    glPopMatrix()


# RoadSegment class to store bounds for collision detection
class RoadSegment:
    def __init__(self, type_, params):
        self.type = type_
        self.params = params


# Define road segments for each layout (replace full list with actual roads from your layouts)

layout1_segments = [
    RoadSegment('vertical', {
        'center_x': 0, 'y_min': -GRID_LENGTH, 'y_max': GRID_LENGTH * 2, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': 100, 'center_y': GRID_LENGTH - 1200, 'radius': 200, 'half_width': 200,
        'start_angle': math.pi, 'end_angle': math.pi + math.pi / 2, 'x_shift': 100
    }),
    RoadSegment('horizontal', {
        'center_y': GRID_LENGTH - 1400, 'x_min': 200, 'x_max': 1800, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': 1800, 'center_y': -GRID_LENGTH - 400, 'radius': 200, 'half_width': 200,
        'start_angle': 0, 'end_angle': math.pi / 2, 'x_shift': 0
    }),
    RoadSegment('vertical', {
        'center_x': 2000, 'y_min': -GRID_LENGTH - 2800, 'y_max': GRID_LENGTH, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': 1700 + 100, 'center_y': GRID_LENGTH - 4000, 'radius': 200, 'half_width': 200,
        'start_angle': 0, 'end_angle': -math.pi / 2, 'x_shift': 0
    }),
    RoadSegment('horizontal', {
        'center_y': GRID_LENGTH - 4200, 'x_min': -2200, 'x_max': 1800, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': -2300 + 100, 'center_y': GRID_LENGTH - 4000, 'radius': 200, 'half_width': 200,
        'start_angle': -math.pi, 'end_angle': -math.pi / 2, 'x_shift': 0
    }),
    RoadSegment('vertical', {
        'center_x': -2400, 'y_min': -GRID_LENGTH - 2800, 'y_max': GRID_LENGTH * 2 + 400, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': -2300 + 100, 'center_y': GRID_LENGTH, 'radius': 200, 'half_width': 200,
        'start_angle': math.pi, 'end_angle': math.pi / 2, 'x_shift': 0
    }),
    RoadSegment('horizontal', {
        'center_y': GRID_LENGTH + 200, 'x_min': -2200, 'x_max': -200, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': -300 + 100, 'center_y': GRID_LENGTH, 'radius': 200, 'half_width': 200,
        'start_angle': 0, 'end_angle': math.pi / 2, 'x_shift': 0
    }),
]

# Similarly define layout2_segments and layout3_segments with their road bounding segments according to layout2 and layout3 definitions
# For simplicity, using same as layout1 here but in actual use they differ
layout2_segments = [
    RoadSegment('vertical', {
        'center_x': 0, 'y_min': -GRID_LENGTH - 2400, 'y_max': GRID_LENGTH * 5, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': -300 + 100, 'center_y': GRID_LENGTH - 3600, 'radius': 200, 'half_width': 200,
        'start_angle': 0, 'end_angle': -math.pi / 2, 'x_shift': 0
    }),
    RoadSegment('horizontal', {
        'center_y': GRID_LENGTH - 3800, 'x_min': -3400, 'x_max': -200, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': -3500 + 100, 'center_y': GRID_LENGTH - 4000, 'radius': 200, 'half_width': 200,
        'start_angle': math.pi, 'end_angle': math.pi / 2, 'x_shift': 0
    }),
    RoadSegment('vertical', {
        'center_x': -3600, 'y_min': -GRID_LENGTH - 4000, 'y_max': GRID_LENGTH * 2, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': -3900 + 100, 'center_y': GRID_LENGTH - 5200, 'radius': 200, 'half_width': 200,
        'start_angle': 0, 'end_angle': -math.pi / 2, 'x_shift': 0
    }),
    RoadSegment('horizontal', {
        'center_y': GRID_LENGTH - 5400, 'x_min': -6000, 'x_max': -3800, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': -6100 + 100, 'center_y': GRID_LENGTH - 5200, 'radius': 200, 'half_width': 200,
        'start_angle': -math.pi, 'end_angle': -math.pi / 2, 'x_shift': 0
    }),
    RoadSegment('vertical', {
        'center_x': -6200, 'y_min': -GRID_LENGTH - 4000, 'y_max': GRID_LENGTH * 7, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': -6100 + 100, 'center_y': GRID_LENGTH, 'radius': 200, 'half_width': 200,
        'start_angle': math.pi, 'end_angle': math.pi / 2, 'x_shift': 0
    }),
    RoadSegment('horizontal', {
        'center_y': GRID_LENGTH + 200, 'x_min': -6000, 'x_max': -220, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': -300 + 100, 'center_y': GRID_LENGTH, 'radius': 200, 'half_width': 200,
        'start_angle': 0, 'end_angle': math.pi / 2, 'x_shift': 0
    }),
]

layout3_segments = [
    RoadSegment('vertical', {
        'center_x': 0, 'y_min': -GRID_LENGTH - 2400, 'y_max': GRID_LENGTH * 5, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': -300 + 100, 'center_y': GRID_LENGTH - 3600, 'radius': 200, 'half_width': 200,
        'start_angle': 0, 'end_angle': -math.pi / 2, 'x_shift': 0
    }),
    RoadSegment('horizontal', {
        'center_y': GRID_LENGTH - 3800, 'x_min': -4800, 'x_max': 0, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': -5100 + 100, 'center_y': GRID_LENGTH - 3600, 'radius': 400, 'half_width': 200,
        'start_angle': -math.pi, 'end_angle': -math.pi / 2, 'x_shift': 0
    }),
    RoadSegment('vertical', {
        'center_x': -5200, 'y_min': -GRID_LENGTH - 2400, 'y_max': GRID_LENGTH * 2, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': -5100 + 100, 'center_y': GRID_LENGTH, 'radius': 200, 'half_width': 200,
        'start_angle': math.pi, 'end_angle': math.pi / 2, 'x_shift': 0
    }),
    RoadSegment('horizontal', {
        'center_y': GRID_LENGTH + 200, 'x_min': -5000, 'x_max': -200, 'half_width': 200
    }),
    RoadSegment('curve', {
        'center_x': -300 + 100, 'center_y': GRID_LENGTH, 'radius': 200, 'half_width': 200,
        'start_angle': 0, 'end_angle': math.pi / 2, 'x_shift': 0
    }),
]


def is_point_in_vertical_road(x, y, seg):
    return (seg['center_x'] - seg['half_width'] <= x <= seg['center_x'] + seg['half_width'] and
            seg['y_min'] <= y <= seg['y_max'])


def is_point_in_horizontal_road(x, y, seg):
    return (seg['x_min'] <= x <= seg['x_max'] and
            seg['center_y'] - seg['half_width'] <= y <= seg['center_y'] + seg['half_width'])


def is_point_in_curved_road(x, y, seg):
    cx = seg['center_x'] + seg.get('x_shift', 0)
    cy = seg['center_y']
    dx = x - cx
    dy = y - cy
    dist = math.sqrt(dx*dx + dy*dy)
    margin = 15  # collision margin in units

    # Enlarged borders for safety
    if dist < seg['radius'] - seg['half_width'] - margin or dist > seg['radius'] + seg['half_width'] + margin:
        return False

    angle = math.atan2(dy, dx)

    def normalize(a):
        while a < 0:
            a += 2*math.pi
        while a >= 2*math.pi:
            a -= 2*math.pi
        return a

    def is_angle_in_range(angle, start_angle, end_angle, epsilon=0.05):
        angle = normalize(angle)
        start = normalize(start_angle - epsilon)
        end = normalize(end_angle + epsilon)
        if start < end:
            return start <= angle <= end
        else:
            return angle >= start or angle <= end

    start_angle = seg['start_angle']
    end_angle = seg['end_angle']

    return is_angle_in_range(angle, start_angle, end_angle)


# Use this instead of original angular check in is_point_in_curved_road


def check_collision(car_x, car_y):
    segments = []

    global selected_layout
    if selected_layout == layout1:
        segments = layout1_segments
    elif selected_layout == layout2:
        segments = layout2_segments
    elif selected_layout == layout3:
        segments = layout3_segments
    else:
        # Safe fallback: allow free movement if no layout
        return False

    for seg in segments:
        if seg.type == 'vertical':
            if is_point_in_vertical_road(car_x, car_y, seg.params):
                return False
        elif seg.type == 'horizontal':
            if is_point_in_horizontal_road(car_x, car_y, seg.params):
                return False
        elif seg.type == 'curve':
            if is_point_in_curved_road(car_x, car_y, seg.params):
                return False

    # If none of the segments match, car is out of the road area: collision
    return True


def keyboard(key, x, y):
    global car_pos, car_angle, lives, collision_cooldown
    step = 20
    turn_speed = 5

    angle_rad = math.radians(car_angle - 90)
    moved = False
    old_pos = car_pos[:]

    if key == b'w':
        car_pos[0] -= step * math.cos(angle_rad)
        car_pos[1] -= step * math.sin(angle_rad)
        moved = True
    elif key == b's':
        car_pos[0] += step * math.cos(angle_rad)
        car_pos[1] += step * math.sin(angle_rad)
        moved = True
    elif key == b'a':
        car_angle += turn_speed
    elif key == b'd':
        car_angle -= turn_speed

    if moved:
        if check_collision(car_pos[0], car_pos[1]):
            if collision_cooldown == 0:
                lives -= 1
                collision_cooldown = 10  # frames cooldown
            # Reflect car back to old position and reverse angle roughly
            car_pos[:] = old_pos
            car_angle = (car_angle + 180) % 360
    if collision_cooldown > 0:
        collision_cooldown -= 1

    glutPostRedisplay()


def special_keyboard(key, x, y):
    global car_pos, car_angle, lives, collision_cooldown
    step = 20
    turn_speed = 5

    angle_rad = math.radians(car_angle - 90)
    moved = False
    old_pos = car_pos[:]

    if key == GLUT_KEY_UP:
        car_pos[0] -= step * math.cos(angle_rad)
        car_pos[1] -= step * math.sin(angle_rad)
        moved = True
    elif key == GLUT_KEY_DOWN:
        car_pos[0] += step * math.cos(angle_rad)
        car_pos[1] += step * math.sin(angle_rad)
        moved = True
    elif key == GLUT_KEY_LEFT:
        car_angle += turn_speed
    elif key == GLUT_KEY_RIGHT:
        car_angle -= turn_speed

    if moved:
        if check_collision(car_pos[0], car_pos[1]):
            if collision_cooldown == 0:
                lives -= 1
                collision_cooldown = 10  # frames cooldown
            car_pos[:] = old_pos
            car_angle = (car_angle + 180) % 360
    if collision_cooldown > 0:
        collision_cooldown -= 1

    glutPostRedisplay()


def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 1.0, 2000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    x, y, z = car_pos
    offset_distance = math.sqrt(camera_offset[0] ** 2 + camera_offset[1] ** 2)
    offset_angle = math.atan2(camera_offset[1], camera_offset[0])
    total_angle = math.radians(car_angle) + offset_angle
    camera_x = x + offset_distance * math.cos(total_angle)
    camera_y = y + offset_distance * math.sin(total_angle)
    camera_z = z + camera_offset[2]
    gluLookAt(camera_x, camera_y, camera_z, x, y, z, 0, 0, 1)


def idle():
    glutPostRedisplay()


def showScreen_with_minimap():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    # --- Main viewport (full window) ---
    glViewport(0, 0, 1000, 800)
    setupCamera()
    draw_road()
    draw_player_car(car_pos[0], car_pos[1], car_pos[2], car_angle, 0)
    draw_text(10, 770, "CSE423 Car Game Demo - Extended Road with 90° Turn")
    draw_text(10, 750, f"Lives: {lives}")

    # --- Mini viewport (top-right corner) ---
    mini_width, mini_height = 200, 200
    glViewport(1000 - mini_width - 20, 800 - mini_height - 20, mini_width, mini_height)

    # Save current matrices
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(-3000, 3000, -3000, 3000, -1000, 1000)  # Adjust bounds to cover map

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glClear(GL_DEPTH_BUFFER_BIT)  # Clear depth only for minimap viewport

    # Top-down camera
    gluLookAt(car_pos[0], car_pos[1], 1000,
              car_pos[0], car_pos[1], 0,
              0, 1, 0)

    # Draw the scene again from top-down perspective
    draw_road()
    draw_player_car(car_pos[0], car_pos[1], car_pos[2], car_angle, 0)

    # Draw a red dot at car position to make it more visible on minimap
    glColor3f(1.0, 0.0, 0.0)
    dot_size = 50
    glBegin(GL_QUADS)
    glVertex2f(car_pos[0] - dot_size, car_pos[1] - dot_size)
    glVertex2f(car_pos[0] + dot_size, car_pos[1] - dot_size)
    glVertex2f(car_pos[0] + dot_size, car_pos[1] + dot_size)
    glVertex2f(car_pos[0] - dot_size, car_pos[1] + dot_size)
    glEnd()

    # Restore matrices
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    # Restore main viewport
    glViewport(0, 0, 1000, 800)

    glutSwapBuffers()



def layout1():
    draw_straight_road(center_x=0, start_y=-GRID_LENGTH, length=2 * GRID_LENGTH)
    draw_curved_road(center_x=100, center_y=GRID_LENGTH - 1200, curve_radius=200, angle_start=math.pi,
                     angle_end=math.pi + math.pi / 2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH - 1400, start_x=200, length=1600)
    draw_curved_road(center_x=1800, center_y=-GRID_LENGTH - 400, curve_radius=200, angle_start=0, angle_end=math.pi / 2)
    draw_straight_road(center_x=2000, start_y=-GRID_LENGTH - 1600, length=2 * GRID_LENGTH)
    draw_straight_road(center_x=2000, start_y=-GRID_LENGTH - 2800, length=2 * GRID_LENGTH)
    draw_curved_road(center_x=1700, center_y=GRID_LENGTH - 4000, curve_radius=200, angle_start=0,
                     angle_end=-math.pi / 2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH - 4200, start_x=200, length=1600)
    draw_horizontal_road(center_y=GRID_LENGTH - 4200, start_x=-2200, length=2400)
    draw_curved_road(center_x=-2300, center_y=GRID_LENGTH - 4000, curve_radius=200, angle_start=-math.pi,
                     angle_end=-math.pi / 2, x_shift=100)
    draw_straight_road(center_x=-2400, start_y=-GRID_LENGTH - 2800, length=6 * GRID_LENGTH + 400)
    draw_curved_road(center_x=-2300, center_y=GRID_LENGTH, curve_radius=200, angle_start=math.pi, angle_end=math.pi / 2,
                     x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH + 200, start_x=-2200, length=2000)
    draw_curved_road(center_x=-300, center_y=GRID_LENGTH, curve_radius=200, angle_start=0, angle_end=math.pi / 2,
                     x_shift=100)


def layout2():
    draw_straight_road(center_x=0, start_y=-GRID_LENGTH-2400, length=6*GRID_LENGTH)
    draw_curved_road(center_x=-300, center_y=GRID_LENGTH-3600, curve_radius=200, angle_start=0, angle_end=-math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH-3800, start_x=-3400, length=3200)
    draw_curved_road(center_x=-3500, center_y=GRID_LENGTH-4000, curve_radius=200, angle_start=math.pi, angle_end=math.pi/2, x_shift=100)
    draw_straight_road(center_x=-3600, start_y=-GRID_LENGTH-4000, length=2*GRID_LENGTH)
    draw_curved_road(center_x=-3900, center_y=GRID_LENGTH-5200, curve_radius=200, angle_start=0, angle_end=-math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH-5400, start_x=-6000, length=2200)
    draw_curved_road(center_x=-6100, center_y=GRID_LENGTH-5200, curve_radius=200, angle_start=-math.pi, angle_end=-math.pi/2, x_shift=100)
    draw_straight_road(center_x=-6200, start_y=-GRID_LENGTH-4000, length=8*GRID_LENGTH+400)
    draw_curved_road(center_x=-6100, center_y=GRID_LENGTH, curve_radius=200, angle_start=math.pi, angle_end=math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH+200, start_x=-6000, length=5800)
    draw_curved_road(center_x=-300, center_y=GRID_LENGTH, curve_radius=200, angle_start=0, angle_end=math.pi/2, x_shift=100)

def layout3():
    draw_straight_road(center_x=0, start_y=-GRID_LENGTH-2400, length=6*GRID_LENGTH)
    draw_curved_road(center_x=-300, center_y=GRID_LENGTH-3600, curve_radius=200, angle_start=0, angle_end=-math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH-3800, start_x=-5000, length=4800)
    draw_curved_road(center_x=-5100, center_y=GRID_LENGTH-3600, curve_radius=200, angle_start=-math.pi, angle_end=-math.pi/2, x_shift=100)
    draw_straight_road(center_x=-5200, start_y=-GRID_LENGTH-2400, length=6*GRID_LENGTH)
    draw_curved_road(center_x=-5100, center_y=GRID_LENGTH, curve_radius=200, angle_start=math.pi, angle_end=math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH+200, start_x=-5000, length=4800)
    draw_curved_road(center_x=-300, center_y=GRID_LENGTH, curve_radius=200, angle_start=0, angle_end=math.pi/2, x_shift=100)


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Car Game: Extended Road with Curve")
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keyboard)
    glClearColor(0.0, 0.4, 0.0, 1.0)

    glutDisplayFunc(showScreen_with_minimap)
    glutIdleFunc(idle)
    global selected_layout, layout2_segments, layout3_segments

    # For simplicity, use layout1's segments for layout2 and layout3 (can be replaced with actual data)
   

    layouts = [layout1, layout2, layout3]
    selected_layout = random.choice(layouts)
    print(f"Selected layout: {selected_layout.__name__}")
    glutMainLoop()


if __name__ == "__main__":
    main()
