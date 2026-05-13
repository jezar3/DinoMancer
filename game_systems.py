import math, random, os, pygame

def _make_circle_surf(radius, color, glow_color=None):
    size = radius * 4
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    if glow_color:
        for r in range(radius * 2, radius, -1):
            a = max(0, int(80 * (1 - (r - radius) / radius)))
            pygame.draw.circle(surf, (*glow_color, a), (cx, cy), r)
    pygame.draw.circle(surf, color, (cx, cy), radius)

    pygame.draw.circle(surf, (255, 255, 255, 120), (cx - radius // 3, cy - radius // 3), radius // 3)
    return surf

ORB_MAGNET_RANGE = 2000
ORB_SPEED = 30
ORB_XP_VALUE = 10

class XPOrb:
    _sprite = None

    def __init__(self, x, y):
        if XPOrb._sprite is None:
            XPOrb._sprite = _make_circle_surf(14, (100, 140, 255), (60, 80, 220))
        self.image = XPOrb._sprite
        self.x, self.y = float(x), float(y)
        self.alive = True

    def update(self, player):
        dx = player.rect.centerx - self.x
        dy = player.rect.centery - self.y
        dist = math.hypot(dx, dy)
        if dist < 30:
            self.alive = False
            return ORB_XP_VALUE
        if dist < ORB_MAGNET_RANGE:
            self.x += dx / dist * ORB_SPEED
            self.y += dy / dist * ORB_SPEED
        return 0

    def get_render_obj(self):
        return {"world_x": self.x, "world_y": self.y, "image": self.image}


HEAL_AMOUNT = 2

class HealthPickup:
    _sprite = None

    def __init__(self, x, y):
        if HealthPickup._sprite is None:
            HealthPickup._sprite = _make_circle_surf(16, (220, 50, 50), (200, 30, 30))
        self.image = HealthPickup._sprite
        self.x, self.y = float(x), float(y)
        self.alive = True

    def update(self, player):
        dx = player.rect.centerx - self.x
        dy = player.rect.centery - self.y
        if math.hypot(dx, dy) < 50:
            self.alive = False
            player.hp = min(player.max_hp, player.hp + HEAL_AMOUNT)
            return True
        return False

    def get_render_obj(self):
        return {"world_x": self.x, "world_y": self.y, "image": self.image}


LARGE_ORB_XP = 20

class LargeXPOrb:
    _sprite = None

    def __init__(self, x, y):
        if LargeXPOrb._sprite is None:
            LargeXPOrb._sprite = _make_circle_surf(22, (180, 100, 255), (140, 60, 240))
        self.image = LargeXPOrb._sprite
        self.x, self.y = float(x), float(y)
        self.alive = True

    def update(self, player):
        dx = player.rect.centerx - self.x
        dy = player.rect.centery - self.y
        dist = math.hypot(dx, dy)
        if dist < 40:
            self.alive = False
            return LARGE_ORB_XP
        if dist < ORB_MAGNET_RANGE * 1.3:
            self.x += dx / dist * ORB_SPEED
            self.y += dy / dist * ORB_SPEED
        return 0

    def get_render_obj(self):
        return {"world_x": self.x, "world_y": self.y, "image": self.image}


WAVE_DISPLAY_MS = 2000

class WaveAnnouncer:
    def __init__(self):
        self.wave = 0
        self._show_time = -99999
        self._font = None

    def announce(self, wave_num):
        self.wave = wave_num
        self._show_time = pygame.time.get_ticks()

    @property
    def is_showing(self):
        return pygame.time.get_ticks() - self._show_time < WAVE_DISPLAY_MS

    def draw(self, window):
        elapsed = pygame.time.get_ticks() - self._show_time
        if elapsed >= WAVE_DISPLAY_MS:
            return
        if self._font is None:
            self._font = pygame.font.SysFont("Monocraft", max(28, window.get_width() // 14))
        t = elapsed / WAVE_DISPLAY_MS
        alpha = int(255 * (1 - t) ** 0.5)
        scale = 1.0 + t * 0.3
        txt = self._font.render(f"Wave {self.wave}", True, (255, 220, 80))
        w = int(txt.get_width() * scale)
        h = int(txt.get_height() * scale)
        scaled = pygame.transform.scale(txt, (w, h))
        scaled.set_alpha(alpha)
        sw, sh = window.get_size()
        window.blit(scaled, scaled.get_rect(center=(sw // 2, sh // 3)))


STREAK_TIMEOUT_MS = 3000

class KillStreak:
    def __init__(self):
        self.count = 0
        self._last_kill = -99999
        self._font = None

    def register_kill(self):
        now = pygame.time.get_ticks()
        if now - self._last_kill > STREAK_TIMEOUT_MS:
            self.count = 0
        self.count += 1
        self._last_kill = now

    def draw(self, window):
        now = pygame.time.get_ticks()
        if now - self._last_kill > STREAK_TIMEOUT_MS:
            self.count = 0
            return
        if self.count < 2:
            return
        if self._font is None:
            self._font = pygame.font.SysFont("Monocraft", max(16, window.get_width() // 30))
        fade = max(0, min(255, int(255 * (1 - (now - self._last_kill) / STREAK_TIMEOUT_MS))))
        colors = [(255,255,255),(255,220,80),(255,140,40),(255,60,60)]
        ci = min(len(colors)-1, self.count // 5)
        txt = self._font.render(f"x{self.count} STREAK!", True, colors[ci])
        txt.set_alpha(fade)
        sw = window.get_width()
        window.blit(txt, (sw // 2 - txt.get_width() // 2, 60))


DEFAULT_CLIP = 6
RELOAD_TIME_MS = 1500

class AmmoSystem:
    def __init__(self, clip_size=DEFAULT_CLIP):
        self.clip_size = clip_size
        self.ammo = clip_size
        self.reloading = False
        self._reload_start = 0
        self._font = None

    def can_fire(self):
        if self.reloading:
            return False
        return self.ammo > 0

    def consume(self):
        if self.ammo > 0:
            self.ammo -= 1
            if self.ammo == 0:
                self.start_reload()

    def start_reload(self):
        if not self.reloading and self.ammo < self.clip_size:
            self.reloading = True
            self._reload_start = pygame.time.get_ticks()

    def update(self):
        if self.reloading:
            if pygame.time.get_ticks() - self._reload_start >= RELOAD_TIME_MS:
                self.ammo = self.clip_size
                self.reloading = False

    def get_reload_progress(self):
        if not self.reloading:
            return 1.0
        return min(1.0, (pygame.time.get_ticks() - self._reload_start) / RELOAD_TIME_MS)

    def draw(self, window):
        if self._font is None:
            self._font = pygame.font.SysFont("Monocraft", max(12, window.get_width() // 40))
        sw, sh = window.get_size()
        x, y = sw - 140, sh - 100

        dot_r = 5
        for i in range(self.clip_size):
            cx = x + i * (dot_r * 3)
            cy = y
            if i < self.ammo:
                pygame.draw.circle(window, (255, 220, 80), (cx, cy), dot_r)
            else:
                pygame.draw.circle(window, (60, 60, 60), (cx, cy), dot_r)
            pygame.draw.circle(window, (180, 180, 180), (cx, cy), dot_r, 1)

        if self.reloading:
            prog = self.get_reload_progress()
            bar_w = self.clip_size * dot_r * 3
            pygame.draw.rect(window, (60, 60, 60), (x - dot_r, y + 12, bar_w, 6))
            pygame.draw.rect(window, (255, 180, 40), (x - dot_r, y + 12, int(bar_w * prog), 6))
            txt = self._font.render("RELOADING", True, (255, 180, 40))
            window.blit(txt, (x - dot_r, y + 22))
        else:
            txt = self._font.render(f"{self.ammo}/{self.clip_size}", True, (200, 200, 200))
            window.blit(txt, (x - dot_r, y + 14))


DIFFICULTY_TIERS = [
    (0,    1.0),
    (60,   1.3),
    (120,  1.7),
    (180,  2.2),
    (240,  3.0),
]

class RunTimer:
    def __init__(self):
        self._start = pygame.time.get_ticks()
        self._font = None

    def elapsed_s(self):
        return (pygame.time.get_ticks() - self._start) / 1000.0

    def difficulty_mult(self):
        t = self.elapsed_s()
        mult = 1.0
        for threshold, m in DIFFICULTY_TIERS:
            if t >= threshold:
                mult = m
        return mult

    def draw(self, window):
        if self._font is None:
            self._font = pygame.font.SysFont("Monocraft", max(12, window.get_width() // 40))
        secs = int(self.elapsed_s())
        m, s = divmod(secs, 60)
        txt = self._font.render(f"{m:02d}:{s:02d}", True, (200, 200, 200))
        window.blit(txt, (window.get_width() - txt.get_width() - 16, 10))


class DynamicLighting:
    def __init__(self, w, h):
        self.width, self.height = w, h
        self._mw = w * 3
        self._mh = h * 3
        self._mask = pygame.Surface((self._mw, self._mh), pygame.SRCALPHA)
        self._build_mask()

    def _build_mask(self):
        mw, mh = self._mw, self._mh
        sw, sh = mw // 4, mh // 4
        small = pygame.Surface((sw, sh), pygame.SRCALPHA)
        cx, cy = sw // 2, sh // 2
        bright_r = min(self.width, self.height) * 0.45 / 4
        for y in range(sh):
            for x in range(sw):
                dist = math.hypot(x - cx, y - cy)
                t = min(1.0, dist / bright_r)
                dark = t * t * (3 - 2 * t)
                alpha = int(dark * 200)
                small.set_at((x, y), (0, 0, 0, alpha))
        self._mask = pygame.transform.smoothscale(small, (mw, mh))

    def draw(self, window, player_screen_x, player_screen_y):
        ox = int(player_screen_x - self._mw / 2)
        oy = int(player_screen_y - self._mh / 2)
        window.blit(self._mask, (ox, oy))

SKILL_DEFS = {
    "speed_up": {
        "name": "Swift Feet",
        "desc": "Move speed +1",
        "color": (80, 200, 255),
        "unique": False,
    },
    "attack_up": {
        "name": "Sharpen",
        "desc": "Attack power +1",
        "color": (255, 100, 80),
        "unique": False,
    },
    "bullet_attack": {
        "name": "Bullet Shot",
        "desc": "Unlock projectile gun",
        "color": (255, 220, 60),
        "unique": True,
    },
    "dash": {
        "name": "Shadow Dash",
        "desc": "Unlock dash (Q key)",
        "color": (180, 80, 255),
        "unique": True,
    },
    "clip_size_up": {
        "name": "Extended Mag",
        "desc": "Clip size +2",
        "color": (120, 255, 120),
        "unique": False,
    },
}

XP_THRESHOLDS = {1: 40, 2: 200, 3: 400, 4: 700}

class SkillPicker:

    def __init__(self):
        self.active = False
        self.choices = []
        self._acquired_uniques = set()
        self._card_img = None
        self._font = None
        self._font_sm = None
        self._game_snapshot = None
        self._hovered = -1

    def _load_card(self):
        if self._card_img is None:
            raw = pygame.image.load("assets/ui/choice option.png").convert_alpha()
            for y in range(raw.get_height()):
                for x in range(raw.get_width()):
                    r, g, b, a = raw.get_at((x, y))
                    if r + g + b < 40:
                        raw.set_at((x, y), (0, 0, 0, 0))
            self._card_img = raw

    def open(self, player_has_bullet, player_has_dash, game_surface=None):
        self._load_card()
        if game_surface is not None:
            self._game_snapshot = game_surface.copy()
        pool = []
        pool.append("speed_up")
        pool.append("attack_up")
        pool.append("clip_size_up")
        if "bullet_attack" not in self._acquired_uniques and not player_has_bullet:
            pool.append("bullet_attack")
        if "dash" not in self._acquired_uniques and not player_has_dash:
            pool.append("dash")

        random.shuffle(pool)
        self.choices = pool[:3]
        self.active = True
        self._hovered = -1

    def handle_event(self, event, card_rects):
        if not self.active:
            return None
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self._hovered = -1
            for i, r in enumerate(card_rects):
                if r.collidepoint(mx, my):
                    self._hovered = i
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, r in enumerate(card_rects):
                if r.collidepoint(mx, my):
                    chosen = self.choices[i]
                    if SKILL_DEFS[chosen]["unique"]:
                        self._acquired_uniques.add(chosen)
                    self.active = False
                    return chosen
        return None

    def apply_skill(self, skill_id, player, dash_obj, ammo_sys):
        if skill_id == "speed_up":
            player.speed += 1
        elif skill_id == "attack_up":
            player.damage += 1
        elif skill_id == "bullet_attack":
            return "unlock_bullet"
        elif skill_id == "dash":
            return "unlock_dash"
        elif skill_id == "clip_size_up":
            ammo_sys.clip_size += 2
            ammo_sys.ammo = ammo_sys.clip_size
        return None

    def draw(self, window):
        if not self.active:
            return []
        if self._font is None:
            self._font = pygame.font.SysFont("Monocraft", max(10, window.get_width() // 50))
            self._font_sm = pygame.font.SysFont("Monocraft", max(8, window.get_width() // 65))

        sw, sh = window.get_size()

        if self._game_snapshot is not None:
            window.blit(self._game_snapshot, (0, 0))
        dim = pygame.Surface((sw, sh), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        window.blit(dim, (0, 0))

        title = self._font.render("Choose an Upgrade", True, (255, 230, 80))
        window.blit(title, title.get_rect(center=(sw // 2, sh // 6)))

        card_w = min(280, sw // 4)
        card_h = int(card_w * 0.48)
        gap = 30
        total_w = card_w * 3 + gap * 2
        start_x = (sw - total_w) // 2
        cy = sh // 2

        card_rects = []
        for i, skill_id in enumerate(self.choices):
            info = SKILL_DEFS[skill_id]
            x = start_x + i * (card_w + gap)
            y = cy - card_h // 2

            rect = pygame.Rect(x, y, card_w, card_h)
            card_rects.append(rect)

            card = pygame.transform.scale(self._card_img, (card_w, card_h))
            window.blit(card, (x, y))

            name_surf = self._font.render(info["name"], True, info["color"])
            name_r = name_surf.get_rect(center=(x + card_w // 2, y + card_h // 3))
            window.blit(name_surf, name_r)

            desc_surf = self._font_sm.render(info["desc"], True, (220, 220, 220))
            desc_r = desc_surf.get_rect(center=(x + card_w // 2, y + card_h * 2 // 3))
            window.blit(desc_surf, desc_r)

        return card_rects

class MapDecorations:

    def __init__(self):
        self.chunk_size = 512
        self._cache = {}
        raw = pygame.image.load("assets/world assets/bear_head.png").convert_alpha()
        scaled = pygame.transform.scale(raw, (300, 300))
        for y in range(scaled.get_height()):
            for x in range(scaled.get_width()):
                r, g, b, a = scaled.get_at((x, y))
                if r + g + b < 40:
                    scaled.set_at((x, y), (0, 0, 0, 0))
        self._bear_head = scaled

    def get_decorations_in_range(self, cx, cy, view_dist):
        c1 = int((cx - view_dist) // self.chunk_size) - 1
        c2 = int((cx + view_dist) // self.chunk_size) + 2
        r1 = int((cy - view_dist) // self.chunk_size) - 1
        r2 = int((cy + view_dist) // self.chunk_size) + 2

        result = []
        for row in range(r1, r2):
            for col in range(c1, c2):
                key = (col, row)
                if key not in self._cache:
                    rng = random.Random(col * 48271 + row * 12347)
                    decos = []
                   
                    if rng.random() < 0.001:
                        lx = rng.randint(0, self.chunk_size - 64)
                        ly = rng.randint(0, self.chunk_size - 64)
                        wx = col * self.chunk_size + lx
                        wy = row * self.chunk_size + ly
                        decos.append((wx, wy))
                    self._cache[key] = decos
                for wx, wy in self._cache[key]:
                    result.append({"world_x": wx, "world_y": wy, "image": self._bear_head})
        return result
