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


def draw_car(x, y, z, angle, body, accent, gun_angle=None, bank=0.0):
    """Draw a lit, detailed car.

    ``gun_angle`` (if given) mounts a tracking turret; ``bank`` rolls the body
    into corners so a turning car leans instead of pivoting flat like a robot.
    """
    S = C.CAR_SCALE
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(angle, 0, 0, 1)
    if bank:
        glRotatef(bank, 1, 0, 0)          # lean into the turn (roll about forward)

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
        self.bank = 0.0              # current body roll (smoothed, degrees)
        self.gun_angle = 0.0         # turret heading relative to body forward
        self.fire_cd = 0.0           # next time this rival may shoot
        self.aiming = False          # turret currently tracking the player
        if len(path) > 1:
            dx = path[1][0] - path[0][0]
            dy = path[1][1] - path[0][1]
            self.angle = math.degrees(math.atan2(dy, dx))
        else:
            self.angle = 90.0

    def _steer_target(self):
        """Aim a little past the next waypoint so corners are rounded, not
        clipped 90-degree pivots.  Blends the current leg with the next one as
        the car nears the corner, which is what removes the 'robotic' feel."""
        i = self.segment
        goal = self.path[i + 1]
        dx, dy = goal[0] - self.pos[0], goal[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        # within a corner-radius of the waypoint, start blending toward the
        # following leg's direction so the heading eases through the turn
        if i + 2 < len(self.path) and dist < 260:
            nxt = self.path[i + 2]
            blend = 1.0 - (dist / 260.0)          # 0 far -> 1 at the corner
            ndx, ndy = nxt[0] - goal[0], nxt[1] - goal[1]
            nd = math.hypot(ndx, ndy) or 1.0
            gx = dx / (dist or 1.0) * (1 - blend) + ndx / nd * blend
            gy = dy / (dist or 1.0) * (1 - blend) + ndy / nd * blend
            return math.atan2(gy, gx), dist
        return math.atan2(dy, dx), dist

    def update(self):
        if self.finished or self.segment >= len(self.path) - 1:
            self.bank *= 0.85
            return
        goal = self.path[self.segment + 1]
        target, dist = self._steer_target()
        if dist == 0:
            self.segment += 1
            return

        cur = math.radians(self.angle)
        diff = ((target - cur + math.pi) % (2 * math.pi)) - math.pi
        # capped, proportional steering: big errors turn near the cap, small
        # ones ease in -- smooth arcs instead of instant snaps
        max_turn = math.radians(C.ENEMY_MAX_TURN)
        step = max(-max_turn, min(max_turn, diff * 0.35))
        cur += step
        self.angle = math.degrees(cur)

        # bank into the corner proportional to how hard we're steering
        target_bank = max(-16.0, min(16.0, -math.degrees(step) * 4.5))
        self.bank += (target_bank - self.bank) * 0.18

        # slow for sharp corners so the racing line reads as deliberate driving
        spd = self.speed
        corner = min(1.0, abs(diff) / (math.pi / 2))
        spd *= 1.0 - (1.0 - C.ENEMY_CORNER_SLOWDOWN) * corner
        if time.time() < self.slow_until:
            spd *= 0.45

        heading = (math.cos(cur), math.sin(cur))
        self.pos[0] += spd * heading[0]
        self.pos[1] += spd * heading[1]

        if math.hypot(goal[0] - self.pos[0], goal[1] - self.pos[1]) < spd + 2:
            self.segment += 1

    def aim_and_maybe_fire(self, player, now):
        """Track the player with the turret; return a Bullet if it fires.

        Only rivals whose turret can see a nearby player pull the trigger, so
        the guns feel like a threat you provoke by tailgating rather than a
        constant hail of fire."""
        self.aiming = False
        if self.finished or self.lives <= 0:
            self.gun_angle *= 0.9
            return None
        dx = player.pos[0] - self.pos[0]
        dy = player.pos[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        if dist > C.ENEMY_GUN_RANGE:
            self.gun_angle *= 0.9                 # relax turret back to centre
            return None
        self.aiming = True
        # desired turret heading relative to the body
        want = math.degrees(math.atan2(dy, dx)) - self.angle
        want = ((want + 180) % 360) - 180
        d = ((want - self.gun_angle + 180) % 360) - 180
        self.gun_angle += max(-C.ENEMY_GUN_TURN, min(C.ENEMY_GUN_TURN, d))
        self.gun_angle = ((self.gun_angle + 180) % 360) - 180   # keep it bounded
        # fire only when the barrel is actually lined up and cooled down
        aligned = abs(((want - self.gun_angle + 180) % 360) - 180) < 12
        if aligned and now >= self.fire_cd:
            self.fire_cd = now + C.ENEMY_FIRE_COOLDOWN
            a = math.radians(self.angle + self.gun_angle)
            return Bullet(self.pos[0] + C.CAR_LENGTH / 2 * math.cos(a),
                          self.pos[1] + C.CAR_LENGTH / 2 * math.sin(a),
                          28, self.angle + self.gun_angle, team="enemy")
        return None

    def respawn(self):
        self.pos = list(self.path[0])
        self.segment = 0
        self.lives = C.ENEMY_MAX_LIVES
        self.finished = False
        self.bank = 0.0
        self.gun_angle = 0.0
        if len(self.path) > 1:
            dx = self.path[1][0] - self.path[0][0]
            dy = self.path[1][1] - self.path[0][1]
            self.angle = math.degrees(math.atan2(dy, dx))

    def draw(self):
        # rivals are armed: the turret is always mounted and swings toward the
        # player when in range (it relaxes back to forward otherwise)
        draw_car(self.pos[0], self.pos[1], self.pos[2], self.angle,
                 C.COL_ENEMY_BODY, (1.0, 0.6, 0.3),
                 gun_angle=self.gun_angle, bank=self.bank)


# ---------------------------------------------------------------------------
# Bullets
# ---------------------------------------------------------------------------
class Bullet:
    __slots__ = ("x", "y", "z", "angle", "team", "born")

    def __init__(self, x, y, z, angle, team="player"):
        self.x, self.y, self.z, self.angle = x, y, z, angle
        self.team = team
        self.born = time.time()

    def speed(self):
        return C.BULLET_SPEED if self.team == "player" else C.ENEMY_BULLET_SPEED

    def advance(self):
        a = math.radians(self.angle)
        self.x += self.speed() * math.cos(a)
        self.y += self.speed() * math.sin(a)


def draw_bullets(bullets):
    """Draw bullets as glowing energy bolts -- a bright core, a tapered nose
    and a fading tracer tail -- so they read as fast rounds, not floating balls."""
    for b in bullets:
        core, tail = (C.COL_PLAYER_TRACER, (1.0, 0.55, 0.1)) \
            if b.team == "player" else (C.COL_ENEMY_TRACER, (1.0, 0.2, 0.08))
        glPushMatrix()
        glTranslatef(b.x, b.y, b.z)
        glRotatef(b.angle, 0, 0, 1)          # orient the bolt along its travel
        glRotatef(90, 0, 1, 0)               # bolt long axis -> local +X

        # fading tracer streak behind the round (additive glow, no depth write)
        gfx.lighting(False)
        glDepthMask(GL_FALSE)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glBegin(GL_TRIANGLES)
        length = 42.0
        for hw, aa in ((3.2, 0.5), (1.4, 0.9)):
            glColor4f(*tail, 0.0)
            glVertex3f(0, 0, length)
            glColor4f(*core, aa)
            glVertex3f(-hw, 0, 0)
            glColor4f(*core, aa)
            glVertex3f(hw, 0, 0)
            glColor4f(*tail, 0.0)
            glVertex3f(0, 0, length)
            glColor4f(*core, aa)
            glVertex3f(0, -hw, 0)
            glColor4f(*core, aa)
            glVertex3f(0, hw, 0)
        glEnd()
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # solid glowing slug at the head
        gfx.lighting(True)
        gfx.set_emissive(core)
        glColor3f(*core)
        gfx.tapered_cylinder(3.0, 0.4, 11.0, 10)     # tapered nose along +Z
        glPushMatrix(); glTranslatef(0, 0, -3.0)
        gfx.sphere(3.0, 8, 6); glPopMatrix()          # rounded tail cap
        gfx.clear_emissive()
        glDepthMask(GL_TRUE)
        glPopMatrix()
