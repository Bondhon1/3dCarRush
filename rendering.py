"""OpenGL rendering system with split-screen support"""

import math
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18, glutBitmapCharacter


class Camera:
    """Camera for viewport rendering"""
    def __init__(self, position=(0, 0, 100), target=(0, 0, 0), up=(0, 0, 1)):
        self.position = list(position)
        self.target = list(target)
        self.up = list(up)
    
    def update_from_car(self, car_pos, car_angle, fpv=False):
        """Update camera to follow a car"""
        x, y, z = car_pos
        angle_rad = math.radians(car_angle)
        
        if fpv:
            # First-person view
            eye_forward = 50
            eye_height = 30
            
            self.position = [
                x - eye_forward * math.sin(angle_rad),
                y + eye_forward * math.cos(angle_rad),
                z + eye_height
            ]
            
            # Look at gun direction
            self.target = [
                x + 200 * math.cos(angle_rad),
                y + 200 * math.sin(angle_rad),
                z + eye_height
            ]
        else:
            # Third-person view
            offset_distance = 150
            offset_angle = math.atan2(0, -offset_distance)
            total_angle = angle_rad + offset_angle
            
            self.position = [
                x + offset_distance * math.cos(total_angle),
                y + offset_distance * math.sin(total_angle),
                z + 75
            ]
            
            self.target = [x, y, z + 10]
        
        self.up = [0, 0, 1]
    
    def apply(self):
        """Apply this camera to the current OpenGL context"""
        gluLookAt(
            self.position[0], self.position[1], self.position[2],
            self.target[0], self.target[1], self.target[2],
            self.up[0], self.up[1], self.up[2]
        )


class Renderer:
    """Main rendering system"""
    
    def __init__(self, window_width=1000, window_height=800):
        self.window_width = window_width
        self.window_height = window_height
        self.cameras = []
        self.num_players = 1
    
    def setup_split_screen(self, num_players):
        """Setup split-screen viewports for multiple players"""
        self.num_players = num_players
        
        if num_players == 1:
            self.viewports = [(0, 0, self.window_width, self.window_height)]
        elif num_players == 2:
            # Side-by-side
            w = self.window_width // 2
            self.viewports = [
                (0, 0, w, self.window_height),
                (w, 0, w, self.window_height)
            ]
        elif num_players == 3:
            # 2 on top, 1 on bottom
            w = self.window_width // 2
            h = self.window_height // 2
            self.viewports = [
                (0, h, w, h),
                (w, h, w, h),
                (0, 0, self.window_width, h)
            ]
        elif num_players == 4:
            # 2x2 grid
            w = self.window_width // 2
            h = self.window_height // 2
            self.viewports = [
                (0, h, w, h),
                (w, h, w, h),
                (0, 0, w, h),
                (w, 0, w, h)
            ]
        
        # Create cameras for each viewport
        self.cameras = [Camera() for _ in range(num_players)]
    
    def render_viewport(self, viewport_idx, camera, scene_func):
        """Render a single viewport with camera and scene"""
        x, y, w, h = self.viewports[viewport_idx]
        
        # Set viewport
        glViewport(x, y, w, h)
        
        # Setup projection
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        
        aspect = w / h if h > 0 else 1
        gluPerspective(60, aspect, 0.1, 10000)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Apply camera
        camera.apply()
        
        # Render scene
        scene_func()
        
        # Restore matrices
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
    
    def clear_screen(self, r=0.0, g=0.4, b=0.0):
        """Clear the screen with background color"""
        glClearColor(r, g, b, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    def enable_depth_test(self, enabled=True):
        """Enable or disable depth testing"""
        if enabled:
            glEnable(GL_DEPTH_TEST)
        else:
            glDisable(GL_DEPTH_TEST)


class RenderUtils:
    """Utility functions for rendering primitives"""
    
    @staticmethod
    def draw_cube(size=1.0):
        """Draw a unit cube"""
        glBegin(GL_QUADS)
        
        # Front face
        glVertex3f(-size, -size, size)
        glVertex3f(size, -size, size)
        glVertex3f(size, size, size)
        glVertex3f(-size, size, size)
        
        # Back face
        glVertex3f(-size, -size, -size)
        glVertex3f(-size, size, -size)
        glVertex3f(size, size, -size)
        glVertex3f(size, -size, -size)
        
        # Left face
        glVertex3f(-size, -size, -size)
        glVertex3f(-size, -size, size)
        glVertex3f(-size, size, size)
        glVertex3f(-size, size, -size)
        
        # Right face
        glVertex3f(size, -size, -size)
        glVertex3f(size, size, -size)
        glVertex3f(size, size, size)
        glVertex3f(size, -size, size)
        
        # Top face
        glVertex3f(-size, size, -size)
        glVertex3f(-size, size, size)
        glVertex3f(size, size, size)
        glVertex3f(size, size, -size)
        
        # Bottom face
        glVertex3f(-size, -size, -size)
        glVertex3f(size, -size, -size)
        glVertex3f(size, -size, size)
        glVertex3f(-size, -size, size)
        
        glEnd()
    
    @staticmethod
    def draw_cylinder(radius, height, slices=16, stacks=1):
        """Draw a cylinder"""
        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)
        gluCylinder(quadric, radius, radius, height, slices, stacks)
        gluDeleteQuadric(quadric)
    
    @staticmethod
    def draw_cone(base_radius, height, slices=16, stacks=1):
        """Draw a cone"""
        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)
        gluCylinder(quadric, base_radius, 0, height, slices, stacks)
        gluDeleteQuadric(quadric)
    
    @staticmethod
    def draw_sphere(radius, slices=16, stacks=16):
        """Draw a sphere"""
        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)
        gluSphere(quadric, radius, slices, stacks)
        gluDeleteQuadric(quadric)
    
    @staticmethod
    def draw_text_2d(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
        """Draw 2D text at specified position"""
        glRasterPos2f(x, y)
        for ch in text:
            glutBitmapCharacter(font, ord(ch))
    
    @staticmethod
    def draw_quad(x1, y1, x2, y2, x3, y3, x4, y4, z=0):
        """Draw a 2D quad"""
        glBegin(GL_QUADS)
        glVertex3f(x1, y1, z)
        glVertex3f(x2, y2, z)
        glVertex3f(x3, y3, z)
        glVertex3f(x4, y4, z)
        glEnd()
    
    @staticmethod
    def set_color(r, g, b, a=1.0):
        """Set OpenGL color"""
        if a < 1.0:
            glColor4f(r, g, b, a)
        else:
            glColor3f(r, g, b)
