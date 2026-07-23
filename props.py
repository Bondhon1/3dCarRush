"""Pickups, hazards and scenery: health/shield kits, bombs, explosions,
speed breakers and trees.  All lit, most gently animated."""

import math
import time
import random
from OpenGL.GL import *

import config as C
import gfx


def _bob(period=1.6, amp=6.0, phase=0.0):
    return amp * math.sin(time.time() * (2 * math.pi / period) + phase)


# ---------------------------------------------------------------------------
# Health kit -- a floating red cross
# ---------------------------------------------------------------------------
def draw_health_kit(x, y, base_z=0.0):
    z = base_z + 26 + _bob(phase=x * 0.01)
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
def draw_shield_kit(x, y, base_z=0.0):
    z = base_z + 30 + _bob(phase=y * 0.01)
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
def draw_bomb(x, y, base_z=0.0):
    pulse = 1.0 + 0.1 * math.sin(time.time() * 5)
    size = 18 * pulse
    glPushMatrix()
    glTranslatef(x, y, base_z + size * 0.9)
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
# Car explosion -- a car being destroyed: a rolling fireball, a ground
# shockwave, tumbling debris chunks and a lingering plume of smoke.  Used
# when a rival is wrecked or the player's armor runs out.
# ---------------------------------------------------------------------------
class CarExplosion:
    def __init__(self, x, y, base_z=0.0, tint=None, duration=1.3):
        self.x, self.y = x, y
        self.z = base_z + 18.0            # roughly the car's body height
        self.start = time.time()
        self.duration = duration
        # a car's paint flecks colour the debris; default to a hot orange
        self.tint = tint or (0.75, 0.75, 0.78)
        rnd = random.Random(int((x * 13.7 + y * 7.3)) ^ 0x9E37)
        # tumbling chunks blown outward, each with its own arc and spin
        self.debris = []
        for _ in range(14):
            ang = rnd.uniform(0, 2 * math.pi)
            speed = rnd.uniform(120, 340)
            self.debris.append({
                'vx': math.cos(ang) * speed,
                'vy': math.sin(ang) * speed,
                'vz': rnd.uniform(180, 360),
                'spin': rnd.uniform(180, 620) * rnd.choice((-1, 1)),
                'axis': (rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)),
                'size': rnd.uniform(4, 11),
                'metal': rnd.random() < 0.5,   # metal shard vs painted panel
            })
        # smoke puffs drift up and outward as the fireball dies down
        self.smoke = []
        for _ in range(7):
            ang = rnd.uniform(0, 2 * math.pi)
            self.smoke.append({
                'dx': math.cos(ang) * rnd.uniform(0, 26),
                'dy': math.sin(ang) * rnd.uniform(0, 26),
                'rise': rnd.uniform(70, 150),
                'r': rnd.uniform(20, 34),
                'delay': rnd.uniform(0.0, 0.25),
            })

    @property
    def alive(self):
        return time.time() - self.start < self.duration

    def draw(self):
        t = (time.time() - self.start) / self.duration
        if t > 1:
            return
        g = 520.0                        # debris gravity (units/s^2)
        life = self.duration
        gfx.lighting(False)
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)

        # --- ground shockwave: a flat ring flashing outward, early only ---
        if t < 0.5:
            st = t / 0.5
            glPushMatrix()
            glTranslatef(0, 0, -self.z + 2.0)
            glColor4f(1.0, 0.85, 0.4, 0.55 * (1 - st))
            _ring(20 + 150 * st, 6 + 10 * st)
            glPopMatrix()

        # --- fireball: layered emissive spheres punching up and fading ---
        if t < 0.65:
            ft = t / 0.65
            rise = 34 * ft
            glPushMatrix()
            glTranslatef(0, 0, rise)
            core = 16 + 44 * ft
            glColor4f(1.0, 0.95, 0.55, (1 - ft) * 0.95)
            gfx.sphere(core * 0.55, 12, 10)
            glColor4f(1.0, 0.55, 0.12, (1 - ft) * 0.8)
            gfx.sphere(core, 14, 12)
            glColor4f(0.7, 0.22, 0.05, (1 - ft) * 0.5)
            gfx.sphere(core * 1.4, 14, 12)
            glPopMatrix()

        # --- tumbling debris chunks on ballistic arcs ---
        rt = t * life
        for d in self.debris:
            dz = d['vz'] * rt - 0.5 * g * rt * rt
            if dz < -self.z:
                dz = -self.z          # rest on the ground once it lands
            glPushMatrix()
            glTranslatef(d['vx'] * rt, d['vy'] * rt, dz)
            glRotatef(d['spin'] * rt, *d['axis'])
            if d['metal']:
                glColor4f(0.35, 0.36, 0.4, 1 - t * 0.7)
            else:
                glColor4f(self.tint[0], self.tint[1], self.tint[2], 1 - t * 0.7)
            s = d['size']
            gfx.box(s, s * 0.6, s * 0.4)
            glPopMatrix()

        # --- smoke plume: dark puffs rising and swelling as fire dies ---
        for s in self.smoke:
            if t < s['delay']:
                continue
            st = (t - s['delay']) / (1 - s['delay'])
            shade = 0.28 - 0.12 * st
            glColor4f(shade, shade * 0.92, shade * 0.88, 0.5 * (1 - st))
            glPushMatrix()
            glTranslatef(s['dx'] * (0.5 + st), s['dy'] * (0.5 + st),
                         28 + s['rise'] * st)
            gfx.sphere(s['r'] * (0.6 + 0.9 * st), 10, 8)
            glPopMatrix()

        glPopMatrix()
        gfx.lighting(True)


def _ring(radius, width, segments=28):
    """A flat filled annulus on the z=0 plane (shockwave / scorch)."""
    inner = max(0.0, radius - width)
    glBegin(GL_TRIANGLE_STRIP)
    for i in range(segments + 1):
        a = 2 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        glVertex3f(inner * ca, inner * sa, 0)
        glVertex3f(radius * ca, radius * sa, 0)
    glEnd()


# ---------------------------------------------------------------------------
# Speed breaker -- striped hump across the road
# ---------------------------------------------------------------------------
def breaker_local(br, x, y):
    """Transform a world point into a hump's local frame.

    Returns ``(along, across)`` -- distance along the direction of travel and
    laterally across the road -- or ``(None, None)`` if the point is off the
    hump.  Works at any road angle, which procedural circuits need."""
    bx, by, w, d, ang = br
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    dx, dy = x - bx, y - by
    along = dx * ca + dy * sa          # spans the hump's depth
    across = -dx * sa + dy * ca        # spans the road width
    if abs(along) <= d / 2 and abs(across) <= w / 2:
        return along, across
    return None, None


# A raised-cosine ramp: height H at the crest, and -- unlike a half-circle --
# it meets the tarmac with ZERO slope at both edges, so a car rolls on and off
# smoothly instead of hitting a vertical wall.
def _breaker_profile(t):
    return C.BREAKER_HEIGHT * 0.5 * (1.0 + math.cos(math.pi * t))


def _breaker_slope(t, depth):
    return -C.BREAKER_HEIGHT * math.pi * math.sin(math.pi * t) / depth


def breaker_surface_z(br, x, y):
    """Height of the hump's surface under a point (0 when off the hump).

    Driving slowly now RIDES this profile instead of ploughing through it."""
    along, _ = breaker_local(br, x, y)
    if along is None:
        return 0.0
    return _breaker_profile(2.0 * along / br[3])


def breaker_pitch(br, x, y):
    """Body pitch (degrees, + = nose down) for a car sitting on the hump."""
    along, _ = breaker_local(br, x, y)
    if along is None:
        return 0.0
    slope = _breaker_slope(2.0 * along / br[3], br[3])
    pitch = -math.degrees(math.atan(slope))   # nose rises on the way up
    return max(-C.BREAKER_MAX_PITCH, min(C.BREAKER_MAX_PITCH, pitch))


def draw_speed_breaker(x, y, width=C.BREAKER_WIDTH, depth=C.BREAKER_DEPTH,
                       angle=0.0, base_z=0.0, height=C.BREAKER_HEIGHT,
                       height_fn=None):
    """A proper road hump: a rounded ridge banded with hazard stripes across
    the road, closed ends, and a grounded rubber skirt.

    Built directly in WORLD space and sampled against ``height_fn`` at every
    vertex, so it follows the road up and down. Drawn flat (as it used to be)
    a hump buries one end in the tarmac and floats the other clear of it --
    the road can rise 50+ units across a footprint while the hump is only ~18
    tall.
    """
    h = height_fn or (lambda wx, wy: base_z)
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)        # travel direction
    px, py = -sa, ca                         # across the road
    segs, stripes = 16, 10

    def world(u, v):
        """u = along travel, v = across the road -> world x, y, road z."""
        wx = x + ca * u + px * v
        wy = y + sa * u + py * v
        return wx, wy, h(wx, wy)

    def prof(i):
        t = -1.0 + 2.0 * i / segs
        return t * depth / 2, height * 0.5 * (1.0 + math.cos(math.pi * t)), t

    # striped shell
    for sIdx in range(stripes):
        v0 = -width / 2 + width * sIdx / stripes
        v1 = -width / 2 + width * (sIdx + 1) / stripes
        glColor3f(*((0.96, 0.78, 0.06) if sIdx % 2 == 0 else (0.11, 0.11, 0.12)))
        glBegin(GL_QUAD_STRIP)
        for i in range(segs + 1):
            u, z, t = prof(i)
            slope = -height * math.pi * math.sin(math.pi * t) / depth
            nl = math.hypot(slope, 1.0)
            nx, nz = -slope / nl, 1.0 / nl
            glNormal3f(nx * ca, nx * sa, nz)
            for v in (v0, v1):
                wx, wy, wz = world(u, v)
                glVertex3f(wx, wy, wz + z)
        glEnd()

    # closed ends
    for v, sgn in ((-width / 2, -1.0), (width / 2, 1.0)):
        glColor3f(0.13, 0.13, 0.14)
        glBegin(GL_TRIANGLE_FAN)
        glNormal3f(px * sgn, py * sgn, 0.0)
        wx, wy, wz = world(0.0, v)
        glVertex3f(wx, wy, wz)
        for i in range(segs + 1):
            u, z, _ = prof(i)
            wx, wy, wz = world(u, v)
            glVertex3f(wx, wy, wz + z)
        glEnd()

    # dark skirt where the hump meets the tarmac
    glColor3f(0.08, 0.08, 0.09)
    glNormal3f(0, 0, 1)
    for u0, u1 in ((-depth / 2 - 5, -depth / 2), (depth / 2, depth / 2 + 5)):
        glBegin(GL_QUADS)
        for (uu, vv) in ((u0, -width / 2), (u1, -width / 2),
                         (u1, width / 2), (u0, width / 2)):
            wx, wy, wz = world(uu, vv)
            glVertex3f(wx, wy, wz + 0.35)
        glEnd()


# ---------------------------------------------------------------------------
# Ground shadow blob beneath a car
# ---------------------------------------------------------------------------
def draw_car_shadow(pos, angle, base_z=0.0):
    gfx.lighting(False)
    glDepthMask(GL_FALSE)                 # don't let the shadow occlude itself
    glPushMatrix()
    glTranslatef(pos[0], pos[1], base_z + 0.3)
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
def draw_tree(x, y, scale=1.0, base_z=0.0, kind=0):
    """Three silhouettes -- conifer, broadleaf and scrub -- so woodland reads as
    a varied treeline instead of rows of identical cones."""
    dark, light = C.T('tree_dark'), C.T('tree_light')
    mid = tuple((dark[i] + light[i]) / 2 for i in range(3))
    glPushMatrix()
    glTranslatef(x, y, base_z)
    glScalef(scale, scale, scale)
    glRotatef((x * 7.3 + y * 3.1) % 360, 0, 0, 1)

    if kind == 1:                       # broadleaf: bare trunk + round canopy
        glColor3f(0.40, 0.26, 0.13)
        gfx.capped_cylinder(8, 76, 9)
        for (bz, br, col) in ((88, 44, dark), (112, 38, mid), (132, 26, light)):
            glColor3f(*col)
            glPushMatrix(); glTranslatef(0, 0, bz)
            glScalef(1.0, 1.0, 0.78); gfx.sphere(br, 12, 9); glPopMatrix()
    elif kind == 2:                     # scrub: low clustered bush
        glColor3f(0.38, 0.26, 0.14)
        gfx.capped_cylinder(6, 22, 8)
        for (bx, by_, bz, br) in ((0, 0, 34, 30), (16, 8, 26, 22),
                                  (-14, -10, 24, 20)):
            glColor3f(*(dark if br > 24 else mid))
            glPushMatrix(); glTranslatef(bx, by_, bz)
            glScalef(1.0, 1.0, 0.7); gfx.sphere(br, 10, 8); glPopMatrix()
    else:                               # conifer: stacked tapering tiers
        glColor3f(0.45, 0.28, 0.12)
        gfx.capped_cylinder(9, 58, 10)
        for (z, r, h, col) in ((52, 46, 62, dark), (88, 38, 58, mid),
                               (120, 30, 54, mid), (150, 20, 46, light)):
            glColor3f(*col)
            glPushMatrix(); glTranslatef(0, 0, z)
            gfx.cone(r, h, 12); glPopMatrix()
    glPopMatrix()


# ---------------------------------------------------------------------------
# Rock -- a low lit boulder (irregular squashed sphere)
# ---------------------------------------------------------------------------
def draw_rock(x, y, scale=1.0, rot=0.0, base_z=0.0):
    glPushMatrix()
    glTranslatef(x, y, base_z)
    glRotatef(rot, 0, 0, 1)
    glScalef(30 * scale, 22 * scale, 16 * scale)
    glColor3f(*C.COL_ROCK)
    gfx.sphere(1.0, 9, 7)                       # low-poly -> faceted boulder look
    glPopMatrix()


# ---------------------------------------------------------------------------
# Hill -- an irregular, sun-shaded grassy mound with rocky faces.
#
# A single smooth dome reads as a green blob; real hills have an undulating
# ridgeline, secondary humps and light/shadow across their slopes.  We build a
# lumpy radial height-field once per random seed (with proper per-vertex
# normals so GL_LIGHT0 shades it) and cache it in a display list, then scale an
# instance for each placed hill.
# ---------------------------------------------------------------------------
_HILL_LISTS = {}
_HILL_SEEDS = 6


def reset_hill_cache():
    """Drop the baked hill lists so they re-bake in the new circuit's theme."""
    global _HILL_LISTS
    for lid in _HILL_LISTS.values():
        try:
            glDeleteLists(lid, 1)
        except Exception:
            pass
    _HILL_LISTS = {}


def _v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _v_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _v_norm(v):
    m = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
    return (v[0] / m, v[1] / m, v[2] / m)


def _lerp3(a, b, t):
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)


def _build_hill_list(seed):
    """Compile one lumpy unit hill (base radius ~1, peak height ~1) to a list."""
    rng = random.Random(seed)
    R, A = 24, 40                                   # radial rings, azimuth segs
    # azimuthal ridge undulation (a few low harmonics)
    ridge = [(rng.uniform(0.05, 0.16), rng.randint(2, 5), rng.uniform(0, 6.283))
             for _ in range(3)]
    # a couple of off-centre secondary humps break the dome symmetry
    peaks = []
    for _ in range(rng.randint(1, 3)):
        pu = rng.uniform(0, 6.283)
        pr = rng.uniform(0.22, 0.6)
        peaks.append((pr * math.cos(pu), pr * math.sin(pu),
                      rng.uniform(0.16, 0.38), rng.uniform(0.16, 0.30)))

    def height(rr, u):
        base = math.cos(min(1.0, rr) * math.pi / 2) ** 1.25   # 1 centre -> 0 rim
        r = sum(a * math.sin(k * u + p) for a, k, p in ridge)
        z = base * (1.0 + r * (1.0 - rr))                     # ridge grounded at rim
        x, y = rr * math.cos(u), rr * math.sin(u)
        for px, py, amp, w in peaks:
            d2 = (x - px) ** 2 + (y - py) ** 2
            z += amp * math.exp(-d2 / (2 * w * w)) * (1.0 - rr * rr)
        return max(0.0, z)

    # position grid
    pos = [[(0.0, 0.0, 0.0)] * (A + 1) for _ in range(R + 1)]
    zmax = 1e-6
    for i in range(R + 1):
        rr = i / R
        for j in range(A + 1):
            u = 2 * math.pi * j / A
            z = height(rr, u)
            pos[i][j] = (rr * math.cos(u), rr * math.sin(u), z)
            zmax = max(zmax, z)

    # smooth per-vertex normals from grid neighbours
    nrm = [[(0.0, 0.0, 1.0)] * (A + 1) for _ in range(R + 1)]
    for i in range(R + 1):
        for j in range(A + 1):
            du = _v_sub(pos[i][(j + 1) % A], pos[i][(j - 1) % A])
            dv = _v_sub(pos[min(R, i + 1)][j], pos[max(0, i - 1)][j])
            n = _v_cross(dv, du)
            if n[2] < 0:
                n = (-n[0], -n[1], -n[2])
            nrm[i][j] = _v_norm(n)

    def vcolor(i, j):
        p, n = pos[i][j], nrm[i][j]
        hn = min(1.0, p[2] / zmax)
        col = _lerp3(C.T('hill_low'), C.T('hill_high'), hn ** 0.8)
        slope = 1.0 - max(0.0, min(1.0, n[2]))            # 0 flat .. 1 steep
        col = _lerp3(col, C.COL_HILL_ROCK, min(0.65, slope * 1.1))
        jit = (rng.random() - 0.5) * 0.05
        return (max(0.0, col[0] + jit), max(0.0, col[1] + jit), max(0.0, col[2] + jit))

    lid = glGenLists(1)
    glNewList(lid, GL_COMPILE)
    for i in range(R):
        glBegin(GL_QUAD_STRIP)
        for j in range(A + 1):
            for ii in (i + 1, i):
                c = vcolor(ii, j); n = nrm[ii][j]; p = pos[ii][j]
                glColor3f(*c); glNormal3f(*n); glVertex3f(*p)
        glEnd()
    glEndList()
    return lid


def draw_hill(x, y, radius, height, base_z=0.0):
    seed = (int(x) * 73856093) ^ (int(y) * 19349663)
    key = seed % _HILL_SEEDS
    lid = _HILL_LISTS.get(key)
    if lid is None:
        lid = _build_hill_list(key + 1)
        _HILL_LISTS[key] = lid
    glPushMatrix()
    glTranslatef(x, y, base_z - 8)          # tuck the foot slightly into ground
    glScalef(radius, radius, height)
    glCallList(lid)
    glPopMatrix()


# ---------------------------------------------------------------------------
# Lake -- a flat translucent water disc with a rim, gently shimmering
# ---------------------------------------------------------------------------
def draw_lake(x, y, rx, ry, base_z=0.0):
    glPushMatrix()
    glTranslatef(x, y, base_z + 1.0)
    glScalef(rx, ry, 1.0)
    glNormal3f(0, 0, 1)
    shimmer = 0.5 + 0.5 * math.sin(time.time() * 0.8)
    # sandy/grassy rim
    glColor3f(*C.COL_LAKE_EDGE)
    _flat_disc(1.08, z=-0.6)
    # water surface (slightly translucent so ground tints through)
    glDepthMask(GL_FALSE)
    glColor4f(C.COL_LAKE[0], C.COL_LAKE[1],
              C.COL_LAKE[2] + 0.06 * shimmer, 0.82)
    _flat_disc(1.0, z=0.0)
    # a brighter sky-glint band across the middle
    glColor4f(0.7, 0.85, 0.95, 0.18 + 0.12 * shimmer)
    _flat_disc(0.55, z=0.05)
    glDepthMask(GL_TRUE)
    glPopMatrix()


def _flat_disc(r, z=0.0, seg=40):
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(0, 0, z)
    for i in range(seg + 1):
        a = 2 * math.pi * i / seg
        glVertex3f(r * math.cos(a), r * math.sin(a), z)
    glEnd()


# ---------------------------------------------------------------------------
# Bridge -- railings + pillars where the road spans the lake basin
# ---------------------------------------------------------------------------
def draw_bridge(x, y, angle, length, deck_z, water_z, width=C.ROAD_WIDTH):
    """Side railings along the deck and stone pillars down into the water."""
    glPushMatrix()
    glTranslatef(x, y, 0)
    glRotatef(angle, 0, 0, 1)        # local +X runs along the road
    hw = width / 2
    hl = length / 2

    # railings down both edges
    posts = max(4, int(length / 90))
    for side in (-1, 1):
        sy = side * (hw + 6)
        glColor3f(0.72, 0.72, 0.76)
        for i in range(posts + 1):
            px = -hl + length * i / posts
            glPushMatrix()
            glTranslatef(px, sy, deck_z)
            gfx.box(5, 5, 26)
            glPopMatrix()
        glColor3f(0.86, 0.86, 0.90)   # top rail
        glPushMatrix()
        glTranslatef(0, sy, deck_z + 26)
        gfx.box(hl, 7, 5)
        glPopMatrix()

    # pillars into the water
    glColor3f(0.46, 0.45, 0.44)
    drop = max(20.0, deck_z - water_z)
    for px in (-hl * 0.55, hl * 0.55):
        for py in (-hw * 0.6, hw * 0.6):
            glPushMatrix()
            glTranslatef(px, py, water_z - 10)
            gfx.capped_cylinder(22, drop + 12, slices=10)
            glPopMatrix()
    # deck underside so the span reads as solid from below
    glColor3f(0.30, 0.30, 0.33)
    glPushMatrix()
    glTranslatef(0, 0, deck_z - 9)
    gfx.box(hl, hw, 7)
    glPopMatrix()
    glPopMatrix()


# ---------------------------------------------------------------------------
# Street lamp -- a curved pole with a head that glows after dark
# ---------------------------------------------------------------------------
def draw_street_lamp(x, y, angle, base_z=0.0, night=False):
    """Roadside lamp. At night the head is emissive and throws a soft pool of
    light onto the tarmac, so circuits read clearly in the dark themes."""
    H = C.LAMP_HEIGHT
    glPushMatrix()
    glTranslatef(x, y, base_z)
    glRotatef(angle, 0, 0, 1)          # +X points across, toward the road
    # pole
    glColor3f(0.34, 0.35, 0.38)
    gfx.capped_cylinder(5.0, H, slices=10)
    # curved arm reaching over the verge
    seg = 7
    for i in range(seg):
        t0, t1 = i / seg, (i + 1) / seg
        for (t, r) in ((t0, 4.2), (t1, 4.2)):
            pass
        a0 = t0 * math.pi / 2
        a1 = t1 * math.pi / 2
        R = 52.0
        x0, z0 = R * math.sin(a0), H + R * (1 - math.cos(a0)) * 0.55
        x1, z1 = R * math.sin(a1), H + R * (1 - math.cos(a1)) * 0.55
        glPushMatrix()
        glTranslatef(x0, 0, z0)
        dx, dz = x1 - x0, z1 - z0
        L = math.hypot(dx, dz) or 1.0
        glRotatef(math.degrees(math.atan2(dx, dz)), 0, 1, 0)
        gfx.capped_cylinder(4.0, L, slices=8)
        glPopMatrix()
    # lamp head
    hx, hz = 52.0, H + 52.0 * 0.55
    glPushMatrix()
    glTranslatef(hx, 0, hz - 6)
    glColor3f(0.30, 0.31, 0.34)
    glPushMatrix(); glScalef(1.6, 1.0, 0.5); gfx.sphere(11, 12, 8); glPopMatrix()
    if night:
        gfx.set_emissive((1.0, 0.92, 0.62))
        glColor3f(1.0, 0.95, 0.7)
        glPushMatrix(); glTranslatef(0, 0, -5)
        glScalef(1.3, 0.9, 0.4); gfx.sphere(9, 10, 8); glPopMatrix()
        gfx.clear_emissive()
    glPopMatrix()

    if night:
        # glow halo + pool of light on the road (unlit, additive)
        gfx.lighting(False)
        glDepthMask(GL_FALSE)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glPushMatrix(); glTranslatef(hx, 0, hz - 8)
        glColor4f(1.0, 0.9, 0.55, 0.30)
        gfx.sphere(26, 10, 8)
        glPopMatrix()
        glBegin(GL_TRIANGLE_FAN)          # light pool
        glColor4f(1.0, 0.88, 0.55, 0.16)
        glVertex3f(hx, 0, 1.6)
        glColor4f(1.0, 0.88, 0.55, 0.0)
        for i in range(19):
            t = 2 * math.pi * i / 18
            glVertex3f(hx + 150 * math.cos(t), 150 * math.sin(t), 1.6)
        glEnd()
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthMask(GL_TRUE)
        gfx.lighting(True)
    glPopMatrix()
