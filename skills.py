import math
import pygame

DASH_SPEED      = 220       
DASH_DURATION   = 6
DASH_COOLDOWN   = 650       
IFRAMES         = 4
GHOST_LIFETIME  = 18
GHOST_TINT      = (100, 60, 200)


def _make_ghost(image, alpha):
    ghost = image.copy()
    tint = pygame.Surface(ghost.get_size(), pygame.SRCALPHA)
    tint.fill((*GHOST_TINT, 100))
    ghost.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    ghost.set_alpha(alpha)
    return ghost


class _Ghost:
    __slots__ = ("world_x", "world_y", "image", "life")

    def __init__(self, wx, wy, img, life):
        self.world_x = wx
        self.world_y = wy
        self.image = img
        self.life = life


class Dash:

    def __init__(self):
        self._active     = False
        self._frame       = 0
        self._dir_x       = 0.0
        self._dir_y       = 0.0
        self._last_dash   = -99999
        self._ghosts      = []


    @property
    def is_dashing(self):
        return self._active

    @property
    def is_invincible(self):
        return self._active and self._frame < IFRAMES

    def try_activate(self, player, cam_angle, dash_sound=None, dash_channel=None):
        now = pygame.time.get_ticks()
        if self._active or now - self._last_dash < DASH_COOLDOWN:
            return

        
        if hasattr(player, 'debuff_active') and player.debuff_active:
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
        if dash_sound:
            if dash_channel:
                dash_channel.play(dash_sound)
            else:
                dash_sound.play()

    def update(self, player):
        for g in self._ghosts:
            g.life -= 1
        self._ghosts = [g for g in self._ghosts if g.life > 0]

        if hasattr(player, 'debuff_active') and player.debuff_active:
            self._active = False
            return

        if not self._active:
            return

        alpha = int(180 * (1 - self._frame / DASH_DURATION))
        ghost_img = _make_ghost(player.current_image, alpha)
        self._ghosts.append(_Ghost(
            player.rect.centerx, player.rect.centery,
            ghost_img, GHOST_LIFETIME
        ))

        player.rect.x += int(self._dir_x * DASH_SPEED)
        player.rect.y += int(self._dir_y * DASH_SPEED)

        self._frame += 1
        if self._frame >= DASH_DURATION:
            self._active = False

    def get_ghost_render_objs(self):
        return [{"world_x": g.world_x, "world_y": g.world_y, "image": g.image}
                for g in self._ghosts]
