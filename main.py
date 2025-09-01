import sys
import math
import random
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import time

# Camera and constants
camera_offset = [0, -150, 75]  # Camera offset relative to car
car_pos = [0, -600, 10]  # Start car at y = -GRID_LENGTH, slightly above ground
car_angle = 0.0   # Angle in degrees
fovY = 60  # Reduced for better focus
GRID_LENGTH = 600
selected_layout = None
lives = 10
road_positions = set()
border_positions = set()


# --- Movement state ---
normal_speed = 15.0
boost_speed = 20.0
slow_speed = 10.0

current_speed = normal_speed
turn_speed = 3        # degrees per press

collision_flag = False
collision_start_time = 0

boost_active = False
boost_start_time = 0

# At the top
finish_line_pos = None
finish_line_angle = 0
finish_crossed = False
prev_car_pos = car_pos[:]
finish_line_width = 450  # or match the road width at the finish line





# Global constants for borders
BORDER_HEIGHT = 30.0
BORDER_THICKNESS = 12.0

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

def draw_finish_line(x, y, angle=0, width=450, depth=20, banner_height=40, banner_scale_x=1.0, banner_x_angle=90):
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
    finish_line_pos = (0, -GRID_LENGTH-20)
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


def draw_player_car(x=0, y=0, z=30, car_angle=0, gun_angle=0):
    scale_factor = 15  # Increase size by 1.5x

    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(car_angle-90, 0, 0, 1)

    # Main body - lighter blue
    glPushMatrix()
    glScalef(2.5 * scale_factor, 1.2 * scale_factor, 0.6 * scale_factor)
    glColor3f(0.4, 0.5, 0.9)  # Light sky blue
    draw_cube(1.0)
    glPopMatrix()

    # Cabin - light grey
    glPushMatrix()
    glTranslatef(0.0, 0.0, 0.65 * scale_factor)
    glScalef(1.2 * scale_factor, 0.9 * scale_factor, 0.55 * scale_factor)
    glColor3f(0.0, 0.85, 0.9)  # Light grey-blue
    draw_cube(1.0)
    glPopMatrix()

    # Gun mount platform - pale yellow
    glPushMatrix()
    glTranslatef(0.6 * scale_factor, 0.0, 1.1 * scale_factor)
    glScalef(0.5 * scale_factor, 0.5 * scale_factor, 0.1 * scale_factor)
    glColor3f(0.5, 0.2, 0.5)  # Pale yellow
    draw_cube(1.0)
    glPopMatrix()

    # Gun barrel - light silver
    glPushMatrix()
    glTranslatef(0.6 * scale_factor, 0.0, 1.2 * scale_factor)
    glRotatef(gun_angle, 0, 0, 1)
    glRotatef(90, 0, 1, 0)
    glColor3f(0.2, 0.2, 0.2)  # Light silver
    draw_cylinder(0.1 * scale_factor, 1.0 * scale_factor)
    glPopMatrix()

    # Wheels - black cylinders
    wheel_positions = [(-1.4 * scale_factor, 1.3 * scale_factor, 0.0),
                       (-1.4 * scale_factor, -1.3 * scale_factor, 0.0),
                       (1.4 * scale_factor, 1.3 * scale_factor, 0.0),
                       (1.4 * scale_factor, -1.3 * scale_factor, 0.0)]
    for wx, wy, wz in wheel_positions:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glRotatef(90, 1, 0, 0)
        glColor3f(0.05, 0.05, 0.05)  # Near black tires
        draw_cylinder(0.3 * scale_factor, 0.2 * scale_factor)
        glPopMatrix()

    glPopMatrix()


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

    return within_width and crossed_zone



def update_car():
    global car_pos, car_angle, current_speed, prev_car_pos, finish_crossed
    global collision_flag, collision_start_time
    global boost_active, boost_start_time
    if finish_crossed:
        current_speed = 0
        glutPostRedisplay()
        return
    now = time.time()

    # --- Handle boost timeout ---
    if boost_active and now - boost_start_time > 3:
        boost_active = False
        current_speed = normal_speed

    # --- Collision handling (backward movement) ---
    if collision_flag:
        if now - collision_start_time < 3:
            angle_rad = math.radians(car_angle - 90)
            old_pos = car_pos[:]
            car_pos[0] += slow_speed * math.cos(angle_rad)
            car_pos[1] += slow_speed * math.sin(angle_rad)

            # Check collision while moving backward
            if is_car_colliding():
                print("Collision while reversing → stopping immediately")
                car_pos = old_pos[:]  # stay at safe position
                collision_flag = False
                current_speed = 0
        else:
            # Done with backward phase
            collision_flag = False
            current_speed = normal_speed

        glutPostRedisplay()
        return

    # --- Normal forward motion ---
    angle_rad = math.radians(car_angle - 90)
    new_x = car_pos[0] - current_speed * math.cos(angle_rad)
    new_y = car_pos[1] - current_speed * math.sin(angle_rad)

    old_pos = car_pos[:]
    car_pos[0], car_pos[1] = new_x, new_y

    # Check collision going forward
    if is_car_colliding():
        print("Collision detected!")
        collision_flag = True
        collision_start_time = now
        car_pos = old_pos[:]  # undo step
        current_speed = 0     # freeze until handled
    if not finish_crossed and has_crossed_finish_line():
        finish_crossed = True
        print("Win!")
    prev_car_pos = car_pos[:]
    
    glutPostRedisplay()



def keyboard(key, x, y):
    global current_speed, car_angle, boost_active, boost_start_time

    

    if key == b'w' and not collision_flag:  # temporary boost
        boost_active = True
        boost_start_time = time.time()
        current_speed = boost_speed
    elif key == b's' and not collision_flag:  # slow down (not reverse)
        current_speed = slow_speed
    elif key == b'a':  # turn left
        car_angle += turn_speed
    elif key == b'd':  # turn right
        car_angle -= turn_speed




def special_keyboard(key, x, y):
    global current_speed, car_angle, boost_active, boost_start_time

   

    if key == GLUT_KEY_UP and not collision_flag:
        boost_active = True
        boost_start_time = time.time()
        current_speed = boost_speed
    elif key == GLUT_KEY_DOWN and not collision_flag:
        current_speed = slow_speed
    elif key == GLUT_KEY_LEFT:
        car_angle += turn_speed
    elif key == GLUT_KEY_RIGHT:
        car_angle -= turn_speed



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
    if finish_line_pos:
        draw_finish_line(finish_line_pos[0], finish_line_pos[1], finish_line_angle)

    draw_player_car(car_pos[0], car_pos[1], car_pos[2], car_angle, 0)
    if finish_crossed:
        draw_text(400, 400, "Congratulations! You finished the race!")

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
    if finish_line_pos:
        draw_finish_line(finish_line_pos[0], finish_line_pos[1], finish_line_angle)

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


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Car Game: Extended Road with Curve")
    glutSpecialFunc(special_keyboard)
    glutKeyboardFunc(keyboard)
    glClearColor(0.0, 0.4, 0.0, 1.0)
    glutIdleFunc(update_car)
    glutDisplayFunc(showScreen)
    
    global selected_layout
    layouts = [layout1, layout2, layout3]
    selected_layout = random.choice(layouts)
    print(selected_layout.__name__)
    glutMainLoop()

if __name__ == "__main__":
    main()