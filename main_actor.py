import math
import pygame
from enemies import applyHitFlash

LEVEL_DAMAGE = {1: 0.2, 2: 0.5, 3: 1, 4: 1.5, 5: 2}
XP_THRESHOLDS = {1: 40, 2: 200, 3: 400, 4: 700}


class Player:
    def __init__(self, x, y, speed):
        self.speed = speed
        self.image_left = pygame.transform.scale(
            pygame.image.load("assets/running-Veritical/walking_up_left_leg.png").convert_alpha(), (180, 180))
        self.image_right = pygame.transform.scale(
            pygame.image.load("assets/running-Veritical/walking_up_right_leg.png").convert_alpha(), (180, 180))
        self.walkIndex = 0
        self.walkTimer = 0
        self.current_image = self.image_left
        self.rect = self.current_image.get_rect(topleft=(x, y))

        self.level, self.xp = 1, 0
        self.damage = LEVEL_DAMAGE[1]
        self.max_hp = 10
        self.hp = self.max_hp
        self.last_hit_time = -1000
        self.hitTime = -1000
        self.pending_levelup = False

    def addXP(self, amount):
        self.xp += amount
        if self.level < 5 and self.xp >= XP_THRESHOLDS.get(self.level, 99999):
            self.level += 1
            self.damage = LEVEL_DAMAGE.get(self.level, self.damage)
            self.pending_levelup = True

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

        cos_a = math.cos(cam_angle)
        sin_a = math.sin(cam_angle)
        self.rect.x += int(round(forward * sin_a + strafe * cos_a))
        self.rect.y += int(round(-forward * cos_a + strafe * sin_a))

        if moving:
            now = pygame.time.get_ticks()
            if now - self.walkTimer >= 333:
                self.walkTimer = now
                self.walkIndex = 1 - self.walkIndex
        else:
            self.walkIndex = 0

        frame = self.image_left if self.walkIndex == 0 else self.image_right
        self.current_image = applyHitFlash(frame, self.hitTime)