import math
import pygame

ATTACK_FRAME_TIME = 80
BEAM_DAMAGE_COOLDOWN = 250
BEAM_DAMAGE_MULTIPLIER = 0.2
BULLET_FIRE_COOLDOWN = 500
BULLET_DAMAGE_PER_LEVEL = {1: 0.5, 2: 1.0, 3: 1.5, 4: 2.0, 5: 3.0}
BULLET_SPEED = 14
BULLET_LIFETIME = 90
BULLET_SCALE = 1.25

def loadFrames(paths):
    return [pygame.image.load(p).convert_alpha() for p in paths]


def getScreenPos(actor, camera, renderer):
    horizon = max(0, min(renderer.height - 1, renderer.horizon + int(camera.camPITCH)))
    cosYaw, sinYaw = math.cos(camera.camYAW), math.sin(camera.camYAW)

    dx = actor.rect.centerx - camera.world_x
    dy = actor.rect.centery - camera.world_y
    
    forwardDist = dx * sinYaw - dy * cosYaw
    if forwardDist <= 10: return None

    sideDist = dx * cosYaw + dy * sinYaw

    drawScale = min(renderer.fov / forwardDist, 8)

    drawW = max(2, min(renderer.width * 2,  int(actor.current_image.get_width()  * drawScale)))
    drawH = max(2, min(renderer.height * 2, int(actor.current_image.get_height() * drawScale)))

    screenX = int(renderer.width / 2 + sideDist * drawScale)
    screenY = int(horizon + renderer.camera_height * drawScale - drawH / 2)
    
    return {"x": screenX, "y": screenY, "scale": drawScale, "w": drawW, "h": drawH}


def distToLine(px, py, lineX1, lineY1, lineX2, lineY2):
    dx, dy = lineX2 - lineX1, lineY2 - lineY1
    lenSq = dx * dx + dy * dy
    if lenSq == 0: return math.hypot(px - lineX1, py - lineY1)
    t = max(0, min(1, ((px - lineX1) * dx + (py - lineY1) * dy) / lenSq))
    return math.hypot(px - (lineX1 + dx * t), py - (lineY1 + dy * t))


class Bullet:
   
    def __init__(self, sx, sy, dir_x, dir_y, image, angle, damage):
        self.sx = float(sx)
        self.sy = float(sy)
        self.dir_x = dir_x
        self.dir_y = dir_y
        self.angle = angle
        self.base_image = pygame.transform.rotate(
            pygame.transform.scale(image, (int(image.get_width() * BULLET_SCALE),
                                           int(image.get_height() * BULLET_SCALE))),
            -angle)
        self.lifetime = BULLET_LIFETIME
        self.max_lifetime = BULLET_LIFETIME
        self.alive = True
        self.hit_enemies = set()
        self.damage = damage

    def update(self):
        self.sx += self.dir_x * BULLET_SPEED
        self.sy += self.dir_y * BULLET_SPEED
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False

    def check_hit(self, enemies, kill_list, camera, renderer):
        for enemy in enemies:
            if enemy.hp <= 0 or id(enemy) in self.hit_enemies:
                continue
            enemyScreenPos = getScreenPos(enemy, camera, renderer)
            if enemyScreenPos is None:
                continue
            hitRadius = max(20, min(90, enemyScreenPos["h"] * 0.35))
            dist = math.hypot(self.sx - enemyScreenPos["x"],
                              self.sy - enemyScreenPos["y"])
            if dist <= hitRadius:
                enemy.take_damage(self.damage)
                self.hit_enemies.add(id(enemy))
                if enemy.hp <= 0:
                    kill_list.append(enemy)
                self.alive = False
                return True
        return False

    def draw(self, window):
        t = 1.0 - (self.lifetime / self.max_lifetime)
        scale = max(0.3, 1.0 - t * 0.7)
        w = max(2, int(self.base_image.get_width() * scale))
        h = max(2, int(self.base_image.get_height() * scale))
        scaled = pygame.transform.scale(self.base_image, (w, h))
        rect = scaled.get_rect(center=(int(self.sx), int(self.sy)))
        window.blit(scaled, rect)


class BeamAttack:
    def __init__(self):
        self.levelFrames = {}
        lv1 = loadFrames([f"assets/attacks/level 1 beam/LaserShot{i}.png" for i in range(1, 4)])
        self.levelFrames[1] = {"intro": lv1[:2], "loop": lv1}
        lv2 = loadFrames([f"assets/attacks/level 2 beam/LaserShot{i}.png" for i in range(1, 5)])
        self.levelFrames[2] = {"intro": lv2[:3], "loop": lv2[2:]}
        lv3 = loadFrames([f"assets/attacks/level 3 beam/LaserShot{i}.png" for i in range(1, 8)])
        self.levelFrames[3] = {"intro": lv3[:3], "loop": lv3[3:]}
        self.levelFrames[4] = self.levelFrames[3]
        self.levelFrames[5] = self.levelFrames[3]

        self.healthBarFrames = loadFrames([f"assets/Specials/health bar/Sprite-000{i}.png" for i in range(3, 6)])

        rawHp = loadFrames([f"assets/Necromancer/HP/HP{i}.png" for i in range(1, 6)])
        self.bossHpFrames = []
        for img in rawHp:
            bbox = img.get_bounding_rect()
            if bbox.width > 0 and bbox.height > 0:
                self.bossHpFrames.append(img.subsurface(bbox).copy())
            else:
                self.bossHpFrames.append(img)

    
        self.bulletImage = pygame.image.load("assets/attacks/level 3 beam/LaserShot2.png").convert_alpha()

        self.reset()

        self.weaponMode = "beam"
        self.has_bullet = False
        self.bullets: list[Bullet] = []
        self.lastBulletTime = 0

    def reset(self):
        self.isAttacking = self.isLooping = False
        self.frameIndex = self.lastFrameTime = self.beamLength = self.playerScale = 0
        self.currentFrame = self.beamStart = self.beamDir = None

    def switchWeapon(self):
        if not self.has_bullet:
            return
        if self.weaponMode == "beam":
            self.weaponMode = "bullet"
            self.reset()
        else:
            self.weaponMode = "beam"

    def update(self, player, enemies, camera, renderer, ammo_sys=None):
        kills = []

        for b in self.bullets:
            b.update()
            if b.alive:
                b.check_hit(enemies, kills, camera, renderer)
        self.bullets = [b for b in self.bullets if b.alive]

        if self.weaponMode == "bullet":
            self._updateBullet(player, enemies, camera, renderer, kills, ammo_sys)
        else:
            self._updateBeam(player, enemies, camera, renderer, kills)
        return kills

    def _updateBullet(self, player, enemies, camera, renderer, kills, ammo_sys):
        self.reset()
        now = pygame.time.get_ticks()
        if not pygame.mouse.get_pressed()[0]:
            return
        if now - self.lastBulletTime < BULLET_FIRE_COOLDOWN:
            return

        if ammo_sys and not ammo_sys.can_fire():
            return

        playerScreenPos = getScreenPos(player, camera, renderer)
        if playerScreenPos is None:
            return

        mx, my = pygame.mouse.get_pos()
        px, py = playerScreenPos["x"], playerScreenPos["y"]
        dx_s = mx - px
        dy_s = my - py
        length = math.hypot(dx_s, dy_s)
        if length < 5:
            return

        dir_x = dx_s / length
        dir_y = dy_s / length
        angle = math.degrees(math.atan2(dir_y, dir_x))

        muzzle = max(20, min(60, playerScreenPos["scale"] * 20))
        start_x = px + dir_x * muzzle
        start_y = py + dir_y * muzzle

        self.lastBulletTime = now
        if ammo_sys:
            ammo_sys.consume()
        dmg = BULLET_DAMAGE_PER_LEVEL.get(player.level, 0.5)
        self.bullets.append(Bullet(start_x, start_y, dir_x, dir_y,
                                   self.bulletImage, angle, dmg))

    def _updateBeam(self, player, enemies, camera, renderer, kills):
        now = pygame.time.get_ticks()
        if not pygame.mouse.get_pressed()[0]:
            self.reset(); return

        level = min(player.level, 5)
        introFrames = self.levelFrames[level]["intro"]
        loopFrames = self.levelFrames[level]["loop"]

        if not self.isAttacking:
            self.isAttacking, self.lastFrameTime, self.frameIndex, self.isLooping = True, now, 0, False

        while now - self.lastFrameTime >= ATTACK_FRAME_TIME:
            self.lastFrameTime += ATTACK_FRAME_TIME
            if self.isLooping:
                self.frameIndex = (self.frameIndex + 1) % len(loopFrames)
            else:
                self.frameIndex += 1
                if self.frameIndex >= len(introFrames):
                    self.isLooping, self.frameIndex = True, 0

        self.currentFrame = loopFrames[self.frameIndex] if self.isLooping else introFrames[self.frameIndex]

        playerScreenPos = getScreenPos(player, camera, renderer)
        if playerScreenPos is None:
            self.beamStart = self.beamDir = None; self.beamLength = 0; return

        mouseX, mouseY = pygame.mouse.get_pos()
        playerX, playerY = playerScreenPos["x"], playerScreenPos["y"]
        self.playerScale = playerScreenPos["scale"]
        beamLength = math.hypot(mouseX - playerX, mouseY - playerY)
        if beamLength < 8:
            self.beamStart = self.beamDir = None; self.beamLength = 0; return

        dirX, dirY = (mouseX - playerX) / beamLength, (mouseY - playerY) / beamLength
        muzzleOffset = max(32, min(90, player.current_image.get_height() * self.playerScale * 0.24))
        startX, startY = int(playerX + dirX * muzzleOffset), int(playerY + dirY * muzzleOffset)
        beamLength = math.hypot(mouseX - startX, mouseY - startY)
        if beamLength < 8:
            self.beamStart = self.beamDir = None; self.beamLength = 0; return

        self.beamStart = (startX, startY)
        self.beamDir, self.beamLength = (dirX, dirY), beamLength

        for enemy in enemies:
            if enemy.hp <= 0: continue
            enemyScreenPos = getScreenPos(enemy, camera, renderer)
            if enemyScreenPos is None: continue
            hitRadius = max(20, min(90, enemyScreenPos["h"] * 0.32))
            if distToLine(enemyScreenPos["x"], enemyScreenPos["y"], startX, startY, mouseX, mouseY) <= hitRadius \
               and now - enemy.last_beam_damage_time >= BEAM_DAMAGE_COOLDOWN:
                enemy.take_damage(player.damage * BEAM_DAMAGE_MULTIPLIER)
                enemy.last_beam_damage_time = now
                if enemy.hp <= 0:
                    kills.append(enemy)

    def draw(self, window):
        if self.currentFrame is not None and self.beamStart is not None:
            startX, startY = self.beamStart
            dirX, dirY = self.beamDir
            drawScale = max(1.5, min(3.5, self.playerScale * 1.45))
            angle = -math.degrees(math.atan2(dirY, dirX))
            numSegments = 10
            segLength = self.beamLength / numSegments

            for i in range(numSegments):
                t = i / numSegments
                heightScale = drawScale * (1.0 - t * 0.65)
                segW = max(4, int(segLength + 2))
                segH = max(2, int(self.currentFrame.get_height() * heightScale))

                segment = pygame.transform.scale(self.currentFrame, (segW, segH))
                rotated = pygame.transform.rotate(segment, angle)

                cx = startX + dirX * (segLength * (i + 0.5))
                cy = startY + dirY * (segLength * (i + 0.5))
                window.blit(rotated, rotated.get_rect(center=(int(cx), int(cy))))

        for b in self.bullets:
            b.draw(window)

    def drawHealthBars(self, window, enemies, camera, renderer):
        for enemy in enemies:
            if enemy.hp <= 0 or enemy.hp >= enemy.max_hp:
                continue
            
            screenPos = getScreenPos(enemy, camera, renderer)
            if screenPos is None: continue

            idx = int(min(len(self.healthBarFrames) - 1, (enemy.max_hp - enemy.hp) // max(1, enemy.max_hp / len(self.healthBarFrames))))
            bar = self.healthBarFrames[idx]

            drawScale = max(2, min(4, screenPos["scale"] * 1.2))
            drawW, drawH = int(bar.get_width() * drawScale), int(bar.get_height() * drawScale)
            scaled = pygame.transform.scale(bar, (drawW, drawH))
            window.blit(scaled, scaled.get_rect(center=(screenPos["x"], int(screenPos["y"] - screenPos["h"] / 2 - drawH / 2 - 6))))


    def drawBossHp(self, window, boss):
        if boss is None or boss.hp <= 0:
            return

        sw = window.get_width()
        bar_w = min(400, sw // 2)
        bar_h = 18
        x = (sw - bar_w) // 2
        y = 28

        ratio = max(0.0, min(1.0, boss.hp / boss.max_hp))

        if not hasattr(self, '_boss_bar_cache') or self._boss_bar_cache is None or self._boss_bar_w != bar_w:
            self._boss_bar_w = bar_w
            grad = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
            for col in range(bar_w):
                t = col / max(1, bar_w)
                r = int(200 + 55 * (1 - t))
                g = int(40 + 60 * t)
                b = 30
                pygame.draw.line(grad, (r, g, b, 240), (col, 0), (col, bar_h - 1))
            self._boss_bar_cache = grad
            bg = pygame.Surface((bar_w + 4, bar_h + 4), pygame.SRCALPHA)
            pygame.draw.rect(bg, (0, 0, 0, 200), (0, 0, bar_w + 4, bar_h + 4), border_radius=4)
            self._boss_bg_cache = bg
            self._boss_shine = pygame.Surface((bar_w, bar_h // 3), pygame.SRCALPHA)
            self._boss_shine.fill((255, 255, 255, 50))

        window.blit(self._boss_bg_cache, (x - 2, y - 2))

        fill_w = int(bar_w * ratio)
        if fill_w > 0:
            window.blit(self._boss_bar_cache, (x, y), (0, 0, fill_w, bar_h))
            window.blit(self._boss_shine, (x, y), (0, 0, fill_w, bar_h // 3))

        pygame.draw.rect(window, (180, 160, 140), (x - 1, y - 1, bar_w + 2, bar_h + 2), 2, border_radius=4)

        if not hasattr(self, '_boss_font') or self._boss_font is None:
            self._boss_font = pygame.font.SysFont("Monocraft", max(10, bar_h - 2))
        label = self._boss_font.render("NECROMANCER", True, (255, 220, 180))
        window.blit(label, label.get_rect(center=(sw // 2, y - 14)))


    def drawXpBar(self, window, player):
        from main_actor import XP_THRESHOLDS
        sw, sh = window.get_size()

        bar_w = max(160, sw // 4)
        bar_h = max(14, sh // 25)
        x = 20
        y = sh - bar_h - 50

        
        if player.level >= 5:
            fill_ratio = 1.0
            xp_label = "MAX"
        else:
            prev = XP_THRESHOLDS.get(player.level - 1, 0) if player.level > 1 else 0
            needed = XP_THRESHOLDS[player.level] - prev
            current = player.xp - prev
            fill_ratio = min(1.0, max(0.0, current / needed))
            xp_label = f"{current}/{needed}"

        if not hasattr(self, '_xp_bar_cache') or self._xp_bar_cache is None or self._xp_bar_w != bar_w:
            self._xp_bar_w = bar_w
            grad = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
            for col in range(bar_w):
                t = col / max(1, bar_w)
                r = int(50 + 30 * t)
                g = int(140 + 80 * t)
                b = int(240 - 80 * t)
                pygame.draw.line(grad, (r, g, b, 230), (col, 0), (col, bar_h - 1))
            self._xp_bar_cache = grad
            bg = pygame.Surface((bar_w + 4, bar_h + 4), pygame.SRCALPHA)
            pygame.draw.rect(bg, (0, 0, 0, 180), (0, 0, bar_w + 4, bar_h + 4), border_radius=5)
            self._xp_bg_cache = bg
            self._xp_shine = pygame.Surface((bar_w, bar_h // 3), pygame.SRCALPHA)
            self._xp_shine.fill((255, 255, 255, 45))

        window.blit(self._xp_bg_cache, (x - 2, y - 2))

        pygame.draw.rect(window, (100, 100, 120), (x - 1, y - 1, bar_w + 2, bar_h + 2), 1, border_radius=4)

        fill_w = int(bar_w * fill_ratio)
        if fill_w > 0:
            window.blit(self._xp_bar_cache, (x, y), (0, 0, fill_w, bar_h))
            window.blit(self._xp_shine, (x, y), (0, 0, fill_w, bar_h // 3))

        if not hasattr(self, '_xp_font') or self._xp_font is None:
            self._xp_font = pygame.font.SysFont("Monocraft", max(10, bar_h - 4))

        lv = self._xp_font.render(f"LV{player.level}", True, (255, 220, 60))
        window.blit(lv, (x + 4, y + (bar_h - lv.get_height()) // 2))

        xp = self._xp_font.render(xp_label, True, (255, 255, 255))
        window.blit(xp, (x + bar_w - xp.get_width() - 4, y + (bar_h - xp.get_height()) // 2))

    def drawPlayerHp(self, window, player):
        if not hasattr(self, '_hp_font') or self._hp_font is None:
            self._hp_font = pygame.font.SysFont("Monocraft", max(10, window.get_height() // 30))

        sw, sh = window.get_size()
        pip_w, pip_h = 16, 18
        gap = 3
        total_w = player.max_hp * (pip_w + gap)
        x = sw - total_w - 20
        y = sh - pip_h - 20

        bg = pygame.Surface((total_w + 8, pip_h + 8), pygame.SRCALPHA)
        pygame.draw.rect(bg, (0, 0, 0, 140), (0, 0, total_w + 8, pip_h + 8), border_radius=4)
        window.blit(bg, (x - 4, y - 4))

        for i in range(player.max_hp):
            px = x + i * (pip_w + gap)
            if i < player.hp:
                pygame.draw.rect(window, (220, 40, 40), (px, y, pip_w, pip_h), border_radius=3)
                pygame.draw.rect(window, (255, 100, 100), (px + 2, y + 2, pip_w - 4, pip_h // 3), border_radius=2)
            else:
                pygame.draw.rect(window, (50, 20, 20), (px, y, pip_w, pip_h), border_radius=3)
            pygame.draw.rect(window, (120, 50, 50), (px, y, pip_w, pip_h), 1, border_radius=3)

        label = self._hp_font.render(f"HP {player.hp}/{player.max_hp}", True, (220, 180, 180))
        window.blit(label, (x, y - label.get_height() - 2))
