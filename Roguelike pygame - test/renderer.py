utf-8import math
import pygame


class PerspectiveRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.camera_height = 200
        self.fov = 400
        self.horizon = int(height * 0.35)
        self.sky = pygame.transform.scale(pygame.image.load("assets/sky.png").convert(), (width, height))
        self.ground = pygame.transform.scale(pygame.image.load("assets/ground.png").convert(), (width, height))

    def setGround(self, path):
        self.ground = pygame.transform.scale(pygame.image.load(path).convert(), (self.width, self.height))

    def render(self, camera, objects, window):
        horizon = max(0, min(self.height - 1, self.horizon + int(camera.camPITCH)))

        
        window.blit(self.sky, (0, 0), pygame.Rect(0, 0, self.width, horizon + 1))

        if horizon + 1 < self.height:
            window.blit(self.ground, (0, horizon + 1), pygame.Rect(0, 0, self.width, self.height - horizon - 1))

        cos_a = math.cos(camera.camYAW)
        sin_a = math.sin(camera.camYAW)

        
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

            w = max(2, min(self.width * 2, int(image.get_width() * scale)))
            h = max(2, min(self.height * 2, int(image.get_height() * scale)))

            x = int(self.width / 2 + side * scale - w / 2)
            y = int(horizon + self.camera_height * scale - h)
            
            window.blit(pygame.transform.scale(image, (w, h)), (x, y))
