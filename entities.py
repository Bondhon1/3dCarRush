"""Cars (player + AI enemies), the turret gun and its bullets.

Convention for the whole new engine:  ``angle`` is a heading in degrees where
0 deg faces +X and the forward vector is (cos a, sin a).  Car models are modelled
pointing along +X and simply rotated by ``angle`` about Z.
"""

import math
import time
from OpenGL.GL import *

import config as C
import gfx


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


def _section(w, h, cz, n=4.0, seg=16):
    """One rounded cross-section of the car body (a superellipse).

    ``n`` controls how boxy it is: 2 = ellipse, 4 = softly rounded rectangle.
    Returns points in the Y-Z plane plus their outward normals."""
    pts = []
    for i in range(seg):
        t = 2.0 * math.pi * i / seg
        ct, st = math.cos(t), math.sin(t)
        p = 2.0 / n
        yy = w * math.copysign(abs(ct) ** p, ct)
        zz = h * math.copysign(abs(st) ** p, st)
        # outward normal of a superellipse
        ny = (abs(ct) ** (2 - p) / w) * math.copysign(1.0, ct) if ct else 0.0
        nz = (abs(st) ** (2 - p) / h) * math.copysign(1.0, st) if st else 0.0
        nl = math.hypot(ny, nz) or 1.0
        pts.append((yy, cz + zz, ny / nl, nz / nl))
    return pts


def _loft(stations, seg=16):
    """Skin a list of (x, halfwidth, halfheight, centre_z) stations.

    This is what gives the cars a genuinely curved shell -- a swept, rounded
    hull -- instead of the stack of boxes they used to be."""
    secs = [(x, _section(w, h, cz, seg=seg)) for (x, w, h, cz) in stations]
    for i in range(len(secs) - 1):
        x0, s0 = secs[i]
        x1, s1 = secs[i + 1]
        glBegin(GL_QUAD_STRIP)
        for k in range(seg + 1):
            j = k % seg
            for (xx, sec) in ((x0, s0), (x1, s1)):
                yy, zz, ny, nz = sec[j]
                glNormal3f(0.0, ny, nz)
                glVertex3f(xx, yy, zz)
        glEnd()
    # cap the nose and tail so the hull reads as solid
    for (xx, sec), nx in ((secs[0], -1.0), (secs[-1], 1.0)):
        glBegin(GL_TRIANGLE_FAN)
        glNormal3f(nx, 0.0, 0.0)
        cz = sum(p[1] for p in sec) / len(sec)
        glVertex3f(xx, 0.0, cz)
        rng = range(seg, -1, -1) if nx < 0 else range(seg + 1)
        for k in rng:
            yy, zz, _, _ = sec[k % seg]
            glVertex3f(xx, yy, zz)
        glEnd()


def draw_car(x, y, z, angle, body, accent, gun_angle=None, bank=0.0, pitch=0.0):
    """Draw a lit, detailed car.

    ``gun_angle`` (if given) mounts a tracking turret; ``bank`` rolls the body
    into corners so a turning car leans instead of pivoting flat like a robot;
    ``pitch`` tips the nose down (+) or up (-) for bumps and hump crests.
    """
    S = C.CAR_SCALE
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(angle, 0, 0, 1)
    if bank:
        glRotatef(bank, 1, 0, 0)          # lean into the turn (roll about forward)
    if pitch:
        glRotatef(pitch, 0, 1, 0)         # nose dips/rises about the lateral axis

    # --- curved hull -------------------------------------------------------
    # A swept, rounded shell: wide and low through the middle, tapering to a
    # pointed nose and a cut-off tail.
    glColor3f(*body)
    _loft([
        (-2.45 * S, 0.72 * S, 0.22 * S, 0.30 * S),   # tail
        (-1.95 * S, 0.98 * S, 0.32 * S, 0.30 * S),
        (-0.90 * S, 1.10 * S, 0.38 * S, 0.30 * S),
        ( 0.30 * S, 1.12 * S, 0.38 * S, 0.29 * S),   # widest point
        ( 1.45 * S, 1.02 * S, 0.33 * S, 0.28 * S),
        ( 2.20 * S, 0.76 * S, 0.24 * S, 0.27 * S),
        ( 2.55 * S, 0.42 * S, 0.14 * S, 0.26 * S),   # nose
    ])

    # darker rocker panel hugging the underside
    glColor3f(*(c * 0.55 for c in body))
    _loft([
        (-2.30 * S, 0.74 * S, 0.10 * S, 0.10 * S),
        ( 0.30 * S, 1.14 * S, 0.12 * S, 0.09 * S),
        ( 2.30 * S, 0.78 * S, 0.10 * S, 0.10 * S),
    ])

    # domed glasshouse (a squashed ellipsoid = curved windscreen + roofline)
    glColor3f(*C.COL_GLASS)
    glPushMatrix()
    glTranslatef(-0.15 * S, 0, 0.62 * S)
    glScalef(1.25 * S, 0.80 * S, 0.42 * S)
    gfx.sphere(1.0, 20, 14)
    glPopMatrix()
    # accent roof strip following the dome
    glColor3f(*(min(1.0, c + 0.12) for c in accent))
    glPushMatrix()
    glTranslatef(-0.15 * S, 0, 0.92 * S)
    glScalef(0.95 * S, 0.34 * S, 0.10 * S)
    gfx.sphere(1.0, 14, 10)
    glPopMatrix()

    # accent stripe down the spine
    glColor3f(*accent)
    glPushMatrix(); glTranslatef(0.9 * S, 0, 0.60 * S)
    glScalef(1.5 * S, 0.11 * S, 0.06 * S)
    gfx.sphere(1.0, 12, 8); glPopMatrix()

    # rounded wheel arches
    glColor3f(*(c * 0.7 for c in body))
    for ax in (1.45 * S, -1.45 * S):
        for ay in (1.02 * S, -1.02 * S):
            glPushMatrix()
            glTranslatef(ax, ay, 0.30 * S)
            glScalef(0.62 * S, 0.16 * S, 0.42 * S)
            gfx.sphere(1.0, 12, 8)
            glPopMatrix()

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

    def reset(self, pos=None, angle=90.0, lives=None):
        """Place the car on the grid. Procedural circuits pass their own start
        position and heading, so the car always lines up down the straight."""
        self.pos = list(pos) if pos else list(C.PLAYER_START)
        if len(self.pos) < 3:
            self.pos = [self.pos[0], self.pos[1], C.CAR_GROUND_Z]
        self.angle = angle
        self.speed = C.NORMAL_SPEED
        self.gun_angle = 0.0         # relative to car forward
        self.lives = C.PLAYER_MAX_LIVES if lives is None else lives
        self.max_lives = self.lives   # health kits refill up to the grid armor
        self.finished = False
        self.bump_start = -99.0      # pothole dip animation clock
        self.pitch = 0.0             # current body pitch (bumps + hump crests)
        self.boost_active = False
        self.boost_start = 0.0
        self.boost_cd_until = 0.0     # earliest time the next boost may fire
        self.pothole_until = 0.0      # bogged down after clipping a pothole
        self.shield_active = False
        self.shield_start = 0.0
        self.jump_active = False
        self.jump_start = 0.0
        self.jump_mode = None
        self.wrecked = False          # true once armor runs out -> car hidden

    def forward_vec(self):
        a = math.radians(self.angle)
        return math.cos(a), math.sin(a)

    def bullet_angle(self):
        return self.angle + self.gun_angle

    def bump_offset(self, now):
        """Suspension response to a pothole: a quick nose-down dip that eases
        back up, returned as (pitch_degrees, z_drop). Smooth and self-settling."""
        t = now - self.bump_start
        if t < 0 or t > C.POTHOLE_BUMP_TIME:
            return 0.0, 0.0
        u = t / C.POTHOLE_BUMP_TIME
        # one damped oscillation: down, back up, settle
        env = (1.0 - u) ** 2
        wave = math.sin(u * 2.0 * math.pi)
        return C.POTHOLE_BUMP_PITCH * wave * env, -C.POTHOLE_BUMP_DROP * wave * env

    def draw(self):
        if self.wrecked:              # blown up -- the explosion stands in for it
            return
        draw_car(self.pos[0], self.pos[1], self.pos[2], self.angle,
                 C.COL_PLAYER_BODY, C.COL_PLAYER_ACCENT, self.gun_angle,
                 pitch=self.pitch)


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
        self.rage_until = 0.0        # temporary speed surge (player hit a rail)
        self.catchup = 1.0           # rubber-band multiplier (trailing OR leading)
        self.corner_grip = C.ENEMY_CORNER_SLOWDOWN  # per-difficulty AI skill
        self.role = None             # sprinter / bruiser / gunner
        self.tag = "E"               # short label for the HUD
        self.ram = 1                 # damage this rival deals by ramming
        self.grade_factor = 1.0      # gradient penalty/bonus set by the engine
        self.bank = 0.0              # current body roll (smoothed, degrees)
        self.gun_angle = 0.0         # turret heading relative to body forward
        self.fire_cd = 0.0           # next time this rival may shoot
        self.fire_gap = C.ENEMY_FIRE_COOLDOWN   # seconds between shots (difficulty)
        self.aiming = False          # turret currently tracking the player
        if len(path) > 1:
            dx = path[1][0] - path[0][0]
            dy = path[1][1] - path[0][1]
            self.angle = math.degrees(math.atan2(dy, dx))
        else:
            self.angle = 90.0

    def update(self, fs=1.0):
        """Advance along the waypoint path.

        ``fs`` is the engine's frame-scale (1.0 == 60 FPS) so rivals cover the
        same ground per second on any machine.  The follower is deliberately
        robust: it steers toward the *current* waypoint (never a blended point
        that could aim backward) and advances as soon as it reaches OR drives
        past a waypoint -- so a car can no longer orbit a corner it can't quite
        hit, which is what made them spin in place and double back."""
        if self.finished or self.segment >= len(self.path) - 1:
            self.bank *= 0.85
            return

        goal = self.path[self.segment + 1]
        dx, dy = goal[0] - self.pos[0], goal[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        hd = math.radians(self.angle)
        hx, hy = math.cos(hd), math.sin(hd)

        # reached, or overshot past the waypoint's plane -> take the next leg
        accept = max(70.0, self.speed * 6.0)
        if dist < accept or (dist < 260 and (dx * hx + dy * hy) < 0):
            self.segment += 1
            if self.segment >= len(self.path) - 1:
                return
            goal = self.path[self.segment + 1]
            dx, dy = goal[0] - self.pos[0], goal[1] - self.pos[1]
            dist = math.hypot(dx, dy) or 1.0

        # eased, capped steering toward the waypoint -> smooth arcs, but the cap
        # is high enough (and the car slows below) to actually round 90s
        target = math.atan2(dy, dx)
        diff = ((target - hd + math.pi) % (2 * math.pi)) - math.pi
        max_turn = math.radians(C.ENEMY_MAX_TURN) * fs
        step = max(-max_turn, min(max_turn, diff * 0.5))
        self.angle = math.degrees(hd + step)

        # lean into the turn (roll rate is per-frame, so divide fs back out)
        target_bank = max(-16.0, min(16.0, -math.degrees(step / max(fs, 1e-3)) * 4.5))
        self.bank += (target_bank - self.bank) * min(1.0, 0.18 * fs)

        # slow proportionally to the heading error -> a believable racing line.
        # corner_grip is the AI's skill knob: low tiers brake hard for corners,
        # INSANE carries most of its speed through.
        err = min(1.0, abs(diff) / (math.pi / 2))
        spd = self.speed * (1.0 - (1.0 - self.corner_grip) * err)
        now = time.time()
        if now < self.slow_until:
            spd *= 0.45
        if now < self.rage_until:                 # surge after a player rail bump
            spd *= C.ENEMY_RAGE_FACTOR
        spd *= self.catchup                       # two-way rubber band + DDA trim
        # climbing a hill costs a rival speed too -- they need the gradient
        spd *= self.grade_factor
        # no stack of multipliers may outrun the player's boost
        spd = min(spd, C.ENEMY_SPEED_CAP)
        a = math.radians(self.angle)
        self.pos[0] += spd * fs * math.cos(a)
        self.pos[1] += spd * fs * math.sin(a)

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
            self.fire_cd = now + self.fire_gap
            a = math.radians(self.angle + self.gun_angle)
            return Bullet(self.pos[0] + C.CAR_LENGTH / 2 * math.cos(a),
                          self.pos[1] + C.CAR_LENGTH / 2 * math.sin(a),
                          self.pos[2] + C.GUN_MUZZLE_Z,
                          self.angle + self.gun_angle, team="enemy")
        return None

    def respawn(self):
        self.pos = list(self.path[0])
        self.segment = 0
        self.lives = C.ENEMY_MAX_LIVES
        self.finished = False
        self.bank = 0.0
        self.gun_angle = 0.0
        self.rage_until = 0.0
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

    def advance(self, fs=1.0):
        a = math.radians(self.angle)
        self.x += self.speed() * fs * math.cos(a)
        self.y += self.speed() * fs * math.sin(a)


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
