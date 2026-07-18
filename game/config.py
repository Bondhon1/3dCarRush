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
NORMAL_SPEED = 5.0
BOOST_SPEED = 10.0
SLOW_SPEED = 2.0
TURN_SPEED = 1.2               # degrees per frame while turning
BOOST_DURATION = 3.0

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

# ---------------------------------------------------------------------------
# Pickup / hazard counts
# ---------------------------------------------------------------------------
NUM_HEALTH_KITS = 4
NUM_SHIELD_KITS = 3
NUM_BOMBS = 6
NUM_TREES = 60
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

# HUD
COL_HUD_PANEL = (0.06, 0.08, 0.11, 0.72)
COL_HUD_EDGE = (0.20, 0.85, 0.95)
COL_HUD_TEXT = (0.86, 0.93, 0.97)
COL_HUD_DIM = (0.55, 0.60, 0.66)
COL_HUD_GOOD = (0.30, 0.90, 0.45)
COL_HUD_WARN = (1.0, 0.75, 0.15)
COL_HUD_BAD = (1.0, 0.32, 0.32)

# Player start (matches legacy)
PLAYER_START = [50.0, -600.0, CAR_GROUND_Z]
