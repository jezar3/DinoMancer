utf-8import math
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
        walkRaw = loadSheet("assets/enemies/necromancer_front.png", 4, 2, (2800, 2800))
        self.walkFrames = walkRaw + walkRaw[-2:0:-1]
        self.castFrames = loadSheet("assets/Necromancer/Sprite-00042-Sheet.png", 12, 1, (2800, 2800))
        self.walkIndex = self.castIndex = 0.0
        self.current_image = self.walkFrames[0]
        self.rect = self.current_image.get_rect(topleft=(x, y))
        self.isCasting = False
        self.castStartTime = self.lastCastEnd = pygame.time.get_ticks()
        self.max_hp = self.hp = 100
        self.last_beam_damage_time = self.hitTime = -1000

    def take_damage(self, dmg):
        self.hp = max(0, self.hp - dmg)
        self.hitTime = pygame.time.get_ticks()

    def update(self, player):
        
        now = pygame.time.get_ticks()
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        spawned = []

        if dist > 5000:
            self.rect.x += round(dx / dist * 2)
            self.rect.y += round(dy / dist * 2)

        if not self.isCasting and now - self.lastCastEnd >= 5000:
            self.isCasting, self.castIndex, self.castStartTime = True, 0.0, now
            
            import random
            for _ in range(4):
                gx = self.rect.centerx + random.randint(-400, 400)
                gy = self.rect.centery + random.randint(-400, 400)
                spawned.append(Ghoul(gx, gy))

        if self.isCasting:

            frame = self.castFrames[int(self.castIndex)]

            
            self.castIndex = (self.castIndex + 0.2) if self.castIndex < 11 else 7.0

            
            if now - self.castStartTime >= 4000:
                self.isCasting, self.lastCastEnd = False, now

        else:
            self.walkIndex = (self.walkIndex + 0.2) % len(self.walkFrames)
            frame = self.walkFrames[int(self.walkIndex)]

        self.current_image = applyHitFlash(frame, self.hitTime)
        
        return spawned