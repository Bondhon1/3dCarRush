"""2D overlays: dashboard, minimap, start menu and result screens."""

import math
import time
from OpenGL.GL import *

from . import config as C
from . import gfx


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def draw_dashboard(g):
    gfx.begin_2d(g.width, g.height)
    p = g.player

    x0, y0 = 18, 18
    w, h = 360, 196
    x1, y1 = x0 + w, y0 + h
    gfx.rounded_rect(x0, y0, x1, y1, 14, C.COL_HUD_PANEL)
    gfx.rect_outline(x0, y0, x1, y1, C.COL_HUD_EDGE, 1.6)

    # Speed readout + bar
    num = f"{int(p.speed * 6)}"
    gfx.text(x0 + 18, y1 - 32, num, C.COL_HUD_TEXT)
    gfx.text_small(x0 + 18 + gfx.text_width(num) + 6, y1 - 32, "km/h", C.COL_HUD_DIM)
    view = "COCKPIT" if g.fpv else "CHASE"
    gfx.hbar(x0 + 120, y1 - 36, 148, 12, p.speed / C.BOOST_SPEED, C.COL_HUD_EDGE)
    gfx.text_small(x1 - 74, y1 - 30, view, C.COL_HUD_DIM)

    # Armor pips
    lives_col = C.COL_HUD_GOOD if p.lives >= 5 else C.COL_HUD_BAD
    gfx.text_small(x0 + 18, y1 - 64, "ARMOR", C.COL_HUD_DIM)
    _pips(x0 + 86, y1 - 70, C.PLAYER_MAX_LIVES, p.lives, lives_col, size=13, gap=4)

    # Status chips (boost shows a live recharge bar while on cooldown)
    _boost_indicator(x0 + 18, y1 - 98, p)
    _chip(x0 + 150, y1 - 98, "SHIELD", p.shield_active, C.COL_SHIELD)

    # Live race position
    place, total = g.player_place()
    pcol = C.COL_HUD_GOOD if place == 1 else (C.COL_HUD_WARN if place == 2 else C.COL_HUD_BAD)
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(place, "th")
    gfx.text(x1 - 96, y1 - 66, f"{place}{suffix}", pcol)
    gfx.text_small(x1 - 96, y1 - 84, f"of {total}", C.COL_HUD_DIM)

    # Rival standings (roomy vertical list)
    gfx.text_small(x0 + 18, y1 - 126, "RIVALS", C.COL_HUD_DIM)
    ry = y1 - 146
    for i, e in enumerate(g.enemies):
        # show each rival's role -- the pack is a sprinter, a bruiser and a
        # gunner, and knowing which is which changes how you race them
        chasing = getattr(e, 'catchup', 1.0) > 1.02
        col = C.COL_HUD_WARN if chasing else (0.95, 0.55, 0.5)
        gfx.text_small(x0 + 18, ry - i * 18, getattr(e, 'tag', f"E{i+1}"), col)
        _pips(x0 + 62, ry - 6 - i * 18, getattr(e, 'max_lives', C.ENEMY_MAX_LIVES),
              max(0, e.lives), C.COL_HUD_BAD, size=9, gap=3)

    # transient flash message
    if g.message and time.time() < g.message_until:
        gfx.text_centered(g.width / 2, g.height - 60, g.message, C.COL_HUD_WARN)

    gfx.end_2d()


def _pips(x, y, total, filled, color, size=14, gap=5):
    for i in range(total):
        c = color if i < filled else (0.22, 0.24, 0.28)
        glColor3f(*c)
        px = x + i * (size + gap)
        glBegin(GL_QUADS)
        glVertex2f(px, y); glVertex2f(px + size, y)
        glVertex2f(px + size, y + size * 0.55); glVertex2f(px, y + size * 0.55)
        glEnd()


def _boost_indicator(x, y, p):
    """BOOST readiness: lit while active, a filling bar while recharging,
    'READY' once available again."""
    from . import config as C
    now = time.time()
    if p.boost_active:
        col, label, frac = C.COL_HUD_WARN, "BOOST", 1.0
    elif now < p.boost_cd_until:
        col, label = C.COL_HUD_DIM, "CHARGING"
        frac = 1.0 - (p.boost_cd_until - now) / C.BOOST_COOLDOWN
    else:
        col, label, frac = C.COL_HUD_GOOD, "BOOST", None
    glColor3f(*col)
    glBegin(GL_QUADS)
    glVertex2f(x, y); glVertex2f(x + 12, y)
    glVertex2f(x + 12, y + 12); glVertex2f(x, y + 12)
    glEnd()
    gfx.text_small(x + 18, y, label, col)
    if frac is not None and label == "CHARGING":
        gfx.hbar(x + 18, y - 8, 100, 5, frac, C.COL_HUD_WARN)


def _chip(x, y, label, active, color):
    on = color if active else C.COL_HUD_DIM
    glColor3f(*on)
    glBegin(GL_QUADS)
    glVertex2f(x, y); glVertex2f(x + 12, y)
    glVertex2f(x + 12, y + 12); glVertex2f(x, y + 12)
    glEnd()
    gfx.text_small(x + 18, y, label, on)


# ---------------------------------------------------------------------------
# Minimap (schematic top-down)
# ---------------------------------------------------------------------------
def draw_minimap(g):
    gfx.begin_2d(g.width, g.height)
    size = 220
    pad = 18
    x1 = g.width - pad
    y1 = g.height - pad
    x0 = x1 - size
    y0 = y1 - size
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    gfx.rounded_rect(x0, y0, x1, y1, 14, (0.05, 0.07, 0.10, 0.78))
    gfx.rect_outline(x0, y0, x1, y1, C.COL_HUD_EDGE, 1.6)

    span = 5200.0 * C.TRACK_SCALE        # world units shown across the map
    scale = size / span
    px, py = g.player.pos[0], g.player.pos[1]

    def to_map(wx, wy):
        return cx + (wx - px) * scale, cy + (wy - py) * scale

    def inside(sx, sy):
        return x0 + 4 < sx < x1 - 4 and y0 + 4 < sy < y1 - 4

    # road
    glColor3f(0.4, 0.42, 0.48)
    glPointSize(2.0)
    glBegin(GL_POINTS)
    for (wx, wy) in g.track.mini_points:
        sx, sy = to_map(wx, wy)
        if inside(sx, sy):
            glVertex2f(sx, sy)
    glEnd()
    glPointSize(1.0)

    # finish line
    fx, fy = g.track.finish_line['pos']
    sfx, sfy = to_map(fx, fy)
    if inside(sfx, sfy):
        hw = g.track.finish_line['width'] / 2 * scale
        glColor3f(0.95, 0.95, 0.95)
        glLineWidth(2.0)
        glBegin(GL_LINES)
        glVertex2f(sfx - hw, sfy); glVertex2f(sfx + hw, sfy)
        glEnd()
        glLineWidth(1.0)

    # enemies
    glColor3f(*C.COL_ENEMY_BODY)
    for e in g.enemies:
        sx, sy = to_map(e.pos[0], e.pos[1])
        if inside(sx, sy):
            _dot(sx, sy, 4)

    # player arrow
    a = math.radians(g.player.angle)
    glColor3f(*C.COL_PLAYER_ACCENT)
    glBegin(GL_TRIANGLES)
    for da, r in ((0, 8), (2.4, 5), (-2.4, 5)):
        glVertex2f(cx + r * math.cos(a + da), cy + r * math.sin(a + da))
    glEnd()

    gfx.end_2d()


def _dot(x, y, r):
    glBegin(GL_QUADS)
    glVertex2f(x - r, y - r); glVertex2f(x + r, y - r)
    glVertex2f(x + r, y + r); glVertex2f(x - r, y + r)
    glEnd()


# ---------------------------------------------------------------------------
# Start menu
# ---------------------------------------------------------------------------
def draw_menu(g):
    gfx.begin_2d(g.width, g.height)
    # dim veil over the sky
    glColor4f(0.03, 0.05, 0.08, 0.55)
    glBegin(GL_QUADS)
    glVertex2f(0, 0); glVertex2f(g.width, 0)
    glVertex2f(g.width, g.height); glVertex2f(0, g.height)
    glEnd()

    # Brand logo (loaded once, cached on the game). Falls back to vector text
    # if the asset or texturing is unavailable.
    if not getattr(g, "logo_loaded", False):
        g.logo = gfx.load_texture("assets/logo.png")
        g.logo_loaded = True
    if getattr(g, "logo", None):
        tid, lw, lh = g.logo
        dw = min(520, g.width - 160)
        dh = dw * lh / lw
        logo_bottom = g.height - 34 - dh
        gfx.draw_texture(tid, g.width / 2 - dw / 2, logo_bottom, dw, dh)
        sub_y = logo_bottom - 24
    else:
        gfx.big_text(g.width / 2, g.height - 110, "3D CAR RUSH", 0.42,
                     C.COL_HUD_EDGE, 3.0)
        sub_y = g.height - 150
    gfx.text_centered(g.width / 2, sub_y,
                      "A new circuit is generated every race. Pick your fight.",
                      C.COL_HUD_TEXT)

    # difficulty cards -- the circuit itself is randomised each race
    names = [f"{C.DIFFICULTIES[i]['name']}  ·  {C.DIFFICULTIES[i]['desc']}"
             for i in range(1, C.NUM_LAYOUTS + 1)]
    cw, ch = 460, 52
    cx = g.width / 2
    top = sub_y - (ch + 22)         # `top` is the first card's lower edge
    for i, name in enumerate(names):
        y = top - i * (ch + 12)
        x0, x1 = cx - cw / 2, cx + cw / 2
        sel = (i == g.menu_index)
        bg = (0.10, 0.30, 0.36, 0.92) if sel else (0.08, 0.10, 0.14, 0.85)
        gfx.rounded_rect(x0, y, x1, y + ch, 12, bg)
        gfx.rect_outline(x0, y, x1, y + ch,
                         C.COL_HUD_EDGE if sel else C.COL_HUD_DIM, 2.0 if sel else 1.2)
        gfx.text(x0 + 26, y + ch / 2 - 6, name,
                 C.COL_HUD_TEXT if sel else C.COL_HUD_DIM)
        if sel:
            gfx.text(x1 - 54, y + ch / 2 - 6, "RACE", C.COL_HUD_EDGE)

    gfx.text_centered(g.width / 2, 70,
                      "1-5 or UP/DOWN select      ENTER or CLICK to race",
                      C.COL_HUD_WARN)
    gfx.text_centered(g.width / 2, 44,
                      "Drive WASD    Aim ARROWS    Fire SPACE    View V",
                      C.COL_HUD_DIM)
    gfx.end_2d()


# ---------------------------------------------------------------------------
# Start countdown
# ---------------------------------------------------------------------------
def draw_countdown(g, value):
    if value is None:
        return
    gfx.begin_2d(g.width, g.height)
    go = (value == "GO!")
    col = C.COL_HUD_GOOD if go else C.COL_HUD_WARN
    scale = 1.0 if go else 0.9
    gfx.big_text(g.width / 2, g.height / 2 - 10, value, scale, col, 4.0)
    if not go:
        gfx.text_centered(g.width / 2, g.height / 2 - 80, "GET READY", C.COL_HUD_TEXT)
    gfx.end_2d()


# ---------------------------------------------------------------------------
# Result / pause overlay
# ---------------------------------------------------------------------------
def draw_overlay(g):
    from .engine import WIN, LOSE, ENEMY_WIN, PAUSED
    gfx.begin_2d(g.width, g.height)
    glColor4f(0.02, 0.03, 0.05, 0.6)
    glBegin(GL_QUADS)
    glVertex2f(0, 0); glVertex2f(g.width, 0)
    glVertex2f(g.width, g.height); glVertex2f(0, g.height)
    glEnd()

    if g.state == WIN:
        title, col, sub = "VICTORY", C.COL_HUD_GOOD, "You crossed the line first!"
    elif g.state == LOSE:
        title, col, sub = "WRECKED", C.COL_HUD_BAD, "Out of armor."
    elif g.state == ENEMY_WIN:
        title, col, sub = "DEFEAT", C.COL_HUD_WARN, "A rival finished ahead of you."
    else:
        title, col, sub = "PAUSED", C.COL_HUD_EDGE, "Take a breath."

    gfx.big_text(g.width / 2, g.height / 2 + 20, title, 0.5, col, 3.2)
    gfx.text_centered(g.width / 2, g.height / 2 - 30, sub, C.COL_HUD_TEXT)
    if g.state == PAUSED:
        hint = "P resume   ·   R restart   ·   M menu"
    else:
        hint = "R race again   ·   M main menu"
    gfx.text_centered(g.width / 2, g.height / 2 - 70, hint, C.COL_HUD_DIM)
    gfx.end_2d()
