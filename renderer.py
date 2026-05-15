import math
import pygame


class PerspectiveRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.camera_height = 300
        self.fov = 305
        self.horizon = int(height * 0.35)
        self.sky = pygame.transform.scale(pygame.image.load("assets/sky.png").convert(), (width, height))
        self.ground = pygame.transform.scale(pygame.image.load("assets/ground.png").convert(), (width, height))
        self._scale_cache = {}
        self._cache_limit = 1024

    def setGround(self, path):
        self.ground = pygame.transform.scale(pygame.image.load(path).convert(), (self.width, self.height))

    def _scaled(self, image, w, h):
        key = (id(image), w, h)
        cached = self._scale_cache.get(key)
        if cached is not None:
            return cached
        scaled = pygame.transform.scale(image, (w, h))
        if len(self._scale_cache) >= self._cache_limit:
            keys = list(self._scale_cache)
            for k in keys[:len(keys) // 4]:
                del self._scale_cache[k]
        self._scale_cache[key] = scaled
        return scaled

    def render(self, camera, objects, window):
        horizon = max(0, min(self.height - 1, self.horizon + int(camera.camPITCH)))

        window.blit(self.sky, (0, 0), pygame.Rect(0, 0, self.width, horizon + 1))

        if horizon + 1 < self.height:
            window.blit(self.ground, (0, horizon + 1), pygame.Rect(0, 0, self.width, self.height - horizon - 1))

        cos_a = math.cos(camera.camYAW)
        sin_a = math.sin(camera.camYAW)

        half_w = self.width / 2
        max_w = self.width * 2
        max_h = self.height * 2

        visible = []
        for obj in objects:
            dx = obj["world_x"] - camera.world_x
            dy = obj["world_y"] - camera.world_y
            forward = dx * sin_a - dy * cos_a
            if forward <= 10:
                continue
            side = dx * cos_a + dy * sin_a
            visible.append((forward, side, obj["image"]))

        visible.sort(key=lambda item: item[0], reverse=True)

        for forward, side, image in visible:

            scale = min(self.fov / forward, 8)

            w = max(2, min(max_w, int(image.get_width() * scale)))
            h = max(2, min(max_h, int(image.get_height() * scale)))

            x = int(half_w + side * scale - w / 2)
            y = int(horizon + self.camera_height * scale - h)

            if x + w < 0 or x > self.width or y + h < 0 or y > self.height:
                continue
            
            window.blit(self._scaled(image, w, h), (x, y))
