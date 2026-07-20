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

NUM_LAYOUTS = 5                # menu entries (now DIFFICULTY levels, see below)

# ---------------------------------------------------------------------------
# Difficulty presets
#
# The circuit itself is generated procedurally and differently every race, so
# the five menu entries select how HARD that race is rather than which fixed
# track you drive.  Each preset shapes the generated layout (corner count and
# how irregular it is), the rivals, and how many hazards are strewn about.
# ---------------------------------------------------------------------------
DIFFICULTIES = {
    1: dict(name="ROOKIE",  desc="Open, flowing circuit",
            corners=(6, 7),  size=3000, radius_var=(0.86, 1.14),
            enemy_speed=(6.2, 6.9), enemy_fire=2.6, damage_scale=2.6,
            bombs=6, breakers=1, lives=12, catchup=0.10, enemy_lives=3, elev=0.35),
    2: dict(name="AMATEUR", desc="A few real corners",
            corners=(7, 8),  size=2900, radius_var=(0.82, 1.18),
            enemy_speed=(7.3, 8.1), enemy_fire=2.2, damage_scale=2.2,
            bombs=8, breakers=1, lives=11, catchup=0.18, enemy_lives=4, elev=0.60),
    3: dict(name="PRO",     desc="Technical and quick",
            corners=(8, 10), size=2800, radius_var=(0.78, 1.22),
            enemy_speed=(8.3, 9.3), enemy_fire=1.8, damage_scale=1.9,
            bombs=12, breakers=2, lives=10, catchup=0.26, enemy_lives=5, elev=0.85),
    4: dict(name="EXPERT",  desc="Tight, punishing line",
            corners=(9, 11), size=2750, radius_var=(0.74, 1.26),
            enemy_speed=(9.2, 10.2), enemy_fire=1.5, damage_scale=1.6,
            bombs=14, breakers=2, lives=9, catchup=0.34, enemy_lives=6, elev=1.05),
    5: dict(name="INSANE",  desc="Relentless rivals",
            corners=(10, 13), size=2700, radius_var=(0.70, 1.30),
            enemy_speed=(10.1, 11.2), enemy_fire=1.2, damage_scale=1.4,
            bombs=18, breakers=3, lives=8, catchup=0.45, enemy_lives=7, elev=1.30),
}

# ---------------------------------------------------------------------------
# Terrain elevation
#
# The landscape rolls: circuits climb and descend, and a steep enough drag
# genuinely needs boost to hold speed up.  Each difficulty scales the amplitude
# via its `elev` factor.
# ---------------------------------------------------------------------------
ELEV_BASE_AMP = 130.0          # peak hill height at elev == 1.0
ELEV_WAVELEN = (2600.0, 4600.0)   # world units per hill (long = gentle sweeps)
# Gradient handling. A climb SHIFTS YOU DOWN A GEAR rather than scaling your
# speed: boosting uphill only nets normal pace, and normal pace drops to a
# crawl. A descent shifts you up a gear the same way. Bounding it to the speed
# tiers is what stops steep sections turning into a dead stop.
GRADE_STEEP = 0.28             # slope at which the full one-gear shift applies
# Gravity along the slope. This is what makes hills FEEL physical: rather than
# snapping to a new target speed you visibly build pace on a descent and bleed
# it climbing, and momentum carries you over a crest.
GRAVITY_ACCEL = 0.26           # speed change per 60fps frame at slope 1.0
GRADE_PITCH_K = 0.9            # how much of the slope shows as body pitch
ENEMY_GRADE_UP = 0.70          # rival speed kept on a full climb
ENEMY_GRADE_DOWN = 1.15        # rival speed on a full descent

# Ground mesh. GROUND_TILE must stay small next to ELEV_WAVELEN or the flat
# quads bulge above the curved terrain and the grass pokes through the road.
ROAD_TESS = 110.0              # road surface subdivision along a straight;
                              # must be fine enough to hug the rolling terrain
GROUND_TILE = 130.0
GROUND_DROP = 10.0              # grass sits this far below the road surface

# Sky: real 3-D cloud volumes drifting overhead (the old flat 2-D puffs read
# as static fog because they never parallaxed or rose into view).
NUM_CLOUDS = 26
CLOUD_Z = (1100.0, 2100.0)     # altitude band
CLOUD_SPREAD = 11000.0         # how far they scatter horizontally
CLOUD_DRIFT = 9.0              # world units/sec of wind
NUM_STARS = 220                # night skies only

# Street lighting -- poles down the verges that glow after dark
LAMP_SPACING = 900.0           # distance between poles along the road
LAMP_HEIGHT = 150.0
LAMP_VERGE = 90.0              # pole stands this far beyond the road edge
LAMP_CLEAR2 = 2500.0           # reject a pole within sqrt() of any tarmac
NUM_TREES_EXTRA = 90           # trees added on top of NUM_TREES

# Bridge / lake basin
BRIDGE_DEPTH = 150.0           # how far the ground scoops below the road deck

# Generator guard-rails (unscaled layout units)
GEN_MIN_EDGE = 1150.0          # shortest allowed straight between corners
GEN_MIN_ANGLE = 68.0           # tightest allowed interior angle (degrees)
GEN_FILLET = 320.0             # nominal corner radius before edge clamping

# Broken-road detailing. One "damage cluster" (pothole + cracks + grit) is
# scattered per this many square world-units of asphalt; lower = rougher road.
# Base density; each difficulty multiplies this by its `damage_scale`, so a
# bigger number means FEWER potholes.
ROAD_DAMAGE_AREA = 150000.0
ROAD_PATCH_AREA = 210000.0     # resurfaced repair squares are rarer

# Hitting a pothole costs you momentum (no damage, just a bogged-down moment).
POTHOLE_SLOW_TIME = 2.0        # seconds
POTHOLE_SLOW_FACTOR = 0.8      # 20% slower while it lasts
POTHOLE_HIT_RADIUS = 14.0      # extra reach beyond the hole's own radius
POTHOLE_BUMP_TIME = 0.55       # seconds of the dip-and-recover animation
POTHOLE_BUMP_PITCH = 7.0       # peak nose-down tilt (degrees)
POTHOLE_BUMP_DROP = 4.5        # peak body drop (world units)

# ---------------------------------------------------------------------------
# Speed breakers (humps)
# ---------------------------------------------------------------------------
BREAKER_WIDTH = 400.0          # spans across the road
BREAKER_DEPTH = 170.0          # along the direction of travel
BREAKER_HEIGHT = 18.0          # crest height (low + long = a believable ramp)
BREAKER_MAX_PITCH = 20.0       # clamp so cresting never looks cartoonish
BREAKER_FAST_LAUNCH = 1.15     # speed multiple of NORMAL above which you launch

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
SPEED_FLOOR = 1.2              # gravity can bog you down but never stall you
SPEED_CEILING = BOOST_SPEED * 1.35   # terminal velocity down a steep descent

# Enemy pace (difficulty). Rivals push a touch harder than the player's cruise
# so you must use boost, kits and gunfire to stay ahead.
ENEMY_SPEED_MIN = 7.0
ENEMY_SPEED_MAX = 8.4
ENEMY_MAX_TURN = 4.6           # deg/frame cap -> smooth but corners are makeable
ENEMY_CORNER_SLOWDOWN = 0.5    # fraction of speed kept mid-corner
# Rubber-band punishment: clip a side rail and the rivals surge ahead for a bit.
ENEMY_RAGE_TIME = 3.0          # seconds the surge lasts after a wall bump
ENEMY_RAGE_FACTOR = 1.5        # speed multiplier during the surge

# Rival roles -- each race fields one of each, so the pack has a fast-but-frail
# car, a tanky bully and a trigger-happy gunner instead of three clones.
# (speed multiplier, bonus armour, fire-rate multiplier, ram damage)
ENEMY_ROLES = (
    dict(tag="SPR", name="Sprinter", speed=1.14, armor=-1, fire=1.4, ram=1),
    dict(tag="BRU", name="Bruiser",  speed=0.93, armor=+2, fire=1.2, ram=2),
    dict(tag="GUN", name="Gunner",   speed=1.02, armor=0,  fire=0.6, ram=1),
)

# Catch-up ("rubber band"): rivals dig in when the player pulls clear, so a
# good lead never turns into a boring procession. Strength is per-difficulty.
CATCHUP_START = 900.0          # lead (world units) before rivals respond
CATCHUP_FULL = 3200.0          # lead at which the surge reaches full strength

# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------
FOV_Y = 62
NEAR_PLANE = 6.0
FAR_PLANE = 9000.0
CAM_BACK = 190.0               # 3rd-person distance behind the car
CAM_HEIGHT = 95.0
CAM_LOOK_AHEAD = 40.0
CAM_MIN_CLEAR = 45.0           # never let the eye dip below the terrain
# Combat / hazards
# ---------------------------------------------------------------------------
GUN_TURN_SPEED = 5.0
PLAYER_FIRE_COOLDOWN = 0.22    # rate-limits the gun so rapid taps can't spam
                              # dozens of overlapping shot sounds
BULLET_SPEED = 34.0
BULLET_HIT_RADIUS = 55.0
ENEMY_MAX_LIVES = 8
PLAYER_MAX_LIVES = 10
JUMP_HEIGHT_MAX = 22
JUMP_DURATION = 0.8

# Fast speed-breaker hazard (parity with the legacy game): taking a hump at
# speed launches the car AND costs a life unless shielded.
BREAKER_FAST_DAMAGE = 1
BREAKER_FAST_SPEED = NORMAL_SPEED + 0.5   # above this = a dangerous fast hit

# Enemy guns -- rivals only open fire when the player strays too close.
ENEMY_GUN_RANGE = 720.0        # will only shoot the player within this distance
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
NUM_TREES = 150
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
        road=(0.19, 0.18, 0.17), road_edge=(0.24, 0.23, 0.21),
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
        sun=(0.55, 0.70, 1.0), night=True,
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
        road=(0.17, 0.15, 0.15), road_edge=(0.22, 0.19, 0.18),
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
