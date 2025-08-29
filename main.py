from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18
import math
import random

# Camera and constants
camera_pos = [0, 500, 500]
fovY = 120
GRID_LENGTH = 600

selected_layout = None  # Will be assigned to layout1, layout2, or layout3


# Global constants for borders
BORDER_HEIGHT = 30.0      # Vertical height of border walls
BORDER_THICKNESS = 12.0   # Thickness of border walls

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
    glColor3f(0.6, 0.6, 0.2)  # Yellowish border wall
    # Left side border
    glBegin(GL_QUADS)
    glVertex3f(x_left, y_start, height)
    glVertex3f(x_left + thickness, y_start, 0.1)
    glVertex3f(x_left + thickness, y_end, 0.1)
    glVertex3f(x_left, y_end, height)
    glEnd()
    # Right side border
    glBegin(GL_QUADS)
    glVertex3f(x_right - thickness, y_start, height)
    glVertex3f(x_right, y_start, 0.1)
    glVertex3f(x_right, y_end, 0.1)
    glVertex3f(x_right - thickness, y_end, height)
    glEnd()

def draw_horizontal_borders(y_left, y_right, x_start, x_end, height=BORDER_HEIGHT, thickness=BORDER_THICKNESS):
    glColor3f(0.6, 0.6, 0.2)
    # Left side border (at y_left)
    glBegin(GL_QUADS)
    glVertex3f(x_start, y_left, 0.1)
    glVertex3f(x_end, y_left, 0.1)
    glVertex3f(x_end, y_left - thickness, height)
    glVertex3f(x_start, y_left - thickness, height)
    glEnd()
    # Right side border (at y_right)
    glBegin(GL_QUADS)
    glVertex3f(x_start, y_right, 0.1)
    glVertex3f(x_end, y_right, 0.1)
    glVertex3f(x_end, y_right + thickness, height)
    glVertex3f(x_start, y_right + thickness, height)
    glEnd()

def draw_curved_border(center_x, center_y, radius, half_width, start_angle, end_angle, height=BORDER_HEIGHT, thickness=BORDER_THICKNESS):
    segments = 32
    glColor3f(0.6, 0.6, 0.2)
    # Borders at inner and outer radius edges
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

    # Road surface
    glColor3f(0.1, 0.1, 0.1)
    glBegin(GL_QUADS)
    glVertex3f(center_x - half_width, start_y, 0.1)
    glVertex3f(center_x + half_width, start_y, 0.1)
    glVertex3f(center_x + half_width, end_y, 0.1)
    glVertex3f(center_x - half_width, end_y, 0.1)
    glEnd()

    # Borders
    draw_vertical_borders(center_x - half_width, center_x + half_width, start_y, end_y)

    # Dashed lane lines (4 lanes)
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

    # Road surface
    glColor3f(0.1, 0.1, 0.1)
    glBegin(GL_QUADS)
    glVertex3f(start_x, center_y - half_width, 0.1)
    glVertex3f(end_x, center_y - half_width, 0.1)
    glVertex3f(end_x, center_y + half_width, 0.1)
    glVertex3f(start_x, center_y + half_width, 0.1)
    glEnd()

    # Borders
    draw_horizontal_borders(center_y - half_width, center_y + half_width, start_x, end_x)

    # Dashed lane lines (4 lanes)
    glColor3f(1, 1, 1)
    for lane_y in [center_y - 100, center_y, center_y + 100]:
        for x in range(int(start_x) + 20, int(end_x), 80):
            glBegin(GL_QUADS)
            glVertex3f(x, lane_y - 5, 1)
            glVertex3f(x + 40, lane_y - 5, 1)
            glVertex3f(x + 40, lane_y + 5, 1)
            glVertex3f(x, lane_y + 5, 1)
            glEnd()

def draw_curved_road(center_x, center_y, curve_radius, road_width=400, angle_start=0, angle_end=math.pi/2, x_shift=0):
    half_width = road_width // 2
    segments = 32

    # Road surface
    glColor3f(0.1, 0.1, 0.1)
    for i in range(segments):
        angle1 = angle_start + i * (angle_end - angle_start) / segments
        angle2 = angle_start + (i+1) * (angle_end - angle_start) / segments
        
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

    # Borders
    draw_curved_border(center_x + x_shift, center_y, curve_radius, half_width, angle_start, angle_end)

    # Dashed lane lines
    glColor3f(1, 1, 1)
    lane_offsets = [-100, 0, 100]
    for lane_offset in lane_offsets:
        lane_r = curve_radius + lane_offset
        lane_segments = 16
        for i in range(0, lane_segments, 2):
            ang1 = angle_start + i * (angle_end - angle_start) / lane_segments
            ang2 = angle_start + (i+1) * (angle_end - angle_start) / lane_segments

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


def layout1():
    #layout 1
    draw_straight_road(center_x=0, start_y=-GRID_LENGTH, length=2*GRID_LENGTH)
    draw_curved_road(center_x=100, center_y=GRID_LENGTH-1200, curve_radius=200,
                     angle_start=math.pi, angle_end=math.pi+math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH-1400, start_x=200, length=1600)
    draw_curved_road(center_x=1800, center_y=-GRID_LENGTH-400, curve_radius=200,
                     angle_start=0, angle_end=math.pi/2)
    draw_straight_road(center_x=2000, start_y=-GRID_LENGTH-1600, length=2*GRID_LENGTH)
    draw_straight_road(center_x=2000, start_y=-GRID_LENGTH-2800, length=2*GRID_LENGTH)
    draw_curved_road(center_x=1700, center_y=GRID_LENGTH-4000, curve_radius=200,
                     angle_start=0, angle_end=-math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH-4200, start_x=200, length=1600)
    draw_horizontal_road(center_y=GRID_LENGTH-4200, start_x=-2200, length=2400)
    draw_curved_road(center_x=-2300, center_y=GRID_LENGTH-4000, curve_radius=200,
                     angle_start=-math.pi, angle_end=-math.pi/2, x_shift=100)
    draw_straight_road(center_x=-2400, start_y=-GRID_LENGTH-2800, length=6*GRID_LENGTH+400)
    draw_curved_road(center_x=-2300, center_y=GRID_LENGTH, curve_radius=200,
                     angle_start=math.pi, angle_end=math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH+200, start_x=-2200, length=2000)
    draw_curved_road(center_x=-300, center_y=GRID_LENGTH, curve_radius=200,
                     angle_start=0, angle_end=math.pi/2, x_shift=100)
    

def layout2():

    #layout 2
    draw_straight_road(center_x=0, start_y=-GRID_LENGTH-2400, length=6*GRID_LENGTH)
    draw_curved_road(center_x=-300, center_y=GRID_LENGTH-3600, curve_radius=200,
                     angle_start=0, angle_end=-math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH-3800, start_x=-3400, length=3200)
    draw_curved_road(center_x=-3500, center_y=GRID_LENGTH-4000, curve_radius=200,
                      angle_start=math.pi, angle_end=math.pi/2, x_shift=100)
    draw_straight_road(center_x=-3600, start_y=-GRID_LENGTH-4000, length=2*GRID_LENGTH)
    draw_curved_road(center_x=-3900, center_y=GRID_LENGTH-5200, curve_radius=200,
                     angle_start=0, angle_end=-math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH-5400, start_x=-6000, length=2200)
    draw_curved_road(center_x=-6100, center_y=GRID_LENGTH-5200, curve_radius=200,
                      angle_start=-math.pi, angle_end=-math.pi/2, x_shift=100)
    draw_straight_road(center_x=-6200, start_y=-GRID_LENGTH-4000, length=8*GRID_LENGTH+400)
    draw_curved_road(center_x=-6100, center_y=GRID_LENGTH, curve_radius=200,
                     angle_start=math.pi, angle_end=math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH+200, start_x=-6000, length=5800)
    draw_curved_road(center_x=-300, center_y=GRID_LENGTH, curve_radius=200,
                     angle_start=0, angle_end=math.pi/2, x_shift=100)
    
def layout3():
    #layout 3
    draw_straight_road(center_x=0, start_y=-GRID_LENGTH-2400, length=6*GRID_LENGTH)
    draw_curved_road(center_x=-300, center_y=GRID_LENGTH-3600, curve_radius=200,
                     angle_start=0, angle_end=-math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH-3800, start_x=-5000, length=4800)
    draw_curved_road(center_x=-5100, center_y=GRID_LENGTH-3600, curve_radius=200,
                     angle_start=-math.pi, angle_end=-math.pi/2, x_shift=100)
    draw_straight_road(center_x=-5200, start_y=-GRID_LENGTH-2400, length=6*GRID_LENGTH)
    draw_curved_road(center_x=-5100, center_y=GRID_LENGTH, curve_radius=200,
                     angle_start=math.pi, angle_end=math.pi/2, x_shift=100)
    draw_horizontal_road(center_y=GRID_LENGTH+200, start_x=-5000, length=4800)
    draw_curved_road(center_x=-300, center_y=GRID_LENGTH, curve_radius=200,
                     angle_start=0, angle_end=math.pi/2, x_shift=100)


def draw_road():
    selected_layout()

def draw_cube(size):
    """Draw a cube with given size, centered at origin."""
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
    """Draw a cylinder along the z-axis, centered at origin."""
    quad = gluNewQuadric()
    gluCylinder(quad, radius, radius, height, slices, 1)
    # Draw end caps
    glPushMatrix()
    glTranslatef(0, 0, height)
    gluDisk(quad, 0, radius, slices, 1)
    glPopMatrix()
    glPushMatrix()
    glRotatef(180, 1, 0, 0)
    gluDisk(quad, 0, radius, slices, 1)
    glPopMatrix()
    gluDeleteQuadric(quad)

def draw_player_car(x=0, y=0, z=30, gun_angle=0):
    """Draw a simple car with a gun on top, positioned at (x, y, z)."""
    glPushMatrix()
    glTranslatef(x, y, z)

    # Car body (main cube)
    glPushMatrix()
    glScalef(2.0, 1.0, 0.5)  # Long, wide, low
    glColor3f(0.7, 0.2, 0.2)  # Reddish color
    draw_cube(1.0)
    glPopMatrix()

    # Car cabin (smaller cube on top)
    glPushMatrix()
    glTranslatef(0.0, 0.0, 0.5)
    glScalef(1.0, 0.8, 0.3)  # Smaller, raised cabin
    glColor3f(0.3, 0.3, 0.3)  # Dark gray
    draw_cube(1.0)
    glPopMatrix()

    # Wheels (4 small cubes)
    wheel_positions = [(-1.5, 0.8, -0.5), (-1.5, -0.8, -0.5), (1.5, 0.8, -0.5), (1.5, -0.8, -0.5)]
    for wx, wy, wz in wheel_positions:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glScalef(0.3, 0.3, 0.2)
        glColor3f(0.1, 0.1, 0.1)  # Black wheels
        draw_cube(1.0)
        glPopMatrix()

    # Windows (2 flat cubes on cabin sides)
    glPushMatrix()
    glTranslatef(-0.1, 0.81, 0.7)
    glScalef(0.8, 0.01, 0.2)
    glColor3f(0.1, 0.1, 0.5)  # Blue-tinted windows
    draw_cube(1.0)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(-0.1, -0.81, 0.7)
    glScalef(0.8, 0.01, 0.2)
    glColor3f(0.1, 0.1, 0.5)
    draw_cube(1.0)
    glPopMatrix()

    # Gun on top, facing backward
    glPushMatrix()
    glTranslatef(0.0, 0.0, 1.0)  # Position on top of cabin
    glRotatef(gun_angle, 0, 0, 1)  # Rotate around z-axis
    glRotatef(90, 0, 1, 0)  # Orient backward along y-axis
    glColor3f(0.5, 0.5, 0.5)  # Silver gun
    draw_cylinder(0.1, 1.0)  # Thin, long cylinder
    glPopMatrix()

    glPopMatrix()


def special_keyboard(key, x, y):
    step = 20  # Movement step size
    global camera_pos

    if key == GLUT_KEY_UP:
        camera_pos[1] -= step   # Move forward along +y
    elif key == GLUT_KEY_DOWN:
        camera_pos[1] += step   # Move backward along -y
    elif key == GLUT_KEY_LEFT:
        camera_pos[0] += step   # Move left along -x
    elif key == GLUT_KEY_RIGHT:
        camera_pos[0] -= step   # Move right along +x

    # Optional: Add camera height change with PageUp/PageDown if desired
    elif key == GLUT_KEY_PAGE_UP:
        camera_pos[2] += step
    elif key == GLUT_KEY_PAGE_DOWN:
        camera_pos[2] -= step

    glutPostRedisplay()


def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 2000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    x, y, z = camera_pos
    gluLookAt(x, y, z,  # Eye position = current camera_pos
              x, y-100, 0,  # Look at the point right below camera at ground (z=0)
              0, 0, 1)  # Up vector along z



def idle():
    glutPostRedisplay()

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)
    setupCamera()
    draw_road()
    draw_player_car(0, 0, 0, 45)  # Example call with gun rotated 45 degrees
    draw_text(10, 770, "CSE423 Car Game Demo - Extended Road with 90° Turn")
    glutSwapBuffers()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Car Game: Extended Road with Curve")
  
    glutSpecialFunc(special_keyboard)
    glClearColor(0.0, 0.4, 0.0, 1.0)
    glutDisplayFunc(showScreen)
    glutIdleFunc(idle)
    global selected_layout
    layouts = [layout1, layout2, layout3]
    selected_layout = random.choice(layouts)

    glutMainLoop()

if __name__ == "__main__":
    main()
