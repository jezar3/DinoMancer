import math
import pygame
from enemies import applyHitFlash

LEVEL_DAMAGE = {1: 0.2, 2: 0.5, 3: 1, 4: 1.5, 5: 2}



def _xp_threshold(level):
    """Return cumulative XP needed to reach *level*."""
    if level <= 0:
        return 0
    if level == 1:
        return 40
    if level == 2:
        return 200
    if level == 3:
        return 400
    if level == 4:
        return 700
    
    base = 700
    for lv in range(5, level + 1):
        
        base += 200 + int(80 * math.log2(max(2, lv)))
    return base

XP_THRESHOLDS = {}
for _lv in range(1, 6):
    XP_THRESHOLDS[_lv] = _xp_threshold(_lv)


class Player:
    def __init__(self, x, y, speed, use_nmancer=False):
        self.speed = speed
        self.base_speed = speed
        self.use_nmancer = use_nmancer
        if use_nmancer:
            sprite_dir = "assets/Nmancer run"
            self.image_left = pygame.transform.scale(
                pygame.image.load(f"{sprite_dir}/walking_up_left_leg.png").convert_alpha(), (180, 180))
            self.image_right = pygame.transform.scale(
                pygame.image.load(f"{sprite_dir}/walking_up_right_leg.png").convert_alpha(), (180, 180))
            self.walk_interval = 35
        else:
            self.image_left = pygame.transform.scale(
                pygame.image.load("assets/running-Veritical/walking_up_left_leg.png").convert_alpha(), (180, 180))
            self.image_right = pygame.transform.scale(
                pygame.image.load("assets/running-Veritical/walking_up_right_leg.png").convert_alpha(), (180, 180))
            self.walk_interval = 333
        self.walkIndex = 0
        self.walkTimer = 0
        self.current_image = self.image_left
        self.rect = self.current_image.get_rect(topleft=(x, y))

        self.level, self.xp = 1, 0
        self.damage = LEVEL_DAMAGE[1]
        self.max_hp = 8          
        self.hp = self.max_hp
        self.last_hit_time = -1000
        self.hitTime = -1000
        self.pending_levelup = False

        
        self.debuff_active = False
        self.debuff_end_time = 0
        self.debuff_immunity_end = 0    

    def addXP(self, amount):
        self.xp += amount
        threshold = XP_THRESHOLDS.get(self.level)
        if threshold is None:
            threshold = _xp_threshold(self.level)
            XP_THRESHOLDS[self.level] = threshold
        if self.xp >= threshold:
            self.level += 1
            
            if self.level <= 5:
                self.damage = LEVEL_DAMAGE.get(self.level, self.damage)
            else:
                self.damage += 0.15  
            self.pending_levelup = True

    def apply_debuff(self, duration_ms):
        """Apply TreeMob root: disable attacks, dash, and movement."""
        now = pygame.time.get_ticks()
        if now < self.debuff_immunity_end:
            return False
        self.debuff_active = True
        self.debuff_end_time = now + duration_ms
        from enemies import TREE_MOB_IMMUNITY_MS
        self.debuff_immunity_end = self.debuff_end_time + TREE_MOB_IMMUNITY_MS
        return True

    def update_debuff(self):
        """Must be called every frame. Clears expired debuff."""
        if self.debuff_active and pygame.time.get_ticks() >= self.debuff_end_time:
            self.debuff_active = False

    @property
    def debuff_time_remaining(self):
        if not self.debuff_active:
            return 0.0
        return max(0, self.debuff_end_time - pygame.time.get_ticks()) / 1000.0

    def wasd(self, cam_angle=0):
        keys = pygame.key.get_pressed()
        forward, strafe = 0, 0
        moving = False

        if keys[pygame.K_w]: forward += self.speed; moving = True
        if keys[pygame.K_s]: forward -= self.speed; moving = True
        if keys[pygame.K_d]: strafe += self.speed; moving = True
        if keys[pygame.K_a]: strafe -= self.speed; moving = True

        if forward != 0 and strafe != 0:
            forward *= 0.707
            strafe *= 0.707

        
        if self.debuff_active:
            forward = 0
            strafe = 0

        cos_a = math.cos(cam_angle)
        sin_a = math.sin(cam_angle)
        self.rect.x += int(round(forward * sin_a + strafe * cos_a))
        self.rect.y += int(round(-forward * cos_a + strafe * sin_a))

        if moving:
            now = pygame.time.get_ticks()
            if now - self.walkTimer >= self.walk_interval:
                self.walkTimer = now
                self.walkIndex = 1 - self.walkIndex
        else:
            self.walkIndex = 0

        frame = self.image_left if self.walkIndex == 0 else self.image_right
        self.current_image = applyHitFlash(frame, self.hitTime)
