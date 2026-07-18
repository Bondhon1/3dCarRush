"""Pickups, hazards and scenery: health/shield kits, bombs, explosions,
speed breakers and trees.  All lit, most gently animated."""

import math
import time
import random
from OpenGL.GL import *

from . import config as C
from . import gfx


def _bob(period=1.6, amp=6.0, phase=0.0):
    return amp * math.sin(time.time() * (2 * math.pi / period) + phase)


# ---------------------------------------------------------------------------
# Health kit -- a floating red cross
# ---------------------------------------------------------------------------
def draw_health_kit(x, y):
    z = 26 + _bob(phase=x * 0.01)
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef((time.time() * 40) % 360, 0, 0, 1)
    gfx.set_emissive((0.35, 0.02, 0.05))
    glColor3f(*C.COL_HEALTH)
    gfx.box(9, 24, 9)
    gfx.box(24, 9, 9)
    gfx.clear_emissive()
    glPopMatrix()


# ---------------------------------------------------------------------------
# Shield kit -- a spinning cyan diamond
# ---------------------------------------------------------------------------
def draw_shield_kit(x, y):
    z = 30 + _bob(phase=y * 0.01)
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef((time.time() * 70) % 360, 0, 0, 1)
    gfx.set_emissive((0.05, 0.22, 0.32))
    glColor3f(*C.COL_SHIELD)
    _octahedron(22)
    gfx.clear_emissive()
    glPopMatrix()


def _octahedron(s):
    tips = [(s, 0, 0), (-s, 0, 0), (0, s, 0), (0, -s, 0)]
    top, bot = (0, 0, s), (0, 0, -s)
    ring = [(s, 0, 0), (0, s, 0), (-s, 0, 0), (0, -s, 0)]
    glBegin(GL_TRIANGLES)
    for i in range(4):
        a = ring[i]
        b = ring[(i + 1) % 4]
        for apex in (top, bot):
            nx = (a[1] * b[2] - a[2] * b[1])
            glNormal3f(apex[0], apex[1], apex[2])
            glVertex3f(*apex); glVertex3f(*a); glVertex3f(*b)
    glEnd()


# ---------------------------------------------------------------------------
# Bomb -- a pulsing dark sphere with a fuse
# ---------------------------------------------------------------------------
def draw_bomb(x, y):
    pulse = 1.0 + 0.1 * math.sin(time.time() * 5)
    size = 18 * pulse
    glPushMatrix()
    glTranslatef(x, y, size * 0.9)
    glColor3f(0.12, 0.12, 0.14)
    gfx.sphere(size, 18, 14)
    glColor3f(0.4, 0.25, 0.1)
    glPushMatrix(); glTranslatef(0, 0, size * 0.7)
    gfx.tapered_cylinder(size * 0.16, size * 0.1, size * 0.6, 8); glPopMatrix()
    gfx.set_emissive((1.0, 0.6, 0.1))
    glColor3f(1.0, 0.7, 0.2)
    glPushMatrix(); glTranslatef(0, 0, size * 1.35)
    gfx.sphere(size * 0.16, 8, 6); glPopMatrix()
    gfx.clear_emissive()
    glPopMatrix()


# ---------------------------------------------------------------------------
# Explosions -- expanding emissive burst, lifetime managed by the caller
# ---------------------------------------------------------------------------
class Explosion:
    def __init__(self, x, y, duration=0.9):
        self.x, self.y = x, y
        self.start = time.time()
        self.duration = duration

    @property
    def alive(self):
        return time.time() - self.start < self.duration

    def draw(self):
        t = (time.time() - self.start) / self.duration
        if t > 1:
            return
        gfx.lighting(False)
        radius = 12 + 46 * t
        glPushMatrix()
        glTranslatef(self.x, self.y, 20)
        # bright core fading out
        glColor4f(1.0, 0.9 - 0.6 * t, 0.1, 1.0 - t)
        gfx.sphere(radius * 0.5, 12, 10)
        glColor4f(1.0, 0.4, 0.05, 0.7 * (1 - t))
        gfx.sphere(radius, 14, 12)
        glPopMatrix()
        gfx.lighting(True)


# ---------------------------------------------------------------------------
# Speed breaker -- striped hump across the road
# ---------------------------------------------------------------------------
def draw_speed_breaker(x, y, width=400, depth=150, height=34):
    """Half-cylinder hump; ``width`` spans across the road (X), depth along Y."""
    glPushMatrix()
    glTranslatef(x, y, 0)
    slices = 22
    for i in range(slices):
        t0 = i / slices * math.pi
        t1 = (i + 1) / slices * math.pi
        y0 = math.cos(t0) * depth / 2
        z0 = math.sin(t0) * height
        y1 = math.cos(t1) * depth / 2
        z1 = math.sin(t1) * height
        glColor3f(*((0.95, 0.85, 0.1) if i % 2 == 0 else (0.1, 0.1, 0.1)))
        ny = (z1 - z0)
        nz = -(y1 - y0)
        glBegin(GL_QUADS)
        glNormal3f(0, ny, nz)
        glVertex3f(-width / 2, y0, z0)
        glVertex3f(width / 2, y0, z0)
        glVertex3f(width / 2, y1, z1)
        glVertex3f(-width / 2, y1, z1)
        glEnd()
    glPopMatrix()


# ---------------------------------------------------------------------------
# Ground shadow blob beneath a car
# ---------------------------------------------------------------------------
def draw_car_shadow(pos, angle):
    gfx.lighting(False)
    glDepthMask(GL_FALSE)                 # don't let the shadow occlude itself
    glPushMatrix()
    glTranslatef(pos[0], pos[1], 0.3)
    glRotatef(angle, 0, 0, 1)
    hl = C.CAR_LENGTH * 0.62
    hw = C.CAR_WIDTH * 0.72
    glColor4f(0.0, 0.0, 0.0, 0.32)
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(0, 0)
    seg = 16
    for i in range(seg + 1):
        t = i / seg * 2 * math.pi
        glVertex2f(hl * math.cos(t), hw * math.sin(t))
    glEnd()
    glPopMatrix()
    glDepthMask(GL_TRUE)
    gfx.lighting(True)


# ---------------------------------------------------------------------------
# Boost exhaust flames (drawn behind the player car while boosting)
# ---------------------------------------------------------------------------
def draw_boost_flames(pos, angle):
    S = C.CAR_SCALE
    flick = 1.0 + 0.35 * math.sin(time.time() * 40)
    gfx.lighting(False)
    glPushMatrix()
    glTranslatef(pos[0], pos[1], pos[2])
    glRotatef(angle, 0, 0, 1)
    for fy in (0.55 * S, -0.55 * S):
        glPushMatrix()
        glTranslatef(-2.3 * S, fy, 0.1 * S)
        glRotatef(-90, 0, 1, 0)           # point the cone backward (-X)
        # outer orange flame
        glColor4f(1.0, 0.45, 0.08, 0.85)
        gfx.cone(0.22 * S, 1.1 * S * flick, 10)
        # inner yellow core
        glColor4f(1.0, 0.9, 0.4, 0.95)
        gfx.cone(0.12 * S, 0.7 * S * flick, 10)
        glPopMatrix()
    glPopMatrix()
    gfx.lighting(True)


# ---------------------------------------------------------------------------
# Tree -- lit trunk + stacked cones
# ---------------------------------------------------------------------------
def draw_tree(x, y):
    glPushMatrix()
    glTranslatef(x, y, 0)
    glColor3f(0.45, 0.28, 0.12)
    gfx.capped_cylinder(9, 58, 10)
    tiers = [(58, 42, 60, (0.10, 0.42, 0.14)),
             (92, 36, 56, (0.12, 0.52, 0.16)),
             (124, 28, 50, (0.14, 0.60, 0.18))]
    for z, r, h, col in tiers:
        glColor3f(*col)
        glPushMatrix(); glTranslatef(0, 0, z)
        gfx.cone(r, h, 12); glPopMatrix()
    glPopMatrix()
