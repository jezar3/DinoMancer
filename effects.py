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

        txt = self._font.render("LEVEL UP!", True, (255, 230, 80))
        txt.set_alpha(alpha)

        sw, sh = window.get_size()
        rect = txt.get_rect(center=(sw // 2, sh // 2 - rise))
        window.blit(txt, rect)
