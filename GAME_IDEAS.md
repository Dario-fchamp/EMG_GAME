# EMG-Controlled Game: Design Proposal

Two muscles, two commands: **LEFT** (muscle 1) and **RIGHT** (muscle 2).
You handle acquisition and command detection. The game only receives commands.

---

## 1. Command Interface (shared by all games)

I suggest the game accepts two kinds of input, so you can pick whichever works best for your signal:

| Mode | What you send | Typical use |
|------|---------------|-------------|
| **Discrete (event)** | `LEFT` / `RIGHT` pulses, sent once per contraction onset | Step-wise moves (change lane, jump) |
| **Continuous (state)** | `left_active: bool`, `right_active: bool`, optionally `left_level: 0..1`, `right_level: 0..1` | Hold-to-move, proportional speed |

**Threshold or acceleration?** I'd go with a threshold on the **envelope** (rectified + low-pass filtered, or RMS over a 50–150 ms window), using:
- **Hysteresis**: ON threshold above the OFF threshold, so the signal doesn't flicker around one value.
- **Refractory period** (~200–300 ms) after each discrete event, so one contraction gives one command.
- Optional **co-contraction** (both muscles above threshold) as a third command, e.g. pause/start or confirm.

Using the derivative ("acceleration") of the raw EMG makes noise worse. It is only worth trying on the smoothed envelope, if you want very fast onset detection.

**Transport**: the game reads from a `CommandSource` class. I'll provide:
- `KeyboardSource`: arrow keys, so the game can be tested without EMG.
- `UDPSource` (or a `queue.Queue` / LSL inlet if you prefer): your acquisition code sends small messages such as `LEFT`, `RIGHT`, or `{"l":0.7,"r":0.0}`.

Swapping between keyboard and EMG input is one line of config.

**Stack**: Python 3 + `pygame`. One file per game, plus the shared input module.

---

## 2. Game Ideas

### Idea A: Lane Dodger 🚗
A car drives on a 3- (or 5-) lane road. Obstacles scroll down from the top.
- **LEFT** → move one lane left, **RIGHT** → move one lane right.
- Score = distance survived; speed slowly increases.
- **Input mode**: discrete events (the most forgiving for EMG).
- **Why it fits**: one clear contraction = one action. Easy to learn, and it tolerates latency at low speeds.
- **Difficulty to code**: ⭐ (very easy)

### Idea B: Basket Catcher 🧺
A basket at the bottom of the screen catches falling objects (fruits = good, bombs = bad).
- Basket moves **left/right while the muscle is active**. With `level` values, speed is proportional to contraction strength.
- Score = items caught; lives lost on bombs or missed fruits.
- **Input mode**: continuous (bool or proportional).
- **Why it fits**: trains sustained and graded control, not just onsets. It also works as a biofeedback/training task.
- **Difficulty to code**: ⭐ (very easy)

### Idea C: Reaction Arena 🎯 (research-friendly)
A target appears on the **left** or **right** side at random intervals. The player contracts the matching muscle as fast as possible.
- Correct and fast → points; wrong side or too slow → miss.
- Logs every trial to CSV: cue time, response time, reaction time, correct/incorrect.
- Optional "Go/No-Go" variant: red targets must be ignored.
- **Input mode**: discrete events.
- **Why it fits**: doubles as an experimental paradigm. You get reaction times and error rates per muscle for free, and you can align timestamps with your EMG recording.
- **Difficulty to code**: ⭐⭐ (easy; logging and timing need some extra care)

---

## 3. Recommendation

- Start with **A (Lane Dodger)** to validate the pipeline end-to-end, since discrete commands are the most robust.
- Use **C (Reaction Arena)** if you want quantitative data from the sessions.
- Use **B (Basket Catcher)** if you want to exploit the analogue nature of EMG (proportional control).

All three share the same `CommandSource` interface, so writing the second and third is cheap once the first is done.

---

## 4. Open Questions for You

1. ~~Which game(s) should I implement first?~~ → **Game A (Lane Dodger)**.
2. ~~How will commands reach the game?~~ → **Bonsai reads the EMG and launches the script (later). Keyboard only for now**.
3. ~~Discrete events, continuous levels, or both?~~ → **Discrete, one command per contraction**.
4. ~~Co-contraction as a third command?~~ → **No. Menus are keyboard-only; keyboard is always a fallback**.
5. ~~Timestamped CSV logs?~~ → **Not for now. Show the score (meters until crash) and keep a Top 10**.

---

## 5. Implementation Spec: Game A (Lane Dodger), Keyboard Version

This section is meant to be handed to a coding agent as-is.

**Decisions (confirmed):**
- **Keyboard only for now.** EMG is out of scope. Later, Bonsai will read the EMG commands and launch the Python script. The input layer is kept behind a small `CommandSource` interface so a Bonsai source can be added later without touching the game logic (see 5.11).
- Gameplay commands are discrete: **LEFT** / **RIGHT**, one lane per key press (later: one per contraction).
- **One crash = game over.** No lives.
- **Score = distance driven, in meters**, shown live and on the game-over screen.
- **Top 10 scores** are kept across sessions (saved to a JSON file).
- **No CSV log** for now.
- Obstacles are **rocks, trees, stickmen and crashed cars**, drawn with pygame shapes (no image files needed).
- **3 lanes**; speed **accelerates over time** up to a cap.
- Top 10 entries: the player **types a name** when their score qualifies.
- **Resizable window** (starts at 600x800). The game renders at a fixed logical resolution and is scaled to fit, keeping the aspect ratio.
- **No sound.**
- **Single global Top 10**, saved next to the script. No reset key: delete `highscores.json` to reset.
- **Lane switching only**: the car has no boost/brake. LEFT/RIGHT map exactly to the 2 future EMG commands.
- **Conda environment**: Python 3.11, pygame as the only dependency (`environment.yml`). Bonsai will later call that environment's `python.exe`.

### 5.1 File Structure

```
EMG_GAME/
├── GAME_IDEAS.md
├── environment.yml         # conda env "emg_game": python=3.11, pip: pygame>=2.5
├── config.py               # every tunable constant
├── input_sources.py        # Command enum + CommandSource interface + KeyboardSource
├── obstacles.py            # Obstacle class + procedural drawing of each obstacle type
├── highscores.py           # load / save / insert top-10 scores
├── lane_dodger.py          # the game (entry point): python lane_dodger.py
└── highscores.json         # created at runtime
```

### 5.2 `config.py`

```
# Window
WIDTH = 600, HEIGHT = 800, FPS = 60  # LOGICAL game resolution: all game coordinates use this
WINDOW_START_SIZE = (600, 800)       # initial size of the real, RESIZABLE window
TITLE = "EMG Lane Dodger"

# Road / lanes
N_LANES = 3
ROAD_MARGIN = 50                    # px of grass on each side
LANE_WIDTH = (WIDTH - 2*ROAD_MARGIN) / N_LANES
DASH_LEN = 40, DASH_GAP = 30        # lane divider dashes

# Distance / units
PIXELS_PER_METER = 20               # 250 px/s = 12.5 m/s = 45 km/h

# Player car
CAR_W = 0.6 * LANE_WIDTH, CAR_H = 100
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
HITBOX_SHRINK = 0.15                # hitboxes are 15% smaller than the drawing (forgiving)
USE_SPRITES = False                 # True -> load assets/<kind>.png instead of drawing shapes

# Game over
CRASH_ANIM_TIME = 1.0               # s of crash animation before the game-over screen

# High scores
HIGHSCORE_FILE = "highscores.json"  # stored next to the script (use the script's folder, not the cwd,
                                    # because Bonsai may launch it from another working directory)
N_HIGHSCORES = 10
NAME_MAX_LEN = 10
DEFAULT_NAME = "Player"

# Keyboard mapping
KEYS_LEFT  = [K_LEFT, K_a]
KEYS_RIGHT = [K_RIGHT, K_d]
KEYS_START = [K_SPACE, K_RETURN]    # start / restart / resume
KEYS_PAUSE = [K_p]
KEYS_BACK  = [K_ESCAPE]             # in game: pause; paused/game over: menu; menu: quit

# Colors (RGB): GRASS, ROAD, LANE_LINE, CAR, CAR_WINDOW, TEXT, TEXT_HIGHLIGHT, OVERLAY_BG,
#   ROCK, ROCK_DARK, TREE_TRUNK, TREE_LEAVES, TREE_LEAVES_DARK, STICKMAN, STICKMAN_SHIRT,
#   WRECK_BODY, WRECK_DARK, SMOKE, FIRE
```

### 5.3 `input_sources.py`

The game never reads `pygame.KEYDOWN` for steering directly. It only consumes `Command`s from sources. This is what lets Bonsai be plugged in later.

```
enum Command: LEFT, RIGHT, START, PAUSE, BACK, QUIT

abstract class CommandSource:
    start()             -> None
    poll(pygame_events) -> list[Command]    # non-blocking; all commands since the last call
    stop()              -> None

class KeyboardSource(CommandSource):
    poll(pygame_events):
        out = []
        for e in pygame_events:
            if e.type == KEYDOWN:           # KEYDOWN only -> holding a key = one command
                key in KEYS_LEFT  -> LEFT
                key in KEYS_RIGHT -> RIGHT
                key in KEYS_START -> START
                key in KEYS_PAUSE -> PAUSE
                key in KEYS_BACK  -> BACK
            if e.type == pygame.QUIT -> QUIT   # window close button
        return out
```

Name entry on the high-score screen needs raw text input, so in that state the game reads `pygame.TEXTINPUT` / `K_BACKSPACE` events directly (see 5.7). This is the only place the game touches raw keyboard events.

### 5.4 `highscores.py`

```
file format (JSON list, sorted best first, max N_HIGHSCORES entries):
    [ {"name": "Dario", "meters": 1534, "date": "2026-10-29 14:32"}, ... ]

path(): os.path.join(os.path.dirname(os.path.abspath(__file__)), HIGHSCORE_FILE)

load() -> list:
    if file missing -> return []
    try: read JSON, keep only valid entries (name: str, meters: int), sort desc by meters, cut to N
    except (JSONDecodeError, OSError): print warning, return []   # never crash over a bad file

qualifies(scores, meters) -> bool:
    return meters > 0 and (len(scores) < N_HIGHSCORES or meters > scores[-1]["meters"])

insert(scores, name, meters) -> (new_scores, rank):
    entry = {"name": name or DEFAULT_NAME, "meters": meters, "date": now formatted}
    insert, sort desc by meters (ties: older entry stays above), cut to N
    rank = index of the new entry (0-based), or None if it was cut
    return new_scores, rank

save(scores):
    write to a temp file in the same folder, then os.replace(temp, path)   # atomic, no corrupt file
    on OSError: print warning, keep playing
```

### 5.5 Game Entities

```
function lane_center_x(lane): return ROAD_MARGIN + (lane + 0.5) * LANE_WIDTH

class Car:                                  # in lane_dodger.py
    lane = START_LANE
    x = lane_center_x(lane)                 # current drawn center x (float)
    anim_from_x = anim_to_x = x
    anim_t = LANE_SWITCH_TIME               # = not animating

    move(direction):                        # -1 (LEFT) or +1 (RIGHT)
        new_lane = lane + direction
        if new_lane < 0 or new_lane >= N_LANES: return   # at the edge: ignore
        lane = new_lane
        anim_from_x = x                     # start from CURRENT x (works mid-animation)
        anim_to_x = lane_center_x(lane)
        anim_t = 0

    update(dt):
        if anim_t < LANE_SWITCH_TIME:
            anim_t += dt
            k = clamp(anim_t / LANE_SWITCH_TIME, 0, 1)
            k = 1 - (1 - k)**2              # ease-out
            x = lerp(anim_from_x, anim_to_x, k)

    hitbox(): Rect centered on x, top CAR_Y, size (CAR_W, CAR_H), shrunk by HITBOX_SHRINK
    draw(screen):
        rounded rect body CAR, windshield + rear window CAR_WINDOW, 4 dark wheels at corners,
        2 small yellow headlights at the top

class Obstacle:                             # in obstacles.py
    __init__(lane, kind):
        spec = OBSTACLE_TYPES[kind]
        w = spec["w"] * LANE_WIDTH, h = spec["h"]
        y = -h                              # top edge, starts just above the screen
        variant = random.random()           # per-instance randomness (shape, tilt, colors)
    update(dt, speed): y += speed * dt
    rect():   Rect centered on lane_center_x(lane), top y, size (w, h)    # drawing area
    hitbox(): rect() shrunk by HITBOX_SHRINK on each side
    off_screen(): y > HEIGHT
    draw(screen, t): DRAWERS[kind](screen, rect(), variant, t)
                     (or blit assets/<kind>.png scaled to rect if USE_SPRITES)

class RoadScroller:
    offset = 0
    update(dt, speed): offset = (offset + speed*dt) % (DASH_LEN + DASH_GAP)
    draw(screen): fill GRASS, draw ROAD rectangle between margins,
                  draw dashed LANE_LINE dividers between lanes, shifted down by offset
                  (optional: decorative grass tufts on the margins scrolling at the same speed)
```

#### Obstacle drawings (`obstacles.py`, pygame primitives only)

All drawers take `(surface, rect, variant, t)` and draw inside `rect`. `variant` (0..1) makes each instance a bit different: seed a `random.Random(variant)` inside the drawer so the shape stays the same every frame. `t` = elapsed time, used for small animations. View: top-down / slightly from the front, like a classic arcade racer.

```
draw_rock(surf, r, v, t):
    # irregular grey boulder
    shadow: dark semi-transparent ellipse slightly below r
    points: 8 points around r.center, angle i*45° ± jitter, radius_x = r.w/2 * (0.8..1.0),
            radius_y = r.h/2 * (0.8..1.0)           (jitter from the seeded RNG)
    polygon(ROCK, points); polygon outline (ROCK_DARK, width 3)
    2-3 short ROCK_DARK lines inside as cracks; 1 lighter small polygon as highlight

draw_tree(surf, r, v, t):
    # trunk + round foliage
    shadow ellipse at the bottom
    trunk: TREE_TRUNK rect, width r.w*0.2, bottom 35% of r, centered
    foliage: 3 overlapping TREE_LEAVES circles (left, right, top) covering the upper 70% of r
    shading: one TREE_LEAVES_DARK circle offset bottom-right, drawn first

draw_stickman(surf, r, v, t):
    # pedestrian standing on the road, lines width 3
    head:  circle radius r.w*0.25 at the top, STICKMAN outline + skin fill
    body:  line neck -> hips (mid-height), in STICKMAN_SHIRT (bright, visible on grey road)
    arms:  2 lines from the shoulders, waving: angle = 30° * sin(t*6 + v*10)
    legs:  2 lines from the hips, walking swing: angle = 15° * sin(t*8 + v*10)

draw_crashed_car(surf, r, v, t):
    # wrecked car, tilted 10-25° (sign from variant) so it looks crashed
    draw on a temporary SRCALPHA Surface of size (r.w, r.h), then
    pygame.transform.rotate, then blit centered on r.center:
        body:        rounded rect WRECK_BODY (different color from the player car)
        windshield:  darker quad with 2 crack lines
        dent:        WRECK_DARK polygon cut into one side
        wheels:      4 dark rects at the corners, one offset (broken)
    smoke (drawn after, not rotated): 3 SMOKE semi-transparent circles above the car;
        each rises and fades in a loop: phase = (t*0.8 + i/3 + v) % 1,
        y_offset = -phase * 40, alpha = 160 * (1 - phase), radius = 8 + phase*10
    optional fire: small FIRE triangle, height * (1 + 0.2*sin(t*20))
    hitbox: the un-rotated rect, shrunk (simple and forgiving)

DRAWERS = {"rock": draw_rock, "tree": draw_tree,
           "stickman": draw_stickman, "crashed_car": draw_crashed_car}
```

### 5.6 Spawning Rules (fairness)

```
class Spawner:
    timer = 0
    update(dt, speed) -> list[Obstacle]:
        interval = SPAWN_INTERVAL_START * SPEED_START / speed     # faster road -> denser rows
        interval = max(interval, SPAWN_INTERVAL_MIN)
        # Fairness: time between rows must cover the tallest obstacle + a lane switch + reaction
        tallest = max(t["h"] for t in OBSTACLE_TYPES.values())
        interval = max(interval, MIN_REACTION_TIME + tallest / speed)
        timer += dt
        if timer < interval: return []
        timer = 0
        n = 2 if (N_LANES >= 3 and random() < DOUBLE_SPAWN_PROB) else 1
        n = min(n, MAX_OBST_PER_ROW)
        lanes = random.sample(range(N_LANES), n)
        kinds = random.choices(list(OBSTACLE_TYPES),
                               weights=[t["weight"] for t in OBSTACLE_TYPES.values()], k=n)
        return [Obstacle(l, k) for l, k in zip(lanes, kinds)]
```

Every row leaves at least one free lane, and consecutive rows are spaced so a dodge is always possible.

### 5.7 Game States

```
MENU        title "EMG LANE DODGER", controls help, TOP 10 table
            "SPACE / ENTER: start    ESC: quit"
            START -> reset_game(); COUNTDOWN (3 s)        BACK -> quit

COUNTDOWN   road visible but frozen; big "3", "2", "1", then "GO!" (0.3 s); LEFT/RIGHT ignored
            -> PLAYING when done                           BACK -> MENU

PLAYING     main gameplay; LEFT/RIGHT steer
            PAUSE or BACK -> PAUSED
            window loses focus (pygame.WINDOWFOCUSLOST) -> PAUSED

PAUSED      world frozen; overlay "PAUSED - SPACE: resume    ESC: menu"
            START or PAUSE -> COUNTDOWN (1 s)             BACK -> MENU (run discarded, not saved)

CRASHED     entered on collision; lasts CRASH_ANIM_TIME; world frozen
            animation: car shakes (random ±5 px), red flash overlay fading out,
            a few orange/grey circles expanding at the impact point
            input ignored (avoids skipping the result by accident)
            then: if highscores.qualifies(scores, meters) -> NAME_ENTRY else -> GAME_OVER

NAME_ENTRY  "NEW HIGH SCORE!  1534 m  - rank #3"
            "Enter your name:" text field with blinking cursor; pygame.key.start_text_input()
            TEXTINPUT: append printable chars (max NAME_MAX_LEN)
            K_BACKSPACE: delete last char
            K_RETURN: confirm -> highscores.insert + save; remember rank -> GAME_OVER
            K_ESCAPE: confirm with DEFAULT_NAME
            (on leaving: pygame.key.stop_text_input())
            Note: SPACE goes into the name here, so START is NOT used to confirm in this state.

GAME_OVER   "CRASHED!"   "Distance: 1534 m"   (big, centered)
            "Top speed: 162 km/h"  (optional)
            TOP 10 table, with the new entry highlighted (TEXT_HIGHLIGHT) if it got in
            "SPACE / ENTER: play again    ESC: menu"
            START -> reset_game(); COUNTDOWN (3 s)        BACK -> MENU

any state   QUIT (window close) -> clean shutdown (pygame.quit, sys.exit)
```

TOP 10 table layout: `rank. name ........ meters m   date`, with aligned columns (render each column separately at a fixed x). If there are fewer than 10 scores, show empty rows as `-`.

### 5.8 Main Loop (`lane_dodger.py`)

```
main():
    pygame.init()
    window = set_mode(WINDOW_START_SIZE, pygame.RESIZABLE); set_caption(TITLE); clock = Clock()
    screen = pygame.Surface((WIDTH, HEIGHT))   # everything below draws on this logical surface
    # Resizable window: each frame, scale `screen` to fit the window, keeping the 600:800 aspect
    # ratio, centered, with black bars (letterbox). See present() below.
    fonts = {big: 72, medium: 36, small: 22}  (pygame.font.Font(None, size))
    sources = [KeyboardSource()]; for s in sources: s.start()
    scores = highscores.load()
    state = MENU; last_rank = None

    reset_game():
        car = Car(); obstacles = []; spawner = Spawner(); road = RoadScroller()
        speed = SPEED_START; elapsed = 0; distance_px = 0; last_rank = None

    meters(): return int(distance_px / PIXELS_PER_METER)
    kmh():    return int(speed / PIXELS_PER_METER * 3.6)

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000, 0.05)     # cap to avoid jumps after a hiccup

        # ---- 1. Input ----
        pg_events = pygame.event.get()
        if state == NAME_ENTRY:
            handle_name_entry(pg_events)           # raw TEXTINPUT / KEYDOWN, see 5.7
            commands = [QUIT] if any(e.type == pygame.QUIT for e in pg_events) else []
        else:
            commands = concat(s.poll(pg_events) for s in sources)
        if any(e.type == WINDOWFOCUSLOST for e in pg_events) and state == PLAYING:
            state = PAUSED
        for cmd in commands:
            if cmd == QUIT: running = False; break
            handle_command(state, cmd)             # transition table of 5.7
                # PLAYING + LEFT -> car.move(-1);  PLAYING + RIGHT -> car.move(+1)

        # ---- 2. Update ----
        if state == COUNTDOWN:
            countdown -= dt
            if countdown <= -0.3: state = PLAYING          # 0..-0.3 s shows "GO!"
        elif state == PLAYING:
            elapsed += dt
            speed = min(SPEED_MAX, SPEED_START + SPEED_ACCEL * elapsed)
            distance_px += speed * dt
            road.update(dt, speed); car.update(dt)
            obstacles += spawner.update(dt, speed)
            for o in obstacles: o.update(dt, speed)
            obstacles = [o for o in obstacles if not o.off_screen()]
            for o in obstacles:
                if car.hitbox().colliderect(o.hitbox()):
                    state = CRASHED; crash_timer = CRASH_ANIM_TIME; crash_point = o.rect().midbottom
                    break
        elif state == CRASHED:
            crash_timer -= dt
            if crash_timer <= 0:
                state = NAME_ENTRY (start_text_input, name = "") if qualifies(scores, meters())
                        else GAME_OVER

        # ---- 3. Draw ----
        road.draw(screen)
        for o in sorted(obstacles, key=lambda o: o.y): o.draw(screen, elapsed)   # far ones first
        car.draw(screen)      (with shake offset if CRASHED)
        if state in (PLAYING, COUNTDOWN, PAUSED, CRASHED):
            HUD: top-left "1534 m" (medium font), top-right "162 km/h" (small font)
        overlay for the current state (semi-transparent OVERLAY_BG rect + texts):
            MENU / COUNTDOWN / PAUSED / CRASHED flash / NAME_ENTRY / GAME_OVER (see 5.7)
        present()

    present():
        win_w, win_h = window.get_size()
        scale = min(win_w / WIDTH, win_h / HEIGHT)
        size = (int(WIDTH * scale), int(HEIGHT * scale))
        window.fill(black)
        window.blit(pygame.transform.smoothscale(screen, size),
                    ((win_w - size[0]) // 2, (win_h - size[1]) // 2))
        pygame.display.flip()
    (pygame 2 updates the window size automatically on VIDEORESIZE; no need to call set_mode again.
     The game uses no mouse input, so mouse coordinates never need converting.)

    for s in sources: s.stop()
    pygame.quit()

if __name__ == "__main__": main()
```

### 5.9 Look & Feel Checklist

- Road scrolls smoothly; lane dashes move with the speed so acceleration is visible.
- Distance counter in the HUD ticks up continuously (integer meters).
- Speed readout in km/h (derived from `PIXELS_PER_METER`).
- Car slides between lanes in ~0.12 s (not teleporting).
- All obstacle types readable at a glance; stickman and smoke animate.

### 5.10 Acceptance Criteria (for the coding agent)

1. `conda env create -f environment.yml`, `conda activate emg_game`, then `python lane_dodger.py` opens the menu with the Top 10 table (empty rows on first run).
2. SPACE/ENTER starts a 3-2-1-GO countdown, then the game. ←/→ (and A/D) change lanes, one lane per key press. Holding a key does not repeat.
3. The car never leaves the road; pressing LEFT in the leftmost lane does nothing.
4. All four obstacle types appear and are clearly recognisable; the stickman and the smoke animate.
5. Every obstacle row leaves at least one free lane; speed increases over time and is capped at `SPEED_MAX`.
6. The HUD shows the distance in meters, increasing continuously.
7. The first collision ends the run: crash animation, then (if the score qualifies) name entry, then the game-over screen with "Distance: N m" and the Top 10.
8. `highscores.json` holds at most 10 entries sorted best first. Scores survive closing and reopening the game. A missing or corrupt file does not crash the game.
9. P / ESC pause during play; ESC from the menu quits; closing the window exits cleanly at any time, including during name entry.
10. The game works when launched from another working directory (e.g. `python D:\EMG_GAME\lane_dodger.py` from `C:\`): `highscores.json` is still read/written next to the script.
11. All constants live in `config.py`. Nothing tunable is hard-coded in the game logic.
12. Resizing the window (including maximizing it) scales the game to fit, without distortion (black bars where needed), and gameplay is unaffected.

### 5.11 Later: Bonsai / EMG Integration (out of scope now)

> **Update:** this is now implemented with OSC. See section 8.

Bonsai will read the EMG commands and launch the script. When we get there, only a new `CommandSource` is needed, which returns `LEFT` / `RIGHT`. Possible transports, to decide later:
- **UDP / OSC** from Bonsai (`Bonsai.Osc` package) → `UDPSource` listening on localhost.
- **stdin** of the launched process → `StdinSource` reading lines on a background thread.

The game loop, states and menus stay unchanged. The menus remain keyboard-only.

---

## 6. Implementation (as built, 2026-10-29)

The keyboard version of Game A is implemented in this folder, following section 5.

### 6.1 How to Run

From an Anaconda Prompt (conda was not found on the regular PATH):

```
cd D:\EMG_GAME
conda env create -f environment.yml      # once
conda activate emg_game
python lane_dodger.py                    # keyboard only
python lane_dodger.py --input osc        # + LEFT/RIGHT from Bonsai over OSC (port 5005), see section 8
```

Controls: **←/→** or **A/D** change lane · **SPACE/ENTER** start / resume / play again · **P** pause · **ESC** pause in game, back to menu otherwise, quit from the menu.

### 6.2 Files

| File | Role |
|------|------|
| `lane_dodger.py` | Entry point. Game loop, states, car, road, spawner, all screens. |
| `config.py` | Every tunable constant: window, lanes, speeds, obstacles, timings, keys, fonts, colors. |
| `obstacles.py` | `Obstacle` class and the four obstacle drawings. |
| `highscores.py` | Load / insert / save the Top 10 in `highscores.json`. |
| `input_sources.py` | `Command` enum, `CommandSource` interface, `KeyboardSource`, `OscSource` (commands from Bonsai). |
| `osc_protocol.py` | Minimal OSC 1.0 decoder/encoder (no external dependency). |
| `osc_output.py` | `OscSender`: game → Bonsai events (star caught → `/lanedodger/star` on port 5006), see 8.8. |
| `osc_test_sender.py` | Sends LEFT/RIGHT over OSC like Bonsai would, for testing without Bonsai. |
| `bonsai/LaneDodger_Osc.bonsai` | Bonsai workflow sending `/mcoords` (left, right) to the game: your OSC example without the receive branch (mouse X/Y). |
| `bonsai/LaneDodger_KeyDown.bonsai` | Your Bonsai workflow sending keys A / S on `/mcoords` (LEFT / RIGHT), see 8.7. |
| `environment.yml` | Conda environment `emg_game`: Python 3.11 + pygame. |
| `highscores.json` | Created after the first qualifying run. Delete it to reset the Top 10. |

#### `lane_dodger.py`
- **`Car`**: knows its `lane` and its drawn `x`. `move(±1)` changes lane (ignored at the road edge) and starts a 0.12 s ease-out slide from the current position, so a second command mid-slide works. `hitbox()` is the body shrunk by `HITBOX_SHRINK` on each side.
- **`RoadScroller`**: keeps a total scroll distance and draws grass, grass tufts, road edges and dashed lane dividers shifted by it. This makes the speed visible.
- **`Spawner`**: every `interval` seconds creates a row of 1 obstacle (or 2, with `DOUBLE_SPAWN_PROB`), never filling all lanes. Obstacle types are chosen by their `weight`. The interval shrinks as speed rises but never goes below `MIN_REACTION_TIME + tallest_obstacle / speed` (see 6.4).
- **`Game`**: holds everything and runs the loop `process_input → update → draw` at 60 FPS (frame time capped at `MAX_DT`).
  - *States*: `MENU`, `COUNTDOWN`, `PLAYING`, `PAUSED`, `CRASHED`, `NAME_ENTRY`, `GAME_OVER`. Transitions are in `handle_command()` and follow the table in 5.7.
  - *Input*: commands come only from `self.sources` (today: `[KeyboardSource()]`). The one exception is `NAME_ENTRY`, which reads raw text events in `handle_name_entry()`. Text input is switched on only in that state, so SPACE types a space there instead of restarting.
  - *Update*: in `PLAYING`, speed = `SPEED_START + SPEED_ACCEL × time`, capped at `SPEED_MAX`. Distance accumulates in pixels and is shown as `meters = px / PIXELS_PER_METER`. The first hitbox overlap starts `CRASHED`. After `CRASH_ANIM_TIME`, the game goes to `NAME_ENTRY` if the score makes the Top 10, otherwise to `GAME_OVER`.
  - *Drawing*: everything is drawn on a fixed 600×800 logical surface. `present()` scales it into the resizable window, keeping the aspect ratio (black bars). Helpers: `text()` (fonts loaded on first use), `panel()` (semi-transparent box), `prompt()` (blinking bottom instruction on its own panel), `draw_top10()`, `draw_hud()` (meters + km/h), `draw_crash_effect()` (red flash + expanding fire/smoke circles; the car also shakes).

#### `config.py`
Grouped constants. Compared with 5.2, it adds `MAX_DT`, `DASH_WIDTH`, `MENU_SCROLL_SPEED`, `ASSETS_DIR`, the countdown timings (`COUNTDOWN_TIME`, `RESUME_COUNTDOWN_TIME`, `GO_TIME`), `CRASH_SHAKE`, font sizes, and the keypad Enter key as an extra START key.

#### `obstacles.py`
- `lane_center_x()` and `shrink()` are shared with the car.
- `Obstacle(lane, kind)` takes its size from `OBSTACLE_TYPES`, starts just above the screen, and moves down with the road. Its random `variant` seeds the drawing, so each rock or wreck looks a bit different but stays stable from frame to frame.
- Drawers, all using pygame shapes:
  - `draw_rock`: irregular 8-point boulder with highlight and cracks.
  - `draw_tree`: trunk with three shaded foliage circles.
  - `draw_stickman`: pedestrian with an orange shirt, waving arms and walking legs.
  - `draw_crashed_car`: tilted wreck with dent, cracked windshield and crumpled hood, plus a flickering fire and rising, fading smoke.
- Setting `USE_SPRITES = True` loads `assets/<kind>.png` instead. A missing image falls back to the drawing.

#### `highscores.py`
- The file path is always next to the scripts, so it works when Bonsai launches the game from another folder.
- `load()` ignores invalid entries and returns an empty list for a missing or corrupt file, printing a warning instead of crashing.
- `rank_for()` / `qualifies()`: a tie ranks below the older score.
- `insert()` returns the new list and the new entry's rank, used to highlight it on the game-over screen.
- `save()` writes a temp file and then swaps it in, so the scores file is never left half-written.

#### `input_sources.py`
- `Command` = `LEFT, RIGHT, START, PAUSE, BACK, QUIT`.
- `KeyboardSource.poll()` maps key *presses* to commands: holding a key gives one command, matching "one contraction = one command". The window close button maps to `QUIT`.
- `OscSource` receives LEFT/RIGHT from Bonsai over OSC. It is enabled with `--input osc`; see section 8.2. Any other input (e.g. serial, LSL) would be one more `CommandSource` subclass, added to `Game.sources`.

### 6.3 Testing Done

A headless script (not part of the project) drove the game through all states and checked:
- the full flow: menu → countdown → play → crash → name entry → game over → pause → menu;
- lane clamping at the road edge;
- the speed cap;
- that no spawned row ever blocks all lanes (5,000 rows);
- the 10-character name limit;
- Top 10 sorting, the cut at 10 entries and tie order;
- the corrupt-file fallback;
- letterboxed scaling of a resized window.

Screenshots of each screen were checked visually. It has not yet been played in a real window or run from the conda environment.

### 6.4 ⚠️ Warning: Reaction Time with EMG

The difficulty is tuned for **keyboard** play. With EMG, each command takes longer:

| Delay source | Typical |
|---|---|
| Human reaction to seeing the obstacle | 250–300 ms |
| Envelope / RMS window before the threshold is crossed | 50–150 ms |
| Bonsai processing + transport to the game | 10–50 ms |
| Refractory period before the **next** command on the same muscle | 200–300 ms |

Time between obstacle rows, from the spawner rule:

| Speed | Time between rows |
|---|---|
| 250 px/s (start) | ~1.4 s |
| 900 px/s (max, reached after ~110 s) | ~0.8 s |

At max speed, roughly 0.2 s of that is spent while the car and the obstacle pass each other. That leaves **~0.6 s** to react and switch lanes.

**The hard case is a two-obstacle row**, for example lanes 1 and 2 blocked while the car is in lane 2: the car must move twice (2 → 1 → 0). Two contractions of the same muscle within ~0.6 s, including the refractory period, will often be too slow. The player crashes because of the interface, not because they reacted badly.

Settings to adjust in `config.py` when switching to EMG, from the most to the least effective:
1. **`DOUBLE_SPAWN_PROB = 0`**: with one obstacle per row, an adjacent lane is always free, so **one command is always enough** to dodge.
2. **`MIN_REACTION_TIME`**: raise from 0.7 s to **1.2–1.5 s** to give room for EMG latency and refractory time.
3. **`SPEED_MAX`** (e.g. 600) and/or **`SPEED_ACCEL`** (e.g. 3): lower the top difficulty, or reach it more slowly.
4. Optionally keep separate configs (e.g. `config_keyboard` / `config_emg`), so EMG scores aren't compared with keyboard scores in the same Top 10.

Measure the real end-to-end latency of the Bonsai pipeline first. Then set `MIN_REACTION_TIME` to at least *human reaction + EMG latency + one refractory period* (if double rows are kept), plus a safety margin.

---

## 7. Stars (bonus points)

Golden stars appear on the road. Driving over one catches it.

**Score = distance in meters + `STAR_POINTS` (50) × stars caught.**

- **Where stars appear** (`Spawner.update` in `lane_dodger.py`):
  - With probability `STAR_ROW_PROB` (0.5), an obstacle row also gets a star in one of its **free** lanes. Choosing the lane with the star is rewarded, and it is always safe.
  - With probability `STAR_MID_PROB` (0.35), a star appears **halfway between two rows**, in any lane. It may tempt the player into a lane that is badly placed for the next row (risk/reward).
  - Stars never overlap an obstacle.
- **Catching**: the car's full body (not the shrunk hitbox) is used, so catching is generous. A fading "+50" rises above the car.
- **Drawing** (`Star` and `draw_star_shape` in `obstacles.py`): rotating, pulsing 5-point star with a soft glow. The same shape is the star icon in the HUD and the Top 10.
- **HUD**: the score in large text, with distance (m) and stars caught below it. Speed is shown on the right.
- **Game over**: `Score`, plus the breakdown "`N m + K stars x 50`".
- **Top 10**: ranked by score, with columns score / distance / stars / date. `highscores.json` entries are now `{"name", "score", "meters", "stars", "date"}`. Older entries that only have `meters` still load, with score = meters and 0 stars.
- **Tuning** in `config.py`: `STAR_POINTS`, `STAR_SIZE`, `STAR_ROW_PROB`, `STAR_MID_PROB`, `POPUP_TIME`.

---

## 8. Integrating the Game with Bonsai

Goal: a **button in Bonsai launches the game**, and a **Bonsai value** (later produced by the EMG pipeline) **sends LEFT/RIGHT** to it.

### 8.1 Architecture (your Bonsai OSC workflow, unchanged)

The game takes the place of the receiving side (`UdpReceive` + `ReceiveMessage`) of your Bonsai OSC example. The sending side stays exactly as it is.

```
┌──────────── Bonsai workflow (bonsai/LaneDodger_Osc.bonsai) ────────────┐           ┌───── Python process ─────┐
│                                                                        │           │                          │
│  CreateUdpClient "UdpSend"   Port 0 ─► localhost : 5005                │           │  lane_dodger.py          │
│                                                                        │           │      --input osc         │
│  MouseMove (now) / 2 digital inputs (later)                            │    OSC    │                          │
│     ├─► X  (later: LEFT muscle)  ─┐                                    │  /mcoords │  OscSource (port 5005)   │
│     └─► Y  (later: RIGHT muscle) ─┴─► Zip ─► SendMessage "/mcoords" ───┼───"ii"───►│   Item1 rises → LEFT     │
│                                           (Connection UdpSend)         │    UDP    │   Item2 rises → RIGHT    │
│                                                                        │           │  Keyboard still works    │
└────────────────────────────────────────────────────────────────────────┘           └──────────────────────────┘
```

**Why a separate process plus OSC**, rather than running Python inside Bonsai:
- pygame needs its own main loop and window. Embedding it in Bonsai (e.g. with `Bonsai.Scripting.Python`) would block or fight the Bonsai thread.
- Bonsai's IronPython scripting can't load pygame at all.
- A separate process keeps the two independent: if the game crashes, Bonsai keeps recording, and the reverse.
- OSC over UDP on localhost adds negligible latency (well under 1 ms).
- Bonsai has an official OSC package (`Bonsai.Osc`). The game decodes OSC itself (`osc_protocol.py`), so nothing extra needs installing in Python.

### 8.1b OSC Quick Start (step by step)

**What OSC is:** Open Sound Control. Small messages sent over UDP, each made of an **address** (here `/mcoords`) and **arguments** (here two numbers, type tag `ii`). Bonsai sends, the game listens. Both run on the same computer (localhost).

1. **Test the game alone, without Bonsai.**
   - Anaconda Prompt 1:
     ```
     cd /d D:\EMG_GAME
     conda activate emg_game
     python lane_dodger.py --input osc
     ```
     The menu's bottom line must read **"OSC listening on port 5005"**.
   - Anaconda Prompt 2: run the same `cd` and `conda activate`, then `python osc_test_sender.py`. Type `l` or `r` + ENTER. Each one sends `/mcoords (1, 0)` then `(0, 0)` for LEFT, or `(0, 1)` then `(0, 0)` for RIGHT, like a short contraction. The menu's two status lines update. Press SPACE in the game window, then send `l` / `r` again: the car moves.
2. **Test the link with Bonsai (mouse).**
   - In Bonsai, install the **Bonsai - OSC Library** and **Bonsai - Windows Input Library** packages if they aren't installed yet.
   - Open `bonsai\LaneDodger_Osc.bonsai` (your workflow without the receive part) or your original workflow, and press Start.
   - Move the mouse. In the game menu, the line **"received N   last: /mcoords (812, 455)"** follows the mouse. This proves Bonsai → game works.
   - Mouse coordinates are not real commands. Both values are above the threshold, so they trigger LEFT and RIGHT once, then nothing until a value returns to 0.
3. **Switch to the digital inputs / EMG.** Replace `MouseMove → X / Y` with your two signals: **LEFT muscle → first input of `Zip` (Item1)**, **RIGHT muscle → second input (Item2)**. Values can be `0/1` ints, booleans, or `0..1` floats. See 8.5 for when to use `Zip` or `CombineLatest`.
4. **Check the difficulty for EMG** (section 6.4) before the first session.

**Settings that must match on both sides:**

| Bonsai | Game (`config.py` / command line) |
|---|---|
| `CreateUdpClient` "UdpSend": `RemoteHostName` = `localhost`, `RemotePort` = `5005`, `Port` = `0` | `OSC_PORT` / `--port` = `5005`; listens on `127.0.0.1` and `::1` |
| `SendMessage`: `Address` = `/mcoords`, `Connection` = `UdpSend` | `OSC_ADDRESS_PAIR` = `"/mcoords"` |
| `Zip` input 1 (Item1) / input 2 (Item2) | Item1 → LEFT, Item2 → RIGHT |
| values 0/1 (or false/true, or 0..1) | `OSC_PAIR_THRESHOLD_ON` / `_OFF` = 0.5 |

**A Bonsai `UdpReceive` on the same port as the game:** tested on this PC. The game listens on 127.0.0.1, and Bonsai's `UdpReceive` listens on all addresses. Both can run at the same time, in either order, and **the game receives all the messages**; Bonsai's `ReceiveMessage` then gets nothing. In your KeyDown workflow, `UdpReceive` uses port 5006, different from the game's 5005, so it doesn't matter at all.

**Troubleshooting:**

| Symptom | Cause / fix |
|---|---|
| Menu line red: "OSC ERROR: port 5005 in use" | Another game instance is already running. Close it, or use another port on both sides (`RemotePort` and `--port`). |
| Menu line says "Input: keyboard" | The game was started without `--input osc`. |
| "nothing received yet" while Bonsai runs | Wrong `RemotePort` in "UdpSend", or the workflow isn't started. |
| Values arrive but the car doesn't move | Not in a run: OSC steers only while PLAYING. Press SPACE in the game window. Or the values never return to 0 between contractions. |
| Console: "ignoring OSC address ..." | The `SendMessage` `Address` differs from `/mcoords`. Change it in Bonsai, or set `OSC_ADDRESS_PAIR`. |
| Console: "/mcoords needs 2 values" | Something other than the `Zip` of two values reaches `SendMessage`. |
| LEFT/RIGHT swapped | Swap the two inputs of `Zip`. |

### 8.2 Python Side (implemented)

Start the game in OSC mode:

```
python lane_dodger.py --input osc              # listens on port 5005 (127.0.0.1 and ::1)
python lane_dodger.py --input osc --port 6000  # other port
```

The keyboard always stays active. **Nothing received over OSC can start, pause or quit the game**: menus are keyboard-only, and OSC LEFT/RIGHT only steer the car while playing.

**OSC protocol:**

| Address | Arguments | Effect |
|---|---|---|
| **`/mcoords`** (main, = your workflow) | **2 values**: `ii` (ints), `ff` (floats), `TF` (bools)... | **Item1** going above 0.5 → **LEFT**; **Item2** going above 0.5 → **RIGHT** |
| **`/mcoords`** (KeyDown workflow, 8.7) | **a key**: code `65`/`83`, name `"A"`/`"S"`, or a key event | **A → LEFT**, **S → RIGHT**, one per message |
| `/lanedodger/cmd` | int `1` / `2` (`0` ignored), or string `"LEFT"`/`"RIGHT"` | LEFT / RIGHT (alternative) |
| `/lanedodger/left`, `/lanedodger/right` | `true` / non-zero / no argument | LEFT / RIGHT (alternative; `false` / `0` ignored) |

**How `/mcoords` becomes commands (rising edge):** each of the two values is a channel (muscle) with an on/off state.
- A channel turns **on** when its value goes **above `OSC_PAIR_THRESHOLD_ON`** (0.5). That gives **one** lane change.
- It turns **off** again when the value goes back to **≤ `OSC_PAIR_THRESHOLD_OFF`** (0.5). Only then can it trigger again.

Consequences:
- It works whether Bonsai sends **every sample** (e.g. `(1,0)` repeated 500 times during a contraction) or **only on changes**. Either way it's one contraction = one lane change, so no `DistinctUntilChanged` is needed.
- Two contractions need a return to 0 in between, which is natural for a digital input.
- For **analog** values later (e.g. an EMG envelope normalised to 0..1), set `OSC_PAIR_THRESHOLD_OFF` lower than `_ON` (e.g. ON 0.6 / OFF 0.4). This hysteresis stops the noise around the threshold from producing several commands.

The single-value addresses use `OSC_TRIGGER`: `"every"` (default) = each active message is a command; `"rising"` = edge detection, like `/mcoords`.

**Files involved:**
- `osc_protocol.py`: a minimal OSC 1.0 decoder/encoder, so no extra package is needed. It handles int, float, double, long, string, bool, blob and bundles, and was checked byte-for-byte against the `python-osc` reference library.
- `input_sources.py` → `OscSource`:
  - UDP sockets on 127.0.0.1 and ::1, read on a background thread (in case Bonsai's `localhost` resolves to IPv6);
  - decodes packets, applies the rules above, and queues `Command.LEFT/RIGHT`. `poll()` empties the queue every frame without blocking;
  - malformed packets and unknown addresses are ignored with a one-time console warning;
  - if the port is busy, the game still starts. The menu shows the error in red and the keyboard keeps working.
- `lane_dodger.py`: the `--input / --host / --port` options. In OSC mode the **menu shows two status lines**:
  - "received N   last: /mcoords (1, 0)": the raw values, which prove the Bonsai link works;
  - "OSC listening on port 5005 | last command: LEFT (12)": the commands produced.
- `config.py`: `OSC_PORT = 5005`, `OSC_ADDRESS_PAIR = "/mcoords"`, `OSC_PAIR_THRESHOLD_ON/OFF`, `OSC_LISTEN_IPV6`, the alternative addresses, `OSC_TRIGGER`, and `PAUSE_ON_FOCUS_LOST_OSC = False`. In OSC mode the game does **not** auto-pause when you click in Bonsai.
- `osc_test_sender.py`: sends `/mcoords` pairs exactly like the Bonsai workflow, for testing without Bonsai (`l` / `r` interactive, or `--random 20`).
- `bonsai/LaneDodger_Osc.bonsai`: your OSC example workflow, node for node, without the `UdpReceive`/`ReceiveMessage` branch (the game is now the receiver). Open it in Bonsai 2.8.2 and replace `MouseMove → X / Y` with your signals.

### 8.3 Bonsai Side: Packages

In Bonsai: **Tools → Manage Packages**, then install:
- **Bonsai - OSC Library** (`Bonsai.Osc`): `CreateUdpClient`, `SendMessage`.
- **Bonsai - GUI Library** (`Bonsai.Gui`): a clickable `Button` control. Alternative without it: `KeyDown` from **Bonsai - Windows Input Library**, e.g. F5 = launch.
- **Bonsai - Windows Input Library** (`Bonsai.Windows.Input`): `MouseMove`, used by the workflow to test the OSC link before the digital inputs are connected.

### 8.4 Bonsai Side: Launch Button

Bonsai has no ready-made "start an external program" node, so we add a tiny **C# scripting extension**. Bonsai compiles every `.cs` file in the `Extensions` folder next to the workflow (`.bonsai`) file. After saving the workflow, create `Extensions\LaunchGame.cs` with:

```csharp
using Bonsai;
using System;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Reactive.Linq;

[Combinator]
[Description("Starts the Lane Dodger game each time the input fires (only one instance at a time).")]
[WorkflowElementCategory(ElementCategory.Sink)]
public class LaunchGame
{
    public LaunchGame()
    {
        PythonExe = @"C:\Users\dario\anaconda3\envs\emg_game\python.exe";
        Script = @"D:\EMG_GAME\lane_dodger.py";
        Arguments = "--input osc --port 5005";   // OSC mode, see 8.2
        CloseGameOnStop = true;
    }

    [Description("python.exe of the emg_game conda environment.")]
    public string PythonExe { get; set; }

    [Description("Full path of lane_dodger.py.")]
    public string Script { get; set; }

    [Description("Extra command-line arguments for the game.")]
    public string Arguments { get; set; }

    [Description("Close the game window when the Bonsai workflow stops.")]
    public bool CloseGameOnStop { get; set; }

    System.Diagnostics.Process game;   // fully qualified: "Process" is also the method name below

    public IObservable<TSource> Process<TSource>(IObservable<TSource> source)
    {
        return source.Do(_ =>
        {
            if (game != null && !game.HasExited) return;   // already running
            game = System.Diagnostics.Process.Start(new ProcessStartInfo
            {
                FileName = PythonExe,
                Arguments = string.Format("\"{0}\" {1}", Script, Arguments),
                WorkingDirectory = Path.GetDirectoryName(Script),
                UseShellExecute = false
            });
        }).Finally(() =>
        {
            if (CloseGameOnStop && game != null && !game.HasExited) game.Kill();
        });
    }
}
```

Reload the workflow (or restart Bonsai). **`LaunchGame`** then appears in the toolbox under the workflow's extensions. Wire it as:

```
Button (Bonsai.Gui)  ──►  LaunchGame
   or KeyDown (F5) ──► Condition (Key == F5) ──► LaunchGame
```

Notes:
- Run the workflow, then click the button (double-click the `Button` node to open its control). The game window opens on the menu.
- Calling the env's `python.exe` directly is enough; `conda activate` is not needed for a pure pip package like pygame. If an import error ever shows up, use `FileName = "cmd.exe"` and `Arguments = "/c conda activate emg_game && python ..."` instead.
- Clicking again while the game runs does nothing (one instance at a time).

### 8.5 Bonsai Side: Sending the Commands

Same structure as your OSC example: one `CreateUdpClient` for sending, two values combined into one pair, one `SendMessage`.

```
CreateUdpClient    Name = UdpSend, Port = 0, RemoteHostName = localhost, RemotePort = 5005

── Now: test the link with the mouse ───────────────────────────────────────────
MouseMove ─┬─► X ─┐
           └─► Y ─┴─► Zip ─► SendMessage   Connection = UdpSend, Address = /mcoords

── Later, case A: both lines come from the SAME sample (one device, one port read) ──
DigitalInput sample ─┬─► left line  (0/1) ─┐
                     └─► right line (0/1) ─┴─► Zip ─► SendMessage (UdpSend, /mcoords)

── Later, case B: two SEPARATE sources that emit independently ─────────────────
Digital input LEFT  muscle (0/1) ─┐
Digital input RIGHT muscle (0/1) ─┴─► CombineLatest ─► SendMessage (UdpSend, /mcoords)
```

**`Zip` or `CombineLatest`?**
- `Zip` pairs the *n-th* value of input 1 with the *n-th* value of input 2. That is right for X/Y of the same mouse event, or for two lines read from the same sample (case A).
- With **two independent sources** (case B), `Zip` would wait for the other muscle and pair values from different times. For example, three LEFT contractions with no RIGHT would send nothing. Use **`CombineLatest`** there (Bonsai.Reactive): it sends the latest value of both every time either one changes. That is exactly what the game expects.
- In both cases, the order of the inputs decides the mapping: first input = Item1 = **LEFT**, second = Item2 = **RIGHT**.

**What the values must look like:**
- Each value is the **state** of one muscle: `0` (or false) = relaxed, `1` (or true) = contraction detected.
- The game does the edge detection (8.2), so Bonsai can send every sample or only the changes.
- Booleans work as well as ints. If a digital input gives a different type (e.g. a bit mask), convert it with an `ExpressionTransform` such as `it ? 1 : 0` or a `BitwiseAnd` + `GreaterThan`.
- A **refractory period** (ignoring a new contraction for ~200–300 ms) can be added in Bonsai on each line if the detection is noisy. The game also only fires again after the value has gone back to 0.

### 8.6 Practical Notes

- **Order**: start the Bonsai workflow (this opens the UDP client) → click the launch button → use the keyboard in the game window to start a run → steer with the EMG/Bonsai commands.
- **Window focus**: the menus (SPACE/ESC/P) are keyboard-only and need the **game window** to have focus. OSC steering works even when the game window is not focused. In OSC mode the game does not auto-pause on focus loss (`PAUSE_ON_FOCUS_LOST_OSC`).
- **Port in use**: if the menu shows "OSC ERROR: port 5005 in use", an old game instance is still running. Close it, or change the port in both `CreateUdpClient` (`RemotePort`) and `--port`. A Bonsai `UdpReceive` on the same port does *not* block the game (see 8.1b).
- **Firewall**: localhost traffic is normally not blocked. If Windows asks about network access for `python.exe` at the first launch, allow it for private networks.
- **Latency check**: send a command from Bonsai while looking at the car. If you want numbers, timestamp the OSC message in Bonsai and log the receive time in the game (the CSV logging idea from section 1).
- **Difficulty**: re-read section 6.4 before the first EMG session.

### 8.7 KeyDown Workflow (`bonsai/LaneDodger_KeyDown.bonsai`)

Your test workflow, saved exactly as written (Bonsai 2.9.0):

```
CreateUdpClient "UdpReceive"   Port 5006                        (not used by the game; no conflict)
CreateUdpClient "UdpSend"      Port 0 ─► localhost : 5005        (= the game's default port)

KeyDown (Filter = A) ─┐
                      ├─► Merge ─► SendMessage   Connection = UdpSend, Address = /mcoords
KeyDown (Filter = S) ─┘
```

**How the game reads it:**
- On `/mcoords`, a message that is **not** a pair of two numbers is treated as a **key message**.
- The game looks for the key in whatever form Bonsai serialises it:
  - the Windows key code (`65` for A, `83` for S);
  - the key name (`"A"`, `"S"`);
  - the key code inside a serialised key event with several fields.
- **A → LEFT, S → RIGHT**, one lane change per message.
- The keys are set by `OSC_KEY_LEFT` / `OSC_KEY_RIGHT` in `config.py`. Change them there if you change the `Filter` of the `KeyDown` nodes.
- The **first message of each kind is printed in the game console**, e.g. `OSC: first message of this kind: /mcoords [65]`. You can see exactly what Bonsai sends, and the menu shows it too ("received N   last: /mcoords (65)"). If a key message can't be understood, the console says so once, with its content. Paste that line to me and I'll adapt the parser.

**Steps:**
1. Anaconda Prompt: `python lane_dodger.py --input osc` (port 5005 by default, no `--port` needed).
2. Bonsai: open `LaneDodger_KeyDown.bonsai` and press Start.
3. In the game window, press SPACE to start a run. Press **A** / **S** anywhere: the car moves left / right.

**Things to know:**
- **Arrows only on the game's own keyboard in OSC mode.** Bonsai's `KeyDown` listens to every window, so pressing **A** in the game window is caught by Bonsai, which sends LEFT over OSC. If the game also treated A as LEFT (its normal keyboard mode), the car would move twice. In OSC mode the game's own LEFT/RIGHT keys are therefore **the arrows only** (`KEYS_LEFT_OSC` / `KEYS_RIGHT_OSC`). SPACE, P and ESC are unchanged.
- **`SuppressRepetitions` = false**: holding A down makes Windows repeat the key about 30 times per second, and each repeat is a lane change. To get one lane change per press, like one per contraction, set **`SuppressRepetitions` = true** on both `KeyDown` nodes.
- When the digital inputs replace the keys, switch to the **pair** format (8.5: `Zip` / `CombineLatest` of the two muscle states). It gives proper one-command-per-contraction edge detection on the game side.
- **"System.Windows.Forms.Keys cannot be used for parameters of type System.Int32"** on `SendMessage`: Bonsai.Osc only sends plain values (int, float, string, bool...), not the `Keys` value output by `KeyDown`. Convert it before `SendMessage`:
  - **Option 1 (recommended):** `KeyDown (A) → Int (Value = 1)` and `KeyDown (S) → Int (Value = 2)` → `Merge` → `SendMessage`. The game reads 1 = LEFT, 2 = RIGHT.
  - **Option 2:** `Merge → ExpressionTransform (Expression = Convert.ToInt32(it)) → SendMessage`. This sends the key code (A = 65, S = 83), which the game also understands.

### 8.8 Game → Bonsai: Star Events (e.g. a sound on a Harp board)

The game also **sends** OSC to Bonsai, in OSC mode (`--input osc`): a **binary star signal**, `0` most of the time and `1` for a short pulse each time the car catches a star.

| To | Address | Argument | Values |
|---|---|---|---|
| `127.0.0.1 : 5006` (Bonsai's `UdpReceive`) | `/lanedodger/star` | one int (type tag `i`) | `0` / `1` |

```
signal   1 ┤        ┌─┐               ┌─┐ ┌─┐
         0 ┼────────┘ └───────────────┘ └─┘ └──────
                    ▲  ◄─ 0.1 s ─►    ▲   ▲
                 star caught         2 stars close together: still 2 separate pulses
```

- At game startup: `0` (initial state).
- Star caught: `1`, sent in the same frame as the catch.
- `STAR_PULSE_TIME` (0.1 s) later: `0`.
- If a second star is caught while the signal is still at 1, the game sends `0` then `1` immediately. **Every star is a separate 0 → 1 transition.**
- The signal always returns to 0, even if the car crashes right after a star or the game is closed during a pulse.
- Messages are only sent on changes: one `1` and one `0` per star. Between stars nothing is sent, and the last value received (0) holds.

**Bonsai side** (your workflow already has `CreateUdpClient` "UdpReceive" with `Port` = 5006):

```
CreateUdpClient "UdpReceive"   Port = 5006, RemotePort = 0          (already in your workflow)

ReceiveMessage                 Connection = UdpReceive
                               Address    = /lanedodger/star
                               TypeTag    = i
      │  int: 0 (startup), then 1, 0 for each star
      ▼
your logic (e.g. on the 0 → 1 change, trigger a sound on the Harp board)
```

- `ReceiveMessage` outputs the signal value: `1` when a star is caught, `0` when it ends. To act once per star, react to the value `1`, e.g. `Condition` (`it == 1`).
- To have a value before the first message arrives, Bonsai's `StartWith(0)` can be added after `ReceiveMessage`. The game also sends a `0` at startup.
- The game sends "fire and forget" (UDP): it never waits for Bonsai. If Bonsai isn't running, nothing happens and the game keeps playing.
- Settings in `config.py`: `OSC_SEND_HOST`, `OSC_SEND_PORT` (5006; also `--send-port` on the command line), `OSC_ADDRESS_STAR`, and `STAR_PULSE_TIME` (0.1 s). They must match `UdpReceive`'s `Port` and `ReceiveMessage`'s `Address`.
- At startup the console prints: `OSC: star signal sent to 127.0.0.1:5006 as /lanedodger/star 0/1`.
- Code: `osc_output.py` (`OscSender`). In `lane_dodger.py`, `Game.star_signal_on()` (called when a star is caught) sends 1, and `Game.update_star_signal()` (every frame, in every state) sends the 0 when the pulse ends.
- **Latency:** the message leaves in the same frame as the catch (≤ 16 ms at 60 FPS), plus well under 1 ms over localhost. The rest depends on Bonsai and the Harp board.
- Tested with a stand-in for Bonsai's `UdpReceive`, decoded by the reference `python-osc` library (type tag `,i`):
  - initial `0`;
  - `1` on the catch frame, still 1 at 50 ms, back to `0` after 100 ms;
  - two stars 50 ms apart give `1, 0, 1, 0`;
  - a star followed by a crash gives `1, 0`;
  - quitting during a pulse gives `1, 0`.

