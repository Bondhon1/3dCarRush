import sys
import math
import random
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import time
import numpy as np  # At top with other imports

# Camera and constants
camera_offset = [0, -150, 75]  # Camera offset relative to car
car_pos = [50, -600, 10]  # Start car at y = -GRID_LENGTH, slightly above ground
car_angle = 0.0   # Angle in degrees
fovY = 60  # Reduced for better focus
GRID_LENGTH = 600
selected_layout = None
lives = 10
road_positions = set()
border_positions = set()
cheat_message = ""  # Global or at top
paused = False
# --- Movement state ---
normal_speed = 15.0
boost_speed = 20.0
slow_speed = 10.0

current_speed = normal_speed
bullets = []  # list of active bullets (x, y, z, angle)
gun_angle = 0.0
gun_turn_speed = 5.0   # degrees per key press
bullet_speed = 30.0    # speed of bullet units/frame

turn_speed = 3        # degrees per press
CAR_LENGTH = 15 * 2.5
CAR_WIDTH = 15 * 1.2

enemy_player_collision_flag = False
enemy_player_collision_start_time = 0
collision_flag = False
collision_start_time = 0
COLLISION_DURATION = 2.0     # seconds
COLLISION_PUSH_SPEED = 0.5   # constant displacement per frame

boost_active = False
boost_start_time = 0
shield_active = False
shield_start_time = 0
shield_kits = []  # [(x,y), (x,y), ...]
num_shield_kits = 3  # number of shield kits to spawn
# At the top
finish_line_pos = None
finish_line_angle = 0
finish_crossed = False
prev_car_pos = car_pos[:]
finish_line_width = 450  # or match the road width at the finish line





# Global constants for borders
BORDER_HEIGHT = 30.0
BORDER_THICKNESS = 12.0

bombs = []
explosions = []  # each entry: {'pos': (x, y), 'start_time': time}
# --- NEW GLOBALS ---
health_kits = []   # [(x,y), (x,y), ...]
kit_size = 20      # size of the 3D plus
kit_height = 40    # how tall the plus arms go
num_kits = 4       # number of kits to spawn
kits_spawned = False
def spawn_health_kits():
    global health_kits
    road_list = list(road_positions)
    random.shuffle(road_list)
    health_kits = road_list[:num_kits]  # pick 4 random road positions
def draw_health_kit(x, y, z=20):
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(1.0, 0.0, 0.0)  # Red color
    # Draw a 3D plus: center cube + 2 arms X + 2 arms Y
    def cube(sz):
        glPushMatrix()
        glScalef(sz, sz, sz)
        draw_cube(1.0)
        glPopMatrix()
    arm = kit_size
    thick = kit_size // 2
    # Center
    cube(thick)
    # Arms along X
    glPushMatrix(); glTranslatef(arm, 0, 0); cube(thick); glPopMatrix()
    glPushMatrix(); glTranslatef(-arm, 0, 0); cube(thick); glPopMatrix()
    # Arms along Y
    glPushMatrix(); glTranslatef(0, arm, 0); cube(thick); glPopMatrix()
    glPushMatrix(); glTranslatef(0, -arm, 0); cube(thick); glPopMatrix()
    glPopMatrix()
def check_health_kit_collision():
    global health_kits, lives
    cx, cy, cz = car_pos
    collected = []
    for (hx, hy) in health_kits:
        dist = math.sqrt((cx - hx)**2 + (cy - hy)**2)
        if dist < 60:  # pickup radius
            if lives < 10:
                lives += 1
                print("Picked up health kit! Lives =", lives)
            else:
                print("Health already full!")
            collected.append((hx, hy))
    # Remove collected kits
    health_kits = [pos for pos in health_kits if pos not in collected]

#bomb
def spawn_bombs():
    global bombs
    bombs = []
    road_list = list(road_positions)
    random.shuffle(road_list)
    bombs = road_list[:6]  # pick 6 random road positions
def draw_bomb(x, y, size=20, height=30):
    """Draw a 3D bomb at (x, y). Black base with yellow top."""
    glPushMatrix()
    glTranslatef(x, y, height // 2)  # Raise bomb slightly above ground

    # Black base - cylinder
    glColor3f(0.1, 0.0, 0.0)
    quad = gluNewQuadric()
    gluCylinder(quad, size * 0.6, size * 0.6, height * 0.7, 20, 5)
    glPushMatrix()
    glTranslatef(0, 0, height * 0.7)
    gluDisk(quad, 0, size * 0.6, 20, 1)  # top disk of base
    glPopMatrix()
    gluDisk(quad, 0, size * 0.6, 20, 1)      # bottom disk
    gluDeleteQuadric(quad)

    # Yellow top - sphere
    glColor3f(1.0, 1.0, 0.0)
    glTranslatef(0, 0, height * 0.7)  # move to top of cylinder
    quad2 = gluNewQuadric()
    gluSphere(quad2, size * 0.4, 20, 20)
    gluDeleteQuadric(quad2)

    glPopMatrix()


    # Yellow top (smaller circle)
    glColor3f(1.0, 1.0, 0.0)
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(x, y + size * 0.6)
    for angle in range(0, 361, 10):
        rad = math.radians(angle)
        glVertex2f(x + math.cos(rad) * (size * 0.4),
                   y + size * 0.6 + math.sin(rad) * (size * 0.4))
    glEnd()
def check_bomb_collision():
    global bombs, lives, explosions
    car_x, car_y = car_pos[0], car_pos[1]
    bomb_hit = None
    for (bx, by) in bombs:
        dist = math.hypot(car_x - bx, car_y - by)
        if dist < 30:  # collision radius
            lives -= 1
            bomb_hit = (bx, by)
            break
    if bomb_hit:
        bombs.remove(bomb_hit)
        # Add explosion at bomb location with current time
        explosions.append({'pos': bomb_hit, 'start_time': time.time()})

def draw_simple_cone(x, y, scale, segments=30, height=20, base_radius=10):
    glPushMatrix()
    glTranslatef(x, y, 0)
    glRotatef(90, 1, 0, 0)  # rotate cone to point upwards along +Y axis
    glScalef(scale, scale, scale)
    
    # Draw cone surface with vertical red to yellow gradient
    glBegin(GL_TRIANGLE_FAN)
    # Tip vertex (yellow)
    glColor3f(1.0, 1.0, 0.0)  # yellow at apex
    glVertex3f(0, height, 0)
    
    # Base circle vertices (red)
    glColor3f(1.0, 0.0, 0.0)  # red at base
    for i in range(segments + 1):
        angle = 2 * math.pi * i / segments
        x_pos = base_radius * math.cos(angle)
        z_pos = base_radius * math.sin(angle)
        glVertex3f(x_pos, 0, z_pos)
    glEnd()
    
    glPopMatrix()

def draw_all_explosions():
    global explosions
    current_time = time.time()
    active_explosions = []
    for exp in explosions:
        elapsed = current_time - exp['start_time']
        if elapsed < 1.0:
            scale = 0.3 + 1.2 * (elapsed / 1.0)  # grow scale from 0.3 to 1.5
            draw_simple_cone(exp['pos'][0], exp['pos'][1], scale)
            active_explosions.append(exp)
    explosions = active_explosions

def spawn_shield_kits():
    global shield_kits
    road_list = list(road_positions)
    random.shuffle(road_list)
    shield_kits = road_list[:num_shield_kits]

def draw_shield_kit(x, y, z=20):
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(0.0, 0.8, 1.0)  # cyan color for shield kit
    
    size = 30
    half_size = size / 2
    depth = size / 2  # depth for 3D effect

    # Draw diamond by combining two pyramids (top and bottom)
    # Top pyramid (pointing up)
    glBegin(GL_TRIANGLES)
    # Front face
    glVertex3f(0, half_size, 0)           # top point
    glVertex3f(-half_size, 0, depth)      # front-left
    glVertex3f(half_size, 0, depth)       # front-right
    
    # Right face
    glVertex3f(0, half_size, 0)
    glVertex3f(half_size, 0, depth)
    glVertex3f(half_size, 0, -depth)
    
    # Back face
    glVertex3f(0, half_size, 0)
    glVertex3f(half_size, 0, -depth)
    glVertex3f(-half_size, 0, -depth)
    
    # Left face
    glVertex3f(0, half_size, 0)
    glVertex3f(-half_size, 0, -depth)
    glVertex3f(-half_size, 0, depth)
    glEnd()

    # Bottom pyramid (pointing down)
    glBegin(GL_TRIANGLES)
    # Front face
    glVertex3f(0, -half_size, 0)          # bottom point
    glVertex3f(-half_size, 0, depth)      # front-left
    glVertex3f(half_size, 0, depth)       # front-right

    # Right face
    glVertex3f(0, -half_size, 0)
    glVertex3f(half_size, 0, depth)
    glVertex3f(half_size, 0, -depth)

    # Back face
    glVertex3f(0, -half_size, 0)
    glVertex3f(half_size, 0, -depth)
    glVertex3f(-half_size, 0, -depth)

    # Left face
    glVertex3f(0, -half_size, 0)
    glVertex3f(-half_size, 0, -depth)
    glVertex3f(-half_size, 0, depth)
    glEnd()

    # Middle square or diamond-shaped cross section for seam
    glBegin(GL_QUADS)
    glVertex3f(-half_size, 0, depth)
    glVertex3f(half_size, 0, depth)
    glVertex3f(half_size, 0, -depth)
    glVertex3f(-half_size, 0, -depth)
    glEnd()

    glPopMatrix()


def check_shield_kit_collision():
    global shield_kits, shield_active, shield_start_time
    cx, cy, cz = car_pos
    collected = []
    for (sx, sy) in shield_kits:
        dist = math.sqrt((cx - sx)**2 + (cy - sy)**2)
        if dist < 60:  # pickup radius
            if not shield_active:
                shield_active = True
                shield_start_time = time.time()
                print("Shield activated for 5 seconds!")
            collected.append((sx, sy))
    # Remove collected kits
    shield_kits = [pos for pos in shield_kits if pos not in collected]

def add_rectangle_to_set(xmin, xmax, ymin, ymax, store, dx=12, dy=12):
    for x in range(int(xmin), int(xmax)+1, dx):
        for y in range(int(ymin), int(ymax)+1, dy):
            store.add((x, y))

def add_arc_to_set(center_x, center_y, inner_r, outer_r, angle_start, angle_end, store, dr=8, dtheta=0.04):
    r = inner_r
    while r <= outer_r:
        theta = angle_start
        while (theta <= angle_end if angle_end > angle_start else theta >= angle_end):
            x_raw = center_x + r * math.cos(theta)
            y_raw = center_y + r * math.sin(theta)
            x = int(round(x_raw / 8) * 8)
            y = int(round(y_raw / 8) * 8)
            store.add((x, y))
            theta += dtheta if angle_end > angle_start else -dtheta
        r += dr



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

def draw_straight_road(center_x, start_y, length, road_width=400):
    half_width = road_width // 2
    end_y = start_y + length
    add_rectangle_to_set(center_x - half_width, center_x + half_width, start_y, end_y, road_positions)
    glColor3f(0.1, 0.1, 0.1)
    glBegin(GL_QUADS)
    glVertex3f(center_x - half_width, start_y, 0.1)
    glVertex3f(center_x + half_width, start_y, 0.1)
    glVertex3f(center_x + half_width, end_y, 0.1)
    glVertex3f(center_x - half_width, end_y, 0.1)
    glEnd()
    draw_vertical_borders(center_x - half_width, center_x + half_width, start_y, end_y)
    glColor3f(1, 1, 1)
    # Lane lines and position storing
    for lane_x in [center_x - 100, center_x, center_x + 100]:
        for y in range(int(start_y) + 20, int(end_y), 80):
            
            glBegin(GL_QUADS)
            glVertex3f(lane_x - 5, y, 1)
            glVertex3f(lane_x + 5, y, 1)
            glVertex3f(lane_x + 5, y + 40, 1)
            glVertex3f(lane_x - 5, y + 40, 1)
            glEnd()


def draw_vertical_borders(x_left, x_right, y_start, y_end, height=BORDER_HEIGHT, thickness=BORDER_THICKNESS):
    # Left border
    add_rectangle_to_set(x_left, x_left + thickness, y_start, y_end, border_positions)
    # Right border
    add_rectangle_to_set(x_right - thickness, x_right, y_start, y_end, border_positions)
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

def draw_horizontal_road(center_y, start_x, length, road_width=400):
    half_width = road_width // 2
    end_x = start_x + length
    add_rectangle_to_set(start_x, end_x, center_y - half_width, center_y + half_width, road_positions)
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


def draw_horizontal_borders(y_left, y_right, x_start, x_end, height=BORDER_HEIGHT, thickness=BORDER_THICKNESS):
    add_rectangle_to_set(x_start, x_end, y_left - thickness, y_left, border_positions)
    add_rectangle_to_set(x_start, x_end, y_right, y_right + thickness, border_positions)
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

def draw_curved_road(center_x, center_y, curve_radius, road_width=400, angle_start=0, angle_end=math.pi/2, x_shift=0):
    half_width = road_width // 2
    inner_r = curve_radius - half_width
    outer_r = curve_radius + half_width
    add_arc_to_set(center_x + x_shift, center_y, inner_r, outer_r, angle_start, angle_end, road_positions)
    glColor3f(0.1, 0.1, 0.1)
    segments = 32
    for i in range(segments):
        angle1 = angle_start + i * (angle_end - angle_start) / segments
        angle2 = angle_start + (i+1) * (angle_end - angle_start) / segments
        inner_x1 = center_x + x_shift + inner_r * math.cos(angle1)
        inner_y1 = center_y + inner_r * math.sin(angle1)
        outer_x1 = center_x + x_shift + outer_r * math.cos(angle1)
        outer_y1 = center_y + outer_r * math.sin(angle1)
        inner_x2 = center_x + x_shift + inner_r * math.cos(angle2)
        inner_y2 = center_y + inner_r * math.sin(angle2)
        outer_x2 = center_x + x_shift + outer_r * math.cos(angle2)
        outer_y2 = center_y + outer_r * math.sin(angle2)
        glBegin(GL_QUADS)
        glVertex3f(inner_x1, inner_y1, 0.1)
        glVertex3f(outer_x1, outer_y1, 0.1)
        glVertex3f(outer_x2, outer_y2, 0.1)
        glVertex3f(inner_x2, inner_y2, 0.1)
        glEnd()
    draw_curved_border(center_x + x_shift, center_y, curve_radius, half_width, angle_start, angle_end)
    glColor3f(1, 1, 1)
    lane_offsets = [-100, 0, 100]
    lane_segments = 16
    for lane_offset in lane_offsets:
        lane_r = curve_radius + lane_offset
        for i in range(0, lane_segments, 2):
            ang1 = angle_start + i * (angle_end - angle_start) / lane_segments
            ang2 = angle_start + (i+1) * (angle_end - angle_start) / lane_segments
            x1 = center_x + x_shift + lane_r * math.cos(ang1)
            y1 = center_y + lane_r * math.sin(ang1)
            x2 = center_x + x_shift + lane_r * math.cos(ang2)
            y2 = center_y + lane_r * math.sin(ang2)
            # Sample arc mark
            for t in range(5):  # slightly oversample for mark width
                alpha = t / 4
                xm = x1 * (1 - alpha) + x2 * alpha
                ym = y1 * (1 - alpha) + y2 * alpha
                
            line_width = 5
            perp_angle1 = ang1 + math.pi / 2
            perp_angle2 = ang2 + math.pi / 2
            line_x1_1 = x1 + line_width * math.cos(perp_angle1)
            line_y1_1 = y1 + line_width * math.sin(perp_angle1)
            line_x1_2 = x1 - line_width * math.cos(perp_angle1)
            line_y1_2 = y1 - line_width * math.sin(perp_angle1)
            line_x2_1 = x2 + line_width * math.cos(perp_angle2)
            line_y2_1 = y2 + line_width * math.sin(perp_angle2)
            line_x2_2 = x2 - line_width * math.cos(perp_angle2)
            line_y2_2 = y2 - line_width * math.sin(perp_angle2)
            glBegin(GL_QUADS)
            glVertex3f(line_x1_1, line_y1_1, 1)
            glVertex3f(line_x1_2, line_y1_2, 1)
            glVertex3f(line_x2_2, line_y2_2, 1)
            glVertex3f(line_x2_1, line_y2_1, 1)
            glEnd()

def draw_curved_border(center_x, center_y, radius, half_width, start_angle, end_angle, height=BORDER_HEIGHT, thickness=BORDER_THICKNESS):
    # Inner and outer border arcs
    add_arc_to_set(center_x, center_y, radius - half_width, radius - half_width + thickness, start_angle, end_angle, border_positions)
    add_arc_to_set(center_x, center_y, radius + half_width - thickness, radius + half_width, start_angle, end_angle, border_positions)
    glColor3f(0.6, 0.6, 0.2)
    segments = 32
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

def draw_finish_line(x, y, angle=0, width=450, depth=20, banner_height=30, banner_scale_x=1.0, banner_x_angle=90):
    glPushMatrix()
    glTranslatef(x, y, 1.5)
    glRotatef(angle, 0, 0, 1)
    # Draw finish line (white rectangle)
    glColor3f(1.0, 1.0, 1.0)
    glBegin(GL_QUADS)
    glVertex3f(-width // 2, -depth // 2, 0)
    glVertex3f(width // 2, -depth // 2, 0)
    glVertex3f(width // 2, depth // 2, 0)
    glVertex3f(-width // 2, depth // 2, 0)
    glEnd()

    banner_width = width * banner_scale_x
    base_width = 10  # thickness of base supports
    base_y_bottom = depth // 2
    banner_base_z = 150  # fixed height of base tops where banner attaches

    # Draw bases - vertical quads straight up from ground to banner_base_z
    glColor3f(0.1, 0.1, 0.1)  # dark bases

    # Left base
    glBegin(GL_QUADS)
    glVertex3f(-banner_width // 2 - base_width, base_y_bottom, 0)
    glVertex3f(-banner_width // 2, base_y_bottom, 0)
    glVertex3f(-banner_width // 2, base_y_bottom, banner_base_z)
    glVertex3f(-banner_width // 2 - base_width, base_y_bottom, banner_base_z)
    glEnd()

    # Right base
    glBegin(GL_QUADS)
    glVertex3f(banner_width // 2, base_y_bottom, 0)
    glVertex3f(banner_width // 2 + base_width, base_y_bottom, 0)
    glVertex3f(banner_width // 2 + base_width, base_y_bottom, banner_base_z)
    glVertex3f(banner_width // 2, base_y_bottom, banner_base_z)
    glEnd()

    # Draw banner
    banner_height_half = banner_height // 2
    banner_y = base_y_bottom + 10  # slight forward offset from base front face

    glPushMatrix()
    glTranslatef(0, banner_y, banner_base_z)  # at top of bases (fixed z)
    glRotatef(banner_x_angle, 1, 0, 0)  # tilt banner around X axis here
    glColor3f(0.2, 0.2, 0.8)  # blue banner
    glBegin(GL_QUADS)
    glVertex3f(-banner_width // 2, -banner_height_half, 0)
    glVertex3f(banner_width // 2, -banner_height_half, 0)
    glVertex3f(banner_width // 2, banner_height_half, 0)
    glVertex3f(-banner_width // 2, banner_height_half, 0)
    glEnd()
    glPopMatrix()

    glPopMatrix()


def layout1():
    global finish_line_pos, finish_line_angle
    draw_straight_road(center_x=0, start_y=-GRID_LENGTH, length=2*GRID_LENGTH)
    draw_curved_road(center_x=100, center_y=GRID_LENGTH-1200, curve_radius=200, angle_start=math.pi, angle_end=math.pi+math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH-1400, start_x=200, length=1600)
    draw_curved_road(center_x=1800, center_y=-GRID_LENGTH-400, curve_radius=200, angle_start=0, angle_end=math.pi/2)
    draw_straight_road(center_x=2000, start_y=-GRID_LENGTH-1600, length=2*GRID_LENGTH)
    draw_straight_road(center_x=2000, start_y=-GRID_LENGTH-2800, length=2*GRID_LENGTH)
    draw_curved_road(center_x=1700, center_y=GRID_LENGTH-4000, curve_radius=200, angle_start=0, angle_end=-math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH-4200, start_x=200, length=1600)
    draw_horizontal_road(center_y=GRID_LENGTH-4200, start_x=-2200, length=2400)
    draw_curved_road(center_x=-2300, center_y=GRID_LENGTH-4000, curve_radius=200, angle_start=-math.pi, angle_end=-math.pi/2, x_shift=100)
    draw_straight_road(center_x=-2400, start_y=-GRID_LENGTH-2800, length=6*GRID_LENGTH+400)
    draw_curved_road(center_x=-2300, center_y=GRID_LENGTH, curve_radius=200, angle_start=math.pi, angle_end=math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH+200, start_x=-2200, length=2000)
    draw_curved_road(center_x=-300, center_y=GRID_LENGTH, curve_radius=200, angle_start=0, angle_end=math.pi/2, x_shift=100)
    # Place finish line at start of first straight
    finish_line_pos = (0, -GRID_LENGTH-60)
    finish_line_angle = 0
    draw_finish_line(finish_line_pos[0], finish_line_pos[1], finish_line_angle, width=finish_line_width)


def layout2():
    global finish_line_pos, finish_line_angle
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
    # Place finish line at start of first straight
    finish_line_pos = (0, -GRID_LENGTH-2400 + 40)
    finish_line_angle = 0
    draw_finish_line(finish_line_pos[0], finish_line_pos[1], finish_line_angle, width=finish_line_width)


def layout3():
    global finish_line_pos, finish_line_angle
    draw_straight_road(center_x=0, start_y=-GRID_LENGTH-2400, length=6*GRID_LENGTH)
    draw_curved_road(center_x=-300, center_y=GRID_LENGTH-3600, curve_radius=200, angle_start=0, angle_end=-math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH-3800, start_x=-5000, length=4800)
    draw_curved_road(center_x=-5100, center_y=GRID_LENGTH-3600, curve_radius=200, angle_start=-math.pi, angle_end=-math.pi/2, x_shift=100)
    draw_straight_road(center_x=-5200, start_y=-GRID_LENGTH-2400, length=6*GRID_LENGTH)
    draw_curved_road(center_x=-5100, center_y=GRID_LENGTH, curve_radius=200, angle_start=math.pi, angle_end=math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH+200, start_x=-5000, length=4800)
    draw_curved_road(center_x=-300, center_y=GRID_LENGTH, curve_radius=200, angle_start=0, angle_end=math.pi/2, x_shift=100)
    # Place finish line at start of first straight
    finish_line_pos = (0, -GRID_LENGTH-2400 + 40)
    finish_line_angle = 0
    draw_finish_line(finish_line_pos[0], finish_line_pos[1], finish_line_angle, width=finish_line_width)


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


# Adjust the gun size in draw_player_car function
def draw_player_car(x=0, y=0, z=30, car_angle=0, gun_angle=0):
    scale_factor = 15

    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(car_angle - 90, 0, 0, 1)

    # Main body - lighter blue
    glPushMatrix()
    glScalef(2.5 * scale_factor, 1.2 * scale_factor, 0.6 * scale_factor)
    glColor3f(0.4, 0.5, 0.9)
    draw_cube(1.0)
    glPopMatrix()

    # Cabin
    glPushMatrix()
    glTranslatef(0.0, 0.0, 0.65 * scale_factor)
    glScalef(1.2 * scale_factor, 0.9 * scale_factor, 0.55 * scale_factor)
    glColor3f(0.0, 0.85, 0.9)
    draw_cube(1.0)
    glPopMatrix()

    # Gun mount platform (make it bigger)
    glPushMatrix()
    glTranslatef(0.8 * scale_factor, 0.0, 1.1 * scale_factor)  # Moved further forward
    glScalef(0.7 * scale_factor, 0.7 * scale_factor, 0.15 * scale_factor)  # Larger platform
    glColor3f(0.5, 0.2, 0.5)
    draw_cube(1.0)
    glPopMatrix()

    # Gun barrel (bigger and longer)
    glPushMatrix()
    # rotate around car center by gun_angle (so gun swivels on the turret)
    glRotatef(gun_angle, 0, 0, 1)
    # then translate OUT to the gun mount position
    glTranslatef(0.6 * scale_factor, 0.0, 1.2 * scale_factor)  # Adjusted position
    
    # Draw gun base (wider)
    glPushMatrix()
    glTranslatef(-6, 0, -0.2 * scale_factor)
    glScalef(0.4 * scale_factor, 0.5 * scale_factor, 0.4 * scale_factor)
    glColor3f(0.3, 0.3, 0.3)
    draw_cube(1.0)
    glPopMatrix()
    
    # align cylinder axis
    glRotatef(90, 0, 1, 0)
    glColor3f(0.2, 0.2, 0.2)
    draw_cylinder(0.15 * scale_factor, 1.5 * scale_factor)  # Bigger and longer barrel
    glPopMatrix()

    # Wheels
    wheel_positions = [(-1.4 * scale_factor, 1.3 * scale_factor, 0.0),
                       (-1.4 * scale_factor, -1.3 * scale_factor, 0.0),
                       (1.4 * scale_factor, 1.3 * scale_factor, 0.0),
                       (1.4 * scale_factor, -1.3 * scale_factor, 0.0)]
    for wx, wy, wz in wheel_positions:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glRotatef(90, 1, 0, 0)
        glColor3f(0.05, 0.05, 0.05)
        draw_cylinder(0.3 * scale_factor, 0.2 * scale_factor)
        glPopMatrix()

    glPopMatrix()
# === Bullet drawing/updating ===
def draw_bullets():
    for bx, by, bz, angle in bullets:
        glPushMatrix()
        glTranslatef(bx, by, bz)
        glColor3f(1.0, 0.0, 0.0)  # red bullets
        glutSolidSphere(3, 10, 10)
        glPopMatrix()


def update_bullets():
    global bullets, active_collision_effects
    new_bullets = []
    hit_radius = 50  # tune based on car size

    for bx, by, bz, angle in bullets:
        # Move bullet forward in XY plane
        bx += bullet_speed * math.cos(math.radians(angle - 90))
        by += bullet_speed * math.sin(math.radians(angle - 90))
        bz = 30  # fixed height

        # --- Check collision with enemies ---
        hit_enemy = None
        for car in enemy_cars:
            ex, ey, _ = car.position  # ignore z
            dist = math.hypot(bx - ex, by - ey)  # 2D distance
            if dist < hit_radius:
                hit_enemy = car
                break

        if hit_enemy:
            # Apply slow effect for this enemy
            active_collision_effects.add((id(hit_enemy), time.time()))
            hit_enemy.lives -= 1
            print(f"Enemy hit! Lives left: {hit_enemy.lives}")
            continue  # bullet vanishes on hit

        # --- Keep bullet if in bounds ---
        if -70000 < bx < 70000 and -70000 < by < 70000:
            new_bullets.append((bx, by, bz, angle))

    bullets = new_bullets




# === Shooting function ===
def fire_bullet():
    global bullets, collision_flag
    if not collision_flag:
        bx, by, bz = car_pos[0], car_pos[1], 30
        # Combine car_angle and gun_angle for absolute bullet direction
        bullet_angle = (car_angle + gun_angle) % 360
        bullets.append((bx, by, bz, bullet_angle))


# --- Enemy cars ---
class EnemyCar:
    def __init__(self, color, path_points, speed):
        self.color = color
        self.path_points = path_points  # List of (x, y, z)
        self.segment = 0
        self.position = list(path_points[0])
        self.speed = speed
        self.finished = False
        self.collision_response = {}
        self.lives = 5
        

        # Initialize angle toward second waypoint (if exists)
        if len(path_points) > 1:
            dx = path_points[1][0] - path_points[0][0]
            dy = path_points[1][1] - path_points[0][1]
            self.angle = math.degrees(math.atan2(dy, dx))
        else:
            self.angle = 0


# All enemy cars (created after layout selected)
enemy_cars = []
ENEMY_COUNT = 3  # Set to 2 or 3 as needed

enemy_win = False  # Track if enemy finishes before player

def draw_enemy_car(x=0, y=0, z=30, car_angle=0):
    scale_factor = 15
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(car_angle, 0, 0, 1)
    # Body - red enemy color
    glPushMatrix()
    glScalef(2.5 * scale_factor, 1.2 * scale_factor, 0.6 * scale_factor)
    glColor3f(0.9, 0.3, 0.3)  # Enemy: red
    draw_cube(1.0)
    glPopMatrix()
    # Cabin - darker red
    glPushMatrix()
    glTranslatef(0.0, 0.0, 0.65 * scale_factor)
    glScalef(1.2 * scale_factor, 0.9 * scale_factor, 0.55 * scale_factor)
    glColor3f(0.7, 0.1, 0.1)
    draw_cube(1.0)
    glPopMatrix()
    # Wheels
    wheel_positions = [(-1.4 * scale_factor, 1.3 * scale_factor, 0.0),
                      (-1.4 * scale_factor, -1.3 * scale_factor, 0.0),
                      (1.4 * scale_factor, 1.3 * scale_factor, 0.0),
                      (1.4 * scale_factor, -1.3 * scale_factor, 0.0)]
    for wx, wy, wz in wheel_positions:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glRotatef(90, 1, 0, 0)
        glColor3f(0.05, 0.05, 0.05)
        draw_cylinder(0.3 * scale_factor, 0.2 * scale_factor)
        glPopMatrix()
    glPopMatrix()

def get_enemy_paths_for_layout(layout_num):
    # Create displacements for each enemy car
    offsets = np.linspace(-100, 100, ENEMY_COUNT+1)
    base_paths = []

    # Define waypoints as before for each layout
    if layout_num == 1:
        base_waypoints = [
            (0, -600, 10), (30, 800, 10), (-2300, 800, 10),
            (-2300, -3600, 10), (2000, -3600, 10),
            (2000, -800, 10), (0, -800, 10), (0, finish_line_pos[1] + 40, 10)
        ]
    elif layout_num == 2:
        base_waypoints = [
            (0, -600, 10), (30, 800, 10), (-6200, 800, 10),
            (-6200, -4800, 10), (-3600, -4800, 10),
            (-3600, -3200, 10), (0, -3200, 10), (0, finish_line_pos[1] + 40, 10)
        ]
    elif layout_num == 3:
        base_waypoints = [
            (0, -600, 10), (0, 800, 10), (-5200, 800, 10),
            (-5200, -3200, 10), (0, -3200, 10), (0, finish_line_pos[1] + 40, 10)
        ]
    else:
        return []

    paths = []
    for i, offset in enumerate(offsets):
        if i ==2:
            continue
        
        # Displace in X for vertical segments, in Y for horizontal segments
        enemy_path = []
        for x, y, z in base_waypoints:
            # You can tune here based on segment orientation:
            # For vertical segments
            if abs(x - base_waypoints[0][0]) < 1000:
                enemy_path.append((x + offset, y, z))
            # For horizontal segments, displace Y
            elif abs(y - base_waypoints[0][1]) < 1000:
                enemy_path.append((x, y + offset, z))
            else:
                # For curves or others, displace both
                enemy_path.append((x + offset, y + offset, z))
        paths.append(enemy_path)
    return paths

def enemy_crossed_finish_area(car):
    global finish_line_pos, finish_line_width
    # Define a rectangular area around the finish line (adjust dimensions as needed)
    fx, fy = finish_line_pos
    half_width = finish_line_width / 2
    
    # Define length tolerance before/after finish line y coordinate
    length_tolerance = 50  # Adjust for track scale
    
    # Get enemy car position (ignore front offset and angle)
    cx, cy = car.position[0], car.position[1]

    within_width = (cx >= fx - half_width) and (cx <= fx + half_width)
    within_length = (cy >= fy - length_tolerance) and (cy <= fy + length_tolerance)

    if within_width and within_length:
        return True
    return False


# At initialization, set car.angle = math.atan2(start_dy, start_dx)

COLLISION_EFFECT_TIME = 5  # seconds

def update_enemy_cars():
    global enemy_win, finish_crossed, active_collision_effects
    for car in enemy_cars:
        if car.finished:
            car.position = list(car.path_points[-1])
            if len(car.path_points) > 1:
                dx = car.path_points[-1][0] - car.path_points[-2][0]
                dy = car.path_points[-1][1] - car.path_points[-2][1]
                car.angle = math.degrees(math.atan2(dy, dx))
            continue

        if enemy_crossed_finish_area(car):
            car.finished = True
            if not finish_crossed and not enemy_win:
                enemy_win = True
            car.position = list(car.path_points[-1])
            continue

        if car.segment >= len(car.path_points) - 1:
            continue

        curr = car.position
        goal = car.path_points[car.segment + 1]
        dx, dy = goal[0] - curr[0], goal[1] - curr[1]
        dist = math.hypot(dx, dy)
        if dist == 0:
            continue

        # Smooth angle update
        target_angle = math.atan2(dy, dx)
        current_angle_rad = math.radians(car.angle)
        angle_diff = ((target_angle - current_angle_rad + math.pi) % (2 * math.pi)) - math.pi
        turn_rate_rad = math.radians(4.0)
        if abs(angle_diff) < turn_rate_rad:
            current_angle_rad = target_angle
        else:
            current_angle_rad += turn_rate_rad if angle_diff > 0 else -turn_rate_rad
        car.angle = math.degrees(current_angle_rad)

        # Compute projection to limit side drift
        to_goal = np.array([dx, dy]) / dist
        car_heading = np.array([math.cos(current_angle_rad), math.sin(current_angle_rad)])
        proj_length = np.dot(car_heading, to_goal)

        # --- Apply collision speed multiplier (per enemy) ---
        multiplier = 1.0
        key = id(car)
        if key in active_collision_effects:
            m, start_time = active_collision_effects[key]
            if time.time() - start_time < COLLISION_EFFECT_TIME:
                multiplier = m
            else:
                # Restore to normal speed after 5 seconds
                del active_collision_effects[key]

        # Movement update
        if proj_length < 0:
            move_x, move_y = 0.0, 0.0  # Prevent backward movement
        else:
            effective_speed = car.speed * proj_length * multiplier
            move_x = effective_speed * car_heading[0]
            move_y = effective_speed * car_heading[1]

        # Update position
        car.position[0] += move_x
        car.position[1] += move_y

        # Waypoint arrival update
        new_dx, new_dy = goal[0] - car.position[0], goal[1] - car.position[1]
        new_dist = math.hypot(new_dx, new_dy)
        if new_dist < car.speed:
            car.position = list(goal)
            car.segment += 1



colliding_enemies = set()
def check_collision(player_pos, player_angle_deg, enemy_pos, car_length, car_width, tolerance=0):
    half_len = car_length / 2 + tolerance
    half_wid = car_width / 2 + tolerance

    px, py = player_pos
    ex, ey = enemy_pos

    # Convert angle to radians
    theta = math.radians(player_angle_deg)

    # Relative position vector from player to enemy
    dx = ex - px
    dy = ey - py

    # Rotate relative vector by -theta to align with player car axes
    rotated_x = dx * math.cos(-theta) - dy * math.sin(-theta)
    rotated_y = dx * math.sin(-theta) + dy * math.cos(-theta)

    # Check overlap in rotated frame
    if abs(rotated_x) <= 2 * half_len and abs(rotated_y) <= 2 * half_wid:
        return True
    return False

def check_enemy_player_collision():
    global enemy_player_collision_flag, enemy_player_collision_start_time, colliding_enemies, lives, shield_active
    colliding_enemies.clear()
    player_pos = car_pos[:2]
    player_angle = car_angle
    collision = False
    for enemy in enemy_cars:
        enemy_pos = enemy.position[:2]
        if check_collision(player_pos, player_angle, enemy_pos, CAR_LENGTH, CAR_WIDTH, tolerance=5):
            collision = True
            colliding_enemies.add(enemy)
    if collision and not enemy_player_collision_flag:
        enemy_player_collision_flag = True
        print('Collision detected!')
        enemy_player_collision_start_time = time.time()
        if not shield_active:
            lives -= 1
        return True
    return False



# Add global dicts to track displacement accumulated during collision for player and each enemy car
collision_displacement_accum = {
    "player": 0.0,
    "enemies": {id(enemy): 0.0 for enemy in enemy_cars}
}
MAX_COLLISION_DISPLACEMENT = 10.0  # max units total move during collision effect
DISPLACEMENT_PER_FRAME = 0.3       # units moved per update frame

COLLISION_SPEED_BOOST = 1.5   # multiplier for front car
COLLISION_SPEED_PENALTY = -1.0 # multiplier for rear car
COLLISION_EFFECT_TIME = 2.0   # seconds
active_collision_effects = set()
# Track speed effects
def apply_collision_response():
    global enemy_player_collision_flag, enemy_player_collision_start_time, colliding_enemies, car_pos
    if not enemy_player_collision_flag or not colliding_enemies:
        return
    now = time.time()
    if now - enemy_player_collision_start_time > COLLISION_EFFECT_TIME:
        enemy_player_collision_flag = False
        colliding_enemies.clear()
        active_collision_effects.clear()
        return
    # Nudge cars apart so next frame won’t cause repeat collision
    player_pos = np.array(car_pos[:2])
    player_angle_rad = math.radians(car_angle)
    player_forward = np.array([math.cos(player_angle_rad), math.sin(player_angle_rad)])
    nudge_amt = max(CAR_LENGTH, CAR_WIDTH) + 10  # Large enough to prevent overlap
    for enemy in colliding_enemies:
        enemy_pos = np.array(enemy.position[:2])
        rel_vec = player_pos - enemy_pos
        if np.linalg.norm(rel_vec) == 0:
            rel_vec = np.array([1.0, 0.0])  # Arbitrary direction if exactly overlapped
        rel_vec = rel_vec / np.linalg.norm(rel_vec)
        sep_vec = rel_vec * nudge_amt
        # Update positions
        car_pos[0] += sep_vec[0]
        car_pos[1] += sep_vec[1]
        enemy.position[0] -= sep_vec[0]
        enemy.position[1] -= sep_vec[1]


def is_car_colliding():
    base_length = 2.5
    base_width = 1.2
    multiplier = 1.0  

    car_length = base_length * multiplier
    car_width = base_width * multiplier
    cx, cy, cz = car_pos
    angle_rad = math.radians(car_angle - 90)
    nx, ny = 10, 8  # Lower sampling density for speed

    for i in range(nx):
        for j in range(ny):
            lx = -car_length + (2 * car_length) * (i / (nx - 1))
            ly = -car_width + (2 * car_width) * (j / (ny - 1))
            world_x = cx + lx * math.cos(angle_rad) - ly * math.sin(angle_rad)
            world_y = cy + lx * math.sin(angle_rad) + ly * math.cos(angle_rad)
            grid_x = int(round(world_x / 8) * 8)
            grid_y = int(round(world_y / 8) * 8)

            for dx in [-8, 0, 8]:
                for dy in [-8, 0, 8]:
                    pt = (grid_x + dx, grid_y + dy)
                    if pt in border_positions:
                        explosions.append({'pos': pt, 'start_time': time.time()})
                        return True
    return False

def has_crossed_finish_line():
    car_front_dist = 2.5 * 15
    angle_rad = math.radians(car_angle - 90)
    front_x = car_pos[0] - car_front_dist * math.cos(angle_rad)
    front_y = car_pos[1] - car_front_dist * math.sin(angle_rad)

    fx, fy = finish_line_pos
    half_width = finish_line_width / 2

    within_width = (front_x >= fx - half_width) and (front_x <= fx + half_width)
    crossed_zone = (front_y < fy + 15) and (front_y > fy - 15)

    finish_line_direction = 0  # Adjust to your track!
    direction_error = (car_angle - finish_line_direction) % 360
    if direction_error > 180:
        direction_error -= 360
    facing_forward = abs(direction_error) < 90

    # New: Separate logic for results
    if within_width and crossed_zone:
        if facing_forward:
            return "correct"  # Forward crossing
        else:
            return "cheat"    # Cheating: wrong direction
    return None   # Not crossed

def update_car():
    global car_pos, car_angle, current_speed, prev_car_pos, finish_crossed, enemy_win
    global collision_flag, collision_start_time, active_collision_effects
    global boost_active, boost_start_time
    global cheat_message
    global paused , lives 
    global shield_active, shield_start_time  # Add shield variables
    if lives <= 0:
        
        return
    if paused:
        return  # Game is paused
    if shield_active and (time.time() - shield_start_time) >= 5:
        shield_active = False
    if enemy_win or finish_crossed:
        current_speed = 0
        glutPostRedisplay()
        return
    update_enemy_cars()
    if enemy_win:
        current_speed = 0
        glutPostRedisplay()
        return
    if finish_crossed:
        current_speed = 0
        glutPostRedisplay()
        return
    now = time.time()

    if boost_active and now - boost_start_time > 3:
        boost_active = False
        current_speed = normal_speed

    if collision_flag:
        if now - collision_start_time < 3:
            angle_rad = math.radians(car_angle - 90)
            old_pos = car_pos[:]
            car_pos[0] += slow_speed * math.cos(angle_rad)
            car_pos[1] += slow_speed * math.sin(angle_rad)
            if is_car_colliding():
                print("Collision while reversing → stopping immediately")
                car_pos = old_pos[:]
                collision_flag = False
                current_speed = 0
                # Decrease life on collision
                if not shield_active:
                    lives = max(0, lives - 1)

        else:
            collision_flag = False
            current_speed = normal_speed
        glutPostRedisplay()
        return
    check_enemy_player_collision()
    apply_collision_response()
    check_health_kit_collision()
    check_bomb_collision()
    check_shield_kit_collision()
    update_bullets()

    multiplier = 1.0
    if "player" in active_collision_effects:
        m, start_time = active_collision_effects["player"]
        if time.time() - start_time < COLLISION_EFFECT_TIME:
            multiplier = m
        else:
            del active_collision_effects["player"]

    effective_speed = current_speed * multiplier

        # --- Normal forward motion (with multiplier) ---
    angle_rad = math.radians(car_angle - 90)
    new_x = car_pos[0] - effective_speed * math.cos(angle_rad)
    new_y = car_pos[1] - effective_speed * math.sin(angle_rad)

    old_pos = car_pos[:]
    car_pos[0], car_pos[1] = new_x, new_y


    # Check collision going forward
    if is_car_colliding():
            print("Collision detected! Life lost.")
            collision_flag = True
            collision_start_time = now
            car_pos = old_pos[:]
            current_speed = 0
            # Decrease life on collision
            if not shield_active:
                lives = max(0, lives - 1)

    result = has_crossed_finish_line()
    if not finish_crossed:
        if result == "correct":
            finish_crossed = True
            
        elif result == "cheat":
            cheat_message = "You cannot finish the race backwards! Game restarting..."
            print(cheat_message)
            reset_game()
            

    prev_car_pos = car_pos[:]
    glutPostRedisplay()



def reset_game():
    global car_pos, car_angle, finish_crossed, current_speed, collision_flag, lives
    car_pos = [0, -600, 10]
    car_angle = 0.0
    finish_crossed = False
    current_speed = normal_speed
    collision_flag = False
    lives = 10
    global enemy_cars, enemy_win
    # Reset enemy cars to initial segment/position, and reset angles properly
    for ecar in enemy_cars:
        ecar.position = list(ecar.path_points[0])
        ecar.segment = 0
        if len(ecar.path_points) > 1:
            dx = ecar.path_points[1][0] - ecar.path_points[0][0]
            dy = ecar.path_points[1][1] - ecar.path_points[0][1]
            ecar.angle = math.degrees(math.atan2(dy, dx))
        else:
            ecar.angle = 0
        ecar.finished = False
    enemy_win = False
    spawn_shield_kits()
    glutPostRedisplay()

def keyboard(key, x, y):
    global current_speed, car_angle, boost_active, boost_start_time, paused
    global shield_active, shield_start_time  # Add shield variables
    key_lower = key.lower()
    
    if key_lower == b'p':  # Pause/resume
        paused = not paused
    elif key_lower == b'r':  # Restart
        reset_game()
    elif key_lower == b'w' and not collision_flag:  # temporary boost
        boost_active = True
        boost_start_time = time.time()
        current_speed = boost_speed
    elif key_lower == b's' and not collision_flag:  # slow down (not reverse)
        current_speed = slow_speed
    elif key_lower == b'a':  # turn left
        car_angle += turn_speed
    elif key_lower == b'd':  # turn right
        car_angle -= turn_speed
  



# === Controls ===
def special_keyboard(key, x, y):
    global current_speed, car_angle, boost_active, boost_start_time, gun_angle

    if key == GLUT_KEY_UP and not collision_flag:
        fire_bullet()  # UP arrow fires bullet
    
    elif key == GLUT_KEY_LEFT:
        gun_angle += gun_turn_speed  # rotate gun left
       
    elif key == GLUT_KEY_RIGHT:
        gun_angle -= gun_turn_speed  # rotate gun right


def mouse_click(button, state, x, y):
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        fire_bullet()

def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 1.0, 2000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    x, y, z = car_pos
    # Correct offset calculations!
    offset_distance = math.sqrt(camera_offset[0] ** 2 + camera_offset[1] ** 2)
    offset_angle = math.atan2(camera_offset[1], camera_offset[0])
    total_angle = math.radians(car_angle) + offset_angle
    camera_x = x + offset_distance * math.cos(total_angle)
    camera_y = y + offset_distance * math.sin(total_angle)
    camera_z = z + camera_offset[2] 
    gluLookAt(camera_x, camera_y, camera_z, x, y, z, 0, 0, 1)


def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    
    # --- Main viewport (full window) ---
    glViewport(0, 0, 1000, 800)
    setupCamera()
    draw_road()
    draw_bullets()
    if finish_line_pos:
        draw_finish_line(finish_line_pos[0], finish_line_pos[1], finish_line_angle)
    if cheat_message:
        draw_text(300, 360, cheat_message)
    if enemy_win:
        draw_text(350, 450, "Game Over! Enemy finished first.")


    draw_player_car(car_pos[0], car_pos[1], car_pos[2], car_angle, gun_angle)
    for ecar in enemy_cars:
        draw_enemy_car(ecar.position[0], ecar.position[1], ecar.position[2], ecar.angle)
    if finish_crossed:
        draw_text(400, 400, "Congratulations! You finished the race!")
    if lives <= 0:
        draw_text(450, 400, "Game Over! No lives remaining.")

    global kits_spawned

    if not kits_spawned:
       spawn_health_kits()
       spawn_bombs()
       kits_spawned = True

    
    # --- Draw health kits (main view) ---
    for (hx, hy) in health_kits:
        draw_health_kit(hx, hy, 20)
    for (bx, by) in bombs:
        draw_bomb(bx, by, 20)
    for (sx, sy) in shield_kits:
        draw_shield_kit(sx, sy, 20)
    draw_all_explosions()
    
    draw_dashboard()     
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
    if finish_line_pos:
        draw_finish_line(finish_line_pos[0], finish_line_pos[1], finish_line_angle)

    draw_player_car(car_pos[0], car_pos[1], car_pos[2], car_angle, gun_angle)
    # Draw all enemy cars (main view)
    for ecar in enemy_cars:
        draw_enemy_car(ecar.position[0], ecar.position[1], ecar.position[2], ecar.angle)


    # Draw a red dot at car position to make it more visible on minimap
        # Draw a light skyblue dot for the player car
    glColor3f(0.53, 0.81, 0.98)  # Light skyblue
    dot_size = 50
    glBegin(GL_QUADS)
    glVertex2f(car_pos[0] - dot_size, car_pos[1] - dot_size)
    glVertex2f(car_pos[0] + dot_size, car_pos[1] - dot_size)
    glVertex2f(car_pos[0] + dot_size, car_pos[1] + dot_size)
    glVertex2f(car_pos[0] - dot_size, car_pos[1] + dot_size)
    glEnd()

    # Draw red dots for enemy cars
    glColor3f(1.0, 0.0, 0.0)  # Red
    for ecar in enemy_cars:
        ex, ey, _ = ecar.position
        glBegin(GL_QUADS)
        glVertex2f(ex - dot_size, ey - dot_size)
        glVertex2f(ex + dot_size, ey - dot_size)
        glVertex2f(ex + dot_size, ey + dot_size)
        glVertex2f(ex - dot_size, ey + dot_size)
        glEnd()


    # Restore matrices
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    # Restore main viewport
    glViewport(0, 0, 1000, 800)

    glutSwapBuffers()

def draw_dashboard():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 700)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # === Panel geometry ===
    x0, y0 = 10, 10
    x1, y1 = 480, 230   # wider to fit text & bars comfortably
    
    # Background
    glColor4f(0.1, 0.1, 0.1, 0.8)
    glBegin(GL_QUADS)
    glVertex2f(x0, y0)
    glVertex2f(x1, y0)
    glVertex2f(x1, y1)
    glVertex2f(x0, y1)
    glEnd()
    
    # Border (manual)
    glColor3f(0.5, 0.5, 0.5)
    glLineWidth(2.0)
    glBegin(GL_LINES)
    glVertex2f(x0, y0); glVertex2f(x1, y0)
    glVertex2f(x1, y0); glVertex2f(x1, y1)
    glVertex2f(x1, y1); glVertex2f(x0, y1)
    glVertex2f(x0, y1); glVertex2f(x0, y0)
    glEnd()
    
    # === Text (top area of panel) ===
    glColor3f(0.0, 1.0, 1.0)
    glRasterPos2f(x0 + 10, y1 - 25)
    for ch in f"SPEED: {int(current_speed)} km/h":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    if boost_active:
        glColor3f(1.0, 0.5, 0.0)
        boost_text = "BOOST: ACTIVE!"
    else:
        glColor3f(0.7, 0.7, 0.7)
        boost_text = "BOOST: READY"
    glRasterPos2f(x0 + 10, y1 - 50)
    for ch in boost_text:
        glutBitmapCharacter(GLUT_BITMAP_9_BY_15, ord(ch))
    
    # Player lives text
    if lives < 5:
        glColor3f(1.0, 0.0, 0.0)
    else:
        glColor3f(0.0, 1.0, 0.0)
    glRasterPos2f(x0 + 10, y1 - 75)
    for ch in f"LIVES: {lives}/10":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    # === Life bars (moved to bottom inside panel) ===
    life_bar_start_x = x0 + 200
    player_bar_y = y1 - 75            # player bars near panel bottom
    life_bar_length = 18
    life_bar_thickness = 5
    life_bar_spacing = 3

    # Player life bars (10 slots)
    for i in range(10):
        if i < lives:
            # green when healthy, red when low
            if lives >= 5:
                glColor3f(0.0, 1.0, 0.0)
            else:
                glColor3f(1.0, 0.0, 0.0)
        else:
            glColor3f(0.3, 0.3, 0.3)
        
        x_pos = life_bar_start_x + (i * (life_bar_length + life_bar_spacing))
        y_pos = player_bar_y
        glBegin(GL_QUADS)
        glVertex2f(x_pos, y_pos)
        glVertex2f(x_pos + life_bar_length, y_pos)
        glVertex2f(x_pos + life_bar_length, y_pos - life_bar_thickness)
        glVertex2f(x_pos, y_pos - life_bar_thickness)
        glEnd()

    # Status & shield & controls
    if finish_crossed:
        glColor3f(0.0, 1.0, 0.0); status_text = "STATUS: FINISHED!"
    elif enemy_win:
        glColor3f(1.0, 0.0, 0.0); status_text = "STATUS: ENEMY WON!"
    elif paused:
        glColor3f(1.0, 1.0, 0.0); status_text = "STATUS: PAUSED"
    else:
        glColor3f(0.0, 1.0, 1.0); status_text = "STATUS: RACING"
    glRasterPos2f(x0 + 10, y1 - 100)
    for ch in status_text:
        glutBitmapCharacter(GLUT_BITMAP_9_BY_15, ord(ch))

    if shield_active:
        glColor3f(0.0, 0.5, 1.0); shield_text = "SHIELD: ACTIVE!"
    else:
        glColor3f(0.7, 0.7, 0.7); shield_text = "SHIELD: OFF"
    glRasterPos2f(x0 + 10, y1 - 125)
    for ch in shield_text:
        glutBitmapCharacter(GLUT_BITMAP_9_BY_15, ord(ch))

    glColor3f(0.7, 0.7, 0.7)
    glRasterPos2f(x0 + 10, y1 - 150)
    controls_text = "W/S: Speed  A/D: Turn  R: Reset  P: Pause"
    for ch in controls_text:
        glutBitmapCharacter(GLUT_BITMAP_8_BY_13, ord(ch))
    
    life_bar_start_x = x0 + 200
    player_bar_y = y0 + 20            # player bars near panel bottom
    life_bar_length = 18
    life_bar_thickness = 5
    life_bar_spacing = 3
    
    # === Enemy lives rows (below the player text, just above player bars) ===
    enemy_max_lives = 4
    enemy_row_start_y = player_bar_y + 16  # slightly above player bars

    for idx, car in enumerate(enemy_cars):
        # label (E1, E2, ...)
        label = f"E{idx+1}:"
        glColor3f(1.0, 1.0, 1.0)
        glRasterPos2f(x0 + 10, enemy_row_start_y + idx * (life_bar_thickness + 6) - 2)
        for ch in label:
            glutBitmapCharacter(GLUT_BITMAP_9_BY_15, ord(ch))
        
        # clamp displayed lives so row length = enemy_max_lives
        displayed_lives = max(0, min(car.lives, enemy_max_lives))
        
        for i in range(enemy_max_lives):
            if i < displayed_lives:
                glColor3f(1.0, 0.0, 0.0)   # enemy bars red
            else:
                glColor3f(0.3, 0.3, 0.3)
            
            x_pos = life_bar_start_x + (i * (life_bar_length + life_bar_spacing))
            y_pos = enemy_row_start_y + idx * (life_bar_thickness + 6)
            glBegin(GL_QUADS)
            glVertex2f(x_pos, y_pos)
            glVertex2f(x_pos + life_bar_length, y_pos)
            glVertex2f(x_pos + life_bar_length, y_pos - life_bar_thickness)
            glVertex2f(x_pos, y_pos - life_bar_thickness)
            glEnd()

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"3dCarRush")
    glutSpecialFunc(special_keyboard)
    glutKeyboardFunc(keyboard)
    glClearColor(0.0, 0.4, 0.0, 1.0)
    glutIdleFunc(update_car)
    glutDisplayFunc(showScreen)
    glutMouseFunc(mouse_click)
    global selected_layout
    layouts = [layout1, layout2, layout3]
    selected_layout = random.choice(layouts)

    layout_index = layouts.index(selected_layout) + 1
  
    selected_layout()
    paths = get_enemy_paths_for_layout(layout_index)
    enemy_speeds = [random.uniform(12, 18) for i in range(ENEMY_COUNT)]  # Each enemy has different speed
    global enemy_cars
    enemy_cars = [EnemyCar((0.9, 0.3, 0.3), path, speed) for path, speed in zip(paths, enemy_speeds)]
    spawn_health_kits()
    spawn_shield_kits()
    glutMainLoop()

if __name__ == "__main__":
    main()