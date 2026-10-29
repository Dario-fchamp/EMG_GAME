"""Obstacles (rock, tree, stickman, crashed car), drawn with pygame primitives only."""
import math
import os
import random

import pygame

import config as C


def lane_center_x(lane):
    return C.ROAD_MARGIN + (lane + 0.5) * C.LANE_WIDTH


def shrink(rect, frac):
    """Rect made smaller by `frac` of its size on each side."""
    return rect.inflate(-round(rect.w * frac * 2), -round(rect.h * frac * 2))


def _alpha_ellipse(surf, color, rect, alpha):
    rect = pygame.Rect(rect)
    tmp = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.ellipse(tmp, (*color, alpha), tmp.get_rect())
    surf.blit(tmp, rect.topleft)


def _alpha_circle(surf, color, center, radius, alpha):
    radius = max(1, round(radius))
    tmp = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(tmp, (*color, alpha), (radius, radius), radius)
    surf.blit(tmp, (round(center[0]) - radius, round(center[1]) - radius))


def _shadow(surf, r):
    _alpha_ellipse(surf, C.BLACK, (r.x + r.w * 0.1, r.bottom - r.h * 0.15, r.w * 0.9, r.h * 0.25), 80)


def draw_rock(surf, r, v, t):
    rng = random.Random(v)                      # same shape every frame
    _shadow(surf, r)
    cx, cy = r.center
    pts = []
    for i in range(8):
        a = math.radians(i * 45 + rng.uniform(-15, 15))
        pts.append((cx + math.cos(a) * r.w / 2 * rng.uniform(0.8, 1.0),
                    cy + math.sin(a) * r.h / 2 * rng.uniform(0.8, 1.0)))
    pygame.draw.polygon(surf, C.ROCK, pts)
    highlight = [(cx - r.w * 0.15 + (x - cx) * 0.3, cy - r.h * 0.18 + (y - cy) * 0.3) for x, y in pts]
    pygame.draw.polygon(surf, C.ROCK_LIGHT, highlight)
    for _ in range(rng.randint(2, 3)):
        x0, y0 = cx + rng.uniform(-0.25, 0.25) * r.w, cy + rng.uniform(-0.2, 0.25) * r.h
        x1, y1 = x0 + rng.uniform(-0.15, 0.15) * r.w, y0 + rng.uniform(0.1, 0.2) * r.h
        pygame.draw.line(surf, C.ROCK_DARK, (x0, y0), (x1, y1), 2)
    pygame.draw.polygon(surf, C.ROCK_DARK, pts, 3)


def draw_tree(surf, r, v, t):
    rng = random.Random(v)
    _shadow(surf, r)
    trunk_w = r.w * 0.2
    pygame.draw.rect(surf, C.TREE_TRUNK, (r.centerx - trunk_w / 2, r.y + r.h * 0.6, trunk_w, r.h * 0.4))
    fr = pygame.Rect(r.x, r.y, r.w, r.h * 0.7)  # foliage area
    rad = fr.w * 0.32
    centers = [(fr.x + rad, fr.y + fr.h * 0.6), (fr.right - rad, fr.y + fr.h * 0.6), (fr.centerx, fr.y + rad)]
    for x, y in centers:                        # shading first, offset bottom-right
        pygame.draw.circle(surf, C.TREE_LEAVES_DARK, (x + 4, y + 5), rad)
    for x, y in centers:
        pygame.draw.circle(surf, C.TREE_LEAVES, (x, y), rad)
    for _ in range(3):
        pygame.draw.circle(surf, C.TREE_LEAVES_LIGHT,
                           (fr.centerx + rng.uniform(-0.3, 0.3) * fr.w, fr.y + rng.uniform(0.2, 0.6) * fr.h),
                           max(2, rad * 0.15))


def draw_stickman(surf, r, v, t):
    _shadow(surf, r)
    cx = r.centerx
    head_r = max(6, r.w * 0.25)
    neck_y = r.y + 2 * head_r
    hips_y = r.y + r.h * 0.6
    shoulder = (cx, neck_y + (hips_y - neck_y) * 0.2)
    arm_len, leg_len = r.h * 0.28, r.bottom - hips_y
    arm_swing = 30 * math.sin(t * 6 + v * 10)   # waving arms
    leg_swing = 15 * math.sin(t * 8 + v * 10)   # walking legs
    for side in (-1, 1):
        a = math.radians(45 + side * arm_swing)
        pygame.draw.line(surf, C.STICKMAN, shoulder,
                         (shoulder[0] + side * math.sin(a) * arm_len, shoulder[1] + math.cos(a) * arm_len), 3)
        a = math.radians(20 + side * leg_swing)
        pygame.draw.line(surf, C.STICKMAN, (cx, hips_y),
                         (cx + side * math.sin(a) * leg_len, hips_y + math.cos(a) * leg_len), 3)
    pygame.draw.line(surf, C.STICKMAN_SHIRT, (cx, neck_y), (cx, hips_y), 7)
    pygame.draw.circle(surf, C.SKIN, (cx, r.y + head_r), head_r)
    pygame.draw.circle(surf, C.STICKMAN, (cx, r.y + head_r), head_r, 2)


def draw_crashed_car(surf, r, v, t):
    rng = random.Random(v)
    angle = rng.uniform(10, 25) * rng.choice((-1, 1))
    w, h = r.size
    car = pygame.Surface((w, h), pygame.SRCALPHA)
    ww, wh = w * 0.18, h * 0.2
    for x, y in ((0, h * 0.1), (w - ww, h * 0.1), (0, h * 0.7), (w - ww + 3, h * 0.76)):   # last one broken
        pygame.draw.rect(car, C.WHEEL, (x, y, ww, wh), border_radius=3)
    pygame.draw.rect(car, C.WRECK_BODY, (w * 0.08, 0, w * 0.84, h), border_radius=10)
    pygame.draw.polygon(car, C.WRECK_DARK, [(w * 0.92, h * 0.45), (w * 0.68, h * 0.56), (w * 0.92, h * 0.7)])
    shield = [(w * 0.22, h * 0.22), (w * 0.78, h * 0.22), (w * 0.72, h * 0.38), (w * 0.28, h * 0.38)]
    pygame.draw.polygon(car, C.WRECK_WINDOW, shield)
    crack = (w * 0.45, h * 0.3)
    for end in ((w * 0.25, h * 0.24), (w * 0.7, h * 0.36), (w * 0.6, h * 0.23)):
        pygame.draw.line(car, C.TEXT_DIM, crack, end, 1)
    pygame.draw.rect(car, C.WRECK_WINDOW, (w * 0.28, h * 0.74, w * 0.44, h * 0.12), border_radius=3)
    for i in range(3):                          # crumpled hood
        y = h * (0.06 + i * 0.045)
        pygame.draw.line(car, C.WRECK_DARK, (w * 0.2, y), (w * 0.8, y + rng.uniform(-4, 4)), 2)
    rotated = pygame.transform.rotate(car, angle)
    surf.blit(rotated, rotated.get_rect(center=r.center))

    base = (r.centerx + rng.uniform(-0.15, 0.15) * w, r.y + h * 0.2)
    flicker = 1 + 0.2 * math.sin(t * 20 + v * 10)
    fh = h * 0.18 * flicker
    pygame.draw.polygon(surf, C.FIRE, [(base[0] - 8, base[1] + 6), (base[0] + 8, base[1] + 6), (base[0], base[1] + 6 - fh)])
    pygame.draw.polygon(surf, C.FIRE_CORE, [(base[0] - 4, base[1] + 6), (base[0] + 4, base[1] + 6), (base[0], base[1] + 6 - fh * 0.5)])
    for i in range(3):                          # smoke puffs rising and fading in a loop
        phase = (t * 0.8 + i / 3 + v) % 1
        _alpha_circle(surf, C.SMOKE,
                      (base[0] + 6 * math.sin(phase * 6 + i), base[1] - phase * 40),
                      8 + phase * 10, int(160 * (1 - phase)))


DRAWERS = {"rock": draw_rock, "tree": draw_tree,
           "stickman": draw_stickman, "crashed_car": draw_crashed_car}

_sprite_cache = {}


def _sprite(kind, size):
    """assets/<kind>.png scaled to size, or None if missing (falls back to shapes)."""
    key = (kind, size)
    if key not in _sprite_cache:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), C.ASSETS_DIR, f"{kind}.png")
        try:
            _sprite_cache[key] = pygame.transform.smoothscale(pygame.image.load(p).convert_alpha(), size)
        except (pygame.error, FileNotFoundError):
            print(f"Warning: sprite {p} not found, drawing shapes instead.")
            _sprite_cache[key] = None
    return _sprite_cache[key]


def draw_star_shape(surf, center, radius, angle_deg=0, color=C.STAR, outline=C.STAR_DARK):
    """5-pointed star; also used as the star icon in the HUD and Top 10."""
    pts = []
    for i in range(10):
        r = radius if i % 2 == 0 else radius * 0.45
        a = math.radians(angle_deg - 90 + i * 36)
        pts.append((center[0] + math.cos(a) * r, center[1] + math.sin(a) * r))
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, outline, pts, 2)


class Star:
    """Bonus pickup: caught by driving over it."""

    def __init__(self, lane):
        self.lane = lane
        self.size = C.STAR_SIZE
        self.y = -self.size                     # same spawn line as obstacles (bottom at y = 0)
        self.phase = random.uniform(0, 2 * math.pi)

    def update(self, dt, speed):
        self.y += speed * dt

    def rect(self):
        return pygame.Rect(round(lane_center_x(self.lane) - self.size / 2), round(self.y), self.size, self.size)

    def off_screen(self):
        return self.y > C.HEIGHT

    def draw(self, surf, t):
        center = self.rect().center
        pulse = 1 + 0.12 * math.sin(t * 6 + self.phase)
        _alpha_circle(surf, C.STAR_GLOW, center, self.size * 0.6 * pulse, 90)
        draw_star_shape(surf, center, self.size / 2 * pulse, angle_deg=t * 90 + math.degrees(self.phase))


class Obstacle:
    def __init__(self, lane, kind):
        spec = C.OBSTACLE_TYPES[kind]
        self.lane, self.kind = lane, kind
        self.w, self.h = spec["w"] * C.LANE_WIDTH, spec["h"]
        self.y = -self.h                        # top edge, starts just above the screen
        self.variant = random.random()          # per-instance look (shape, tilt)

    def update(self, dt, speed):
        self.y += speed * dt

    def rect(self):
        return pygame.Rect(round(lane_center_x(self.lane) - self.w / 2), round(self.y), round(self.w), self.h)

    def hitbox(self):
        return shrink(self.rect(), C.HITBOX_SHRINK)

    def off_screen(self):
        return self.y > C.HEIGHT

    def draw(self, surf, t):
        r = self.rect()
        sprite = _sprite(self.kind, r.size) if C.USE_SPRITES else None
        if sprite is not None:
            surf.blit(sprite, r)
        else:
            DRAWERS[self.kind](surf, r, self.variant, t)
