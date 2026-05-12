import math
import os
import random
import pygame

FLASH_DURATION = 420

def loadSheet(path, cols, rows, size):
    sheet = pygame.image.load(path).convert_alpha()
    fw, fh = sheet.get_width() // cols, sheet.get_height() // rows
    return [
        pygame.transform.scale(sheet.subsurface((c * fw, r * fh, fw, fh)).copy(), size)
        for r in range(rows) for c in range(cols)
    ]


def applyHitFlash(image, hitTime):
    elapsed = pygame.time.get_ticks() - hitTime
    if elapsed < FLASH_DURATION:
        t = elapsed / FLASH_DURATION
        tinted = image.copy()
        if t < 0.15:
            white_t = 1.0 - (t / 0.15)
            tinted.fill((255, int(220 * white_t), int(220 * white_t), 0), special_flags=pygame.BLEND_RGB_ADD)
        else:
            red_t = 1.0 - t
            tinted.fill((int(255 * red_t), 0, 0, 0), special_flags=pygame.BLEND_RGB_ADD)
        return tinted
    return image


class Slime:
    def __init__(self, x, y):
        self.walkFrames = loadSheet("assets/enemies/bouncing_slime.png", 9, 1, (180, 180))
        self.frameIndex = 0.0
        self.current_image = self.walkFrames[0]
        self.rect = self.current_image.get_rect(topleft=(x, y))
        self.max_hp = self.hp = 3
        self.last_beam_damage_time = self.hitTime = -1000

    def take_damage(self, dmg):
        self.hp = max(0, self.hp - dmg)
        self.hitTime = pygame.time.get_ticks()

    def update(self, player):
        if self.hp <= 0: return
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        self.frameIndex = (self.frameIndex + 0.2) % len(self.walkFrames)
        self.current_image = applyHitFlash(self.walkFrames[int(self.frameIndex)], self.hitTime)
        if dist > 8:
            self.rect.x += round(dx / dist * 8)
            self.rect.y += round(dy / dist * 8)

class Ghoul:
    def __init__(self, x, y):
        self.walkFrames = [
            pygame.transform.scale(pygame.image.load(f"assets/enemies/ghoul/ghoul-running{i}.png").convert_alpha(), (180, 180))
            for i in (1, 2)
        ]
        self.frameIndex = 0.0
        self.current_image = self.walkFrames[0]
        self.rect = self.current_image.get_rect(topleft=(x, y))
        self.max_hp = self.hp = 4
        self.last_beam_damage_time = self.hitTime = -1000
        self.lastDashTime = pygame.time.get_ticks()

    def take_damage(self, dmg):
        self.hp = max(0, self.hp - dmg)
        self.hitTime = pygame.time.get_ticks()

    def update(self, player):
        if self.hp <= 0: return
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        self.frameIndex = (self.frameIndex + 0.25) % len(self.walkFrames)
        self.current_image = applyHitFlash(self.walkFrames[int(self.frameIndex)], self.hitTime)
        if dist > 8:
            speed = 16
            now = pygame.time.get_ticks()
            if now - self.lastDashTime >= 2000:
                self.lastDashTime = now
                speed = 40
            self.rect.x += round(dx / dist * speed)
            self.rect.y += round(dy / dist * speed)



class Necromancer:
    def __init__(self, x, y):
        walkRaw = loadSheet("assets/enemies/necromancer_front.png", 4, 2, (1300, 1300))
        self.walkFrames = walkRaw + walkRaw[-2:0:-1]
        self.castFrames = loadSheet("assets/Necromancer/Sprite-00042-Sheet.png", 12, 1, (1300, 1300))
        self.beamFrames = [
            pygame.image.load(f"assets/attacks/level 3 beam/LaserShot{i}.png").convert_alpha()
            for i in range(1, 8)
        ]
        self.walkIndex = self.castIndex = 0.0
        self.beamIndex = 0.0
        self.current_image = self.walkFrames[0]
        self.rect = self.current_image.get_rect(topleft=(x, y))
        self.isCasting = False
        self.cast_just_ended = False
        self.castStartTime = self.lastCastEnd = pygame.time.get_ticks()
        self.max_hp = self.hp = 100
        self.last_beam_damage_time = self.hitTime = -1000

    def take_damage(self, dmg):
        self.hp = max(0, self.hp - dmg)
        self.hitTime = pygame.time.get_ticks()

    def get_current_beam_frame(self):
        return self.beamFrames[int(self.beamIndex)]

    def update(self, player):
        now = pygame.time.get_ticks()
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        spawned = []
        self.cast_just_ended = False

        if dist > 5000:
            self.rect.x += round(dx / dist * 2)
            self.rect.y += round(dy / dist * 2)

        if not self.isCasting and now - self.lastCastEnd >= 5000:
            self.isCasting, self.castIndex, self.castStartTime = True, 0.0, now
            self.beamIndex = 0.0
            import random
            for _ in range(4):
                gx = self.rect.centerx + random.randint(-400, 400)
                gy = self.rect.centery + random.randint(-400, 400)
                spawned.append(Ghoul(gx, gy))

        if self.isCasting:

            frame = self.castFrames[int(self.castIndex)]

            self.castIndex = (self.castIndex + 0.2) if self.castIndex < 11 else 7.0
            self.beamIndex = (self.beamIndex + 0.15) % len(self.beamFrames)

            if now - self.castStartTime >= 4000:
                self.isCasting, self.lastCastEnd = False, now
                self.cast_just_ended = True

        else:
            self.walkIndex = (self.walkIndex + 0.2) % len(self.walkFrames)
            frame = self.walkFrames[int(self.walkIndex)]

        self.current_image = applyHitFlash(frame, self.hitTime)
        
        return spawned


def _make_crawler_frames():
    frames = []
    for phase in range(2):
        s = pygame.Surface((180, 180), pygame.SRCALPHA)
        body_color = (120, 80, 160)
        bone_color = (200, 190, 170)
        cy = 100 + (phase * 6 - 3)
        for i in range(6):
            bx = 30 + i * 22
            by = cy + int(math.sin(i + phase * 1.5) * 8)
            pygame.draw.ellipse(s, body_color, (bx, by, 24, 18))
            pygame.draw.ellipse(s, bone_color, (bx + 4, by + 2, 16, 10))
            pygame.draw.line(s, bone_color, (bx + 6, by + 16), (bx, by + 30), 2)
            pygame.draw.line(s, bone_color, (bx + 18, by + 16), (bx + 24, by + 30), 2)
        pygame.draw.circle(s, (180, 60, 60), (24, cy + 2), 14)
        pygame.draw.circle(s, (255, 200, 50), (20, cy - 2), 4)
        pygame.draw.circle(s, (255, 200, 50), (28, cy - 2), 4)
        frames.append(s)
    return frames


class TombCrawler:
    _shared_frames = None

    def __init__(self, x, y):
        if TombCrawler._shared_frames is None:
            path = "assets/enemies/tomb_crawler.png"
            if os.path.exists(path):
                try:
                    raw = pygame.image.load(path).convert_alpha()
                    fw = raw.get_width() // 2
                    fh = raw.get_height()
                    f1 = pygame.transform.scale(raw.subsurface((0, 0, fw, fh)).copy(), (180, 180))
                    f2 = pygame.transform.scale(raw.subsurface((fw, 0, fw, fh)).copy(), (180, 180))
                    for f in (f1, f2):
                        f.set_colorkey((255, 255, 255))
                    TombCrawler._shared_frames = [f1, f2]
                except Exception:
                    TombCrawler._shared_frames = _make_crawler_frames()
            else:
                TombCrawler._shared_frames = _make_crawler_frames()

        self.walkFrames = TombCrawler._shared_frames
        self.frameIndex = 0.0
        self.current_image = self.walkFrames[0]
        self.rect = self.current_image.get_rect(topleft=(x, y))
        self.max_hp = self.hp = 6
        self.last_beam_damage_time = self.hitTime = -1000

    def take_damage(self, dmg):
        self.hp = max(0, self.hp - dmg)
        self.hitTime = pygame.time.get_ticks()

    def update(self, player):
        if self.hp <= 0:
            return
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        self.frameIndex = (self.frameIndex + 0.15) % len(self.walkFrames)
        self.current_image = applyHitFlash(self.walkFrames[int(self.frameIndex)], self.hitTime)
        if dist > 8:
            self.rect.x += round(dx / dist * 10)
            self.rect.y += round(dy / dist * 10)


NECRO_PROJ_SPEED = 230
NECRO_PROJ_DAMAGE = 3
NECRO_PROJ_HIT_RANGE = 140


def _make_projectile_sprite():
    size = 500
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    for r in range(size // 2, 8, -2):
        a = max(0, int(100 * (1 - r / (size // 2))))
        pygame.draw.circle(surf, (140, 30, 180, a), (cx, cy), r)
    pygame.draw.circle(surf, (200, 80, 255, 230), (cx, cy), 16)
    pygame.draw.circle(surf, (240, 180, 255, 255), (cx, cy), 8)
    return surf


class NecromancerProjectile:
    _base_img = None

    def __init__(self, start_x, start_y, target_x, target_y):
        if NecromancerProjectile._base_img is None:
            NecromancerProjectile._base_img = _make_projectile_sprite()
        self.image = NecromancerProjectile._base_img
        self.x, self.y = float(start_x), float(start_y)
        dx = target_x - start_x
        dy = target_y - start_y
        dist = max(1, math.hypot(dx, dy))
        self.dir_x = dx / dist
        self.dir_y = dy / dist
        self.alive = True
        self.lifetime = 360
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def update(self):
        self.x += self.dir_x * NECRO_PROJ_SPEED
        self.y += self.dir_y * NECRO_PROJ_SPEED
        self.rect.center = (int(self.x), int(self.y))
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False

    def check_hit_player(self, player):
        dist = math.hypot(self.x - player.rect.centerx, self.y - player.rect.centery)
        if dist < NECRO_PROJ_HIT_RANGE:
            self.alive = False
            return True
        return False

    def get_render_obj(self):
        return {"world_x": self.x, "world_y": self.y, "image": self.image}