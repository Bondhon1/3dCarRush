"""Game engine: state, camera, input, update loop and the GLUT bootstrap."""

import sys
import math
import time
import random
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

from . import config as C
from . import gfx
from . import track as track_mod
from . import props
from . import hud
from . import audio
from .entities import Player, Enemy, Bullet, draw_bullets


# Game states
MENU = "menu"
COUNTDOWN = "countdown"
PLAYING = "playing"
PAUSED = "paused"
WIN = "win"
LOSE = "lose"
ENEMY_WIN = "enemy_win"

COUNTDOWN_TIME = 3.6           # seconds of "3 2 1 GO!" before the flag drops


class Game:
    def __init__(self):
        self.width = C.WINDOW_WIDTH
        self.height = C.WINDOW_HEIGHT
        self.state = MENU
        self.menu_index = 0            # selected track on the start screen
        self.fpv = False
        self.track = track_mod.Track()
        self.player = Player()
        self.enemies = []
        self.bullets = []
        self.health_kits = []
        self.shield_kits = []
        self.bombs = []
        self.trees = []
        self.hills = []
        self.lakes = []
        self.rocks = []
        self.lamps = []
        self.explosions = []
        self.message = ""
        self.message_until = 0.0
        self.spawn_protect_until = 0.0
        self.countdown_start = 0.0
        self.checkpoint = None         # far-side gate that proves a real lap
        self.checkpoint_reached = False
        self.breaker_cd = 0.0
        self.pothole_cd = 0.0          # one slowdown per pothole strike
        self.fire_cd = 0.0             # player gun rate limit
        self._catchup_at = 0.0         # next rubber-band recompute
        self._catchup_msg = 0.0        # rate-limit the "closing in" warning
        self.difficulty = 3
        # held-key movement state
        self.brake = False
        self.turn_left = False
        self.turn_right = False
        self.gun_left = False
        self.gun_right = False
        self.bump_cd = 0.0             # cooldown so one rival hit costs one life
        self.wall_cd = 0.0             # cooldown so one wall crash costs one life
        self._last_count = None        # last countdown value we beeped for
        self._last_update = None        # wall-clock of the previous update tick
        self.logo = None               # menu logo texture (lazily loaded)
        self.logo_loaded = False

    # ------------------------------------------------------------------ setup
    def start_race(self, difficulty):
        """Cut a brand-new random circuit at the chosen difficulty and line up."""
        self.difficulty = difficulty
        d = C.DIFFICULTIES[difficulty]
        # A random theme each race, so back-to-back runs never look the same.
        # Theme first: the track and hill display lists bake their colours.
        C.set_theme(random.randint(1, len(C.THEMES)))
        gfx.apply_theme()
        props.reset_hill_cache()
        gfx.reset_ground_cache()
        self.track.dispose()
        self.track.build(difficulty)
        gfx.build_sky(random.Random(random.randrange(1 << 30)))
        sx, sy = self.track.start_pos
        self.player.reset(pos=(sx, sy,
                               self.track.height_at(sx, sy) + C.CAR_GROUND_Z),
                          angle=self.track.start_angle,
                          lives=d['lives'])
        self._spawn_enemies(difficulty)
        self._spawn_props()
        self.bullets = []
        self.explosions = []
        # lap checkpoint = the base waypoint farthest from the finish line
        fx, fy = self.track.finish_line['pos']
        base = self._racing_line()
        self.checkpoint = max(base, key=lambda w: (w[0] - fx) ** 2 + (w[1] - fy) ** 2)
        self.checkpoint_reached = False
        self.lap_waypoints = [(w[0], w[1]) for w in base]
        # correct finish-crossing direction = the racing line's final heading
        lx, ly = self.lap_waypoints[-1]
        qx, qy = self.lap_waypoints[-2]
        dd = math.hypot(lx - qx, ly - qy) or 1.0
        self.finish_dir = ((lx - qx) / dd, (ly - qy) / dd)
        self.spawn_protect_until = time.time() + COUNTDOWN_TIME + 1.0
        self.countdown_start = time.time()
        self.state = COUNTDOWN
        self._last_count = None
        self._last_update = None        # fresh frame-clock for the new race
        audio.start_music()
        audio.start_engine()
        audio.set_engine(0.2)

    def _racing_line(self, difficulty=None, fy=None):
        """Centre-line waypoints, generated with the circuit."""
        fl = self.track.finish_line['pos']
        return list(self.track.auto_waypoints) + [(fl[0], fl[1], 10)]

    def _spawn_enemies(self, difficulty):
        base = self._racing_line()
        self.enemies = []
        d = C.DIFFICULTIES[difficulty]
        # Rivals race laterally-offset copies of the centre line. Offsets are
        # perpendicular to the LOCAL road direction, so they work on a circuit
        # running at any angle (not just axis-aligned legs).
        sx, sy = self.track.start_pos
        sa = math.radians(self.track.start_angle)
        fwd = (math.cos(sa), math.sin(sa))
        right = (fwd[1], -fwd[0])
        roles = list(C.ENEMY_ROLES)      # one of each role, in random slots
        random.shuffle(roles)
        for i, off in enumerate((-70, 0, 70)):
            path = []
            for j, (x, y, z) in enumerate(base):
                nx, ny = base[min(j + 1, len(base) - 1)][:2]
                dx, dy = nx - x, ny - y
                dl = math.hypot(dx, dy) or 1.0
                px, py = dy / dl, -dx / dl       # local perpendicular
                path.append((x + px * off, y + py * off, z))
            role = roles[i]
            e = Enemy(path, random.uniform(*d['enemy_speed']) * role['speed'])
            e.role, e.tag, e.ram = role['name'], role['tag'], role['ram']
            e.lives = max(1, d['enemy_lives'] + role['armor'])
            e.max_lives = e.lives
            e.fire_gap = d['enemy_fire'] * role['fire']
            # grid slots: staggered behind the start line, across the road
            lane = (-140, 150, -30)[i]
            back = (-90, -90, -230)[i]
            ex = sx + right[0] * lane + fwd[0] * back
            ey = sy + right[1] * lane + fwd[1] * back
            e.pos = [ex, ey, self.track.height_at(ex, ey) + C.CAR_GROUND_Z]
            e.angle = self.track.start_angle
            self.enemies.append(e)

    def _spawn_props(self):
        road = list(self.track.road_points)
        random.shuffle(road)
        self.health_kits = road[:C.NUM_HEALTH_KITS]
        self.shield_kits = road[C.NUM_HEALTH_KITS:C.NUM_HEALTH_KITS + C.NUM_SHIELD_KITS]
        i = C.NUM_HEALTH_KITS + C.NUM_SHIELD_KITS
        n_bombs = C.DIFFICULTIES[getattr(self, 'difficulty', 3)]['bombs']
        self.bombs = list(road[i:i + n_bombs])
        self._spawn_scenery()

    def _spawn_scenery(self):
        """Scatter trees, rocks, lakes and horizon hills clear of the track.

        Spawn extents scale with the enlarged track so scenery still fills the
        whole world; object sizes and the road-clearance stay in absolute units."""
        self.trees, self.rocks, self.lakes, self.hills = [], [], [], []
        S = C.TRACK_SCALE

        def _place(store, count, xr, yr, clear2, extra=None, tries_mul=25):
            tries = 0
            while len(store) < count and tries < count * tries_mul:
                tries += 1
                x = random.uniform(-xr * S, xr * S)
                y = random.uniform(-yr * S, yr * S)
                if self.track.is_on_road(x, y, radius2=clear2):
                    continue
                store.append((x, y) if extra is None else extra(x, y))

        _place(self.trees, C.NUM_TREES, 6500, 6500, 90000,
               lambda x, y: (x, y, random.uniform(0.75, 1.4),
                             random.choice((0, 0, 1, 1, 2))))
        self._spawn_lamps()
        _place(self.rocks, C.NUM_ROCKS, 6800, 6800, 45000,
               lambda x, y: (x, y, random.uniform(0.6, 1.5), random.uniform(0, 360)))
        # lakes sit well off the racing surface
        _place(self.lakes, C.NUM_LAKES, 6000, 6000, 700000,
               lambda x, y: (x, y, random.uniform(420, 720), random.uniform(300, 520)))
        # hills ring the far horizon for depth
        for _ in range(C.NUM_HILLS):
            ang = random.uniform(0, 2 * math.pi)
            dist = random.uniform(6500, 9500) * S
            x, y = math.cos(ang) * dist, math.sin(ang) * dist
            self.hills.append((x, y, random.uniform(700, 1500),
                               random.uniform(260, 520)))

    def _spawn_lamps(self):
        """Line the verges with street lamps, alternating sides.

        Always drives off the freshly-built track's own centre line -- reading
        `self.lap_waypoints` here would use the PREVIOUS race's line, since it
        isn't assigned until after the props are spawned, which scattered lamps
        across the new circuit (some of them standing in the road).
        """
        self.lamps = []
        line = [(w[0], w[1]) for w in self.track.auto_waypoints]
        if len(line) < 2:
            return
        acc = 0.0
        side = 1
        for i in range(len(line) - 1):
            ax, ay = line[i]
            bx, by = line[i + 1]
            seg = math.hypot(bx - ax, by - ay)
            if seg < 1:
                continue
            ux, uy = (bx - ax) / seg, (by - ay) / seg
            px, py = -uy, ux
            t = -acc
            while t < seg:
                if t >= 0:
                    # Try the intended side, then the other. On the inside of a
                    # bend the racing line is a chord, so a fixed perpendicular
                    # offset can still land on tarmac -- verify against the road
                    # itself rather than trusting the geometry.
                    for s in (side, -side):
                        off = (C.ROAD_WIDTH / 2 + C.LAMP_VERGE) * s
                        lx = ax + ux * t + px * off
                        ly = ay + uy * t + py * off
                        if self.track.is_on_road(lx, ly, radius2=C.LAMP_CLEAR2):
                            continue                  # standing in the road
                        face = math.degrees(math.atan2(-py * s, -px * s))
                        self.lamps.append((lx, ly, face))
                        break
                    side = -side
                t += C.LAMP_SPACING
            acc = (acc + seg) % C.LAMP_SPACING

    def flash(self, msg, seconds=2.5):
        self.message = msg
        self.message_until = time.time() + seconds

    def _lap_progress(self, x, y):
        """Distance travelled along the racing line, for ranking cars."""
        wps = self.lap_waypoints
        best, best_d, cum = 0.0, 1e18, 0.0
        for i in range(len(wps) - 1):
            ax, ay = wps[i]
            bx, by = wps[i + 1]
            dx, dy = bx - ax, by - ay
            seg2 = dx * dx + dy * dy or 1.0
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / seg2))
            projx, projy = ax + dx * t, ay + dy * t
            d = (x - projx) ** 2 + (y - projy) ** 2
            if d < best_d:
                best_d = d
                best = cum + t * math.sqrt(seg2)
            cum += math.sqrt(seg2)
        return best

    def player_place(self):
        pp = self._lap_progress(self.player.pos[0], self.player.pos[1])
        ahead = sum(1 for e in self.enemies
                    if not e.finished and self._lap_progress(e.pos[0], e.pos[1]) > pp)
        return ahead + 1, len(self.enemies) + 1

    # ------------------------------------------------------------------ camera
    def setup_camera(self, viewport_aspect):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(C.FOV_Y, viewport_aspect, C.NEAR_PLANE, C.FAR_PLANE)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        x, y, z = self.player.pos
        a = math.radians(self.player.angle)
        fx, fy = math.cos(a), math.sin(a)
        if self.fpv:
            eye = (x + 12 * fx, y + 12 * fy, z + 26)
            look = (x + 200 * fx, y + 200 * fy, z + 20)
            gluLookAt(*eye, *look, 0, 0, 1)
        else:
            eye = (x - C.CAM_BACK * fx, y - C.CAM_BACK * fy, z + C.CAM_HEIGHT)
            look = (x + C.CAM_LOOK_AHEAD * fx, y + C.CAM_LOOK_AHEAD * fy, z + 14)
            gluLookAt(*eye, *look, 0, 0, 1)

    def countdown_value(self):
        """Return '3'/'2'/'1'/'GO!' or None once racing has begun."""
        t = time.time() - self.countdown_start
        if t >= COUNTDOWN_TIME:
            return None
        if t < COUNTDOWN_TIME - 0.6:
            return str(int(COUNTDOWN_TIME - 0.6 - t) + 1)
        return "GO!"

    # ------------------------------------------------------------------ update
    def update(self):
        now = time.time()
        # Frame-scale: how many 60-FPS frames this tick represents.  Multiplying
        # all motion by it decouples game speed from render/update rate, so the
        # car covers the same distance per second on every PC and every track
        # (fixes the "over-sped on some tracks" render-rate coupling).  Clamped
        # so a lag spike can't teleport a car through a wall.
        if self._last_update is None:
            fs = 1.0
        else:
            fs = max(0.25, min(2.0, (now - self._last_update) * C.TARGET_FPS))
        self._last_update = now

        if self.state == COUNTDOWN:
            # rivals idle on the grid until the flag drops
            cv = self.countdown_value()
            if cv != self._last_count:               # one beep per tick
                if cv == "GO!":
                    audio.play('go', 0.9)
                elif cv is not None:
                    audio.play('beep', 0.7)
                self._last_count = cv
            if cv is None:
                self.state = PLAYING
            return
        if self.state != PLAYING:
            return

        p = self.player
        # timed effects
        if p.boost_active and now - p.boost_start > C.BOOST_DURATION:
            p.boost_active = False
            p.boost_cd_until = now + C.BOOST_COOLDOWN     # start the recharge
        if p.shield_active and now - p.shield_start > C.SHIELD_DURATION:
            p.shield_active = False

        # steering (held keys) -- scaled by frame time
        if self.turn_left:
            p.angle += C.TURN_SPEED * fs
        if self.turn_right:
            p.angle -= C.TURN_SPEED * fs
        if self.gun_left:
            p.gun_angle += C.GUN_TURN_SPEED * fs
        if self.gun_right:
            p.gun_angle -= C.GUN_TURN_SPEED * fs

        self._update_jump(now)

        # forward motion: ease toward the target speed for a smooth ramp instead
        # of snapping (matched accel/decel gives every input the same feel)
        if p.boost_active:
            target_speed = C.BOOST_SPEED
        elif self.brake:
            target_speed = C.SLOW_SPEED
        else:
            target_speed = C.NORMAL_SPEED
        if now < p.pothole_until:            # bogged down in broken tarmac
            target_speed *= C.POTHOLE_SLOW_FACTOR
        # Gradient shifts you a whole gear rather than scaling your speed:
        # uphill a boost only buys you normal pace and normal pace drops to a
        # crawl; downhill does the same in reverse. Blending between the speed
        # tiers keeps a steep climb slow but never a dead stop.
        ha = math.radians(p.angle)
        self.grade = self.track.slope_along(p.pos[0], p.pos[1],
                                            math.cos(ha), math.sin(ha))
        tiers = (C.SLOW_SPEED * 0.7, C.SLOW_SPEED, C.NORMAL_SPEED,
                 C.BOOST_SPEED, C.BOOST_SPEED * 1.18)
        gear = 3 if p.boost_active else (1 if self.brake else 2)
        g = max(-1.0, min(1.0, self.grade / C.GRADE_STEEP))
        if g > 0:                                  # climbing -> down a gear
            target_speed += (tiers[gear - 1] - target_speed) * g
        elif g < 0:                                # descending -> up a gear
            target_speed += (tiers[gear + 1] - target_speed) * (-g)

        # Integrate as ACCELERATION, not a snap to the target: the engine pulls
        # toward the target speed while gravity pushes along the slope. That is
        # what gives hills weight -- you visibly gather pace down a descent,
        # grind down as a climb steepens, and momentum carries you over a crest
        # instead of the speed teleporting to whatever the gradient dictates.
        accel = (target_speed - p.speed) * C.SPEED_LERP
        accel -= self.grade * C.GRAVITY_ACCEL
        p.speed = max(C.SPEED_FLOOR,
                      min(C.SPEED_CEILING, p.speed + accel * fs))

        # engine note tracks throttle; boost adds a whoosh
        audio.set_engine(p.speed / C.BOOST_SPEED)
        audio.set_boost(p.boost_active)

        protected = now < self.spawn_protect_until
        a = math.radians(p.angle)
        fx, fy = math.cos(a), math.sin(a)
        old = list(p.pos)
        p.pos[0] += p.speed * fs * fx
        p.pos[1] += p.speed * fs * fy

        if not protected and self._car_hits_wall(p.pos[0], p.pos[1], p.angle):
            p.pos = old                       # blocked by the wall
            if now >= self.wall_cd:           # one event per bump (not per frame)
                self.wall_cd = now + 1.0
                audio.play('crash', 0.7)
                # clipping a rail lets every rival surge ahead for a few seconds
                for e in self.enemies:
                    e.rage_until = now + C.ENEMY_RAGE_TIME
                self.flash("RIVALS SURGE!", 1.4)
                if not p.shield_active:
                    p.lives = max(0, p.lives - 1)
                    self.explosions.append(props.Explosion(old[0], old[1], 0.6))
                    if p.lives <= 0:
                        self._lose()

        self._update_catchup(now)

        # enemies
        for e in self.enemies:
            if e.lives <= 0:
                e.respawn()
                e.pos[2] = (self.track.height_at(e.pos[0], e.pos[1])
                            + C.CAR_GROUND_Z)
            e.update(fs)
            # rivals track and shoot the player when tailgated too closely
            shot = e.aim_and_maybe_fire(p, now)
            if shot is not None:
                self.bullets.append(shot)
                audio.play('eshot', 0.5)
            if e.segment >= len(e.path) - 1 and not e.finished:
                e.finished = True
                if not p.finished:
                    self.state = ENEMY_WIN
                    audio.play('crash', 0.7)
                    audio.stop_engine()
                    audio.set_boost(False)
        self._enemy_hazards(now)
        if not protected:
            self._enemy_player_collisions()
            self._pickup_and_hazards(now)

        self._update_bullets(fs)
        self._update_body(now, fs)      # hump ride + pothole suspension dip

        # finish line
        self._check_finish(fx, fy)

        # cull dead explosions
        self.explosions = [e for e in self.explosions if e.alive]

    def _lose(self):
        """Transition to the wreck screen with the appropriate audio sting."""
        self.state = LOSE
        audio.play('explosion', 0.9)
        audio.stop_engine()
        audio.set_boost(False)

    def _update_catchup(self, now):
        """Rubber-band the pack: rivals dig in when the player pulls clear.

        Recomputed a few times a second (lap progress is a polyline projection,
        so it isn't worth doing every frame)."""
        if now < self._catchup_at:
            return
        self._catchup_at = now + 0.25
        strength = C.DIFFICULTIES[getattr(self, 'difficulty', 3)]['catchup']
        pp = self._lap_progress(self.player.pos[0], self.player.pos[1])
        surging = False
        for e in self.enemies:
            lead = pp - self._lap_progress(e.pos[0], e.pos[1])
            if lead > C.CATCHUP_START:
                t = min(1.0, (lead - C.CATCHUP_START) /
                        (C.CATCHUP_FULL - C.CATCHUP_START))
                e.catchup = 1.0 + t * strength
                surging = surging or t > 0.4
            else:
                e.catchup = 1.0
        if surging and now >= self._catchup_msg:
            self._catchup_msg = now + 9.0
            self.flash("RIVALS CLOSING IN", 1.4)

    def _update_body(self, now, fs):
        """Settle the car's height and pitch onto whatever it's driving over.

        Taken gently, a speed breaker is now RIDDEN: the body follows the
        hump's actual surface (and tips nose-up then nose-down over the crest)
        instead of ploughing straight through it.  Pothole dips are layered on
        top.  Everything is eased so the motion reads as suspension travel."""
        p = self.player
        bump_pitch, bump_drop = p.bump_offset(now)
        terrain = self.track.height_at(p.pos[0], p.pos[1])
        # lie along the hillside as well as any hump
        grade_pitch = -math.degrees(math.atan(getattr(self, 'grade', 0.0))) \
            * C.GRADE_PITCH_K
        if p.jump_active:
            p.pitch += ((bump_pitch + grade_pitch) - p.pitch) * min(1.0, 0.3 * fs)
            return
        ride_z, ride_pitch = 0.0, 0.0
        for br in self.track.speed_breakers:
            z = props.breaker_surface_z(br, p.pos[0], p.pos[1])
            if z > 0.0:
                ride_z = z
                ride_pitch = props.breaker_pitch(br, p.pos[0], p.pos[1])
                break
        target_z = terrain + C.CAR_GROUND_Z + ride_z + bump_drop
        p.pos[2] += (target_z - p.pos[2]) * min(1.0, 0.35 * fs)
        p.pitch += ((ride_pitch + bump_pitch + grade_pitch) - p.pitch) \
            * min(1.0, 0.3 * fs)

    def _update_jump(self, now):
        p = self.player
        if not p.jump_active:
            return
        t = now - p.jump_start
        if t >= C.JUMP_DURATION:
            p.jump_active = False
            p.jump_mode = None
            p.pos[2] = (self.track.height_at(p.pos[0], p.pos[1])
                        + C.CAR_GROUND_Z)
        else:
            if p.jump_mode == "hit":
                p.pos[2] = (self.track.height_at(p.pos[0], p.pos[1])
                            + C.CAR_GROUND_Z + 8)
            else:
                prog = t / C.JUMP_DURATION
                p.pos[2] = (self.track.height_at(p.pos[0], p.pos[1])
                            + C.CAR_GROUND_Z
                            + 4 * C.JUMP_HEIGHT_MAX * prog * (1 - prog))

    def _car_hits_wall(self, x, y, angle):
        a = math.radians(angle)
        ca, sa = math.cos(a), math.sin(a)
        hl, hw = C.CAR_LENGTH / 2, C.CAR_WIDTH / 2
        for lx in (-hl, 0, hl):
            for ly in (-hw, hw):
                wx = x + lx * ca - ly * sa
                wy = y + lx * sa + ly * ca
                if self.track.hits_border(wx, wy):
                    return True
        return False

    def _enemy_player_collisions(self):
        p = self.player
        now = time.time()
        px, py = p.pos[0], p.pos[1]
        for e in self.enemies:
            if math.hypot(px - e.pos[0], py - e.pos[1]) < C.CAR_LENGTH:
                # push the two cars apart so they don't stick together
                dx, dy = px - e.pos[0], py - e.pos[1]
                d = math.hypot(dx, dy) or 1
                nudge = (C.CAR_LENGTH + 6) * 0.5
                p.pos[0] += dx / d * nudge
                p.pos[1] += dy / d * nudge
                e.pos[0] -= dx / d * nudge
                e.pos[1] -= dy / d * nudge
                if not p.shield_active and now >= self.bump_cd:
                    p.lives = max(0, p.lives - e.ram)   # bruisers hit harder
                    self.bump_cd = now + 1.0
                    audio.play('crash', 0.55)
                    if p.lives <= 0:
                        self._lose()

    def _enemy_hazards(self, now):
        """Keep rivals from clipping into each other and let them jump humps."""
        E = self.enemies
        # pairwise separation
        for i in range(len(E)):
            for j in range(i + 1, len(E)):
                a, b = E[i], E[j]
                dx, dy = b.pos[0] - a.pos[0], b.pos[1] - a.pos[1]
                d = math.hypot(dx, dy)
                if 0 < d < C.CAR_LENGTH:
                    push = (C.CAR_LENGTH - d) / 2 + 1
                    nx, ny = dx / d, dy / d
                    a.pos[0] -= nx * push; a.pos[1] -= ny * push
                    b.pos[0] += nx * push; b.pos[1] += ny * push
        # rivals feel the gradient and sit on the hillside just like the player
        for e in E:
            ea = math.radians(e.angle)
            g = self.track.slope_along(e.pos[0], e.pos[1],
                                       math.cos(ea), math.sin(ea))
            gg = max(-1.0, min(1.0, g / C.GRADE_STEEP))
            e.grade_factor = (1.0 + gg * (C.ENEMY_GRADE_UP - 1.0) if gg > 0
                              else 1.0 - gg * (C.ENEMY_GRADE_DOWN - 1.0))
            if not e.jump_active:
                e.pos[2] = self.track.height_at(e.pos[0], e.pos[1]) + C.CAR_GROUND_Z

        # speed-breaker jumps (so rivals arc over the hump instead of clipping)
        for e in E:
            if not e.jump_active:
                for br in self.track.speed_breakers:
                    if props.breaker_local(br, e.pos[0], e.pos[1])[0] is not None:
                        e.jump_active = True
                        e.jump_start = now
                        break
            if e.jump_active:
                t = now - e.jump_start
                if t >= C.JUMP_DURATION:
                    e.jump_active = False
                    e.pos[2] = (self.track.height_at(e.pos[0], e.pos[1])
                                + C.CAR_GROUND_Z)
                else:
                    prog = t / C.JUMP_DURATION
                    e.pos[2] = (self.track.height_at(e.pos[0], e.pos[1])
                                + C.CAR_GROUND_Z
                                + 4 * C.JUMP_HEIGHT_MAX * prog * (1 - prog))

    def _pickup_and_hazards(self, now):
        p = self.player
        px, py = p.pos[0], p.pos[1]
        # health
        remaining = []
        for (hx, hy) in self.health_kits:
            if math.hypot(px - hx, py - hy) < 55 and p.lives < C.PLAYER_MAX_LIVES:
                p.lives += 1
                self.flash("+1 LIFE", 1.2)
                audio.play('pickup', 0.8)
            else:
                remaining.append((hx, hy))
        self.health_kits = remaining
        # shield
        remaining = []
        for (sx, sy) in self.shield_kits:
            if math.hypot(px - sx, py - sy) < 55:
                p.shield_active = True
                p.shield_start = now
                self.flash("SHIELD ON", 1.5)
                audio.play('shield', 0.8)
            else:
                remaining.append((sx, sy))
        self.shield_kits = remaining
        # bombs
        remaining = []
        for (bx, by) in self.bombs:
            if math.hypot(px - bx, py - by) < 30:
                self.explosions.append(props.Explosion(bx, by))
                audio.play('explosion', 0.7)
                if not p.shield_active:
                    p.lives = max(0, p.lives - 1)
                    if p.lives <= 0:
                        self._lose()
            else:
                remaining.append((bx, by))
        self.bombs = remaining
        # potholes: clipping one costs you momentum for a couple of seconds.
        # No damage -- it punishes a sloppy line rather than ending your race.
        if not p.jump_active and now >= self.pothole_cd:
            for (hx, hy, r, _pts) in self.track.potholes:
                if math.hypot(px - hx, py - hy) < r + C.POTHOLE_HIT_RADIUS:
                    p.pothole_until = now + C.POTHOLE_SLOW_TIME
                    p.bump_start = now              # suspension dip animation
                    self.pothole_cd = now + 1.0
                    audio.play('thud', 0.85)
                    self.flash("POTHOLE!", 0.9)
                    break

        # speed breakers: trigger zone matches the visible hump (depth d spans
        # +/- d/2 across Y). One bump per pass (cooldown); no life loss -- just
        # a jump and a brief loss of momentum if taken fast.
        if not p.jump_active and now >= self.breaker_cd:
            for br in self.track.speed_breakers:
                if props.breaker_local(br, px, py)[0] is None:
                    continue
                # A hump taken at speed launches the car (and costs a life);
                # taken gently you simply ride up and over it -- the ride-over
                # is handled every frame in _update_breaker_ride().
                if p.speed >= C.NORMAL_SPEED * C.BREAKER_FAST_LAUNCH:
                    # The faster you hit it the worse it hurts -- taking a hump
                    # at full boost wrecks the car, not just your momentum.
                    flat_out = p.speed >= C.BOOST_SPEED * 0.9
                    damage = C.BREAKER_FAST_DAMAGE * (2 if flat_out else 1)
                    p.jump_active = True
                    p.jump_start = now
                    p.jump_mode = "jump"
                    self.breaker_cd = now + 1.2
                    p.boost_active = False        # kills a boost; slows you
                    p.boost_cd_until = now + C.BOOST_COOLDOWN
                    p.speed = C.NORMAL_SPEED * 0.55
                    p.bump_start = now            # heavy landing jolt
                    audio.play('crash', 0.8)
                    if not p.shield_active:
                        p.lives = max(0, p.lives - damage)
                        self.explosions.append(props.Explosion(px, py, 0.6))
                        self.flash("SPEED BREAKER! -%d ARMOR" % damage, 1.4)
                        if p.lives <= 0:
                            self._lose()
                break

    def _update_bullets(self, fs=1.0):
        alive = []
        now = time.time()
        p = self.player
        protected = now < self.spawn_protect_until
        for b in list(self.bullets):
            b.advance(fs)
            if b.team == "player":
                hit = None
                for e in self.enemies:
                    if math.hypot(b.x - e.pos[0], b.y - e.pos[1]) < C.BULLET_HIT_RADIUS:
                        hit = e
                        break
                if hit:
                    hit.lives -= 1
                    hit.slow_until = now + 2.0
                    self.explosions.append(props.Explosion(b.x, b.y, 0.5))
                    audio.play('explosion', 0.35)
                    continue
            else:  # enemy round -> can wound the player
                if (not protected and
                        math.hypot(b.x - p.pos[0], b.y - p.pos[1]) < C.BULLET_HIT_RADIUS):
                    self.explosions.append(props.Explosion(b.x, b.y, 0.5))
                    if not p.shield_active:
                        p.lives = max(0, p.lives - C.ENEMY_BULLET_DAMAGE)
                        audio.play('crash', 0.6)
                        self.flash("HIT!", 0.8)
                        if p.lives <= 0:
                            self._lose()
                    continue
            if -70000 < b.x < 70000 and -70000 < b.y < 70000:
                alive.append(b)
        self.bullets = alive

    def _check_finish(self, fx, fy):
        fl = self.track.finish_line
        p = self.player
        # A real lap must pass through the far-side checkpoint first. This stops
        # the layout 2/3 exploit where the finish sits within reach of the start.
        if self.checkpoint is not None and not self.checkpoint_reached:
            if math.hypot(p.pos[0] - self.checkpoint[0],
                          p.pos[1] - self.checkpoint[1]) < 320:
                self.checkpoint_reached = True

        if p.finished:
            return
        front_x = p.pos[0] + C.CAR_LENGTH / 2 * fx
        front_y = p.pos[1] + C.CAR_LENGTH / 2 * fy
        fxc, fyc = fl['pos']
        # Test in the finish line's own frame so it works at ANY orientation
        # (procedural circuits cross the line at arbitrary angles).
        tx, ty = self.finish_dir
        dx, dy = front_x - fxc, front_y - fyc
        along = dx * tx + dy * ty            # distance past the line
        across = -dx * ty + dy * tx          # lateral offset along the line
        if abs(across) > fl['width'] / 2 or abs(along) > 30:
            return
        if not self.checkpoint_reached:
            return                            # haven't run the lap yet
        # dot the heading with the racing line's finish direction
        heading_dot = fx * self.finish_dir[0] + fy * self.finish_dir[1]
        if heading_dot > 0.3:                 # crossing the correct way
            p.finished = True
            self.state = WIN
            audio.play('go', 1.0)
            audio.play('pickup', 0.9)
            audio.stop_engine()
            audio.set_boost(False)
        elif heading_dot < -0.3 and time.time() >= self.breaker_cd:
            self.flash("WRONG WAY - turn around!", 1.5)

    def fire(self):
        if self.state != PLAYING:
            return
        now = time.time()
        if now < self.fire_cd:          # rate-limited: keeps the gun audible
            return
        self.fire_cd = now + C.PLAYER_FIRE_COOLDOWN
        p = self.player
        a = math.radians(p.bullet_angle())
        self.bullets.append(Bullet(p.pos[0] + C.CAR_LENGTH / 2 * math.cos(a),
                                   p.pos[1] + C.CAR_LENGTH / 2 * math.sin(a),
                                   30, p.bullet_angle(), team="player"))
        audio.play('shot', 0.6)

    # ------------------------------------------------------------------ render
    def draw_world(self):
        gfx.place_lights()
        gfx.draw_ground(height=self.track.ground_height_at)
        p = self.player
        gfx.draw_sky_bodies((p.pos[0], p.pos[1], p.pos[2]))
        # distant scenery first (hills sit on the horizon, lakes on the ground)
        H = self.track.ground_height_at      # landscape
        RH = self.track.height_at            # road surface
        for (hx, hy, r, hh) in self.hills:
            props.draw_hill(hx, hy, r, hh, base_z=H(hx, hy))
        for (lx, ly, rx, ry) in self.lakes:
            props.draw_lake(lx, ly, rx, ry, base_z=H(lx, ly))
        if self.track.bridge:
            bx, by, ba, blen = self.track.bridge
            deck = self.track.deck_z
            water = deck - self.track.bowl[3] * 0.72
            props.draw_lake(bx, by, self.track.bowl[2] * 0.92,
                            self.track.bowl[2] * 0.92, base_z=water)
            props.draw_bridge(bx, by, ba, blen, deck, water)
        self.track.draw()
        for (rx, ry, rs, ra) in self.rocks:
            props.draw_rock(rx, ry, rs, ra, base_z=H(rx, ry))
        for (tx, ty, ts, tk) in self.trees:
            props.draw_tree(tx, ty, ts, base_z=H(tx, ty), kind=tk)
        night = gfx._active_night()
        for (lx, ly, la) in getattr(self, 'lamps', []):
            props.draw_street_lamp(lx, ly, la, base_z=H(lx, ly), night=night)
        for (sx, sy, w, d, ang) in self.track.speed_breakers:
            props.draw_speed_breaker(sx, sy, w, d, ang, height_fn=RH)
        # pickups and hazards live ON THE ROAD -> road height, so they float
        # correctly above the tarmac instead of sinking into the hillside
        for (hx, hy) in self.health_kits:
            props.draw_health_kit(hx, hy, base_z=RH(hx, hy))
        for (sx, sy) in self.shield_kits:
            props.draw_shield_kit(sx, sy, base_z=RH(sx, sy))
        for (bx, by) in self.bombs:
            props.draw_bomb(bx, by, base_z=RH(bx, by))
        draw_bullets(self.bullets)
        # ground shadows first so cars sit on top of them
        # cars sit on the ROAD, so their shadows use the road height (on the
        # bridge that keeps them on the deck rather than down on the water)
        props.draw_car_shadow(self.player.pos, self.player.angle,
                              base_z=RH(self.player.pos[0], self.player.pos[1]))
        for e in self.enemies:
            props.draw_car_shadow(e.pos, e.angle, base_z=RH(e.pos[0], e.pos[1]))
        self.player.draw()
        if self.player.boost_active:
            props.draw_boost_flames(self.player.pos, self.player.angle)
        for e in self.enemies:
            e.draw()
        for ex in self.explosions:
            ex.draw()

    def display(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        yaw = (time.time() * 4.0) if self.state == MENU else self.player.angle
        gfx.draw_sky(self.width, self.height, yaw=yaw)
        if self.state == MENU:
            hud.draw_menu(self)
            glutSwapBuffers()
            return

        glViewport(0, 0, self.width, self.height)
        self.setup_camera(self.width / self.height)
        self.draw_world()

        hud.draw_minimap(self)
        hud.draw_dashboard(self)
        if self.state == COUNTDOWN:
            hud.draw_countdown(self, self.countdown_value())
        if self.state in (WIN, LOSE, ENEMY_WIN, PAUSED):
            hud.draw_overlay(self)
        glutSwapBuffers()


APP = None


# ---------------------------------------------------------------------------
# GLUT callbacks
# ---------------------------------------------------------------------------
def _display():
    APP.display()


def _timer(_):
    APP.update()
    glutPostRedisplay()
    glutTimerFunc(int(1000 / C.TARGET_FPS), _timer, 0)


def _reshape(w, h):
    APP.width = max(1, w)
    APP.height = max(1, h)
    glViewport(0, 0, w, h)


def _key_down(key, x, y):
    k = key.lower()
    g = APP
    if g.state == MENU:
        if k in (b'\r', b'\n', b' '):
            g.start_race(g.menu_index + 1)
        elif k.isdigit() and 1 <= int(k) <= C.NUM_LAYOUTS:
            g.menu_index = int(k) - 1
        elif k == b'\x1b':
            sys.exit(0)
        return
    if k == b'p':
        if g.state == PLAYING:
            g.state = PAUSED
            audio.set_engine(0.0)
            audio.set_boost(False)
        elif g.state == PAUSED:
            g.state = PLAYING
    elif k == b'r':
        g.start_race(g.track.layout_id)
    elif k == b'm':
        g.state = MENU
        audio.stop_engine()
    elif k == b'v':
        g.fpv = not g.fpv
    elif k == b'\x1b':
        g.state = MENU
        audio.stop_engine()
    elif k == b'w':
        now = time.time()
        p = g.player
        if p.boost_active:
            pass                                  # already boosting
        elif now < p.boost_cd_until:
            g.flash("BOOST RECHARGING", 0.8)      # still on cooldown
        elif g.state == PLAYING:
            p.boost_active = True
            p.boost_start = now
    elif k == b's':
        g.brake = True
    elif k == b'a':
        g.turn_left = True
    elif k == b'd':
        g.turn_right = True
    elif k == b' ':
        g.fire()


def _key_up(key, x, y):
    k = key.lower()
    g = APP
    if k == b's':
        g.brake = False
    elif k == b'a':
        g.turn_left = False
    elif k == b'd':
        g.turn_right = False


def _special_down(key, x, y):
    g = APP
    if g.state == MENU:                    # arrow keys pick a circuit
        if key == GLUT_KEY_UP:
            g.menu_index = (g.menu_index - 1) % C.NUM_LAYOUTS
        elif key == GLUT_KEY_DOWN:
            g.menu_index = (g.menu_index + 1) % C.NUM_LAYOUTS
        return
    if key == GLUT_KEY_LEFT:
        g.gun_left = True
    elif key == GLUT_KEY_RIGHT:
        g.gun_right = True
    elif key == GLUT_KEY_UP:
        g.fire()


def _special_up(key, x, y):
    g = APP
    if key == GLUT_KEY_LEFT:
        g.gun_left = False
    elif key == GLUT_KEY_RIGHT:
        g.gun_right = False


def _mouse(button, state, x, y):
    g = APP
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        if g.state == MENU:
            g.start_race(g.menu_index + 1)
        else:
            g.fire()
    elif button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        g.fpv = not g.fpv


def run():
    global APP
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(C.WINDOW_WIDTH, C.WINDOW_HEIGHT)
    glutInitWindowPosition(60, 30)
    glutCreateWindow(C.WINDOW_TITLE)

    gfx.init_gl()
    glutIgnoreKeyRepeat(1)
    audio.init()

    APP = Game()

    glutDisplayFunc(_display)
    glutReshapeFunc(_reshape)
    glutKeyboardFunc(_key_down)
    glutKeyboardUpFunc(_key_up)
    glutSpecialFunc(_special_down)
    glutSpecialUpFunc(_special_up)
    glutMouseFunc(_mouse)
    glutTimerFunc(int(1000 / C.TARGET_FPS), _timer, 0)
    glutMainLoop()
