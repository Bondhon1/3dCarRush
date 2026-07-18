"""Cars (player + AI enemies), the turret gun and its bullets.

Convention for the whole new engine:  ``angle`` is a heading in degrees where
0 deg faces +X and the forward vector is (cos a, sin a).  Car models are modelled
pointing along +X and simply rotated by ``angle`` about Z.
"""

import math
import time
from OpenGL.GL import *

from . import config as C
from . import gfx


# ---------------------------------------------------------------------------
# Car models
# ---------------------------------------------------------------------------
def _wheel(wx, wy, wz, radius, width):
    glPushMatrix()
    glTranslatef(wx, wy, wz)
    glRotatef(90, 1, 0, 0)              # lay the cylinder axis along Y
    glTranslatef(0, 0, -width / 2)
    glColor3f(*C.COL_TIRE)
    gfx.capped_cylinder(radius, width, slices=16)
    glColor3f(*C.COL_RIM)               # hub cap
    glPushMatrix()
    glTranslatef(0, 0, width + 0.5)
    gfx.disk(0, radius * 0.55, 12)
    glPopMatrix()
    glPopMatrix()


def draw_car(x, y, z, angle, body, accent, gun_angle=None):
    """Draw a lit, detailed car. If ``gun_angle`` is given, mount a turret."""
    S = C.CAR_SCALE
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(angle, 0, 0, 1)

    # lower skirt (darker, slightly wider) grounds the car visually
    glColor3f(*(c * 0.6 for c in body))
    glPushMatrix(); glTranslatef(0, 0, -0.06 * S)
    gfx.box(2.42 * S, 1.16 * S, 0.16 * S); glPopMatrix()

    # main hull
    glColor3f(*body)
    glPushMatrix(); glTranslatef(0, 0, 0.16 * S)
    gfx.box(2.3 * S, 1.08 * S, 0.34 * S); glPopMatrix()

    # sloped nose + tail wedges for a less boxy silhouette
    glColor3f(*body)
    glPushMatrix(); glTranslatef(2.05 * S, 0, 0.28 * S)
    gfx.box(0.45 * S, 0.95 * S, 0.18 * S); glPopMatrix()
    glPushMatrix(); glTranslatef(-2.05 * S, 0, 0.30 * S)
    gfx.box(0.45 * S, 1.0 * S, 0.2 * S); glPopMatrix()

    # accent racing stripe along the spine
    glColor3f(*accent)
    glPushMatrix(); glTranslatef(0, 0, 0.52 * S)
    gfx.box(2.1 * S, 0.18 * S, 0.03 * S); glPopMatrix()

    # cabin / greenhouse (glass)
    glColor3f(*C.COL_GLASS)
    glPushMatrix(); glTranslatef(-0.1 * S, 0, 0.66 * S)
    gfx.box(1.05 * S, 0.82 * S, 0.36 * S); glPopMatrix()
    # roof cap in accent
    glColor3f(*(min(1.0, c + 0.1) for c in accent))
    glPushMatrix(); glTranslatef(-0.1 * S, 0, 0.98 * S)
    gfx.box(0.9 * S, 0.72 * S, 0.05 * S); glPopMatrix()

    # wheels
    r, w = 0.44 * S, 0.26 * S
    for wx in (1.45 * S, -1.45 * S):
        for wy in (1.05 * S, -1.05 * S):
            _wheel(wx, wy, 0.02 * S, r, w)

    # headlights (front, +X) glow
    gfx.set_emissive(C.COL_HEADLIGHT)
    glColor3f(*C.COL_HEADLIGHT)
    for hy in (0.7 * S, -0.7 * S):
        glPushMatrix(); glTranslatef(2.45 * S, hy, 0.2 * S)
        gfx.sphere(0.16 * S, 10, 8); glPopMatrix()
    # taillights (back, -X) glow red
    gfx.set_emissive((0.6, 0.05, 0.05))
    glColor3f(0.9, 0.1, 0.1)
    for hy in (0.72 * S, -0.72 * S):
        glPushMatrix(); glTranslatef(-2.45 * S, hy, 0.26 * S)
        gfx.box(0.05 * S, 0.16 * S, 0.1 * S); glPopMatrix()
    gfx.clear_emissive()

    # turret + barrel (player only)
    if gun_angle is not None:
        glColor3f(0.28, 0.30, 0.34)
        glPushMatrix()
        glTranslatef(0.2 * S, 0, 0.9 * S)
        glRotatef(gun_angle, 0, 0, 1)
        gfx.box(0.4 * S, 0.5 * S, 0.22 * S)          # turret base
        glTranslatef(0.3 * S, 0, 0.05 * S)
        glColor3f(0.18, 0.19, 0.22)
        glRotatef(90, 0, 1, 0)                        # barrel along +X
        gfx.capped_cylinder(0.13 * S, 2.2 * S, slices=12)
        glPopMatrix()

    glPopMatrix()


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
class Player:
    def __init__(self):
        self.reset()

    def reset(self):
        self.pos = list(C.PLAYER_START)
        self.angle = 90.0            # facing +Y (north), matches legacy start
        self.speed = C.NORMAL_SPEED
        self.gun_angle = 0.0         # relative to car forward
        self.lives = C.PLAYER_MAX_LIVES
        self.finished = False
        self.boost_active = False
        self.boost_start = 0.0
        self.shield_active = False
        self.shield_start = 0.0
        self.jump_active = False
        self.jump_start = 0.0
        self.jump_mode = None

    def forward_vec(self):
        a = math.radians(self.angle)
        return math.cos(a), math.sin(a)

    def bullet_angle(self):
        return self.angle + self.gun_angle

    def draw(self):
        draw_car(self.pos[0], self.pos[1], self.pos[2], self.angle,
                 C.COL_PLAYER_BODY, C.COL_PLAYER_ACCENT, self.gun_angle)


# ---------------------------------------------------------------------------
# Enemy AI (waypoint follower, ported from the legacy path logic)
# ---------------------------------------------------------------------------
class Enemy:
    def __init__(self, path, speed):
        self.path = [list(p) for p in path]
        self.pos = list(path[0])
        self.segment = 0
        self.speed = speed
        self.lives = C.ENEMY_MAX_LIVES
        self.finished = False
        self.jump_active = False
        self.jump_start = 0.0
        self.slow_until = 0.0
        if len(path) > 1:
            dx = path[1][0] - path[0][0]
            dy = path[1][1] - path[0][1]
            self.angle = math.degrees(math.atan2(dy, dx))
        else:
            self.angle = 90.0

    def update(self):
        if self.finished or self.segment >= len(self.path) - 1:
            return
        goal = self.path[self.segment + 1]
        dx, dy = goal[0] - self.pos[0], goal[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        if dist == 0:
            self.segment += 1
            return

        target = math.atan2(dy, dx)
        cur = math.radians(self.angle)
        diff = ((target - cur + math.pi) % (2 * math.pi)) - math.pi
        turn = math.radians(4.5)
        cur = target if abs(diff) < turn else cur + (turn if diff > 0 else -turn)
        self.angle = math.degrees(cur)

        spd = self.speed
        if time.time() < self.slow_until:
            spd *= 0.45
        heading = (math.cos(cur), math.sin(cur))
        proj = (dx / dist) * heading[0] + (dy / dist) * heading[1]
        if proj > 0:
            self.pos[0] += spd * proj * heading[0]
            self.pos[1] += spd * proj * heading[1]

        if math.hypot(goal[0] - self.pos[0], goal[1] - self.pos[1]) < spd + 1:
            self.pos = list(goal)
            self.segment += 1

    def respawn(self):
        self.pos = list(self.path[0])
        self.segment = 0
        self.lives = C.ENEMY_MAX_LIVES
        self.finished = False
        if len(self.path) > 1:
            dx = self.path[1][0] - self.path[0][0]
            dy = self.path[1][1] - self.path[0][1]
            self.angle = math.degrees(math.atan2(dy, dx))

    def draw(self):
        draw_car(self.pos[0], self.pos[1], self.pos[2], self.angle,
                 C.COL_ENEMY_BODY, (1.0, 0.6, 0.3))


# ---------------------------------------------------------------------------
# Bullets
# ---------------------------------------------------------------------------
class Bullet:
    __slots__ = ("x", "y", "z", "angle")

    def __init__(self, x, y, z, angle):
        self.x, self.y, self.z, self.angle = x, y, z, angle

    def advance(self):
        a = math.radians(self.angle)
        self.x += C.BULLET_SPEED * math.cos(a)
        self.y += C.BULLET_SPEED * math.sin(a)


def draw_bullets(bullets):
    gfx.set_emissive((0.9, 0.5, 0.1))
    glColor3f(1.0, 0.75, 0.2)
    for b in bullets:
        glPushMatrix()
        glTranslatef(b.x, b.y, b.z)
        gfx.sphere(4.0, 10, 8)
        glPopMatrix()
    gfx.clear_emissive()
