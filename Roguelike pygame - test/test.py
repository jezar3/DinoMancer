utf-8import math
import numpy as np
import pygame




class PerspectiveRenderer:


    def __init__(self, screen_width, screen_height):
        
        self.sw = screen_width
        self.sh = screen_height
        self.scale = 3
        self.iw = screen_width // self.scale     
        self.ih = screen_height // self.scale  
        self.cam_height = 200
        self.focal = self.iw * 0.5               
        self.horizon = int(self.ih * 0.35)        
        self._precompute_ground()
        self._precompute_sky()
        self.pixels = np.zeros((self.iw, self.ih, 3), dtype=np.uint8)
        self.render_surface = pygame.Surface((self.iw, self.ih))

    def _precompute_ground(self):
     
        self.n_rows = self.ih - self.horizon - 1
        rows = np.arange(1, self.n_rows + 1, dtype=np.float32)
        depths_1d = self.cam_height * self.focal / rows          
        cols = np.arange(self.iw, dtype=np.float32) - self.iw / 2.0  
        self.depths = depths_1d.reshape(-1, 1)                   
        self.horiz  = cols.reshape(1, -1) * self.depths / self.focal 
        max_depth = depths_1d[0]  
        self.fog = np.clip(self.depths / (max_depth * 0.65), 0, 1)

    def _precompute_sky(self):
        h = self.horizon + 1
        self.sky_pixels = np.zeros((self.iw, h, 3), dtype=np.uint8)

        t = np.arange(h, dtype=np.float32) / max(h - 1, 1)  

        r = (70 + 110 * t).astype(np.uint8)    
        g = (110 + 100 * t).astype(np.uint8)    
        b = (170 + 80 * t).astype(np.uint8)     

      
        self.sky_pixels[:, :, 0] = r[np.newaxis, :]
        self.sky_pixels[:, :, 1] = g[np.newaxis, :]
        self.sky_pixels[:, :, 2] = b[np.newaxis, :]


    def render(self, camera, tilemap, objects, window):
       
        self.pixels[:] = 0
        self.pixels[:, :self.horizon + 1] = self.sky_pixels
        cos_a = np.float32(math.cos(camera.cam_angle))
        sin_a = np.float32(math.sin(camera.cam_angle))
        world_x = camera.world_x + self.horiz * cos_a + self.depths * sin_a
        world_y = camera.world_y + self.horiz * sin_a - self.depths * cos_a

        tile_x = np.floor(world_x / tilemap.tilePixelSize).astype(np.int64)
        tile_y = np.floor(world_y / tilemap.tilePixelSize).astype(np.int64)

        h = (tile_x * np.int64(374761393) + tile_y * np.int64(668265263))
        h = h & np.int64(0x7FFFFFFF)          
        snow = (220 + (h % np.int64(26)).astype(np.int32)).astype(np.float32)

        fog = self.fog
        r = np.clip(snow * (1 - fog) + 180 * fog, 0, 255).astype(np.uint8)
        g = np.clip(snow * (1 - fog) + 195 * fog, 0, 255).astype(np.uint8)
        b = np.clip((snow * 0.98) * (1 - fog) + 220 * fog, 0, 255).astype(np.uint8)

        start = self.horizon + 1
        self.pixels[:, start:start + self.n_rows, 0] = r.T
        self.pixels[:, start:start + self.n_rows, 1] = g.T
        self.pixels[:, start:start + self.n_rows, 2] = b.T

     
        pygame.surfarray.blit_array(self.render_surface, self.pixels)
        scaled = pygame.transform.scale(self.render_surface, (self.sw, self.sh))
        window.blit(scaled, (0, 0))

        projected = []
        for obj in objects:
            result = self._project(camera, obj['world_x'], obj['world_y'])
            if result is not None:
                sx, sy, obj_scale, depth = result
                projected.append((depth, sx, sy, obj_scale, obj))

        projected.sort(key=lambda item: -item[0])

        for depth, sx, sy, obj_scale, obj in projected:
            img = obj['image']

            w = max(2, int(img.get_width()  * obj_scale * self.scale))
            h = max(2, int(img.get_height() * obj_scale * self.scale))

            if w > self.sw * 3 or h > self.sh * 3:
                continue

            scaled_img = pygame.transform.scale(img, (w, h))

            draw_x = int(sx * self.scale - w // 2)
            draw_y = int(sy * self.scale - h)

            window.blit(scaled_img, (draw_x, draw_y))

    def _project(self, camera, obj_x, obj_y):
        dx = obj_x - camera.world_x
        dy = obj_y - camera.world_y
        
        cos_a = math.cos(camera.cam_angle)
        sin_a = math.sin(camera.cam_angle)

        z_cam = dx * sin_a - dy * cos_a    
        x_cam = dx * cos_a + dy * sin_a    

        if z_cam <= 10:
            return None

        screen_x = self.iw / 2.0 + x_cam * self.focal / z_cam
        screen_y = self.horizon + self.cam_height * self.focal / z_cam
        scale = self.focal / z_cam

        if screen_x < -self.iw or screen_x > self.iw * 2:
            return None
        if screen_y < -self.ih or screen_y > self.ih * 2:
            return None
        
        return screen_x, screen_y, scale, z_cam