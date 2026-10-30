"""All tunable constants for EMG Lane Dodger. Nothing tunable is hard-coded elsewhere."""
import pygame

# Window
WIDTH, HEIGHT = 600, 800            # LOGICAL game resolution: all game coordinates use this
FPS = 60
MAX_DT = 0.05                       # s, frame time cap (avoids jumps after a hiccup / window drag)
WINDOW_START_SIZE = (600, 800)      # initial size of the real, resizable window
TITLE = "EMG Lane Dodger"

# Road / lanes
N_LANES = 3
ROAD_MARGIN = 50                    # px of grass on each side
LANE_WIDTH = (WIDTH - 2 * ROAD_MARGIN) / N_LANES
DASH_LEN, DASH_GAP = 40, 30         # lane divider dashes
DASH_WIDTH = 6
MENU_SCROLL_SPEED = 120             # px/s, idle road scrolling behind the menu

# Distance / units
PIXELS_PER_METER = 20               # 250 px/s = 12.5 m/s = 45 km/h

# Player car
CAR_W, CAR_H = 0.6 * LANE_WIDTH, 100
CAR_Y = HEIGHT - 150                # fixed vertical position (top edge)
LANE_SWITCH_TIME = 0.12             # s, duration of the sliding animation
START_LANE = N_LANES // 2

# Speed / difficulty
SPEED_START = 250                   # px/s
SPEED_MAX = 900                     # px/s
SPEED_ACCEL = 6                     # px/s gained per second of play

# Obstacles
SPAWN_INTERVAL_START = 1.4          # s
SPAWN_INTERVAL_MIN = 0.45           # s
MIN_REACTION_TIME = 0.7             # s: guarantees a dodge is always possible
MAX_OBST_PER_ROW = N_LANES - 1      # never block every lane
DOUBLE_SPAWN_PROB = 0.25            # chance a row has 2 obstacles (if N_LANES >= 3)
OBSTACLE_TYPES = {                  # relative spawn weight, width (fraction of LANE_WIDTH), height (px)
    "rock":        {"weight": 3, "w": 0.55, "h": 60},
    "tree":        {"weight": 3, "w": 0.65, "h": 110},
    "stickman":    {"weight": 2, "w": 0.35, "h": 90},
    "crashed_car": {"weight": 2, "w": 0.60, "h": 100},
}
HITBOX_SHRINK = 0.15                # hitboxes shrink by this fraction on each side (forgiving)

# Stars (bonus pickups). Score = meters + STAR_POINTS * stars caught
STAR_POINTS = 50
STAR_SIZE = 40                      # px, outer diameter
STAR_ROW_PROB = 0.5                 # chance an obstacle row also gets a star in one of its free lanes
STAR_MID_PROB = 0.35                # chance of a star halfway between two rows (any lane, can tempt you)
POPUP_TIME = 0.8                    # s, "+50" text rising after a catch
USE_SPRITES = False                 # True -> load assets/<kind>.png instead of drawing shapes
ASSETS_DIR = "assets"

# Countdown / crash
COUNTDOWN_TIME = 3.0                # s, before a new run
RESUME_COUNTDOWN_TIME = 1.0         # s, after a pause
GO_TIME = 0.3                       # s, "GO!" shown after the countdown
CRASH_ANIM_TIME = 1.0               # s of crash animation before the result screen
CRASH_SHAKE = 6                     # px, max car shake during the crash animation

# High scores
HIGHSCORE_FILE = "highscores.json"  # stored next to the scripts, not in the working directory
N_HIGHSCORES = 10
NAME_MAX_LEN = 10
DEFAULT_NAME = "Player"

# Input mode (overridden by the command line: python lane_dodger.py --input osc)
INPUT_MODE = "keyboard"             # "keyboard" or "osc" (keyboard stays active in osc mode too)

# OSC input: commands sent by Bonsai (Bonsai.Osc CreateUdpClient + SendMessage)
OSC_HOST = "127.0.0.1"              # listen on this machine only
OSC_LISTEN_IPV6 = True              # also listen on ::1, in case Bonsai's "localhost" resolves to IPv6
OSC_PORT = 5005                     # = RemotePort of Bonsai's "UdpSend" CreateUdpClient

# Main address (= Address of Bonsai's SendMessage). Two kinds of messages are understood on it:
# 1) PAIR, from Zip/CombineLatest(left, right): exactly 2 numbers/bools ("ii", "ff", "TF")
#    Item1 = LEFT channel (muscle 1), Item2 = RIGHT channel (muscle 2). A channel triggers ONE
#    command when it goes from inactive to active (rising edge): every-sample or on-change both work.
# 2) KEY, from KeyDown -> SendMessage: one event per key press. The game looks for the key
#    (as a key code like 65, a name like "A", or inside the serialized key event) and maps it:
OSC_ADDRESS_PAIR = "/mcoords"
OSC_PAIR_THRESHOLD_ON = 0.5         # channel becomes active when value > this (0/1 ints, bools, 0..1 floats)
OSC_PAIR_THRESHOLD_OFF = 0.5        # ... and inactive again when value <= this (set lower for hysteresis)
OSC_KEY_LEFT = "A"                  # Bonsai KeyDown Filter for LEFT  (letters/digits: Windows key code = ASCII)
OSC_KEY_RIGHT = "S"                 # Bonsai KeyDown Filter for RIGHT

# Alternative single-value addresses (also accepted)
OSC_ADDRESS_CMD = "/lanedodger/cmd"     # int 1 = LEFT, 2 = RIGHT (0 = nothing), or string "LEFT"/"RIGHT"
OSC_ADDRESS_LEFT = "/lanedodger/left"   # any true / non-zero value (or no argument) = LEFT
OSC_ADDRESS_RIGHT = "/lanedodger/right" # any true / non-zero value (or no argument) = RIGHT
OSC_TRIGGER = "every"               # (single-value addresses only; the pair address is always rising-edge)
                                    # "every": each active message = one command
                                    # "rising": one command only when an address becomes active
                                    #   (use it if Bonsai streams a held state continuously)
# OSC output: game events sent TO Bonsai (osc mode only), e.g. to play a sound on a Harp board
OSC_SEND_HOST = "127.0.0.1"
OSC_SEND_PORT = 5006                # = Port of Bonsai's "UdpReceive" CreateUdpClient
OSC_ADDRESS_STAR = "/lanedodger/star"   # binary star signal, int (Bonsai ReceiveMessage: TypeTag = i):
                                        #   0 at startup, 1 when a star is caught, back to 0 after STAR_PULSE_TIME
STAR_PULSE_TIME = 0.1               # s the star signal stays at 1
PAUSE_ON_FOCUS_LOST = True          # keyboard mode: pause when the game window loses focus
PAUSE_ON_FOCUS_LOST_OSC = False     # osc mode: keep running (you may click in Bonsai while playing)

# Keyboard mapping
KEYS_LEFT = [pygame.K_LEFT, pygame.K_a]
KEYS_RIGHT = [pygame.K_RIGHT, pygame.K_d]
KEYS_LEFT_OSC = [pygame.K_LEFT]     # in osc mode: arrows only, because Bonsai KeyDown is global and
KEYS_RIGHT_OSC = [pygame.K_RIGHT]   #   letter keys (A, S...) used in Bonsai would move the car twice
KEYS_START = [pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER]   # start / restart / resume
KEYS_PAUSE = [pygame.K_p]
KEYS_BACK = [pygame.K_ESCAPE]       # in game: pause; paused/game over: menu; menu: quit

# Fonts (pygame default font, sizes in logical px)
FONT_BIG, FONT_MEDIUM, FONT_SMALL, FONT_TINY = 72, 40, 28, 22

# Colors (RGB, or RGBA where noted)
BLACK = (0, 0, 0)
GRASS = (62, 140, 62)
GRASS_DARK = (48, 115, 48)
ROAD = (72, 72, 78)
ROAD_EDGE = (225, 225, 225)
LANE_LINE = (240, 240, 240)
CAR = (35, 115, 225)
CAR_DARK = (20, 70, 150)
CAR_WINDOW = (175, 215, 245)
HEADLIGHT = (255, 240, 150)
WHEEL = (25, 25, 25)
TEXT = (255, 255, 255)
TEXT_DIM = (185, 185, 185)
TEXT_HIGHLIGHT = (255, 210, 60)
OVERLAY_BG = (0, 0, 0, 175)         # RGBA
CRASH_FLASH = (255, 40, 40)
ROCK = (135, 135, 140)
ROCK_DARK = (80, 80, 85)
ROCK_LIGHT = (175, 175, 180)
TREE_TRUNK = (110, 75, 40)
TREE_LEAVES = (45, 155, 55)
TREE_LEAVES_DARK = (25, 100, 35)
TREE_LEAVES_LIGHT = (95, 195, 95)
STICKMAN = (20, 20, 20)
STICKMAN_SHIRT = (255, 95, 40)
SKIN = (240, 200, 160)
WRECK_BODY = (150, 70, 55)
WRECK_DARK = (85, 35, 30)
WRECK_WINDOW = (55, 65, 75)
SMOKE = (130, 130, 130)
FIRE = (255, 140, 0)
FIRE_CORE = (255, 230, 80)
STAR = (255, 215, 0)
STAR_DARK = (190, 130, 0)
STAR_GLOW = (255, 240, 150)
