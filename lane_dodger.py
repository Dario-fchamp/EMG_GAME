"""EMG Lane Dodger: dodge obstacles by switching lanes, with the keyboard or OSC commands from Bonsai.

Run: python lane_dodger.py                      (keyboard only)
     python lane_dodger.py --input osc          (+ LEFT/RIGHT from Bonsai over OSC, port 5005)
     python lane_dodger.py --input osc --port 6000
"""
import argparse
import math
import random
import sys

import pygame

import config as C
import highscores
from input_sources import Command, KeyboardSource, OscSource
from osc_output import OscSender
from obstacles import Obstacle, Star, draw_star_shape, lane_center_x, shrink

MENU, COUNTDOWN, PLAYING, PAUSED, CRASHED, NAME_ENTRY, GAME_OVER = (
    "MENU", "COUNTDOWN", "PLAYING", "PAUSED", "CRASHED", "NAME_ENTRY", "GAME_OVER")


class Car:
    def __init__(self):
        self.lane = C.START_LANE
        self.x = lane_center_x(self.lane)       # current drawn center x
        self.anim_from_x = self.anim_to_x = self.x
        self.anim_t = C.LANE_SWITCH_TIME        # = not animating

    def move(self, direction):
        new_lane = self.lane + direction
        if not 0 <= new_lane < C.N_LANES:
            return                              # at the edge: ignore
        self.lane = new_lane
        self.anim_from_x = self.x               # start from the CURRENT x (works mid-animation)
        self.anim_to_x = lane_center_x(new_lane)
        self.anim_t = 0

    def update(self, dt):
        if self.anim_t < C.LANE_SWITCH_TIME:
            self.anim_t += dt
            k = min(self.anim_t / C.LANE_SWITCH_TIME, 1)
            k = 1 - (1 - k) ** 2                # ease-out
            self.x = self.anim_from_x + (self.anim_to_x - self.anim_from_x) * k

    def rect(self):
        return pygame.Rect(round(self.x - C.CAR_W / 2), C.CAR_Y, round(C.CAR_W), C.CAR_H)

    def hitbox(self):
        return shrink(self.rect(), C.HITBOX_SHRINK)

    def draw(self, surf, offset=(0, 0)):
        r = self.rect().move(offset)
        ww, wh = r.w * 0.18, r.h * 0.2
        for x, y in ((r.x - 3, r.y + r.h * 0.12), (r.right - ww + 3, r.y + r.h * 0.12),
                     (r.x - 3, r.y + r.h * 0.68), (r.right - ww + 3, r.y + r.h * 0.68)):
            pygame.draw.rect(surf, C.WHEEL, (x, y, ww, wh), border_radius=3)
        pygame.draw.rect(surf, C.CAR, r, border_radius=12)
        pygame.draw.rect(surf, C.CAR_DARK, r, 2, border_radius=12)
        pygame.draw.rect(surf, C.CAR_WINDOW, (r.x + r.w * 0.15, r.y + r.h * 0.22, r.w * 0.7, r.h * 0.18), border_radius=4)
        pygame.draw.rect(surf, C.CAR_WINDOW, (r.x + r.w * 0.2, r.y + r.h * 0.74, r.w * 0.6, r.h * 0.12), border_radius=4)
        pygame.draw.rect(surf, C.CAR_DARK, (r.x + r.w * 0.15, r.y + r.h * 0.42, r.w * 0.7, r.h * 0.3), border_radius=4)
        for x in (r.x + r.w * 0.2, r.right - r.w * 0.2):
            pygame.draw.circle(surf, C.HEADLIGHT, (x, r.y + 6), 5)


class RoadScroller:
    def __init__(self):
        self.scroll = 0.0

    def update(self, dt, speed):
        self.scroll += speed * dt

    def draw(self, surf):
        surf.fill(C.GRASS)
        period = 160                            # decorative grass tufts on the margins
        for i in range(-1, C.HEIGHT // period + 1):
            y = i * period + self.scroll % period
            for x in (12, C.WIDTH - 38):
                pygame.draw.ellipse(surf, C.GRASS_DARK, (x + (i % 2) * 10, y, 22, 10))
        pygame.draw.rect(surf, C.ROAD, (C.ROAD_MARGIN, 0, C.WIDTH - 2 * C.ROAD_MARGIN, C.HEIGHT))
        for x in (C.ROAD_MARGIN, C.WIDTH - C.ROAD_MARGIN - 4):
            pygame.draw.rect(surf, C.ROAD_EDGE, (x, 0, 4, C.HEIGHT))
        period = C.DASH_LEN + C.DASH_GAP
        offset = self.scroll % period
        for lane in range(1, C.N_LANES):
            x = C.ROAD_MARGIN + lane * C.LANE_WIDTH - C.DASH_WIDTH / 2
            y = -period + offset
            while y < C.HEIGHT:
                pygame.draw.rect(surf, C.LANE_LINE, (x, y, C.DASH_WIDTH, C.DASH_LEN))
                y += period


class Spawner:
    def __init__(self):
        self.timer = 0.0
        self.tallest = max(t["h"] for t in C.OBSTACLE_TYPES.values())
        self.mid_star = False                   # a star is due halfway to the next row

    def update(self, dt, speed):
        """Return (new obstacles, new stars). Stars never overlap obstacles."""
        interval = max(C.SPAWN_INTERVAL_START * C.SPEED_START / speed, C.SPAWN_INTERVAL_MIN)
        # Fairness: time between rows covers the tallest obstacle + a lane switch + reaction
        interval = max(interval, C.MIN_REACTION_TIME + self.tallest / speed)
        self.timer += dt
        stars = []
        if self.mid_star and self.timer >= interval / 2:
            self.mid_star = False
            stars.append(Star(random.randrange(C.N_LANES)))
        if self.timer < interval:
            return [], stars
        self.timer = 0.0
        n = 2 if (C.N_LANES >= 3 and random.random() < C.DOUBLE_SPAWN_PROB) else 1
        n = max(1, min(n, C.MAX_OBST_PER_ROW))
        lanes = random.sample(range(C.N_LANES), n)
        kinds = random.choices(list(C.OBSTACLE_TYPES),
                               weights=[t["weight"] for t in C.OBSTACLE_TYPES.values()], k=n)
        free = [lane for lane in range(C.N_LANES) if lane not in lanes]
        if random.random() < C.STAR_ROW_PROB:
            stars.append(Star(random.choice(free)))
        self.mid_star = random.random() < C.STAR_MID_PROB
        return [Obstacle(lane, kind) for lane, kind in zip(lanes, kinds)], stars


class Game:
    def __init__(self, input_mode=C.INPUT_MODE, osc_host=C.OSC_HOST, osc_port=C.OSC_PORT,
                 send_host=C.OSC_SEND_HOST, send_port=C.OSC_SEND_PORT):
        pygame.init()
        self.window = pygame.display.set_mode(C.WINDOW_START_SIZE, pygame.RESIZABLE)
        pygame.display.set_caption(C.TITLE)
        self.screen = pygame.Surface((C.WIDTH, C.HEIGHT))   # logical surface, scaled in present()
        self.clock = pygame.time.Clock()
        self.fonts = {}                                    # size -> Font, loaded on first use
        self.osc = OscSource(osc_host, osc_port) if input_mode == "osc" else None
        self.osc_out = OscSender(send_host, send_port) if input_mode == "osc" else None   # events to Bonsai
        self.star_signal_timer = 0.0                       # > 0 while the star signal is at 1
        if self.osc_out is not None:
            print(f"OSC: star signal sent to {send_host}:{send_port} as {C.OSC_ADDRESS_STAR} 0/1")
            self.osc_out.send(C.OSC_ADDRESS_STAR, 0)       # defined initial state
        self.sources = [KeyboardSource(osc_mode=self.osc is not None)]   # keyboard is always active
        if self.osc is not None:
            self.sources.append(self.osc)
        self.pause_on_focus_lost = C.PAUSE_ON_FOCUS_LOST_OSC if self.osc else C.PAUSE_ON_FOCUS_LOST
        for s in self.sources:
            s.start()
        pygame.key.stop_text_input()                       # only enabled during name entry
        self.scores = highscores.load()
        self.state = MENU
        self.t = 0.0                                       # global time (blinking texts)
        self.running = True
        self.reset_game()

    # ---------- run state ----------
    def reset_game(self):
        self.car = Car()
        self.obstacles = []
        self.stars = []
        self.stars_caught = 0
        self.popups = []                                   # [x, y, time_left] of "+50" texts
        self.spawner = Spawner()
        self.road = RoadScroller()
        self.speed = C.SPEED_START
        self.elapsed = 0.0
        self.distance_px = 0.0
        self.last_rank = None
        self.name = ""

    def meters(self):
        return int(self.distance_px / C.PIXELS_PER_METER)

    def score(self):
        return self.meters() + C.STAR_POINTS * self.stars_caught

    def kmh(self):
        return int(self.speed / C.PIXELS_PER_METER * 3.6)

    def start_run(self):
        self.reset_game()
        self.begin_countdown(C.COUNTDOWN_TIME)

    def begin_countdown(self, seconds):
        self.countdown = seconds
        self.state = COUNTDOWN

    def go_to_menu(self):
        self.reset_game()
        self.state = MENU

    def crash(self, obstacle):
        self.state = CRASHED
        self.crash_timer = C.CRASH_ANIM_TIME
        self.crash_point = self.car.rect().midtop

    def end_crash(self):
        if highscores.qualifies(self.scores, self.score()):
            self.name = ""
            self.state = NAME_ENTRY
            pygame.key.start_text_input()
        else:
            self.state = GAME_OVER

    def confirm_name(self, name):
        pygame.key.stop_text_input()
        self.scores, self.last_rank = highscores.insert(
            self.scores, name, self.score(), self.meters(), self.stars_caught)
        highscores.save(self.scores)
        self.state = GAME_OVER

    # ---------- input ----------
    def process_input(self):
        events = pygame.event.get()
        if self.state == NAME_ENTRY:
            if any(e.type == pygame.QUIT for e in events):
                self.running = False
            else:
                self.handle_name_entry(events)
            return
        if (self.state == PLAYING and self.pause_on_focus_lost
                and any(e.type == pygame.WINDOWFOCUSLOST for e in events)):
            self.state = PAUSED
        for s in self.sources:
            for cmd in s.poll(events):
                if cmd == Command.QUIT:
                    self.running = False
                    return
                self.handle_command(cmd)

    def handle_command(self, cmd):
        s = self.state
        if s == MENU:
            if cmd == Command.START:
                self.start_run()
            elif cmd == Command.BACK:
                self.running = False
        elif s == COUNTDOWN:
            if cmd == Command.BACK:
                self.go_to_menu()
        elif s == PLAYING:
            if cmd == Command.LEFT:
                self.car.move(-1)
            elif cmd == Command.RIGHT:
                self.car.move(+1)
            elif cmd in (Command.PAUSE, Command.BACK):
                self.state = PAUSED
        elif s == PAUSED:
            if cmd in (Command.START, Command.PAUSE):
                self.begin_countdown(C.RESUME_COUNTDOWN_TIME)
            elif cmd == Command.BACK:
                self.go_to_menu()                          # run discarded, not saved
        elif s == GAME_OVER:
            if cmd == Command.START:
                self.start_run()
            elif cmd == Command.BACK:
                self.go_to_menu()
        # CRASHED: input ignored, so the result cannot be skipped by accident

    def handle_name_entry(self, events):
        for e in events:
            if e.type == pygame.TEXTINPUT:
                for ch in e.text:
                    if ch.isprintable() and len(self.name) < C.NAME_MAX_LEN:
                        self.name += ch
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_BACKSPACE:
                    self.name = self.name[:-1]
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.confirm_name(self.name.strip())
                    return
                elif e.key == pygame.K_ESCAPE:
                    self.confirm_name("")
                    return

    # ---------- update ----------
    def star_signal_on(self):
        """Star caught: binary signal to Bonsai goes 0 -> 1 (back to 0 in update_star_signal)."""
        if self.osc_out is None:
            return
        if self.star_signal_timer > 0:                     # still at 1: drop to 0 first, so every star
            self.osc_out.send(C.OSC_ADDRESS_STAR, 0)       #   is a clean 0 -> 1 transition in Bonsai
        self.osc_out.send(C.OSC_ADDRESS_STAR, 1)
        self.star_signal_timer = C.STAR_PULSE_TIME

    def update_star_signal(self, dt):
        if self.star_signal_timer > 0:
            self.star_signal_timer -= dt
            if self.star_signal_timer <= 0:
                self.star_signal_timer = 0.0
                self.osc_out.send(C.OSC_ADDRESS_STAR, 0)

    def update(self, dt):
        self.t += dt
        self.update_star_signal(dt)                        # runs in every state (e.g. crash right after a star)
        if self.state == MENU:
            self.road.update(dt, C.MENU_SCROLL_SPEED)
        elif self.state == COUNTDOWN:
            self.countdown -= dt
            if self.countdown <= -C.GO_TIME:
                self.state = PLAYING
        elif self.state == PLAYING:
            self.elapsed += dt
            self.speed = min(C.SPEED_MAX, C.SPEED_START + C.SPEED_ACCEL * self.elapsed)
            self.distance_px += self.speed * dt
            self.road.update(dt, self.speed)
            self.car.update(dt)
            new_obstacles, new_stars = self.spawner.update(dt, self.speed)
            self.obstacles += new_obstacles
            self.stars += new_stars
            for o in self.obstacles + self.stars:
                o.update(dt, self.speed)
            self.obstacles = [o for o in self.obstacles if not o.off_screen()]
            car_rect = self.car.rect()                     # full body: catching is generous
            for s in [s for s in self.stars if car_rect.colliderect(s.rect())]:
                self.stars.remove(s)
                self.stars_caught += 1
                self.popups.append([car_rect.centerx, car_rect.top - 15, C.POPUP_TIME])
                self.star_signal_on()
            self.stars = [s for s in self.stars if not s.off_screen()]
            self.update_popups(dt)
            car_box = self.car.hitbox()
            for o in self.obstacles:
                if car_box.colliderect(o.hitbox()):
                    self.crash(o)
                    break
        elif self.state == CRASHED:
            self.update_popups(dt)
            self.crash_timer -= dt
            if self.crash_timer <= 0:
                self.end_crash()

    def update_popups(self, dt):
        for p in self.popups:
            p[1] -= 60 * dt                                # rise
            p[2] -= dt
        self.popups = [p for p in self.popups if p[2] > 0]

    # ---------- drawing helpers ----------
    def text(self, s, size, color, center=None, topleft=None, topright=None):
        img = self.fonts_get(size).render(s, True, color)
        rect = img.get_rect()
        if center is not None:
            rect.center = center
        elif topleft is not None:
            rect.topleft = topleft
        elif topright is not None:
            rect.topright = topright
        self.screen.blit(img, rect)
        return rect

    def panel(self, rect):
        tmp = pygame.Surface(pygame.Rect(rect).size, pygame.SRCALPHA)
        tmp.fill(C.OVERLAY_BG)
        self.screen.blit(tmp, pygame.Rect(rect).topleft)

    def blink(self):
        return (self.t % 1.0) < 0.65

    def prompt(self, s, y):
        """Bottom instruction line on its own panel (stays readable over the car)."""
        self.panel((40, y - 25, C.WIDTH - 80, 50))
        if self.blink():
            self.text(s, C.FONT_SMALL, C.TEXT, center=(C.WIDTH // 2, y))

    def draw_top10(self, y, highlight=None):
        # columns: rank | name | score | distance | stars | date
        x_rank, x_name, x_score, x_dist, x_stars, x_date = 80, 90, 300, 385, 440, 455
        self.panel((40, y, C.WIDTH - 80, 78 + C.N_HIGHSCORES * 27))
        self.text(f"TOP {C.N_HIGHSCORES}", C.FONT_SMALL, C.TEXT_HIGHLIGHT, center=(C.WIDTH // 2, y + 22))
        head_y = y + 44
        self.text("SCORE", C.FONT_TINY, C.TEXT_DIM, topright=(x_score, head_y))
        self.text("DIST", C.FONT_TINY, C.TEXT_DIM, topright=(x_dist, head_y))
        draw_star_shape(self.screen, (x_stars - 8, head_y + 7), 8)
        self.text("DATE", C.FONT_TINY, C.TEXT_DIM, topleft=(x_date, head_y))
        for i in range(C.N_HIGHSCORES):
            row_y = y + 70 + i * 27
            if i < len(self.scores):
                e = self.scores[i]
                color = C.TEXT_HIGHLIGHT if i == highlight else C.TEXT
                self.text(f"{i + 1}.", C.FONT_TINY, color, topright=(x_rank, row_y))
                self.text(e["name"], C.FONT_TINY, color, topleft=(x_name, row_y))
                self.text(str(e["score"]), C.FONT_TINY, color, topright=(x_score, row_y))
                self.text(f"{e['meters']} m", C.FONT_TINY, C.TEXT_DIM, topright=(x_dist, row_y))
                self.text(str(e["stars"]), C.FONT_TINY, C.TEXT_DIM, topright=(x_stars, row_y))
                self.text(e["date"][:10], C.FONT_TINY, C.TEXT_DIM, topleft=(x_date, row_y))
            else:
                self.text(f"{i + 1}.", C.FONT_TINY, C.TEXT_DIM, topright=(x_rank, row_y))
                self.text("-", C.FONT_TINY, C.TEXT_DIM, topleft=(x_name, row_y))

    def draw_hud(self):
        self.panel((10, 10, 190, 72))
        self.text(f"{self.score()}", C.FONT_MEDIUM, C.TEXT_HIGHLIGHT, topleft=(20, 16))
        meters_rect = self.text(f"{self.meters()} m", C.FONT_TINY, C.TEXT, topleft=(20, 54))
        draw_star_shape(self.screen, (meters_rect.right + 22, 61), 9)
        self.text(str(self.stars_caught), C.FONT_TINY, C.TEXT, topleft=(meters_rect.right + 35, 54))
        self.panel((C.WIDTH - 140, 10, 130, 36))
        self.text(f"{self.kmh()} km/h", C.FONT_SMALL, C.TEXT, topright=(C.WIDTH - 20, 18))

    def draw_input_status(self, y):
        """Menu diagnostics: is OSC listening, and what was the last command received?"""
        if self.osc is None:
            s, color = "Input: keyboard   (Bonsai: run with --input osc)", C.TEXT_DIM
        elif not self.osc.ok:
            s, color = self.osc.status, C.CRASH_FLASH
        else:
            last = self.osc.last_command.name if self.osc.last_command else "-"
            s, color = f"{self.osc.status}   |   last command: {last}  ({self.osc.n_commands})", C.TEXT
            if self.osc.last_message is not None:          # raw values: checks the Bonsai link
                address, args = self.osc.last_message
                values = ", ".join(f"{a:g}" if isinstance(a, float) else str(a) for a in args[:4])
                raw = f"received {self.osc.n_messages}   last: {address} ({values})"
            else:
                raw = "nothing received yet"
            self.panel((40, y - 50, C.WIDTH - 80, 26))
            self.text(raw, C.FONT_TINY, C.TEXT_DIM, center=(C.WIDTH // 2, y - 37))
        self.panel((40, y - 16, C.WIDTH - 80, 32))
        self.text(s, C.FONT_TINY, color, center=(C.WIDTH // 2, y))

    def draw_popups(self):
        for x, y, left in self.popups:
            img = self.fonts_get(C.FONT_SMALL).render(f"+{C.STAR_POINTS}", True, C.STAR)
            img.set_alpha(int(255 * left / C.POPUP_TIME))
            self.screen.blit(img, img.get_rect(center=(x, y)))

    def fonts_get(self, size):
        if size not in self.fonts:
            self.fonts[size] = pygame.font.Font(None, size)
        return self.fonts[size]

    def draw_crash_effect(self):
        p = 1 - max(self.crash_timer, 0) / C.CRASH_ANIM_TIME   # 0 -> 1
        fx = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        fx.fill((*C.CRASH_FLASH, int(140 * (1 - p))))
        for i in range(6):
            a = math.radians(i * 60 + 20)
            center = (self.crash_point[0] + math.cos(a) * p * 40, self.crash_point[1] + math.sin(a) * p * 30)
            color = C.FIRE if i % 2 else C.SMOKE
            pygame.draw.circle(fx, (*color, int(220 * (1 - p))), center, 8 + p * 30)
        self.screen.blit(fx, (0, 0))

    # ---------- screens ----------
    def draw(self):
        self.road.draw(self.screen)
        for s in self.stars:
            s.draw(self.screen, self.elapsed)
        for o in sorted(self.obstacles, key=lambda o: o.y):     # far ones first
            o.draw(self.screen, self.elapsed)
        offset = (0, 0)
        if self.state == CRASHED:
            amp = max(1, round(C.CRASH_SHAKE * self.crash_timer / C.CRASH_ANIM_TIME))
            offset = (random.randint(-amp, amp), random.randint(-amp, amp))
        self.car.draw(self.screen, offset)
        self.draw_popups()
        if self.state in (COUNTDOWN, PLAYING, PAUSED, CRASHED):
            self.draw_hud()

        cx = C.WIDTH // 2
        if self.state == MENU:
            self.panel((40, 70, C.WIDTH - 80, 200))
            self.text("EMG LANE DODGER", C.FONT_BIG - 8, C.TEXT_HIGHLIGHT, center=(cx, 120))
            self.text("Dodge the obstacles, catch the stars!", C.FONT_TINY, C.TEXT, center=(cx, 172))
            self.text(f"Score = meters + {C.STAR_POINTS} per star", C.FONT_TINY, C.TEXT, center=(cx, 202))
            self.text("LEFT / RIGHT (or A / D): lane      P: pause      ESC: back",
                      C.FONT_TINY, C.TEXT_DIM, center=(cx, 238))
            self.draw_top10(290)
            self.prompt("SPACE / ENTER: start      ESC: quit", 672)
            self.draw_input_status(770)
        elif self.state == COUNTDOWN:
            label = str(math.ceil(self.countdown)) if self.countdown > 0 else "GO!"
            self.text(label, C.FONT_BIG * 2, C.TEXT_HIGHLIGHT, center=(cx, C.HEIGHT // 2 - 60))
        elif self.state == PAUSED:
            self.panel((60, 300, C.WIDTH - 120, 160))
            self.text("PAUSED", C.FONT_BIG, C.TEXT, center=(cx, 350))
            self.text("SPACE: resume      ESC: menu", C.FONT_SMALL, C.TEXT_DIM, center=(cx, 420))
        elif self.state == CRASHED:
            self.draw_crash_effect()
        elif self.state == NAME_ENTRY:
            rank = highscores.rank_for(self.scores, self.score())
            self.panel((40, 220, C.WIDTH - 80, 330))
            self.text("NEW HIGH SCORE!", C.FONT_BIG - 8, C.TEXT_HIGHLIGHT, center=(cx, 270))
            self.text(f"{self.score()} points   -   rank #{rank + 1}", C.FONT_MEDIUM, C.TEXT, center=(cx, 330))
            self.text("Enter your name:", C.FONT_SMALL, C.TEXT_DIM, center=(cx, 390))
            box = pygame.Rect(0, 0, 320, 50)
            box.center = (cx, 440)
            pygame.draw.rect(self.screen, C.TEXT, box, 2, border_radius=6)
            name_rect = self.text(self.name, C.FONT_MEDIUM, C.TEXT, center=box.center)
            if self.blink():
                cursor_x = name_rect.right + 3 if self.name else box.centerx
                pygame.draw.line(self.screen, C.TEXT, (cursor_x, box.y + 10), (cursor_x, box.bottom - 10), 2)
            self.text(f"ENTER: confirm      ESC: skip (\"{C.DEFAULT_NAME}\")", C.FONT_TINY, C.TEXT_DIM, center=(cx, 510))
        elif self.state == GAME_OVER:
            self.panel((40, 40, C.WIDTH - 80, 220))
            self.text("CRASHED!", C.FONT_BIG, C.CRASH_FLASH, center=(cx, 85))
            self.text(f"Score: {self.score()}", C.FONT_MEDIUM + 8, C.TEXT_HIGHLIGHT, center=(cx, 145))
            self.text(f"{self.meters()} m   +   {self.stars_caught} stars x {C.STAR_POINTS}",
                      C.FONT_SMALL, C.TEXT, center=(cx, 195))
            self.text(f"Speed at crash: {self.kmh()} km/h", C.FONT_TINY, C.TEXT_DIM, center=(cx, 235))
            self.draw_top10(280, highlight=self.last_rank)
            self.prompt("SPACE / ENTER: play again      ESC: menu", 690)
        self.present()

    def present(self):
        """Scale the logical surface to the resizable window, keeping the aspect ratio (letterbox)."""
        win_w, win_h = self.window.get_size()
        if (win_w, win_h) == (C.WIDTH, C.HEIGHT):
            self.window.blit(self.screen, (0, 0))
        else:
            scale = min(win_w / C.WIDTH, win_h / C.HEIGHT)
            size = (max(1, int(C.WIDTH * scale)), max(1, int(C.HEIGHT * scale)))
            self.window.fill(C.BLACK)
            self.window.blit(pygame.transform.smoothscale(self.screen, size),
                             ((win_w - size[0]) // 2, (win_h - size[1]) // 2))
        pygame.display.flip()

    # ---------- main loop ----------
    def run(self):
        while self.running:
            dt = min(self.clock.tick(C.FPS) / 1000, C.MAX_DT)
            self.process_input()
            if not self.running:
                break
            self.update(dt)
            self.draw()
        for s in self.sources:
            s.stop()
        if self.osc_out is not None:
            if self.star_signal_timer > 0:
                self.osc_out.send(C.OSC_ADDRESS_STAR, 0)   # never leave the signal at 1
            self.osc_out.close()
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description=C.TITLE)
    parser.add_argument("--input", choices=["keyboard", "osc"], default=C.INPUT_MODE,
                        help="osc: also accept LEFT/RIGHT from Bonsai over OSC (keyboard always works)")
    parser.add_argument("--host", default=C.OSC_HOST, help=f"OSC listen address (default {C.OSC_HOST})")
    parser.add_argument("--port", type=int, default=C.OSC_PORT, help=f"OSC UDP port (default {C.OSC_PORT})")
    parser.add_argument("--send-port", type=int, default=C.OSC_SEND_PORT,
                        help=f"UDP port of Bonsai's UdpReceive, for star events (default {C.OSC_SEND_PORT})")
    args = parser.parse_args()
    Game(args.input, args.host, args.port, C.OSC_SEND_HOST, args.send_port).run()
    sys.exit(0)


if __name__ == "__main__":
    main()
