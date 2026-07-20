"""Track building: procedurally generated circuits.

Every race cuts a brand-new circuit.  A randomised *radial* polygon (vertices
sorted by angle, so it can never cross itself) is relaxed until every corner is
drivable, then filleted into real sweeping bends by ``_polygon_circuit``.  The
chosen difficulty controls how many corners it has and how irregular they are,
and the builder also hands back the centre-line racing line the AI follows, the
grid/start heading, and the placement of the finish line and speed breakers.

Geometry is emitted as lit surfaces with striped 3D kerbs and weathered asphalt,
compiled into one display list so the static world costs a single call a frame.
"""

import math
import random
from OpenGL.GL import *

from . import config as C
from . import gfx


KERB_SEG = 55.0          # length of one red/white kerb stripe
LANE_DASH = 46.0
LANE_GAP = 34.0


def _round(v, step):
    return int(round(v / step) * step)


class Track:
    def __init__(self):
        self.road_points = set()      # coarse grid, for pickup spawning
        self.border_points = set()    # dense 8-grid, for wall collision
        self.pieces = []              # geometry specs for rendering
        self.finish_line = None       # {'pos': (x, y), 'angle', 'width'}
        self.speed_breakers = []      # [(x, y, width, depth)]
        self.mini_points = []         # down-sampled road points for the minimap
        self.layout_id = 1            # difficulty level this circuit was cut for
        self._list = None
        # pre-generated surface damage (positions kept so gameplay can react)
        self.potholes = []            # [(x, y, r, outline_pts)]
        self.patches = []             # [(x, y, hw, hh)]
        self.cracks = []              # [(polyline_pts, width)]
        self.auto_waypoints = []      # centre-line racing line (scaled)
        self._edges = []              # straights between filleted corners
        self._start_edge = None
        self.start_raw = (0.0, 0.0)   # unscaled grid position
        self.start_pos = (0.0, 0.0)   # scaled world position of the grid
        self.start_angle = 90.0       # heading the cars line up on
        # terrain height field (flat until _init_elevation runs)
        self.elev_amp = 0.0
        self.e_k1 = self.e_k2 = self.e_k3 = 0.001
        self.e_p1 = self.e_p2 = self.e_p3 = 0.0
        self.bridge = None            # (x, y, angle, length) scaled, or None
        self.deck_z = 0.0             # level of the (flat) bridge deck
        self.bowl = None              # (x, y, radius, depth) lake basin under it

    # -- public API --------------------------------------------------------
    def build(self, difficulty, seed=None):
        """Generate a brand-new random circuit tuned to ``difficulty``."""
        self.__init__()
        self.layout_id = difficulty
        rng = random.Random(seed if seed is not None else random.randrange(1 << 30))
        self._seed = seed
        self._init_elevation(difficulty, rng)
        self._generate(difficulty, rng)
        self._place_start_and_furniture(difficulty, rng)
        # Scale the markers to match the enlarged geometry. Their WIDTH/DEPTH
        # stay unscaled (road width is fixed).
        S = C.TRACK_SCALE
        fx, fy = self.finish_line['pos']
        self.finish_line['pos'] = (fx * S, fy * S)
        self.start_pos = (self.start_raw[0] * S, self.start_raw[1] * S)
        self.speed_breakers = [(x * S, y * S, w, d, a)
                               for (x, y, w, d, a) in self.speed_breakers]
        if self.bridge_raw:
            bx, by, ba, blen = self.bridge_raw
            self.bridge = (bx * S, by * S, ba, blen * S)
            # deck sits level with the terrain at the span's midpoint
            self.deck_z = self._base_height(bx * S, by * S)
            ox, oy, orr, od = self.bowl_raw
            self.bowl = (ox * S, oy * S, orr * S, od)
        self._generate_damage(C.DIFFICULTIES[difficulty]['damage_scale'])
        self.mini_points = list(self.road_points)[::4]

    def draw(self):
        if self._list is None:
            self._list = glGenLists(1)
            glNewList(self._list, GL_COMPILE)
            self._emit()
            glEndList()
        glCallList(self._list)

    def dispose(self):
        if self._list is not None:
            glDeleteLists(self._list, 1)
            self._list = None

    # -- terrain elevation --------------------------------------------------
    # The world is no longer flat: a smooth 2-D height field rolls the whole
    # landscape (road, ground and scenery all read from it), so circuits climb
    # and drop.  It is a closed-form function, so height_at() is cheap enough
    # to call per-vertex while baking and per-frame for the cars.
    def _base_height(self, x, y):
        a = self.elev_amp
        if a <= 0.0:
            return 0.0
        return a * (math.sin(x * self.e_k1 + self.e_p1) *
                    math.cos(y * self.e_k2 + self.e_p2)
                    + 0.55 * math.sin((x + y) * self.e_k3 + self.e_p3))

    def height_at(self, x, y):
        """Height of the ROAD surface.

        Flat across the bridge span: a real bridge deck is level, and letting
        the road undulate under a deck drawn at one fixed height is what made
        the bridge structure sit above the tarmac and swallow the car."""
        h = self._base_height(x, y)
        if self.bridge is None:
            return h
        bx, by, ba, blen = self.bridge
        a = math.radians(ba)
        ca, sa = math.cos(a), math.sin(a)
        along = (x - bx) * ca + (y - by) * sa
        half = blen * 0.5
        ramp = half * 0.45                     # ease back onto the terrain
        d = abs(along)
        if d > half + ramp:
            return h
        t = 1.0 if d <= half else 1.0 - (d - half) / ramp
        t = t * t * (3 - 2 * t)                # smoothstep
        return h + (self.deck_z - h) * t

    def ground_height_at(self, x, y):
        """Terrain height for the LANDSCAPE (grass + scenery).

        Identical to the road height except inside the bridge bowl, where the
        ground scoops away into a lake basin.  Keeping the two separate is what
        lets the road stay level and span the water as a real bridge instead of
        diving into it."""
        h = self._base_height(x, y)
        if self.bowl:
            bx, by, br, bd = self.bowl
            d2 = (x - bx) ** 2 + (y - by) ** 2
            if d2 < br * br:
                t = 1.0 - d2 / (br * br)
                h -= bd * t * t
        return h

    def slope_along(self, x, y, dx, dy, probe=60.0):
        """Gradient (rise/run) heading in direction (dx, dy) from (x, y)."""
        if self.elev_amp <= 0.0:
            return 0.0
        h0 = self.height_at(x, y)
        h1 = self.height_at(x + dx * probe, y + dy * probe)
        return (h1 - h0) / probe

    def _init_elevation(self, difficulty, rng):
        d = C.DIFFICULTIES[difficulty]
        self.elev_amp = C.ELEV_BASE_AMP * d['elev']
        # wavelengths long enough that hills are gentle sweeps, not ripples
        self.e_k1 = 2 * math.pi / rng.uniform(*C.ELEV_WAVELEN)
        self.e_k2 = 2 * math.pi / rng.uniform(*C.ELEV_WAVELEN)
        self.e_k3 = 2 * math.pi / rng.uniform(*C.ELEV_WAVELEN)
        self.e_p1 = rng.uniform(0, 6.283)
        self.e_p2 = rng.uniform(0, 6.283)
        self.e_p3 = rng.uniform(0, 6.283)

    def is_on_road(self, x, y, radius2=12000):
        for rx, ry in self.road_points:
            if (x - rx) ** 2 + (y - ry) ** 2 < radius2:
                return True
        return False

    def hits_border(self, x, y):
        gx, gy = _round(x, C.GRID), _round(y, C.GRID)
        for dx in (-C.GRID, 0, C.GRID):
            for dy in (-C.GRID, 0, C.GRID):
                if (gx + dx, gy + dy) in self.border_points:
                    return True
        return False

    # -- collision-set helpers --------------------------------------------
    def _fill_rect(self, xmin, xmax, ymin, ymax, store, step):
        xmin, xmax = int(min(xmin, xmax)), int(max(xmin, xmax))
        ymin, ymax = int(min(ymin, ymax)), int(max(ymin, ymax))
        x = _round(xmin, step)
        while x <= xmax:
            y = _round(ymin, step)
            while y <= ymax:
                store.add((x, y))
                y += step
            x += step

    def _fill_arc(self, cx, cy, r0, r1, a0, a1, store, step, dr=8):
        r = r0
        while r <= r1:
            steps = max(8, int(abs(a1 - a0) * r / step))
            for i in range(steps + 1):
                a = a0 + (a1 - a0) * i / steps
                x = _round(cx + r * math.cos(a), step)
                y = _round(cy + r * math.sin(a), step)
                store.add((x, y))
            r += dr

    # -- piece builders (collision now, geometry later) -------------------
    # Every builder scales its POSITIONS, LENGTHS and RADII by TRACK_SCALE so
    # the whole circuit enlarges uniformly.  Road *width* is deliberately left
    # unscaled -- all pieces share it, so their joints still line up while the
    # laps get bigger and the corners sweep wider.
    def _straight(self, cx, start_y, length, width=C.ROAD_WIDTH):
        S = C.TRACK_SCALE
        cx, start_y, length = cx * S, start_y * S, length * S
        hw = width / 2
        end_y = start_y + length
        self._fill_rect(cx - hw, cx + hw, start_y, end_y, self.road_points, 20)
        for ex in (cx - hw, cx + hw):
            self._fill_rect(ex - C.BORDER_THICKNESS, ex + C.BORDER_THICKNESS,
                            start_y, end_y, self.border_points, C.GRID)
        self.pieces.append(('straight', cx, start_y, length, width))

    def _horizontal(self, cy, start_x, length, width=C.ROAD_WIDTH):
        S = C.TRACK_SCALE
        cy, start_x, length = cy * S, start_x * S, length * S
        hw = width / 2
        end_x = start_x + length
        self._fill_rect(start_x, end_x, cy - hw, cy + hw, self.road_points, 20)
        for ey in (cy - hw, cy + hw):
            self._fill_rect(start_x, end_x, ey - C.BORDER_THICKNESS,
                            ey + C.BORDER_THICKNESS, self.border_points, C.GRID)
        self.pieces.append(('horizontal', cy, start_x, length, width))

    def _curve(self, cx, cy, radius, a0, a1, x_shift=0, width=C.ROAD_WIDTH):
        S = C.TRACK_SCALE
        cx, cy, radius, x_shift = cx * S, cy * S, radius * S, x_shift * S
        cx += x_shift
        hw = width / 2
        self._fill_arc(cx, cy, radius - hw, radius + hw, a0, a1,
                       self.road_points, 20)
        for r in (radius - hw, radius + hw):
            self._fill_arc(cx, cy, r - C.BORDER_THICKNESS, r + C.BORDER_THICKNESS,
                           a0, a1, self.border_points, C.GRID)
        self.pieces.append(('curve', cx, cy, radius, a0, a1, width))

    def _corner(self, X, Y, sx, sy, radius=200):
        """Emit a 90-degree arc joining a vertical road at x=X to a horizontal
        road at y=Y.

        ``sx`` is the direction the HORIZONTAL leg runs away from the corner
        (+1 = toward +X), ``sy`` the direction the VERTICAL leg runs (+1 = +Y).
        The arc therefore meets the vertical road at y = Y + sy*radius and the
        horizontal road at x = X + sx*radius -- author legs to those endpoints
        and the circuit is guaranteed to join up.  Coordinates are unscaled;
        ``_curve`` applies TRACK_SCALE.
        """
        cx, cy = X + sx * radius, Y + sy * radius
        a_v = math.pi if sx > 0 else 0.0            # point on the vertical leg
        a_h = -math.pi / 2 if sy > 0 else math.pi / 2   # point on the horizontal leg
        d = a_h - a_v
        while d > math.pi:
            d -= 2 * math.pi
        while d < -math.pi:
            d += 2 * math.pi
        self._curve(cx, cy, radius, a_v, a_v + d)

    def _segment(self, x0, y0, x1, y1, width=C.ROAD_WIDTH):
        """A straight running in ANY direction (not just axis-aligned).

        This is what lets circuits leave the grid and use diagonals, so corners
        no longer have to be 90 degrees."""
        S = C.TRACK_SCALE
        x0, y0, x1, y1 = x0 * S, y0 * S, x1 * S, y1 * S
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        if L < 1:
            return
        ux, uy = dx / L, dy / L
        px, py = -uy, ux                       # across the road
        hw = width / 2
        n = max(1, int(L / 20))
        m = max(1, int(hw / 20))
        for i in range(n + 1):
            t = i / n
            bx, by = x0 + dx * t, y0 + dy * t
            for j in range(-m, m + 1):
                o = j * 20
                self.road_points.add((_round(bx + px * o, 20),
                                      _round(by + py * o, 20)))
        nb = max(1, int(L / C.GRID))
        for side in (-1, 1):
            for i in range(nb + 1):
                t = i / nb
                bx, by = x0 + dx * t, y0 + dy * t
                k = -C.BORDER_THICKNESS
                while k <= C.BORDER_THICKNESS:
                    o = hw * side + k
                    self.border_points.add((_round(bx + px * o, C.GRID),
                                            _round(by + py * o, C.GRID)))
                    k += C.GRID
        self.pieces.append(('segment', x0, y0, x1, y1, width))

    def _polygon_circuit(self, pts, radius=300, width=C.ROAD_WIDTH):
        """Build a closed circuit through ``pts`` with every corner filleted.

        Because the shape is a closed polygon the circuit is guaranteed to join
        up, and because each corner is rounded by a tangent arc the turn angles
        can be ANYTHING -- gentle sweepers, chicane kinks or tight hairpins --
        instead of the 90-degree grid the older layouts were locked to.

        Also records the centre-line racing line in ``auto_waypoints`` (scaled),
        so the AI follows the real road rather than the raw polygon corners
        (which can sit off the tarmac on sharp bends).
        """
        S = C.TRACK_SCALE
        n = len(pts)
        fil = []
        for i in range(n):
            p, c, q = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
            v1 = (p[0] - c[0], p[1] - c[1])
            v2 = (q[0] - c[0], q[1] - c[1])
            l1 = math.hypot(*v1) or 1.0
            l2 = math.hypot(*v2) or 1.0
            u1 = (v1[0] / l1, v1[1] / l1)
            u2 = (v2[0] / l2, v2[1] / l2)
            dot = max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))
            theta = math.acos(dot)                 # interior angle at the corner
            if theta < 0.05 or abs(theta - math.pi) < 0.05:
                fil.append(None)                   # effectively straight through
                continue
            t = radius / math.tan(theta / 2)
            t = min(t, l1 * 0.45, l2 * 0.45)       # keep arcs off each other
            r = t * math.tan(theta / 2)
            if t < 5 or r < 5:
                fil.append(None)
                continue
            T1 = (c[0] + u1[0] * t, c[1] + u1[1] * t)
            T2 = (c[0] + u2[0] * t, c[1] + u2[1] * t)
            bx, by = u1[0] + u2[0], u1[1] + u2[1]
            bl = math.hypot(bx, by) or 1.0
            d = r / math.sin(theta / 2)
            cc = (c[0] + bx / bl * d, c[1] + by / bl * d)
            a0 = math.atan2(T1[1] - cc[1], T1[0] - cc[0])
            a1 = math.atan2(T2[1] - cc[1], T2[0] - cc[0])
            da = a1 - a0
            while da > math.pi:
                da -= 2 * math.pi
            while da < -math.pi:
                da += 2 * math.pi
            fil.append((T1, T2, cc, a0, a0 + da, r))

        for f in fil:
            if f:
                T1, T2, cc, a0, a1, r = f
                self._curve(cc[0], cc[1], r, a0, a1, width=width)
        self._edges = []
        for i in range(n):
            cur, nxt = fil[i], fil[(i + 1) % n]
            start = cur[1] if cur else pts[i]
            end = nxt[0] if nxt else pts[(i + 1) % n]
            self._edges.append((start, end))
            self._segment(start[0], start[1], end[0], end[1], width)
        self._start_edge = self._edges[0]

        # racing line: leave corner 0, run the loop, come back through corner 0
        wps = []

        def arc_mid(f):
            _, _, cc, a0, a1, r = f
            am = (a0 + a1) / 2
            return (cc[0] + r * math.cos(am), cc[1] + r * math.sin(am))

        wps.append(fil[0][1] if fil[0] else pts[0])
        for i in range(1, n):
            f = fil[i]
            if f:
                wps.extend([f[0], arc_mid(f), f[1]])
            else:
                wps.append(pts[i])
        if fil[0]:
            wps.extend([fil[0][0], arc_mid(fil[0])])
        self.auto_waypoints = [(x * S, y * S, 10) for (x, y) in wps]

    # -- geometry emission -------------------------------------------------
    def _emit(self):
        for p in self.pieces:
            kind = p[0]
            if kind == 'straight':
                self._emit_straight(*p[1:])
            elif kind == 'horizontal':
                self._emit_horizontal(*p[1:])
            elif kind == 'curve':
                self._emit_curve(*p[1:])
            elif kind == 'segment':
                self._emit_segment(*p[1:])
        self._draw_damage()               # wear sits on top of all the paint
        if self.finish_line:
            self._emit_finish(self.finish_line)

    def _quad(self, verts, color, nz=(0, 0, 1)):
        """Emit a quad, lifting every vertex onto the terrain height field."""
        glColor3f(*color)
        glNormal3f(*nz)
        glBegin(GL_QUADS)
        for v in verts:
            glVertex3f(v[0], v[1], v[2] + self.height_at(v[0], v[1]))
        glEnd()

    # -- broken / weathered asphalt -----------------------------------------
    # All damage is baked into the display list (zero per-frame cost) and is
    # driven by a seeded RNG so a given circuit always wears the same way.
    # Drawn just above the lane paint (z=0.7) so holes and cracks visibly cut
    # through the markings, the way real broken road does.
    _DMG_Z = 2.2

    # --- generation (at build time, so gameplay can collide with potholes) ---
    def _gen_cluster(self, cx, cy, rng, big=True):
        """One damage cluster: a ragged hole plus a few radiating cracks."""
        r = rng.uniform(11, 26) if big else rng.uniform(9, 19)
        pts = []
        seg = 10
        for i in range(seg):
            a = 2 * math.pi * i / seg
            rr = r * rng.uniform(0.62, 1.18)
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        self.potholes.append((cx, cy, r, pts))
        for _ in range(rng.randint(2, 4)):
            ang = rng.uniform(0, 2 * math.pi)
            length = rng.uniform(50, 130)
            n = rng.randint(3, 6)
            seg_len = length / n
            poly = [(cx, cy)]
            px, py = cx, cy
            for _ in range(n):
                a = ang + rng.uniform(-0.55, 0.55)
                px, py = px + seg_len * math.cos(a), py + seg_len * math.sin(a)
                poly.append((px, py))
            self.cracks.append((poly, 3.2))

    def _gen_damage_rect(self, x0, x1, y0, y1, rng):
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        inset = 34.0
        if x1 - x0 < 2 * inset or y1 - y0 < 2 * inset:
            return
        area = (x1 - x0) * (y1 - y0)
        for _ in range(int(area / C.ROAD_PATCH_AREA)):
            self.patches.append((rng.uniform(x0 + inset, x1 - inset),
                                 rng.uniform(y0 + inset, y1 - inset),
                                 rng.uniform(26, 60), rng.uniform(26, 60)))
        for _ in range(int(area / self._dmg_area)):
            self._gen_cluster(rng.uniform(x0 + inset, x1 - inset),
                              rng.uniform(y0 + inset, y1 - inset), rng)

    def _gen_damage_arc(self, cx, cy, r_in, r_out, a0, a1, rng):
        span = abs(a1 - a0) * (r_in + r_out) / 2
        area = span * (r_out - r_in)
        pad = 30.0
        if r_out - r_in < 2 * pad:
            return
        for _ in range(int(area / self._dmg_area)):
            a = a0 + (a1 - a0) * rng.random()
            r = rng.uniform(r_in + pad, r_out - pad)
            self._gen_cluster(cx + r * math.cos(a), cy + r * math.sin(a),
                              rng, big=False)

    def _gen_damage_seg(self, x0, y0, x1, y1, width, rng):
        """Damage along an arbitrary-direction segment (oriented placement)."""
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        if L < 80:
            return
        ux, uy = dx / L, dy / L
        px, py = -uy, ux
        hw = width / 2 - 34
        if hw <= 0:
            return
        area = L * width
        for _ in range(int(area / C.ROAD_PATCH_AREA)):
            t = rng.uniform(40, L - 40)
            o = rng.uniform(-hw, hw)
            self.patches.append((x0 + ux * t + px * o, y0 + uy * t + py * o,
                                 rng.uniform(26, 55), rng.uniform(26, 55)))
        for _ in range(int(area / self._dmg_area)):
            t = rng.uniform(40, L - 40)
            o = rng.uniform(-hw, hw)
            self._gen_cluster(x0 + ux * t + px * o, y0 + uy * t + py * o, rng)

    def _generate_damage(self, scale=1.0):
        """Walk every emitted piece and scatter wear across it (seeded).

        ``scale`` divides the density -- higher difficulties leave a rougher
        road, easier ones a cleaner one."""
        self._dmg_area = C.ROAD_DAMAGE_AREA * scale
        rng = random.Random(self.layout_id * 7919 + 13)
        self.potholes, self.patches, self.cracks = [], [], []
        for p in self.pieces:
            kind = p[0]
            if kind == 'straight':
                cx, sy, length, width = p[1], p[2], p[3], p[4]
                hw = width / 2
                self._gen_damage_rect(cx - hw, cx + hw, sy, sy + length, rng)
            elif kind == 'horizontal':
                cy, sx, length, width = p[1], p[2], p[3], p[4]
                hw = width / 2
                self._gen_damage_rect(sx, sx + length, cy - hw, cy + hw, rng)
            elif kind == 'curve':
                cx, cy, radius, a0, a1, width = p[1], p[2], p[3], p[4], p[5], p[6]
                hw = width / 2
                lo, hi = (a0, a1) if a1 >= a0 else (a1, a0)
                self._gen_damage_arc(cx, cy, radius - hw, radius + hw, lo, hi, rng)
            elif kind == 'segment':
                self._gen_damage_seg(p[1], p[2], p[3], p[4], p[5], rng)

    # --- drawing (from the pre-generated data) ------------------------------
    def _draw_damage(self):
        glNormal3f(0, 0, 1)
        for (cx, cy, hw, hh) in self.patches:
            h = self.height_at(cx, cy)
            glColor3f(*C.COL_ROAD_CRACK)
            glBegin(GL_QUADS)
            glVertex3f(cx - hw - 3, cy - hh - 3, self._DMG_Z + h)
            glVertex3f(cx + hw + 3, cy - hh - 3, self._DMG_Z + h)
            glVertex3f(cx + hw + 3, cy + hh + 3, self._DMG_Z + h)
            glVertex3f(cx - hw - 3, cy + hh + 3, self._DMG_Z + h)
            glEnd()
            glColor3f(*C.COL_ROAD_PATCH)
            glBegin(GL_QUADS)
            glVertex3f(cx - hw, cy - hh, self._DMG_Z + 0.02 + h)
            glVertex3f(cx + hw, cy - hh, self._DMG_Z + 0.02 + h)
            glVertex3f(cx + hw, cy + hh, self._DMG_Z + 0.02 + h)
            glVertex3f(cx - hw, cy + hh, self._DMG_Z + 0.02 + h)
            glEnd()

        glColor3f(*C.COL_ROAD_CRACK)
        for (poly, width) in self.cracks:
            w = width
            for i in range(len(poly) - 1):
                (ax, ay), (bx, by) = poly[i], poly[i + 1]
                dx, dy = bx - ax, by - ay
                L = math.hypot(dx, dy) or 1.0
                ox, oy = -dy / L * w / 2, dx / L * w / 2
                ha = self._DMG_Z + 0.02 + self.height_at(ax, ay)
                hb = self._DMG_Z + 0.02 + self.height_at(bx, by)
                glBegin(GL_QUADS)
                glVertex3f(ax - ox, ay - oy, ha)
                glVertex3f(ax + ox, ay + oy, ha)
                glVertex3f(bx + ox, by + oy, hb)
                glVertex3f(bx - ox, by - oy, hb)
                glEnd()
                w = max(1.2, w * 0.8)      # cracks taper as they run out

        for (cx, cy, r, pts) in self.potholes:
            for scale, color, z in ((1.30, C.COL_ROAD_GRIT, self._DMG_Z),
                                    (1.00, C.COL_ROAD_CRACK, self._DMG_Z + 0.03),
                                    (0.62, C.COL_ROAD_HOLE, self._DMG_Z + 0.05)):
                glColor3f(*color)
                zh = z + self.height_at(cx, cy)
                glBegin(GL_POLYGON)
                for (px, py) in pts:
                    glVertex3f(cx + (px - cx) * scale, cy + (py - cy) * scale, zh)
                glEnd()

    def _road_slab(self, x0, x1, y0, y1):
        # (legacy axis-aligned slab) route through the tessellating emitter so
        # it follows the terrain too
        if abs(x1 - x0) > abs(y1 - y0):
            self._emit_segment(x0, (y0 + y1) / 2, x1, (y0 + y1) / 2, abs(y1 - y0))
        else:
            self._emit_segment((x0 + x1) / 2, y0, (x0 + x1) / 2, y1, abs(x1 - x0))
        return

    def _road_slab_flat(self, x0, x1, y0, y1):
        self._quad([(x0, y0, 0.1), (x1, y0, 0.1), (x1, y1, 0.1), (x0, y1, 0.1)],
                   C.T('road'))
        # darker feather along both long edges for a worn-asphalt read
        f = 26
        if abs(x1 - x0) > abs(y1 - y0):   # horizontal slab
            self._quad([(x0, y0, 0.12), (x1, y0, 0.12), (x1, y0 + f, 0.12), (x0, y0 + f, 0.12)], C.T('road_edge'))
            self._quad([(x0, y1 - f, 0.12), (x1, y1 - f, 0.12), (x1, y1, 0.12), (x0, y1, 0.12)], C.T('road_edge'))
        else:
            self._quad([(x0, y0, 0.12), (x0 + f, y0, 0.12), (x0 + f, y1, 0.12), (x0, y1, 0.12)], C.T('road_edge'))
            self._quad([(x1 - f, y0, 0.12), (x1, y0, 0.12), (x1, y1, 0.12), (x1 - f, y1, 0.12)], C.T('road_edge'))

    def _kerb_line(self, ax, ay, bx, by):
        """Striped raised kerb from A to B (a thin 3D box strip)."""
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        if length < 1:
            return
        ux, uy = dx / length, dy / length          # along kerb
        px, py = -uy, ux                            # across kerb
        t = C.BORDER_THICKNESS
        h = C.BORDER_HEIGHT
        n = max(1, int(length / KERB_SEG))
        seg = length / n
        for i in range(n):
            s0 = i * seg
            s1 = s0 + seg
            color = C.T('kerb_a') if i % 2 == 0 else C.T('kerb_b')
            cx0, cy0 = ax + ux * s0, ay + uy * s0
            cx1, cy1 = ax + ux * s1, ay + uy * s1
            l0 = (cx0 - px * t / 2, cy0 - py * t / 2)
            r0 = (cx0 + px * t / 2, cy0 + py * t / 2)
            l1 = (cx1 - px * t / 2, cy1 - py * t / 2)
            r1 = (cx1 + px * t / 2, cy1 + py * t / 2)
            # top
            self._quad([(l0[0], l0[1], h), (r0[0], r0[1], h),
                        (r1[0], r1[1], h), (l1[0], l1[1], h)], color)
            # inner + outer sides (normal roughly across)
            self._quad([(l0[0], l0[1], 0), (l1[0], l1[1], 0),
                        (l1[0], l1[1], h), (l0[0], l0[1], h)], color, (-px, -py, 0))
            self._quad([(r0[0], r0[1], 0), (r0[0], r0[1], h),
                        (r1[0], r1[1], h), (r1[0], r1[1], 0)], color, (px, py, 0))

    def _lane_dashes_line(self, ax, ay, bx, by, halfw=5):
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        if length < 1:
            return
        ux, uy = dx / length, dy / length
        px, py = -uy, ux
        s = 0
        glColor3f(*C.T('lane'))
        glNormal3f(0, 0, 1)
        glBegin(GL_QUADS)
        while s < length:
            e = min(s + LANE_DASH, length)
            x0, y0 = ax + ux * s, ay + uy * s
            x1, y1 = ax + ux * e, ay + uy * e
            for (vx, vy) in ((x0 - px * halfw, y0 - py * halfw),
                             (x0 + px * halfw, y0 + py * halfw),
                             (x1 + px * halfw, y1 + py * halfw),
                             (x1 - px * halfw, y1 - py * halfw)):
                glVertex3f(vx, vy, 1.5 + self.height_at(vx, vy))
            s = e + LANE_GAP
        glEnd()

    def _emit_straight(self, cx, start_y, length, width):
        hw = width / 2
        end_y = start_y + length
        self._road_slab(cx - hw, cx + hw, start_y, end_y)
        self._kerb_line(cx - hw, start_y, cx - hw, end_y)
        self._kerb_line(cx + hw, start_y, cx + hw, end_y)
        for lane_x in (cx - 100, cx, cx + 100):
            self._lane_dashes_line(lane_x, start_y, lane_x, end_y)

    def _emit_horizontal(self, cy, start_x, length, width):
        hw = width / 2
        end_x = start_x + length
        self._road_slab(start_x, end_x, cy - hw, cy + hw)
        self._kerb_line(start_x, cy - hw, end_x, cy - hw)
        self._kerb_line(start_x, cy + hw, end_x, cy + hw)
        for lane_y in (cy - 100, cy, cy + 100):
            self._lane_dashes_line(start_x, lane_y, end_x, lane_y)

    def _emit_segment(self, x0, y0, x1, y1, width):
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy) or 1.0
        ux, uy = dx / L, dy / L
        px, py = -uy, ux
        hw = width / 2
        # Tessellate ALONG the segment. A single long quad would be a flat
        # chord across the rolling terrain and would sink metres below the
        # ground in the middle -- which is exactly how the grass ended up
        # showing through the tarmac while the (already subdivided) kerbs and
        # lane markings stayed visible.
        steps = max(1, int(L / C.ROAD_TESS))
        glColor3f(*C.T('road'))
        glBegin(GL_QUAD_STRIP)
        for i in range(steps + 1):
            t = i / steps
            cx, cy = x0 + dx * t, y0 + dy * t
            lx, ly = cx + px * hw, cy + py * hw
            rx, ry = cx - px * hw, cy - py * hw
            nx = (self.height_at(cx + ux * 40, cy + uy * 40)
                  - self.height_at(cx - ux * 40, cy - uy * 40)) / 80.0
            nl = math.sqrt(nx * nx + 1.0)
            glNormal3f(-nx * ux / nl, -nx * uy / nl, 1.0 / nl)
            glVertex3f(lx, ly, 0.1 + self.height_at(lx, ly))
            glVertex3f(rx, ry, 0.1 + self.height_at(rx, ry))
        glEnd()
        # kerbs down both edges (these already subdivide, so they follow the hills)
        self._kerb_line(x0 + px * hw, y0 + py * hw, x1 + px * hw, y1 + py * hw)
        self._kerb_line(x0 - px * hw, y0 - py * hw, x1 - px * hw, y1 - py * hw)
        for o in (-hw / 2, 0.0, hw / 2):
            self._lane_dashes_line(x0 + px * o, y0 + py * o,
                                   x1 + px * o, y1 + py * o)

    def _emit_curve(self, cx, cy, radius, a0, a1, width):
        hw = width / 2
        inner, outer = radius - hw, radius + hw
        segs = 40
        glColor3f(*C.T('road'))
        glNormal3f(0, 0, 1)
        glBegin(GL_QUAD_STRIP)
        for i in range(segs + 1):
            a = a0 + (a1 - a0) * i / segs
            ca, sa = math.cos(a), math.sin(a)
            ix, iy = cx + inner * ca, cy + inner * sa
            ox, oy = cx + outer * ca, cy + outer * sa
            glVertex3f(ix, iy, 0.1 + self.height_at(ix, iy))
            glVertex3f(ox, oy, 0.1 + self.height_at(ox, oy))
        glEnd()
        # striped kerbs along both radii
        self._emit_arc_kerb(cx, cy, inner, a0, a1)
        self._emit_arc_kerb(cx, cy, outer, a0, a1)
        # centre lane dashes
        glColor3f(*C.T('lane'))
        glBegin(GL_QUADS)
        n = 16
        for i in range(0, n, 2):
            b0 = a0 + (a1 - a0) * i / n
            b1 = a0 + (a1 - a0) * (i + 1) / n
            for r in (radius,):
                self._arc_mark(cx, cy, r, b0, b1)
        glEnd()

    def _arc_mark(self, cx, cy, r, b0, b1, halfw=5):
        c0, s0 = math.cos(b0), math.sin(b0)
        c1, s1 = math.cos(b1), math.sin(b1)
        for (vx, vy) in ((cx + (r - halfw) * c0, cy + (r - halfw) * s0),
                         (cx + (r + halfw) * c0, cy + (r + halfw) * s0),
                         (cx + (r + halfw) * c1, cy + (r + halfw) * s1),
                         (cx + (r - halfw) * c1, cy + (r - halfw) * s1)):
            glVertex3f(vx, vy, 1.5 + self.height_at(vx, vy))

    def _emit_arc_kerb(self, cx, cy, r, a0, a1):
        h = C.BORDER_HEIGHT
        t = C.BORDER_THICKNESS
        length = abs(a1 - a0) * r
        n = max(2, int(length / KERB_SEG))
        for i in range(n):
            b0 = a0 + (a1 - a0) * i / n
            b1 = a0 + (a1 - a0) * (i + 1) / n
            color = C.T('kerb_a') if i % 2 == 0 else C.T('kerb_b')
            c0, s0 = math.cos(b0), math.sin(b0)
            c1, s1 = math.cos(b1), math.sin(b1)
            ri, ro = r - t / 2, r + t / 2
            top = [(cx + ri * c0, cy + ri * s0, h), (cx + ro * c0, cy + ro * s0, h),
                   (cx + ro * c1, cy + ro * s1, h), (cx + ri * c1, cy + ri * s1, h)]
            self._quad(top, color)
            self._quad([(cx + ro * c0, cy + ro * s0, 0), (cx + ro * c0, cy + ro * s0, h),
                        (cx + ro * c1, cy + ro * s1, h), (cx + ro * c1, cy + ro * s1, 0)],
                       color, (c0, s0, 0))

    def _emit_finish(self, fl):
        x, y = fl['pos']
        angle = fl['angle']
        width = fl['width']
        glPushMatrix()
        glTranslatef(x, y, self.height_at(x, y))
        glRotatef(angle, 0, 0, 1)
        # Checkered strip, laid in WORLD space against the terrain: the road can
        # rise tens of units across the line's 450-unit width, so a flat strip
        # would sink into the tarmac at one end and hover at the other.
        check = 40
        cols = int(width / check)
        ar = math.radians(angle)
        car_, sar = math.cos(ar), math.sin(ar)
        glPopMatrix()                      # back to world space for the strip
        glNormal3f(0, 0, 1)
        for i in range(cols):
            for j in range(2):
                glColor3f(*((0.95, 0.95, 0.95) if (i + j) % 2 == 0 else (0.08, 0.08, 0.08)))
                u0 = -width / 2 + i * check
                v0 = -check + j * check
                glBegin(GL_QUADS)
                for (uu, vv) in ((u0, v0), (u0 + check, v0),
                                 (u0 + check, v0 + check), (u0, v0 + check)):
                    wx = x + car_ * uu - sar * vv
                    wy = y + sar * uu + car_ * vv
                    glVertex3f(wx, wy, self.height_at(wx, wy) + 1.6)
                glEnd()
        glPushMatrix()                     # re-enter the local frame for the gantry
        glTranslatef(x, y, self.height_at(x, y))
        glRotatef(angle, 0, 0, 1)
        # gantry posts + banner
        post = 12
        top = 150
        for sx in (-width / 2 - post, width / 2):
            glColor3f(0.12, 0.12, 0.14)
            glPushMatrix()
            glTranslatef(sx + post / 2, check, top / 2)
            gfx.box(post / 2, post / 2, top / 2)
            glPopMatrix()
        glColor3f(0.15, 0.30, 0.75)
        glPushMatrix()
        glTranslatef(0, check, top)
        gfx.box(width / 2 + post, 4, 22)
        glPopMatrix()
        glPopMatrix()


    # -- procedural circuit generation -------------------------------------
    def _generate(self, difficulty, rng):
        """Create a fresh, randomised circuit for the given difficulty.

        The shape is a *radial* polygon -- vertices sorted by angle around a
        centre -- which is guaranteed not to intersect itself, so every
        generated track is a valid closed loop.  Randomising the vertex count,
        their angles and their radii is what makes each race a different
        circuit instead of the same straight-then-left-turn every time.
        The polygon is then relaxed to remove corners that would be too sharp
        or straights that would be too short to drive, and finally filleted by
        _polygon_circuit() into real sweeping bends.
        """
        d = C.DIFFICULTIES[difficulty]
        n = rng.randint(*d['corners'])
        base = d['size']

        # vertices: evenly spread angles with jitter, radii varied per corner
        step = 2 * math.pi / n
        angles = sorted(i * step + rng.uniform(-0.32, 0.32) * step
                        for i in range(n))
        radii = [base * rng.uniform(*d['radius_var']) for _ in range(n)]
        for _ in range(2):      # soften wild radius jumps between neighbours
            radii = [(radii[i - 1] + 2 * radii[i] + radii[(i + 1) % n]) / 4.0
                     for i in range(n)]
        pts = [[math.cos(a) * r, math.sin(a) * r]
               for a, r in zip(angles, radii)]

        pts = self._relax(pts)
        # rotate so the LONGEST straight is edge 0 -- that becomes the
        # start/finish straight, giving every generated track a proper
        # pit-straight to line up on
        n = len(pts)
        k = max(range(n), key=lambda i: math.hypot(
            pts[(i + 1) % n][0] - pts[i][0], pts[(i + 1) % n][1] - pts[i][1]))
        pts = pts[k:] + pts[:k]
        self._polygon_circuit(pts, radius=C.GEN_FILLET)
        return pts

    def _relax(self, pts, iterations=14):
        """Push the polygon into something drivable.

        Drops vertices that make a straight too short for a corner arc to fit,
        and eases corners that are sharper than the AI (and the player) can
        reasonably take by nudging them outward from the centre.
        """
        for _ in range(iterations):
            n = len(pts)
            if n <= 5:
                break
            # 1) remove a vertex if its incoming edge is too short
            worst_i, worst_len = -1, C.GEN_MIN_EDGE
            for i in range(n):
                a, b = pts[i], pts[(i + 1) % n]
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                if L < worst_len:
                    worst_len, worst_i = L, i
            if worst_i >= 0:
                pts.pop((worst_i + 1) % len(pts))
                continue
            # 2) open up any corner that is too tight
            changed = False
            n = len(pts)
            for i in range(n):
                p, c, q = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
                v1 = (p[0] - c[0], p[1] - c[1])
                v2 = (q[0] - c[0], q[1] - c[1])
                l1 = math.hypot(*v1) or 1.0
                l2 = math.hypot(*v2) or 1.0
                dot = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)))
                theta = math.degrees(math.acos(dot))
                if theta < C.GEN_MIN_ANGLE:
                    r = math.hypot(c[0], c[1]) or 1.0
                    pts[i] = [c[0] / r * (r * 1.12), c[1] / r * (r * 1.12)]
                    changed = True
            if not changed:
                break
        return pts

    def _place_start_and_furniture(self, difficulty, rng):
        """Put the start line on the longest straight and scatter humps."""
        a, b = self._start_edge
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        ux, uy = dx / L, dy / L
        self.start_raw = (a[0] + ux * L * 0.22, a[1] + uy * L * 0.22)
        self.start_angle = math.degrees(math.atan2(uy, ux))
        self.finish_line = {
            'pos': (a[0] + ux * L * 0.55, a[1] + uy * L * 0.55),
            'angle': self.start_angle + 90.0,     # strip lies across the road
            'width': 450,
        }
        # Bridge: span the longest non-start straight over a scooped-out lake.
        self.bridge_raw = None
        self.bowl_raw = None
        others = list(self._edges[1:])
        if others:
            bp, bq = max(others, key=lambda e: math.hypot(e[1][0] - e[0][0],
                                                         e[1][1] - e[0][1]))
            elen = math.hypot(bq[0] - bp[0], bq[1] - bp[1])
            if elen > 1400:
                mx, my = (bp[0] + bq[0]) / 2, (bp[1] + bq[1]) / 2
                span = min(elen * 0.5, 1100)
                self.bridge_raw = (mx, my,
                                   math.degrees(math.atan2(bq[1] - bp[1],
                                                           bq[0] - bp[0])),
                                   span)
                self.bowl_raw = (mx, my, span * 0.85, C.BRIDGE_DEPTH)

        # speed breakers: on other straights, oriented along the road
        self.speed_breakers = []
        edges = [e for e in self._edges[1:]]        # never on the start straight
        rng.shuffle(edges)
        for (p, q) in edges[:C.DIFFICULTIES[difficulty]['breakers']]:
            ex, ey = q[0] - p[0], q[1] - p[1]
            el = math.hypot(ex, ey) or 1.0
            t = rng.uniform(0.35, 0.65)
            self.speed_breakers.append((
                p[0] + ex * t, p[1] + ey * t,
                C.BREAKER_WIDTH, C.BREAKER_DEPTH,
                math.degrees(math.atan2(ey, ex)),
            ))
