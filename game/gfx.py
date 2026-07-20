"""Low-level rendering: lighting, materials, atmosphere and lit primitives.

This module is the heart of the visual overhaul. Every 3D primitive here emits
proper surface normals so OpenGL's lighting model gives them real shading and
highlights instead of the flat, unlit look of the legacy game.
"""

import os
import sys
import math
import time as _time
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import (
    glutBitmapCharacter, glutStrokeCharacter,
    GLUT_BITMAP_HELVETICA_18, GLUT_BITMAP_HELVETICA_12,
    GLUT_BITMAP_9_BY_15, GLUT_STROKE_ROMAN,
)

from . import config as C

_quadric = None


def _q():
    """Lazily-created shared GLU quadric with smooth normals + fill."""
    global _quadric
    if _quadric is None:
        _quadric = gluNewQuadric()
        gluQuadricNormals(_quadric, GLU_SMOOTH)
        gluQuadricDrawStyle(_quadric, GLU_FILL)
    return _quadric


# ---------------------------------------------------------------------------
# One-time GL / lighting setup
# ---------------------------------------------------------------------------
def init_gl():
    """Configure depth, shading, lighting and fog once at startup."""
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_NORMALIZE)          # keep normals unit-length under glScalef
    glEnable(GL_COLOR_MATERIAL)     # let glColor drive the diffuse material
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    # A single warm "sun" plus soft sky fill light.
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.35, 0.36, 0.40, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, 0.95, 0.85, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (0.6, 0.6, 0.6, 1.0))

    glEnable(GL_LIGHT1)             # cool fill from the opposite side
    glLightfv(GL_LIGHT1, GL_AMBIENT, (0.0, 0.0, 0.0, 1.0))
    glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.18, 0.22, 0.34, 1.0))
    glLightfv(GL_LIGHT1, GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))

    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.25, 0.25, 0.25, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 24.0)

    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.25, 0.25, 0.28, 1.0))
    glEnable(GL_RESCALE_NORMAL)

    # Distance fog blends the far world into the horizon haze.
    glEnable(GL_FOG)
    glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogf(GL_FOG_START, 1400.0)
    glFogf(GL_FOG_END, 5200.0)

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_LINE_SMOOTH)
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
    apply_theme()


def apply_theme():
    """Push the active circuit theme into the fixed GL state (fog + clear)."""
    glFogfv(GL_FOG_COLOR, (*C.T('fog'), 1.0))
    glClearColor(*C.T('sky_horizon'), 1.0)


def place_lights():
    """Position lights each frame (call after the camera is set)."""
    glLightfv(GL_LIGHT0, GL_POSITION, (0.4, 0.5, 1.0, 0.0))   # directional sun
    glLightfv(GL_LIGHT1, GL_POSITION, (-0.5, -0.4, 0.6, 0.0))


def set_emissive(color):
    """Make the next primitive glow (self-lit). Reset with clear_emissive()."""
    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (*color, 1.0))


def clear_emissive():
    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))


def lighting(enabled):
    (glEnable if enabled else glDisable)(GL_LIGHTING)


# ---------------------------------------------------------------------------
# Textures (used for the menu logo). Everything degrades to None on failure so
# the menu can fall back to vector text.
# ---------------------------------------------------------------------------
def resource_path(rel):
    """Resolve a bundled asset both when run from source and from a frozen
    PyInstaller exe (which unpacks data files to ``sys._MEIPASS``)."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        p = os.path.join(base, rel)
        if os.path.exists(p):
            return p
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, rel)


def load_texture(rel):
    """Load an image asset into a GL texture. Returns (tex_id, w, h) or None."""
    try:
        import pygame
        surf = pygame.image.load(resource_path(rel))
        w, h = surf.get_size()
        data = pygame.image.tostring(surf, "RGBA", True)   # flipped for GL
        tid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tid)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, data)
        glBindTexture(GL_TEXTURE_2D, 0)
        return tid, w, h
    except Exception:
        return None


def draw_texture(tid, x, y, w, h, alpha=1.0):
    """Draw a textured quad in the current 2D overlay (call inside begin_2d)."""
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tid)
    glColor4f(1.0, 1.0, 1.0, alpha)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(x, y)
    glTexCoord2f(1, 0); glVertex2f(x + w, y)
    glTexCoord2f(1, 1); glVertex2f(x + w, y + h)
    glTexCoord2f(0, 1); glVertex2f(x, y + h)
    glEnd()
    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_TEXTURE_2D)


# ---------------------------------------------------------------------------
# Lit primitives (all with normals)
# ---------------------------------------------------------------------------
def box(sx, sy, sz):
    """Axis-aligned box centred on the origin, spanning +/- s on each axis."""
    x, y, z = sx, sy, sz
    faces = (
        # (normal), (four corners)
        ((0, 0, 1), ((-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z))),
        ((0, 0, -1), ((-x, -y, -z), (-x, y, -z), (x, y, -z), (x, -y, -z))),
        ((1, 0, 0), ((x, -y, -z), (x, y, -z), (x, y, z), (x, -y, z))),
        ((-1, 0, 0), ((-x, -y, -z), (-x, -y, z), (-x, y, z), (-x, y, -z))),
        ((0, 1, 0), ((-x, y, -z), (-x, y, z), (x, y, z), (x, y, -z))),
        ((0, -1, 0), ((-x, -y, -z), (x, -y, -z), (x, -y, z), (-x, -y, z))),
    )
    glBegin(GL_QUADS)
    for normal, verts in faces:
        glNormal3f(*normal)
        for v in verts:
            glVertex3f(*v)
    glEnd()


def unit_cube(size=1.0):
    box(size, size, size)


def cylinder(radius, height, slices=20):
    gluCylinder(_q(), radius, radius, height, slices, 1)


def tapered_cylinder(r_bottom, r_top, height, slices=20):
    gluCylinder(_q(), r_bottom, r_top, height, slices, 1)


def cone(radius, height, slices=20):
    gluCylinder(_q(), radius, 0.0, height, slices, 1)


def disk(inner, outer, slices=24):
    gluDisk(_q(), inner, outer, slices, 1)


def sphere(radius, slices=18, stacks=14):
    gluSphere(_q(), radius, slices, stacks)


def capped_cylinder(radius, height, slices=20):
    """A cylinder drawn along +Z with both ends closed off."""
    q = _q()
    gluCylinder(q, radius, radius, height, slices, 1)
    gluDisk(q, 0, radius, slices, 1)          # bottom cap
    glPushMatrix()
    glTranslatef(0, 0, height)
    gluDisk(q, 0, radius, slices, 1)          # top cap
    glPopMatrix()


# ---------------------------------------------------------------------------
# Atmosphere: gradient sky + ground plane
# ---------------------------------------------------------------------------
def draw_sky(width, height, horizon_frac=0.55, yaw=0.0):
    """Full-screen vertical gradient drawn behind everything else.

    ``yaw`` (the camera heading, degrees) scrolls the sun and clouds like a
    distant panorama so they parallax as you turn instead of feeling painted on.
    """
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glDisable(GL_FOG)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, width, 0, height, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    hy = height * horizon_frac
    top = C.T('sky_top')
    hor = C.T('sky_horizon')
    glBegin(GL_QUADS)
    # upper sky: top colour -> horizon colour
    glColor3f(*top);  glVertex2f(0, height);   glVertex2f(width, height)
    glColor3f(*hor);  glVertex2f(width, hy);   glVertex2f(0, hy)
    glEnd()
    # lower band: horizon haze -> a touch darker toward the bottom edge
    fog = C.T('fog')
    glBegin(GL_QUADS)
    glColor3f(*hor);  glVertex2f(0, hy);       glVertex2f(width, hy)
    glColor3f(*fog);  glVertex2f(width, 0);    glVertex2f(0, 0)
    glEnd()

    # Panorama scroll. One full car rotation scrolls the sky exactly once
    # (natural parallax), and a slow, continuous wind term drifts the clouds
    # even when the view is still -- this is what fixes the "clouds look weird
    # in movement" jitter: motion is now smooth and wrapping is seamless.
    period = width * 3.0
    yaw_shift = ((yaw % 360.0) / 360.0) * period
    wind = (_time.time() * 12.0) % period

    # low sun glow near the horizon (parallaxes with the view, no wind)
    sun_y = hy + height * 0.09
    _draw_wrapped(width * 0.62, yaw_shift, period, width, sun_y, _draw_sun, height)

    # Soft layered clouds. Each has a stable azimuth + height + size; near
    # clouds (bigger) drift a touch faster than far ones for gentle depth.
    for az, cyf, s, par in _CLOUDS:
        shift = yaw_shift * par + wind * (0.6 + 0.4 * par)
        _draw_wrapped(width * az, shift, period, width,
                      height * cyf, _cloud, height * 0.05 * s)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_LIGHTING)
    glEnable(GL_FOG)
    glEnable(GL_DEPTH_TEST)


def _set_col(c):
    (glColor4f if len(c) == 4 else glColor3f)(*c)


def _radial(cx, cy, r, inner, outer):
    """Filled radial gradient disc (sun glow / clouds); colors may be rgb or rgba."""
    glBegin(GL_TRIANGLE_FAN)
    _set_col(inner)
    glVertex2f(cx, cy)
    _set_col(outer)
    seg = 24
    for i in range(seg + 1):
        a = i / seg * 2 * math.pi
        glVertex2f(cx + r * math.cos(a), cy + r * math.sin(a))
    glEnd()


# Persistent cloud field: (azimuth fraction, height fraction, size, parallax).
# Spread around a 3x-width panorama so turning keeps revealing fresh sky.
_CLOUDS = (
    (0.05, 0.87, 1.10, 1.00), (0.28, 0.92, 0.75, 0.85), (0.52, 0.84, 1.00, 1.00),
    (0.74, 0.90, 0.65, 0.80), (0.95, 0.86, 0.95, 0.95), (1.20, 0.91, 0.80, 0.85),
    (1.45, 0.83, 1.15, 1.00), (1.70, 0.89, 0.70, 0.82), (1.95, 0.87, 0.90, 0.92),
    (2.20, 0.93, 0.72, 0.80), (2.48, 0.85, 1.05, 1.00), (2.75, 0.90, 0.68, 0.83),
)


def _draw_wrapped(base, shift, period, width, y, fn, arg, margin=260):
    """Draw ``fn(x, y, arg)`` at a scrolled x, tiling across the seam so a
    cloud/sun leaving one edge reappears at the other with no pop."""
    cx = (base - shift) % period
    for xp in (cx - period, cx, cx + period):
        if -margin < xp < width + margin:
            fn(xp, y, arg)


def _draw_sun(cx, cy, height):
    s = C.T('sun')
    _radial(cx, cy, height * 0.18, (*s, 0.5), (*s, 0.0))
    _radial(cx, cy, height * 0.055, (1.0, 0.97, 0.86, 0.95), (*s, 0.0))


def _cloud(cx, cy, r):
    """A soft puffy cloud built from overlapping feathered blobs.

    Low peak alpha + many wide lobes keeps edges gentle so the cloud reads as
    a smooth mass rather than a cluster of hard discs while it drifts."""
    lobes = ((-1.7, -0.05, 0.85), (-0.9, 0.18, 1.05), (0.0, 0.28, 1.25),
             (0.9, 0.15, 1.05), (1.7, -0.05, 0.9), (-0.3, -0.2, 0.95),
             (0.5, -0.22, 0.9))
    for dx, dy, s in lobes:
        _radial(cx + dx * r, cy + dy * r, r * s * 1.9,
                (1.0, 1.0, 1.0, 0.16), (1.0, 1.0, 1.0, 0.0))


_ground_list = None


def reset_ground_cache():
    """Drop the baked ground mesh (call when the terrain or theme changes)."""
    global _ground_list
    if _ground_list is not None:
        try:
            glDeleteLists(_ground_list, 1)
        except Exception:
            pass
        _ground_list = None


def draw_ground(size=8000 * C.TRACK_SCALE, tile=None, height=None):
    """Baked terrain mesh.

    IMPORTANT: the tiles must be small relative to the hill wavelength.  A
    coarse mesh interpolates each quad as a flat chord across a curved hill,
    which can bulge tens of units ABOVE the true surface -- enough for the
    grass to poke up through the road.  Fine tiles keep that error well under
    GROUND_DROP, and baking into a display list makes the extra geometry free.
    """
    global _ground_list
    if _ground_list is None:
        _ground_list = glGenLists(1)
        glNewList(_ground_list, GL_COMPILE)
        _emit_ground(size, tile or C.GROUND_TILE, height)
        glEndList()
    glCallList(_ground_list)


def _emit_ground(size, tile, height):
    """A large lit grass plane with a subtle checker so motion reads clearly.

    ``size`` follows TRACK_SCALE so the grass always extends past the enlarged
    circuit (no void under distant road); the checker keeps a constant tile
    size so its density looks the same at any scale.  ``height`` is the track's
    terrain function -- passing it rolls the grass with the hills so the road
    never floats above or sinks into flat ground."""
    g1 = C.T('ground')
    g2 = tuple(min(1.0, c + 0.05) for c in g1)
    h = height or (lambda x, y: 0.0)
    step = tile

    def vert(vx, vy):
        # normal from the local gradient so the hills actually catch the light
        nx = (h(vx + 40, vy) - h(vx - 40, vy)) / 80.0
        ny = (h(vx, vy + 40) - h(vx, vy - 40)) / 80.0
        nl = math.sqrt(nx * nx + ny * ny + 1.0)
        glNormal3f(-nx / nl, -ny / nl, 1.0 / nl)
        glVertex3f(vx, vy, h(vx, vy) - C.GROUND_DROP)

    y = -size
    row = 0
    glBegin(GL_QUADS)
    while y < size:
        x = -size
        col = row
        while x < size:
            glColor3f(*(g1 if (col + row) % 2 == 0 else g2))
            vert(x, y)
            vert(x + step, y)
            vert(x + step, y + step)
            vert(x, y + step)
            x += step
            col += 1
        y += step
        row += 1
    glEnd()


# ---------------------------------------------------------------------------
# 2D overlay helpers (HUD / menus)
# ---------------------------------------------------------------------------
def begin_2d(width, height):
    """Enter a pixel-space orthographic overlay (lighting/fog/depth off)."""
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glDisable(GL_FOG)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, width, 0, height)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()


def end_2d():
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_FOG)
    glEnable(GL_LIGHTING)
    glEnable(GL_DEPTH_TEST)


def rounded_rect(x0, y0, x1, y1, r, color):
    """Filled rectangle with softened corners (approximated by chamfers)."""
    if len(color) == 4:
        glColor4f(*color)
    else:
        glColor3f(*color)
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    glBegin(GL_POLYGON)
    steps = 5
    corners = [
        (x1 - r, y0 + r, -math.pi / 2, 0),
        (x1 - r, y1 - r, 0, math.pi / 2),
        (x0 + r, y1 - r, math.pi / 2, math.pi),
        (x0 + r, y0 + r, math.pi, 3 * math.pi / 2),
    ]
    for cx, cy, a0, a1 in corners:
        for i in range(steps + 1):
            a = a0 + (a1 - a0) * i / steps
            glVertex2f(cx + r * math.cos(a), cy + r * math.sin(a))
    glEnd()


def rect_outline(x0, y0, x1, y1, color, width=2.0):
    glColor3f(*color[:3])
    glLineWidth(width)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x0, y0); glVertex2f(x1, y0)
    glVertex2f(x1, y1); glVertex2f(x0, y1)
    glEnd()
    glLineWidth(1.0)


def hbar(x, y, w, h, frac, color, bg=(0.16, 0.18, 0.22)):
    """Horizontal progress bar (frac in 0..1)."""
    frac = max(0.0, min(1.0, frac))
    glColor3f(*bg)
    glBegin(GL_QUADS)
    glVertex2f(x, y); glVertex2f(x + w, y)
    glVertex2f(x + w, y + h); glVertex2f(x, y + h)
    glEnd()
    glColor3f(*color[:3])
    glBegin(GL_QUADS)
    glVertex2f(x, y); glVertex2f(x + w * frac, y)
    glVertex2f(x + w * frac, y + h); glVertex2f(x, y + h)
    glEnd()


def text(x, y, s, color=(1, 1, 1), font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(*color[:3])
    glRasterPos2f(x, y)
    for ch in s:
        glutBitmapCharacter(font, ord(ch))


def text_small(x, y, s, color=(1, 1, 1)):
    text(x, y, s, color, GLUT_BITMAP_HELVETICA_12)


def text_mono(x, y, s, color=(1, 1, 1)):
    text(x, y, s, color, GLUT_BITMAP_9_BY_15)


def text_width(s, font=GLUT_BITMAP_HELVETICA_18):
    from OpenGL.GLUT import glutBitmapWidth
    return sum(glutBitmapWidth(font, ord(ch)) for ch in s)


def text_centered(cx, y, s, color=(1, 1, 1), font=GLUT_BITMAP_HELVETICA_18):
    text(cx - text_width(s, font) / 2, y, s, color, font)


def big_text(cx, y, s, scale, color=(1, 1, 1), width=2.4):
    """Vector stroke text for headlines that need to scale up crisply."""
    glColor3f(*color[:3])
    total = sum(_stroke_width(ch) for ch in s) * scale
    glPushMatrix()
    glTranslatef(cx - total / 2, y, 0)
    glScalef(scale, scale, scale)
    glLineWidth(width)
    for ch in s:
        glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(ch))
    glLineWidth(1.0)
    glPopMatrix()


def _stroke_width(ch):
    from OpenGL.GLUT import glutStrokeWidth
    return glutStrokeWidth(GLUT_STROKE_ROMAN, ord(ch))
