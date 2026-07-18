"""Track building: the three proven hand-built layouts, re-rendered.

The layout coordinates come straight from the legacy game (so the racing lines,
finish line and speed-breaker placements stay exactly as tuned), but the
geometry is now emitted as lit surfaces with striped 3D kerbs and compiled into
a display list so the static world is drawn in a single fast call each frame.
"""

import math
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
        self.layout_id = 1
        self._list = None

    # -- public API --------------------------------------------------------
    def build(self, layout_id):
        self.__init__()
        self.layout_id = layout_id
        {1: self._layout1, 2: self._layout2, 3: self._layout3}[layout_id]()
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
    def _straight(self, cx, start_y, length, width=C.ROAD_WIDTH):
        hw = width / 2
        end_y = start_y + length
        self._fill_rect(cx - hw, cx + hw, start_y, end_y, self.road_points, 20)
        for ex in (cx - hw, cx + hw):
            self._fill_rect(ex - C.BORDER_THICKNESS, ex + C.BORDER_THICKNESS,
                            start_y, end_y, self.border_points, C.GRID)
        self.pieces.append(('straight', cx, start_y, length, width))

    def _horizontal(self, cy, start_x, length, width=C.ROAD_WIDTH):
        hw = width / 2
        end_x = start_x + length
        self._fill_rect(start_x, end_x, cy - hw, cy + hw, self.road_points, 20)
        for ey in (cy - hw, cy + hw):
            self._fill_rect(start_x, end_x, ey - C.BORDER_THICKNESS,
                            ey + C.BORDER_THICKNESS, self.border_points, C.GRID)
        self.pieces.append(('horizontal', cy, start_x, length, width))

    def _curve(self, cx, cy, radius, a0, a1, x_shift=0, width=C.ROAD_WIDTH):
        cx += x_shift
        hw = width / 2
        self._fill_arc(cx, cy, radius - hw, radius + hw, a0, a1,
                       self.road_points, 20)
        for r in (radius - hw, radius + hw):
            self._fill_arc(cx, cy, r - C.BORDER_THICKNESS, r + C.BORDER_THICKNESS,
                           a0, a1, self.border_points, C.GRID)
        self.pieces.append(('curve', cx, cy, radius, a0, a1, width))

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
        if self.finish_line:
            self._emit_finish(self.finish_line)

    def _quad(self, verts, color, nz=(0, 0, 1)):
        glColor3f(*color)
        glNormal3f(*nz)
        glBegin(GL_QUADS)
        for v in verts:
            glVertex3f(*v)
        glEnd()

    def _road_slab(self, x0, x1, y0, y1):
        self._quad([(x0, y0, 0.1), (x1, y0, 0.1), (x1, y1, 0.1), (x0, y1, 0.1)],
                   C.COL_ROAD)
        # darker feather along both long edges for a worn-asphalt read
        f = 26
        if abs(x1 - x0) > abs(y1 - y0):   # horizontal slab
            self._quad([(x0, y0, 0.12), (x1, y0, 0.12), (x1, y0 + f, 0.12), (x0, y0 + f, 0.12)], C.COL_ROAD_EDGE)
            self._quad([(x0, y1 - f, 0.12), (x1, y1 - f, 0.12), (x1, y1, 0.12), (x0, y1, 0.12)], C.COL_ROAD_EDGE)
        else:
            self._quad([(x0, y0, 0.12), (x0 + f, y0, 0.12), (x0 + f, y1, 0.12), (x0, y1, 0.12)], C.COL_ROAD_EDGE)
            self._quad([(x1 - f, y0, 0.12), (x1, y0, 0.12), (x1, y1, 0.12), (x1 - f, y1, 0.12)], C.COL_ROAD_EDGE)

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
            color = C.COL_BORDER_A if i % 2 == 0 else C.COL_BORDER_B
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
        glColor3f(*C.COL_LANE)
        glNormal3f(0, 0, 1)
        glBegin(GL_QUADS)
        while s < length:
            e = min(s + LANE_DASH, length)
            x0, y0 = ax + ux * s, ay + uy * s
            x1, y1 = ax + ux * e, ay + uy * e
            glVertex3f(x0 - px * halfw, y0 - py * halfw, 0.6)
            glVertex3f(x0 + px * halfw, y0 + py * halfw, 0.6)
            glVertex3f(x1 + px * halfw, y1 + py * halfw, 0.6)
            glVertex3f(x1 - px * halfw, y1 - py * halfw, 0.6)
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

    def _emit_curve(self, cx, cy, radius, a0, a1, width):
        hw = width / 2
        inner, outer = radius - hw, radius + hw
        segs = 40
        glColor3f(*C.COL_ROAD)
        glNormal3f(0, 0, 1)
        glBegin(GL_QUAD_STRIP)
        for i in range(segs + 1):
            a = a0 + (a1 - a0) * i / segs
            ca, sa = math.cos(a), math.sin(a)
            glVertex3f(cx + inner * ca, cy + inner * sa, 0.1)
            glVertex3f(cx + outer * ca, cy + outer * sa, 0.1)
        glEnd()
        # striped kerbs along both radii
        self._emit_arc_kerb(cx, cy, inner, a0, a1)
        self._emit_arc_kerb(cx, cy, outer, a0, a1)
        # centre lane dashes
        glColor3f(*C.COL_LANE)
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
        glVertex3f(cx + (r - halfw) * c0, cy + (r - halfw) * s0, 0.6)
        glVertex3f(cx + (r + halfw) * c0, cy + (r + halfw) * s0, 0.6)
        glVertex3f(cx + (r + halfw) * c1, cy + (r + halfw) * s1, 0.6)
        glVertex3f(cx + (r - halfw) * c1, cy + (r - halfw) * s1, 0.6)

    def _emit_arc_kerb(self, cx, cy, r, a0, a1):
        h = C.BORDER_HEIGHT
        t = C.BORDER_THICKNESS
        length = abs(a1 - a0) * r
        n = max(2, int(length / KERB_SEG))
        for i in range(n):
            b0 = a0 + (a1 - a0) * i / n
            b1 = a0 + (a1 - a0) * (i + 1) / n
            color = C.COL_BORDER_A if i % 2 == 0 else C.COL_BORDER_B
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
        glTranslatef(x, y, 0)
        glRotatef(angle, 0, 0, 1)
        # checkered strip
        check = 40
        cols = int(width / check)
        depth = 2
        glNormal3f(0, 0, 1)
        for i in range(cols):
            for j in range(2):
                glColor3f(*((0.95, 0.95, 0.95) if (i + j) % 2 == 0 else (0.08, 0.08, 0.08)))
                x0 = -width / 2 + i * check
                y0 = -check + j * check
                glBegin(GL_QUADS)
                glVertex3f(x0, y0, 1.2)
                glVertex3f(x0 + check, y0, 1.2)
                glVertex3f(x0 + check, y0 + check, 1.2)
                glVertex3f(x0, y0 + check, 1.2)
                glEnd()
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

    # -- layouts (coordinates ported verbatim from the legacy game) --------
    def _layout1(self):
        L = C.G_LENGTH
        self._straight(0, -L, 2 * L)
        self._curve(100, L - 1200, 200, math.pi, math.pi + math.pi / 2, 100)
        self._horizontal(L - 1400, 200, 1600)
        self._curve(1800, -L - 400, 200, 0, math.pi / 2)
        self._straight(2000, -L - 1600, 2 * L)
        self._straight(2000, -L - 2800, 2 * L)
        self._curve(1700, L - 4000, 200, 0, -math.pi / 2, 100)
        self._horizontal(L - 4200, 200, 1600)
        self._horizontal(L - 4200, -2200, 2400)
        self._curve(-2300, L - 4000, 200, -math.pi, -math.pi / 2, 100)
        self._straight(-2400, -L - 2800, 6 * L + 400)
        self._curve(-2300, L, 200, math.pi, math.pi / 2, 100)
        self._horizontal(L + 200, -2200, 2000)
        self._curve(-300, L, 200, 0, math.pi / 2, 100)
        self.finish_line = {'pos': (0, -L - 60), 'angle': 0, 'width': 450}
        self.speed_breakers = [(2000, -2800, 400, 150)]

    def _layout2(self):
        L = C.G_LENGTH
        self._straight(0, -L - 2400, 6 * L)
        self._curve(-300, L - 3600, 200, 0, -math.pi / 2, 100)
        self._horizontal(L - 3800, -3400, 3200)
        self._curve(-3500, L - 4000, 200, math.pi, math.pi / 2, 100)
        self._straight(-3600, -L - 4000, 2 * L)
        self._curve(-3900, L - 5200, 200, 0, -math.pi / 2, 100)
        self._horizontal(L - 5400, -6000, 2200)
        self._curve(-6100, L - 5200, 200, -math.pi, -math.pi / 2, 100)
        self._straight(-6200, -L - 4000, 8 * L + 400)
        self._curve(-6100, L, 200, math.pi, math.pi / 2, 100)
        self._horizontal(L + 200, -6000, 5800)
        self._curve(-300, L, 200, 0, math.pi / 2, 100)
        self.finish_line = {'pos': (0, -L - 2400 + 40), 'angle': 0, 'width': 450}
        self.speed_breakers = [(-3600, -4000, 400, 150)]

    def _layout3(self):
        L = C.G_LENGTH
        self._straight(0, -L - 2400, 6 * L)
        self._curve(-300, L - 3600, 200, 0, -math.pi / 2, 100)
        self._horizontal(L - 3800, -5000, 4800)
        self._curve(-5100, L - 3600, 200, -math.pi, -math.pi / 2, 100)
        self._straight(-5200, -L - 2400, 6 * L)
        self._curve(-5100, L, 200, math.pi, math.pi / 2, 100)
        self._horizontal(L + 200, -5000, 4800)
        self._curve(-300, L, 200, 0, math.pi / 2, 100)
        self.finish_line = {'pos': (0, -L - 2400 + 40), 'angle': 0, 'width': 450}
        self.speed_breakers = [(-5200, -2400, 400, 150)]


# Enemy waypoint paths per layout (ported from legacy get_enemy_paths_for_layout)
def enemy_base_waypoints(layout_id, finish_y):
    L = C.G_LENGTH
    if layout_id == 1:
        return [(0, -600, 10), (30, 800, 10), (-2300, 800, 10),
                (-2300, -3600, 10), (2000, -3600, 10),
                (2000, -800, 10), (0, -800, 10), (0, finish_y + 40, 10)]
    if layout_id == 2:
        return [(0, -600, 10), (30, 800, 10), (-6200, 800, 10),
                (-6200, -4800, 10), (-3600, -4800, 10),
                (-3600, -3200, 10), (0, -3200, 10), (0, finish_y + 40, 10)]
    return [(0, -600, 10), (0, 800, 10), (-5200, 800, 10),
            (-5200, -3200, 10), (0, -3200, 10), (0, finish_y + 40, 10)]
