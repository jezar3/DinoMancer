import math
import random
import pygame


SHAKE_INTENSITY = 10       
SHAKE_DURATION  = 300     


class ScreenShake:

    def __init__(self):
        self._start_time = -99999
        self._active = False

    def trigger(self):
        self._start_time = pygame.time.get_ticks()
        self._active = True

    def update(self):
        if not self._active:
            return (0, 0)

        elapsed = pygame.time.get_ticks() - self._start_time
        if elapsed >= SHAKE_DURATION:
            self._active = False
            return (0, 0)

        t = 1.0 - elapsed / SHAKE_DURATION
        magnitude = int(SHAKE_INTENSITY * t)
        ox = random.randint(-magnitude, magnitude)
        oy = random.randint(-magnitude, magnitude)
        return (ox, oy)


def _ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def _draw_alpha_circle(target, x, y, radius, color, alpha, width=0):
    radius = int(max(1, radius))
    alpha = int(max(0, min(255, alpha)))
    if alpha <= 0:
        return
    pad = max(2, width + 2)
    size = radius * 2 + pad * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(
        surf,
        (color[0], color[1], color[2], alpha),
        (size // 2, size // 2),
        radius,
        width,
    )
    target.blit(surf, (int(x - size // 2), int(y - size // 2)))


class _WorldParticle:
    __slots__ = (
        "x", "y", "z", "vx", "vy", "vz", "life", "max_life",
        "radius", "grow", "color", "alpha", "gravity", "ring",
    )

    def __init__(
        self, x, y, z, vx, vy, vz, life, radius, color,
        alpha=230, grow=0.0, gravity=0.0, ring=False,
    ):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.vx = float(vx)
        self.vy = float(vy)
        self.vz = float(vz)
        self.life = int(life)
        self.max_life = max(1, int(life))
        self.radius = float(radius)
        self.grow = float(grow)
        self.color = color
        self.alpha = int(alpha)
        self.gravity = float(gravity)
        self.ring = ring


class WorldVFX:
    def __init__(self, max_particles=520):
        self.max_particles = max_particles
        self._particles = []

    def _push(self, particle):
        self._particles.append(particle)
        overflow = len(self._particles) - self.max_particles
        if overflow > 0:
            del self._particles[:overflow]

    def burst(self, x, y, color, count=16, speed_min=8, speed_max=26,
              z_min=20, z_max=130, radius=4, life_min=22, life_max=42):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(speed_min, speed_max)
            self._push(_WorldParticle(
                x, y, random.uniform(z_min, z_max),
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                random.uniform(1.0, 7.0),
                random.randint(life_min, life_max),
                random.uniform(max(1, radius - 2), radius + 2),
                color,
                alpha=random.randint(160, 240),
                grow=random.uniform(0.1, 0.6),
                gravity=random.uniform(0.06, 0.18),
            ))

    def ring(self, x, y, color, count=22, speed=20, radius=5, life=30):
        for i in range(count):
            angle = math.tau * i / count + random.uniform(-0.08, 0.08)
            pulse = speed * random.uniform(0.8, 1.25)
            self._push(_WorldParticle(
                x, y, random.uniform(8, 45),
                math.cos(angle) * pulse,
                math.sin(angle) * pulse,
                random.uniform(0.5, 2.5),
                life + random.randint(-5, 8),
                radius,
                color,
                alpha=210,
                grow=0.9,
                gravity=0.02,
                ring=True,
            ))

    def death_burst(self, x, y, boss=False):
        if boss:
            self.burst(x, y, (190, 80, 255), count=58, speed_min=16, speed_max=48,
                       z_min=30, z_max=220, radius=7, life_min=36, life_max=70)
            self.ring(x, y, (255, 230, 160), count=42, speed=36, radius=8, life=48)
            return
        color = random.choice(((255, 95, 70), (255, 180, 80), (120, 210, 255)))
        self.burst(x, y, color, count=18, speed_min=8, speed_max=28,
                   z_min=15, z_max=120, radius=4, life_min=20, life_max=38)
        self.ring(x, y, (255, 220, 120), count=14, speed=18, radius=3, life=24)

    def xp_pickup(self, x, y):
        self.burst(x, y, (100, 180, 255), count=10, speed_min=4, speed_max=15,
                   z_min=45, z_max=150, radius=3, life_min=18, life_max=30)

    def heal_pickup(self, x, y):
        self.burst(x, y, (100, 255, 140), count=16, speed_min=5, speed_max=18,
                   z_min=35, z_max=150, radius=4, life_min=22, life_max=36)
        self.ring(x, y, (180, 255, 190), count=18, speed=14, radius=4, life=28)

    def level_up(self, x, y):
        self.burst(x, y, (255, 230, 90), count=44, speed_min=10, speed_max=38,
                   z_min=45, z_max=260, radius=5, life_min=34, life_max=64)
        self.ring(x, y, (255, 255, 190), count=36, speed=28, radius=6, life=44)
        self.ring(x, y, (120, 220, 255), count=28, speed=18, radius=4, life=52)

    def boss_spawn(self, x, y):
        self.burst(x, y, (170, 70, 255), count=62, speed_min=10, speed_max=44,
                   z_min=20, z_max=260, radius=6, life_min=40, life_max=78)
        self.ring(x, y, (120, 30, 200), count=50, speed=34, radius=9, life=60)
        self.ring(x, y, (255, 180, 255), count=28, speed=18, radius=5, life=52)

    def projectile_trail(self, x, y):
        for _ in range(2):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(1, 5)
            self._push(_WorldParticle(
                x, y, random.uniform(25, 110),
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                random.uniform(-0.5, 1.5),
                random.randint(14, 24),
                random.uniform(2, 4),
                (190, 80, 255),
                alpha=150,
                grow=0.35,
                gravity=0.0,
            ))

    def update(self):
        alive = []
        for p in self._particles:
            p.life -= 1
            if p.life <= 0:
                continue
            p.x += p.vx
            p.y += p.vy
            p.z = max(0.0, p.z + p.vz)
            p.vz -= p.gravity
            p.vx *= 0.985
            p.vy *= 0.985
            alive.append(p)
        self._particles = alive

    def draw_world(self, window, camera, renderer):
        if not self._particles:
            return

        horizon = max(0, min(renderer.height - 1, renderer.horizon + int(camera.camPITCH)))
        cos_yaw, sin_yaw = math.cos(camera.camYAW), math.sin(camera.camYAW)
        half_w = renderer.width / 2

        for p in self._particles:
            dx = p.x - camera.world_x
            dy = p.y - camera.world_y
            forward = dx * sin_yaw - dy * cos_yaw
            if forward <= 10:
                continue

            side = dx * cos_yaw + dy * sin_yaw
            scale = min(renderer.fov / forward, 8)
            sx = int(half_w + side * scale)
            sy = int(horizon + renderer.camera_height * scale - p.z * scale)
            if sx < -80 or sx > renderer.width + 80 or sy < -80 or sy > renderer.height + 80:
                continue

            age = 1.0 - p.life / p.max_life
            fade = (p.life / p.max_life) ** 0.75
            radius = p.radius * (1.0 + p.grow * _ease_out_cubic(age))
            radius = max(1, min(42, radius * max(0.45, scale * 0.9)))
            alpha = int(p.alpha * fade)

            if p.ring:
                _draw_alpha_circle(window, sx, sy, radius, p.color, alpha, width=max(1, int(radius * 0.2)))
            else:
                _draw_alpha_circle(window, sx, sy, radius * 2.2, p.color, alpha * 0.28)
                _draw_alpha_circle(window, sx, sy, radius, p.color, alpha)


FLASH_TOTAL_MS   = 1600   
FLASH_FADE_IN_MS = 200    


class LevelUpFlash:

    def __init__(self):
        self._start_time = -99999
        self._active = False
        self._font = None         

    def trigger(self):
        self._start_time = pygame.time.get_ticks()
        self._active = True

    def draw(self, window):
        if not self._active:
            return

        elapsed = pygame.time.get_ticks() - self._start_time
        if elapsed >= FLASH_TOTAL_MS:
            self._active = False
            return

        if self._font is None:
            sw = window.get_width()
            self._font = pygame.font.SysFont("Monocraft", max(20, sw // 18))

        if elapsed < FLASH_FADE_IN_MS:
            alpha = int(255 * (elapsed / FLASH_FADE_IN_MS))
        else:
            alpha = int(255 * (1.0 - (elapsed - FLASH_FADE_IN_MS) / (FLASH_TOTAL_MS - FLASH_FADE_IN_MS)))
        alpha = max(0, min(255, alpha))

        rise = int(40 * (elapsed / FLASH_TOTAL_MS))
        progress = elapsed / FLASH_TOTAL_MS

        sw, sh = window.get_size()
        cx, cy = sw // 2, sh // 2 - rise

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        ring_alpha = int(alpha * 0.55)
        for i in range(3):
            rt = (progress + i * 0.2) % 1.0
            radius = int((90 + i * 35) * _ease_out_cubic(rt))
            _draw_alpha_circle(overlay, cx, cy, radius, (255, 230, 90), ring_alpha * (1.0 - rt), width=3)

        for i in range(18):
            angle = math.tau * i / 18 + progress * 1.4
            inner = 38 + progress * 20
            outer = inner + 60 * (1.0 - progress)
            x1 = cx + math.cos(angle) * inner
            y1 = cy + math.sin(angle) * inner
            x2 = cx + math.cos(angle) * outer
            y2 = cy + math.sin(angle) * outer
            pygame.draw.line(overlay, (255, 250, 180, int(alpha * 0.22)), (x1, y1), (x2, y2), 2)

        window.blit(overlay, (0, 0))

        txt = self._font.render("LEVEL UP!", True, (255, 240, 120))
        txt.set_alpha(alpha)

        shadow = self._font.render("LEVEL UP!", True, (120, 60, 0))
        shadow.set_alpha(int(alpha * 0.45))
        shadow_rect = shadow.get_rect(center=(cx + 3, cy + 3))
        window.blit(shadow, shadow_rect)

        rect = txt.get_rect(center=(cx, cy))
        window.blit(txt, rect)
