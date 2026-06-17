utf-8import math
import pygame




DASH_SPEED      = 250      
DASH_DURATION   = 6      
DASH_COOLDOWN   = 500    
IFRAMES         = 4       


class Dash:
   

    def __init__(self):
        self._active     = False
        self._frame       = 0          
        self._dir_x       = 0.0        
        self._dir_y       = 0.0        
        self._last_dash   = -99999    


    @property
    def is_dashing(self):
        return self._active

    @property
    def is_invincible(self):
        """True while the player is inside i-frames."""
        return self._active and self._frame < IFRAMES

    def try_activate(self, player, cam_angle):
        """Call once when Q is *pressed* (not held). Starts a dash if off cooldown."""
        now = pygame.time.get_ticks()
        if self._active or now - self._last_dash < DASH_COOLDOWN:
            return

       
        keys = pygame.key.get_pressed()
        fwd, strafe = 0.0, 0.0
        if keys[pygame.K_w]: fwd += 1
        if keys[pygame.K_s]: fwd -= 1
        if keys[pygame.K_d]: strafe += 1
        if keys[pygame.K_a]: strafe -= 1
        if fwd == 0 and strafe == 0:
            fwd = 1  

        
        length = math.hypot(fwd, strafe)
        fwd /= length
        strafe /= length
        cos_a = math.cos(cam_angle)
        sin_a = math.sin(cam_angle)
        self._dir_x = fwd * sin_a + strafe * cos_a
        self._dir_y = -fwd * cos_a + strafe * sin_a

        self._active = True
        self._frame = 0
        self._last_dash = now

    def update(self, player):
        """Call every frame. Moves the player while dashing."""
        if not self._active:
            return

        
        player.rect.x += int(self._dir_x * DASH_SPEED)
        player.rect.y += int(self._dir_y * DASH_SPEED)

        self._frame += 1
        if self._frame >= DASH_DURATION:
            self._active = False
