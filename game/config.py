"""Central configuration: window, tunables, and the game's color palette.

Everything a designer might want to tweak lives here so the rest of the code
reads as intent rather than magic numbers.
"""

# ---------------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------------
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
WINDOW_TITLE = b"3D Car Rush"
TARGET_FPS = 60

# ---------------------------------------------------------------------------
# World / road geometry (mirrors the proven legacy scale)
# ---------------------------------------------------------------------------
ROAD_WIDTH = 400
BORDER_HEIGHT = 34.0
BORDER_THICKNESS = 14.0
G_LENGTH = 600                 # base unit the hand-built layouts are laid out in
GRID = 8                       # collision grid resolution for road/border sets

# Uniformly enlarges every circuit: all layout positions, lengths and corner
# radii are multiplied by this (road *width* stays the same, so the road stays
# comfortably wide while the laps get bigger and the corners more sweeping).
TRACK_SCALE = 1.5

NUM_LAYOUTS = 5                # selectable circuits on the start menu

# Broken-road detailing. One "damage cluster" (pothole + cracks + grit) is
# scattered per this many square world-units of asphalt; lower = rougher road.
ROAD_DAMAGE_AREA = 136000.0    # halved density -- potholes are an event, not a texture
ROAD_PATCH_AREA = 210000.0     # resurfaced repair squares are rarer

# Hitting a pothole costs you momentum (no damage, just a bogged-down moment).
POTHOLE_SLOW_TIME = 2.0        # seconds
POTHOLE_SLOW_FACTOR = 0.8      # 20% slower while it lasts
POTHOLE_HIT_RADIUS = 14.0      # extra reach beyond the hole's own radius

# ---------------------------------------------------------------------------
# Car dimensions (world units)
# ---------------------------------------------------------------------------
CAR_SCALE = 15
CAR_LENGTH = CAR_SCALE * 2.5
CAR_WIDTH = CAR_SCALE * 1.2
CAR_GROUND_Z = 12.0            # resting height of the chassis centre

# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------
# NOTE ON UNITS:  every speed / turn value below is expressed in "units per
# frame at 60 FPS".  The engine now multiplies all motion by a measured
# frame-scale (dt * 60), so the *distance travelled per second* is identical on
# a slow PC and a fast one -- no more tracks that feel over- or under-sped.
NORMAL_SPEED = 6.6             # cruise pace (raised: the old 5.0 felt sluggish)
BOOST_SPEED = 11.5             # top speed while boosting
SLOW_SPEED = 3.0              # while braking
TURN_SPEED = 1.9               # degrees per frame while turning
BOOST_DURATION = 3.0
BOOST_COOLDOWN = 2.5           # seconds you must wait after a boost before the
                              # next one -- the speed-up can no longer be spammed
# How quickly the car eases toward its target speed (per 60fps frame, 0..1).
# Gives a smooth accelerate/decelerate ramp instead of an instant snap.
SPEED_LERP = 0.10

# Enemy pace (difficulty). Rivals push a touch harder than the player's cruise
# so you must use boost, kits and gunfire to stay ahead.
ENEMY_SPEED_MIN = 7.0
ENEMY_SPEED_MAX = 8.4
ENEMY_MAX_TURN = 4.6           # deg/frame cap -> smooth but corners are makeable
ENEMY_CORNER_SLOWDOWN = 0.5    # fraction of speed kept mid-corner
# Rubber-band punishment: clip a side rail and the rivals surge ahead for a bit.
ENEMY_RAGE_TIME = 3.0          # seconds the surge lasts after a wall bump
ENEMY_RAGE_FACTOR = 1.5        # speed multiplier during the surge

# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------
FOV_Y = 62
NEAR_PLANE = 1.0
FAR_PLANE = 9000.0
CAM_BACK = 190.0               # 3rd-person distance behind the car
CAM_HEIGHT = 95.0
CAM_LOOK_AHEAD = 40.0

# ---------------------------------------------------------------------------
# Combat / hazards
# ---------------------------------------------------------------------------
GUN_TURN_SPEED = 5.0
BULLET_SPEED = 34.0
BULLET_HIT_RADIUS = 55.0
ENEMY_MAX_LIVES = 4
PLAYER_MAX_LIVES = 10
JUMP_HEIGHT_MAX = 22
JUMP_DURATION = 0.8

# Fast speed-breaker hazard (parity with the legacy game): taking a hump at
# speed launches the car AND costs a life unless shielded.
BREAKER_FAST_DAMAGE = 1
BREAKER_FAST_SPEED = NORMAL_SPEED + 0.5   # above this = a dangerous fast hit

# Enemy guns -- rivals only open fire when the player strays too close.
ENEMY_GUN_RANGE = 620.0        # will only shoot the player within this distance
ENEMY_GUN_FOV = 0.35           # aim tolerance (dot of turret vs. line-to-player)
ENEMY_BULLET_SPEED = 26.0
ENEMY_FIRE_COOLDOWN = 1.7      # seconds between an enemy's shots (fewer rounds/sec)
ENEMY_BULLET_DAMAGE = 1
ENEMY_GUN_TURN = 6.0           # deg/frame the enemy turret tracks the player

# ---------------------------------------------------------------------------
# Pickup / hazard counts
# ---------------------------------------------------------------------------
NUM_HEALTH_KITS = 4
NUM_SHIELD_KITS = 3
NUM_BOMBS = 6
NUM_TREES = 80
NUM_HILLS = 14
NUM_LAKES = 3
NUM_ROCKS = 40
SHIELD_DURATION = 5.0

# ---------------------------------------------------------------------------
# Palette  (r, g, b in 0..1)  ----------------------------------------------
# A cohesive dusk-racing palette: cool asphalt, warm sun, teal accents.
# ---------------------------------------------------------------------------
COL_SKY_TOP = (0.16, 0.28, 0.52)
COL_SKY_HORIZON = (0.86, 0.72, 0.62)
COL_FOG = (0.74, 0.70, 0.72)
COL_GROUND = (0.24, 0.42, 0.24)
COL_GROUND_FAR = (0.30, 0.40, 0.30)

COL_ROAD = (0.15, 0.15, 0.17)
COL_ROAD_EDGE = (0.20, 0.20, 0.23)
COL_LANE = (0.92, 0.90, 0.70)
# Broken / weathered asphalt
COL_ROAD_PATCH = (0.20, 0.20, 0.23)   # resurfaced repair square
COL_ROAD_CRACK = (0.085, 0.085, 0.095)
COL_ROAD_HOLE = (0.04, 0.04, 0.045)   # pothole core
COL_ROAD_GRIT = (0.26, 0.25, 0.24)    # loose gravel around damage
COL_BORDER_A = (0.86, 0.20, 0.20)   # kerb stripe A
COL_BORDER_B = (0.94, 0.94, 0.94)   # kerb stripe B

COL_PLAYER_BODY = (0.15, 0.45, 0.85)
COL_PLAYER_ACCENT = (0.10, 0.80, 0.95)
COL_ENEMY_BODY = (0.85, 0.22, 0.24)
COL_GLASS = (0.10, 0.14, 0.20)
COL_TIRE = (0.06, 0.06, 0.07)
COL_RIM = (0.65, 0.67, 0.72)
COL_HEADLIGHT = (1.0, 0.96, 0.75)

COL_HEALTH = (0.90, 0.20, 0.28)
COL_SHIELD = (0.20, 0.75, 1.0)
COL_BOMB = (0.85, 0.18, 0.14)

# Scenery
COL_HILL = (0.26, 0.40, 0.26)
COL_HILL_FAR = (0.34, 0.44, 0.40)
# Hills use a height/slope gradient: shaded grass at the foot, sun-bleached
# grass up top, bare rock on the steep faces.
COL_HILL_LOW = (0.13, 0.30, 0.15)
COL_HILL_HIGH = (0.48, 0.54, 0.31)
COL_HILL_ROCK = (0.40, 0.37, 0.35)
COL_LAKE = (0.16, 0.40, 0.60)
COL_LAKE_EDGE = (0.30, 0.56, 0.62)
COL_ROCK = (0.42, 0.42, 0.46)
COL_ENEMY_TRACER = (1.0, 0.35, 0.2)
COL_PLAYER_TRACER = (1.0, 0.85, 0.3)

# HUD
COL_HUD_PANEL = (0.06, 0.08, 0.11, 0.72)
COL_HUD_EDGE = (0.20, 0.85, 0.95)
COL_HUD_TEXT = (0.86, 0.93, 0.97)
COL_HUD_DIM = (0.55, 0.60, 0.66)
COL_HUD_GOOD = (0.30, 0.90, 0.45)
COL_HUD_WARN = (1.0, 0.75, 0.15)
COL_HUD_BAD = (1.0, 0.32, 0.32)

# Player start (matches legacy, scaled onto the enlarged track)
PLAYER_START = [50.0 * TRACK_SCALE, -600.0 * TRACK_SCALE, CAR_GROUND_Z]


# ---------------------------------------------------------------------------
# Per-circuit visual themes
#
# Each track paints its own world -- sky, haze, ground, asphalt, kerbs and
# hills -- so you can tell at a glance which circuit you're on from the very
# first frame instead of every track looking like the same place.
# ---------------------------------------------------------------------------
THEMES = {
    1: dict(  # Dusk Circuit -- the original cool blue evening
        name="Dusk Circuit",
        sky_top=(0.16, 0.28, 0.52), sky_horizon=(0.86, 0.72, 0.62),
        fog=(0.74, 0.70, 0.72), ground=(0.24, 0.42, 0.24),
        road=(0.15, 0.15, 0.17), road_edge=(0.20, 0.20, 0.23),
        lane=(0.92, 0.90, 0.70),
        kerb_a=(0.86, 0.20, 0.20), kerb_b=(0.94, 0.94, 0.94),
        hill_low=(0.13, 0.30, 0.15), hill_high=(0.48, 0.54, 0.31),
        tree_dark=(0.10, 0.42, 0.14), tree_light=(0.14, 0.60, 0.18),
        sun=(1.0, 0.82, 0.48),
    ),
    2: dict(  # Desert Run -- bleached sand, hot hazy sky
        name="Desert Run",
        sky_top=(0.32, 0.52, 0.78), sky_horizon=(0.96, 0.86, 0.66),
        fog=(0.92, 0.84, 0.68), ground=(0.76, 0.66, 0.40),
        road=(0.26, 0.24, 0.22), road_edge=(0.32, 0.30, 0.27),
        lane=(0.96, 0.94, 0.80),
        kerb_a=(0.20, 0.42, 0.80), kerb_b=(0.96, 0.96, 0.92),
        hill_low=(0.62, 0.48, 0.28), hill_high=(0.86, 0.76, 0.52),
        tree_dark=(0.34, 0.44, 0.20), tree_light=(0.50, 0.58, 0.26),
        sun=(1.0, 0.90, 0.60),
    ),
    3: dict(  # Midnight City -- dark, neon-lit speedway
        name="Midnight City",
        sky_top=(0.03, 0.04, 0.11), sky_horizon=(0.10, 0.13, 0.28),
        fog=(0.10, 0.12, 0.22), ground=(0.10, 0.14, 0.16),
        road=(0.09, 0.09, 0.11), road_edge=(0.13, 0.13, 0.16),
        lane=(0.85, 0.92, 0.98),
        kerb_a=(0.10, 0.78, 0.85), kerb_b=(0.92, 0.95, 1.0),
        hill_low=(0.07, 0.10, 0.14), hill_high=(0.16, 0.20, 0.28),
        tree_dark=(0.06, 0.18, 0.12), tree_light=(0.09, 0.26, 0.16),
        sun=(0.55, 0.70, 1.0),
    ),
    4: dict(  # Alpine Forest -- deep pine green under a crisp sky
        name="Alpine Forest",
        sky_top=(0.20, 0.42, 0.68), sky_horizon=(0.78, 0.86, 0.90),
        fog=(0.72, 0.80, 0.84), ground=(0.16, 0.34, 0.20),
        road=(0.19, 0.19, 0.20), road_edge=(0.24, 0.24, 0.26),
        lane=(0.95, 0.93, 0.75),
        kerb_a=(0.95, 0.80, 0.10), kerb_b=(0.12, 0.12, 0.14),
        hill_low=(0.10, 0.26, 0.16), hill_high=(0.62, 0.68, 0.66),
        tree_dark=(0.06, 0.30, 0.14), tree_light=(0.10, 0.44, 0.18),
        sun=(1.0, 0.95, 0.85),
    ),
    5: dict(  # Canyon Sunset -- red rock and a burning sky
        name="Canyon Sunset",
        sky_top=(0.34, 0.20, 0.42), sky_horizon=(0.98, 0.60, 0.32),
        fog=(0.88, 0.62, 0.46), ground=(0.62, 0.36, 0.24),
        road=(0.21, 0.17, 0.16), road_edge=(0.27, 0.22, 0.20),
        lane=(0.98, 0.90, 0.70),
        kerb_a=(0.80, 0.16, 0.18), kerb_b=(0.98, 0.92, 0.84),
        hill_low=(0.44, 0.22, 0.16), hill_high=(0.80, 0.50, 0.32),
        tree_dark=(0.28, 0.34, 0.16), tree_light=(0.40, 0.46, 0.20),
        sun=(1.0, 0.66, 0.30),
    ),
}

_active_theme = dict(THEMES[1])


def set_theme(layout_id):
    """Make ``layout_id``'s palette current (call before building a track)."""
    global _active_theme
    _active_theme = THEMES.get(layout_id, THEMES[1])


def T(key):
    """Look up a colour in the active circuit theme."""
    return _active_theme[key]
