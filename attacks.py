import math
import pygame

ATTACK_FRAME_TIME = 80
BEAM_DAMAGE_COOLDOWN = 250
BEAM_DAMAGE_MULTIPLIER = 0.2
BULLET_FIRE_COOLDOWN = 350
BULLET_DAMAGE = 2
BULLET_SPEED = 14
BULLET_LIFETIME = 90
BULLET_SCALE = 1.25
XP_BAR_SCALE = 1.25

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
   
    def __init__(self, sx, sy, dir_x, dir_y, image, angle):
        self.sx = float(sx)           # screen x
        self.sy = float(sy)           # screen y
        self.dir_x = dir_x           # normalised screen direction
        self.dir_y = dir_y
        self.angle = angle            # rotation angle in degrees
        self.image = pygame.transform.rotate(
            pygame.transform.scale(image, (int(image.get_width() * BULLET_SCALE),
                                           int(image.get_height() * BULLET_SCALE))),
            -angle)
        self.lifetime = BULLET_LIFETIME
        self.alive = True
        self.hit_enemies = set()      # avoid multi-hit per bullet

    def update(self):
        self.sx += self.dir_x * BULLET_SPEED
        self.sy += self.dir_y * BULLET_SPEED
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False

    def check_hit(self, enemies, player, camera, renderer):
        #Check if this bullet's screen position overlaps any enemy's screen position
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
                enemy.take_damage(BULLET_DAMAGE)
                self.hit_enemies.add(id(enemy))
                if enemy.hp <= 0:
                    player.addXP(10)
                self.alive = False
                return True
        return False

    def draw(self, window):
        rect = self.image.get_rect(center=(int(self.sx), int(self.sy)))
        window.blit(self.image, rect)


class BeamAttack:
    def __init__(self):
        # Per-level beam frames
        self.levelFrames = {}
        # Level 1: 3 frames total
        lv1 = loadFrames([f"assets/attacks/level 1 beam/LaserShot{i}.png" for i in range(1, 4)])
        self.levelFrames[1] = {"intro": lv1[:2], "loop": lv1}
        # Level 2: 4 frames total
        lv2 = loadFrames([f"assets/attacks/level 2 beam/LaserShot{i}.png" for i in range(1, 5)])
        self.levelFrames[2] = {"intro": lv2[:3], "loop": lv2[2:]}
        # Level 3: 7 frames total
        lv3 = loadFrames([f"assets/attacks/level 3 beam/LaserShot{i}.png" for i in range(1, 8)])
        self.levelFrames[3] = {"intro": lv3[:3], "loop": lv3[3:]}

        self.healthBarFrames = loadFrames([f"assets/Specials/health bar/Sprite-000{i}.png" for i in range(3, 6)])
        self.xpBarFrames = loadFrames([f"assets/Specials/XP bar/Sprite-0001dsaf{i}.png" for i in range(1, 4)])

        # Boss HP images (HP1=full .. HP5=low) 
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

        # Weapon mode: "beam" or "bullet"
        self.weaponMode = "beam"
        self.bullets: list[Bullet] = []
        self.lastBulletTime = 0

    def reset(self):
        self.isAttacking = self.isLooping = False
        self.frameIndex = self.lastFrameTime = self.beamLength = self.playerScale = 0
        self.currentFrame = self.beamStart = self.beamDir = None

    def switchWeapon(self):
        if self.weaponMode == "beam":
            self.weaponMode = "bullet"
            self.reset()
        else:
            self.weaponMode = "beam"

    def update(self, player, enemies, camera, renderer):
        # Update existing bullets regardless of mode
        for b in self.bullets:
            b.update()
            if b.alive:
                b.check_hit(enemies, player, camera, renderer)
        self.bullets = [b for b in self.bullets if b.alive]

        if self.weaponMode == "bullet":
            self._updateBullet(player, enemies, camera, renderer)
        else:
            self._updateBeam(player, enemies, camera, renderer)

    def _updateBullet(self, player, enemies, camera, renderer):
        self.reset()
        now = pygame.time.get_ticks()
        if not pygame.mouse.get_pressed()[0]:
            return
        if now - self.lastBulletTime < BULLET_FIRE_COOLDOWN:
            return

        # Get player screen position as the bullet origin
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

        # Offset start from player a bit (muzzle)
        muzzle = max(20, min(60, playerScreenPos["scale"] * 20))
        start_x = px + dir_x * muzzle
        start_y = py + dir_y * muzzle

        self.lastBulletTime = now
        self.bullets.append(Bullet(start_x, start_y, dir_x, dir_y,
                                   self.bulletImage, angle))

    def _updateBeam(self, player, enemies, camera, renderer):
        now = pygame.time.get_ticks()
        if not pygame.mouse.get_pressed()[0]:
            self.reset(); return

        level = player.level
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
                if enemy.hp <= 0: player.addXP(10)  # XP per slime kill

    def draw(self, window):
        # Draw beam
        if self.currentFrame is not None and self.beamStart is not None:
            startX, startY = self.beamStart
            dirX, dirY = self.beamDir
            drawScale = max(1.5, min(3.5, self.playerScale * 1.45))
            drawW = max(int(self.currentFrame.get_width() * drawScale), int(self.beamLength))
            drawH = int(self.currentFrame.get_height() * drawScale)
            rotated = pygame.transform.rotate(
                pygame.transform.scale(self.currentFrame, (drawW, drawH)),
                -math.degrees(math.atan2(dirY, dirX)))
            window.blit(rotated, rotated.get_rect(
                center=(int(startX + dirX * drawW / 2), int(startY + dirY * drawW / 2))))

        # Draw all bullets (screen-space overlay)
        for b in self.bullets:
            b.draw(window)

    def drawHealthBars(self, window, enemies, camera, renderer):
        for enemy in enemies:
            if enemy.hp <= 0: continue
            
            screenPos = getScreenPos(enemy, camera, renderer)
            if screenPos is None: continue

            idx = int(min(len(self.healthBarFrames) - 1, (enemy.max_hp - enemy.hp) // max(1, enemy.max_hp / len(self.healthBarFrames))))
            bar = self.healthBarFrames[idx]

            drawScale = max(2, min(4, screenPos["scale"] * 1.2))
            drawW, drawH = int(bar.get_width() * drawScale), int(bar.get_height() * drawScale)
            scaled = pygame.transform.scale(bar, (drawW, drawH))
            window.blit(scaled, scaled.get_rect(center=(screenPos["x"], int(screenPos["y"] - screenPos["h"] / 2 - drawH / 2 - 6))))


    def drawBossHp(self, window, boss):
        """Draw boss HP using image assets at top center of screen."""
        if boss is None or boss.hp <= 0:
            return

        # HP1=100, HP2=80, HP3=60, HP4=40, HP5=20 (and below)
        if boss.hp > 80:
            idx = 0
        elif boss.hp > 60:
            idx = 1
        elif boss.hp > 40:
            idx = 2
        elif boss.hp > 20:
            idx = 3
        else:
            idx = 4

        frame = self.bossHpFrames[idx]
        # Scale to fit nicely at top center
        scale = 4
        drawW = int(frame.get_width() * scale)
        drawH = int(frame.get_height() * scale)
        scaled = pygame.transform.scale(frame, (drawW, drawH))
        x = (window.get_width() - drawW) // 2
        y = 10
        window.blit(scaled, (x, y))


    def drawXpBar(self, window, player):
        bar = self.xpBarFrames[min(len(self.xpBarFrames) - 1, player.level - 1)]
        drawW = int(bar.get_width() * XP_BAR_SCALE)
        drawH = int(bar.get_height() * XP_BAR_SCALE)
        

        window.blit(pygame.transform.scale(bar, (drawW, drawH)), (20, window.get_height() - drawH - 50))

    def drawPlayerHp(self, window, player):
        idx = int(min(len(self.healthBarFrames) - 1,
                       (player.max_hp - player.hp) // max(1, player.max_hp / len(self.healthBarFrames))))
        bar = self.healthBarFrames[idx]
        scale = 3
        drawW, drawH = int(bar.get_width() * scale), int(bar.get_height() * scale)
        scaled = pygame.transform.scale(bar, (drawW, drawH))
        x = window.get_width() - drawW - 24
        y = window.get_height() - drawH - 24
        window.blit(scaled, (x, y))

