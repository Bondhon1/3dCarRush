"""Scene rendering - draws all game objects"""

import math
from OpenGL.GL import *
from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18
from rendering import RenderUtils


class SceneRenderer:
    """Renders the game scene"""
    
    def __init__(self):
        self.road_points = None
        self.border_points = None
        self.finish_line = None
        self.tree_positions = []
    
    def setup(self, road_generator):
        """Setup scene from road generator"""
        self.road_points = road_generator.get_road_points()
        self.border_points = road_generator.get_border_points()
        self.finish_line = road_generator.get_finish_line()
        self._generate_trees(num_trees=50)
    
    def _generate_trees(self, num_trees=50):
        """Generate random tree positions outside the road"""
        import random
        
        self.tree_positions = []
        attempts = 0
        max_attempts = 500
        
        while len(self.tree_positions) < num_trees and attempts < max_attempts:
            x = random.uniform(-5000, 5000)
            y = random.uniform(-5000, 5000)
            
            # Check if position is on road
            on_road = any(
                (x - rx)**2 + (y - ry)**2 < 5000
                for rx, ry in list(self.road_points)[:100]
            )
            
            if not on_road:
                self.tree_positions.append((x, y))
            
            attempts += 1
    
    def render_background(self):
        """Render sky and ground"""
        glDisable(GL_DEPTH_TEST)
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, 1000, 0, 800, -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Sky
        glBegin(GL_QUADS)
        RenderUtils.set_color(0.53, 0.81, 0.98)
        glVertex2f(0, 400)
        glVertex2f(1000, 400)
        glVertex2f(1000, 800)
        glVertex2f(0, 800)
        glEnd()
        
        # Ground
        glBegin(GL_QUADS)
        RenderUtils.set_color(0.0, 0.4, 0.0)
        glVertex2f(0, 0)
        glVertex2f(1000, 0)
        glVertex2f(1000, 400)
        glVertex2f(0, 400)
        glEnd()
        
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        glEnable(GL_DEPTH_TEST)
    
    def render_road(self):
        """Render road surface with better visuals"""
        if not self.road_points:
            return
        
        # Use point size for better visibility
        glPointSize(3.0)
        glColor3f(0.3, 0.3, 0.3)  # Dark gray
        glBegin(GL_POINTS)
        
        sample_rate = 3  # Draw every Nth point for performance
        for i, (rx, ry) in enumerate(list(self.road_points)):
            if i % sample_rate == 0:
                glVertex3f(rx, ry, 0.2)  # Slightly above ground
        
        glEnd()
        glPointSize(1.0)
        
        # Draw lane markers
        glColor3f(1.0, 1.0, 0.5)  # Yellow lane markers
        glLineWidth(2.0)
        glBegin(GL_LINES)
        
        sample_points = list(self.road_points)[::20]
        for i in range(0, len(sample_points) - 1, 5):
            x1, y1 = sample_points[i]
            x2, y2 = sample_points[i + 1] if i + 1 < len(sample_points) else (x1, y1 + 20)
            glVertex3f(x1, y1, 0.3)
            glVertex3f(x2, y2, 0.3)
        
        glEnd()
        glLineWidth(1.0)
    
    def render_borders(self):
        """Render road borders with 3D blocks"""
        if not self.border_points:
            return
        
        glColor3f(0.95, 0.95, 0.1)  # Bright yellow borders
        glLineWidth(2.0)
        
        # Draw border as connected line
        glBegin(GL_LINE_STRIP)
        
        for bx, by in list(self.border_points)[::5]:  # Sample every 5th point
            glVertex3f(bx, by, 0)
            glVertex3f(bx, by, 30)
        
        glEnd()
        glLineWidth(1.0)
        
        # Draw 3D border cubes at key positions
        glColor3f(0.9, 0.0, 0.0)  # Red cubes for visibility
        for i, (bx, by) in enumerate(list(self.border_points)):
            if i % 20 == 0:  # Draw every 20th for performance
                glPushMatrix()
                glTranslatef(bx, by, 15)
                RenderUtils.draw_cube(size=6)
                glPopMatrix()
    
    def render_finish_line(self):
        """Render finish line with animated checkered pattern"""
        if not self.finish_line:
            return
        
        x, y = self.finish_line['pos']
        angle = self.finish_line['angle']
        width = self.finish_line.get('width', 400)
        
        glPushMatrix()
        glTranslatef(x, y, 0)
        glRotatef(angle, 0, 0, 1)
        
        # Checkered pattern finish line
        check_size = 40
        checks_wide = int(width / check_size)
        
        for i in range(checks_wide):
            for j in range(2):
                if (i + j) % 2 == 0:
                    RenderUtils.set_color(1, 1, 1)  # White
                else:
                    RenderUtils.set_color(0, 0, 0)  # Black
                
                glBegin(GL_QUADS)
                
                x1 = -width/2 + i * check_size
                y1 = -check_size * j
                x2 = x1 + check_size
                y2 = y1 + check_size
                
                glVertex3f(x1, y1, 0.5)
                glVertex3f(x2, y1, 0.5)
                glVertex3f(x2, y2, 0.5)
                glVertex3f(x1, y2, 0.5)
                
                glEnd()
        
        # Add white border around finish line
        RenderUtils.set_color(1, 1, 1)
        glLineWidth(3.0)
        glBegin(GL_LINE_LOOP)
        glVertex3f(-width/2, -check_size, 1.0)
        glVertex3f(width/2, -check_size, 1.0)
        glVertex3f(width/2, check_size, 1.0)
        glVertex3f(-width/2, check_size, 1.0)
        glEnd()
        glLineWidth(1.0)
        
        glPopMatrix()
    
    def render_trees(self):
        """Render trees in the scene"""
        for tx, ty in self.tree_positions:
            self._draw_tree(tx, ty, 0)
    
    def _draw_tree(self, x, y, z=0):
        """Draw a single tree"""
        glPushMatrix()
        glTranslatef(x, y, z)
        
        # Trunk
        RenderUtils.set_color(0.6, 0.3, 0.1)
        glPushMatrix()
        RenderUtils.draw_cylinder(radius=10, height=60)
        glPopMatrix()
        
        # Foliage (stacked cones)
        RenderUtils.set_color(0.0, 0.5, 0.0)
        glPushMatrix()
        glTranslatef(0, 0, 60)
        RenderUtils.draw_cone(base_radius=40, height=60)
        glPopMatrix()
        
        RenderUtils.set_color(0.0, 0.7, 0.0)
        glPushMatrix()
        glTranslatef(0, 0, 90)
        RenderUtils.draw_cone(base_radius=35, height=60)
        glPopMatrix()
        
        RenderUtils.set_color(0.0, 0.3, 0.0)
        glPushMatrix()
        glTranslatef(0, 0, 120)
        RenderUtils.draw_cone(base_radius=30, height=60)
        glPopMatrix()
        
        glPopMatrix()
    
    def render_player_car(self, x, y, z, angle, color):
        """Render a player car with better visuals"""
        scale = 15
        
        glPushMatrix()
        glTranslatef(x, y, z)
        glRotatef(angle, 0, 0, 1)
        
        # Body - main chassis
        RenderUtils.set_color(*color)
        glPushMatrix()
        glScalef(2.5 * scale, 1.2 * scale, 0.6 * scale)
        RenderUtils.draw_cube(1.0)
        glPopMatrix()
        
        # Cabin - windshield area
        cabin_color = tuple(min(c + 0.2, 1.0) for c in color)  # Lighter version
        RenderUtils.set_color(*cabin_color)
        glPushMatrix()
        glTranslatef(0.0, 0.0, 0.65 * scale)
        glScalef(1.2 * scale, 0.9 * scale, 0.55 * scale)
        RenderUtils.draw_cube(1.0)
        glPopMatrix()
        
        # Headlights
        RenderUtils.set_color(1.0, 1.0, 0.8)  # Yellow lights
        for light_y in [-0.5 * scale, 0.5 * scale]:
            glPushMatrix()
            glTranslatef(-1.5 * scale, light_y, 0.2 * scale)
            RenderUtils.draw_sphere(radius=0.3 * scale, slices=8, stacks=8)
            glPopMatrix()
        
        # Wheels - large and visible
        RenderUtils.set_color(0.1, 0.1, 0.1)  # Dark gray wheels
        wheel_positions = [
            (-1.2 * scale, 1.3 * scale, -2.0),
            (-1.2 * scale, -1.3 * scale, -2.0),
            (1.2 * scale, 1.3 * scale, -2.0),
            (1.2 * scale, -1.3 * scale, -2.0)
        ]
        
        for wx, wy, wz in wheel_positions:
            glPushMatrix()
            glTranslatef(wx, wy, wz)
            glRotatef(90, 1, 0, 0)
            RenderUtils.draw_cylinder(radius=0.5 * scale, height=0.25 * scale)
            
            # Wheel rims
            RenderUtils.set_color(0.6, 0.6, 0.6)
            glTranslatef(0, 0, 0.25 * scale + 0.1 * scale)
            RenderUtils.draw_sphere(radius=0.6 * scale, slices=8, stacks=8)
            glPopMatrix()
        
        glPopMatrix()
    
    def render_enemy_car(self, x, y, z, angle, color=(0.9, 0.3, 0.3)):
        """Render an enemy car (identical to player but different color)"""
        self.render_player_car(x, y, z, angle, color)
    
    def render_ui_panel(self, game_state, player_idx, window_width=1000, window_height=800):
        """Render 2D UI panel for a player"""
        glDisable(GL_DEPTH_TEST)
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        from OpenGL.GLU import gluOrtho2D
        gluOrtho2D(0, window_width, 0, window_height)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        player = game_state.players[player_idx]
        
        # Panel background
        x0, y0 = 10, 10
        x1, y1 = 480, 230
        
        RenderUtils.set_color(0.1, 0.1, 0.1, 0.8)
        glBegin(GL_QUADS)
        glVertex2f(x0, y0)
        glVertex2f(x1, y0)
        glVertex2f(x1, y1)
        glVertex2f(x0, y1)
        glEnd()
        
        # Panel border
        RenderUtils.set_color(0.5, 0.5, 0.5)
        glLineWidth(2.0)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x0, y0)
        glVertex2f(x1, y0)
        glVertex2f(x1, y1)
        glVertex2f(x0, y1)
        glEnd()
        
        # Text info
        RenderUtils.set_color(0.0, 1.0, 1.0)
        RenderUtils.draw_text_2d(x0 + 10, y1 - 25, f"P{player_idx+1} Speed: {int(player.speed)} km/h")
        
        RenderUtils.set_color(1.0, 1.0, 1.0)
        RenderUtils.draw_text_2d(x0 + 10, y1 - 50, f"Lives: {max(0, player.lives)}")
        
        status = "FINISHED" if player.finished else "RACING"
        RenderUtils.set_color(0.0, 1.0, 0.0 if player.finished else 1.0)
        RenderUtils.draw_text_2d(x0 + 10, y1 - 75, f"Status: {status}")
        
        if game_state.paused:
            RenderUtils.set_color(1.0, 1.0, 0.0)
            RenderUtils.draw_text_2d(x0 + 10, y1 - 100, "PAUSED")
        
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        glEnable(GL_DEPTH_TEST)
