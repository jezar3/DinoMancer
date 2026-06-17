utf-8import math
import os
import random
import sys
import pygame
from attacks import BeamAttack
from enemies import Ghoul, Necromancer, Slime
from main_actor import Player
from renderer import PerspectiveRenderer
from skills import Dash
from tilemap import TileMap


def _set_resource_cwd():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        os.chdir(sys._MEIPASS)
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))


_set_resource_cwd()


SLIME_SPAWN_INTERVAL = 200
TREE_VIEW_DISTANCE = 6000
SLIME_HIT_RANGE = 100
SLIME_HIT_COOLDOWN = 1000
BOSS_SPAWN_FRAME = 7200
BOSS_WARN_FRAME = 6940   
WATCHING_FRAME = 3600


def createFullscreenWindow(resolution_scale=2):
    info = pygame.display.Info()
    width = max(640, info.current_w // resolution_scale)
    height = max(360, info.current_h // resolution_scale)
    return pygame.display.set_mode((width, height), pygame.FULLSCREEN | pygame.SCALED)



class Camera:
    def __init__(self, w, h):
        self.width, self.height = w, h
        self.world_x, self.world_y = 0, 0
        self.camDistance = 500
        self.camPITCH, self.camYAW = 0, 0

    def update(self, player):
        self.world_x = player.rect.centerx - math.sin(self.camYAW) * self.camDistance
        self.world_y = player.rect.centery + math.cos(self.camYAW) * self.camDistance



class DayNightCycle:
    def __init__(self, w, h):
        self.time, self.speed = 0.0, 0.0002
        self.overlay = pygame.Surface((w, h))

    def update(self):
        self.time = (self.time + self.speed) % 1.0

    def draw(self, window):
        darkness = (1 - math.cos(2 * math.pi * (self.time - 0.25))) / 2
        if darkness > 0.05:
            self.overlay.fill((10, 10, 30))
            self.overlay.set_alpha(int(darkness * 220))
            window.blit(self.overlay, (0, 0))



def showText(window, clock, text, size, ms=2000, waitKey=False):
    sw, sh = window.get_size()
    rendered = pygame.font.SysFont("Monocraft", size).render(text, True, (255, 255, 255))
    rect = rendered.get_rect(center=(sw // 2, sh // 2))
    start = pygame.time.get_ticks()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                if waitKey: return
                pygame.quit(); raise SystemExit
        if not waitKey and pygame.time.get_ticks() - start >= ms:
            break
        window.fill((0, 0, 0))
        window.blit(rendered, rect)
        pygame.display.flip()
        clock.tick(60)


def startMenu(window, clock):
    sw, sh = window.get_size()
    bg = pygame.transform.scale(pygame.image.load("assets/start_menu/start_backround.png").convert(), (sw, sh))
    font = pygame.font.SysFont("Monocraft", sw // 30)
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit(); raise SystemExit
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                return
        
        alpha = int(130 + 125 * math.sin(pygame.time.get_ticks() * 0.004))
        window.blit(bg, (0, 0))
        txt = font.render("Press ENTER to Play", True, (255, 255, 255))
        txt.set_alpha(alpha)
        window.blit(txt, txt.get_rect(center=(sw // 2, sh - sh // 6)))
        pygame.display.flip()
        clock.tick(60)


def toRenderObj(actor):
    return {"world_x": actor.rect.centerx, 
            "world_y": actor.rect.centery, 
             "image": actor.current_image}


def spawnPos(player):
    return (
        player.rect.centerx + random.choice([-1, 1]) * random.randint(800, 1500),
        player.rect.centery + random.choice([-1, 1]) * random.randint(800, 1500),
    )



pygame.init()
pygame.mixer.init()

window = createFullscreenWindow()

sw, sh = window.get_size()
clock = pygame.time.Clock()


sfx_casting = pygame.mixer.Sound("assets/Necromancer/SFX/necromancer_casting.mp3")
sfx_death = pygame.mixer.Sound("assets/enemies/slime-SFX/slime_death.mp3")
sfx_beam = pygame.mixer.Sound("assets/attacks/beam-SFX/beam.mp3")
beam_channel = pygame.mixer.Channel(1)

while True:
    
    pygame.mixer.music.stop()
    pygame.mixer.stop()

    startMenu(window, clock)
    
    

    
    pygame.mixer.music.load("assets/Necromancer/SFX/before_boss_themesong.mp3")
    pygame.mixer.music.set_volume(0.67)
    pygame.mixer.music.play(-1)

    player = Player(700, 700, 12)
    slimes = []
    ghouls = []
    slimeTimer = 0
    necromancer = None
    frameCount = 0
    bossWarned = False
    watchingShown = False
    bossThemePlayed = False
    mouseLocked = False
    tileMap = TileMap()
    camera = Camera(sw, sh)
    renderer = PerspectiveRenderer(sw, sh)
    dayNight = DayNightCycle(sw, sh)
    beam = BeamAttack()
    dash = Dash()

    running = True
    
    while running:
        frameCount += 1

        
        if frameCount == WATCHING_FRAME and not watchingShown:
            watchingShown = True
            showText(window, clock, "You felt someone is watching you...", sw // 35, 3000)

        
        if frameCount == BOSS_WARN_FRAME and not bossWarned:
            bossWarned = True
            showText(window, clock, "WARNING", sw // 20, 2000)
            showText(window, clock, "A BOSS IS ABOUT TO SPAWN", sw // 50, 2000)

        
        if frameCount >= BOSS_SPAWN_FRAME and necromancer is None:
            necromancer = Necromancer(
                player.rect.centerx + 2000,
                player.rect.centery + 2000
            )
           
            pygame.mixer.music.load("assets/Necromancer/SFX/boss_appear_theme.mp3")
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play(-1)
            
            renderer.setGround("assets/world assets/white_ground.png")
            tileMap.setTreeImage("assets/world assets/magical_spruce_tree.png")

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit(); raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                dash.try_activate(player, camera.camYAW)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_t:
                mouseLocked = not mouseLocked
                pygame.mouse.set_visible(not mouseLocked)
                pygame.event.set_grab(mouseLocked)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                beam.switchWeapon()

       
        mdx, mdy = pygame.mouse.get_rel()
        if mouseLocked:
            camera.camYAW += mdx * 0.002
            camera.camPITCH = max(-250, min(250, camera.camPITCH - mdy * 0.3))
        else:
            
            mouse = pygame.mouse.get_pressed()
            if mouse[2]:
                camera.camYAW += mdx * 0.002
                camera.camPITCH = max(-250, min(250, camera.camPITCH - mdy * 0.3))

        
        player.wasd(camera.camYAW)
        dash.update(player)
        dayNight.update()
        camera.update(player)

        
        prevCount = len(slimes) + len(ghouls)

        
        slimes = [s for s in slimes if s.hp > 0]
        ghouls = [g for g in ghouls if g.hp > 0]

        
        if len(slimes) + len(ghouls) < prevCount:
            sfx_death.play()

        
        slimeTimer += 1
        if slimeTimer >= SLIME_SPAWN_INTERVAL:
            slimeTimer = 0 

            slimes.append(Slime(*spawnPos(player)))
        for s in slimes:
            s.update(player)
        for g in ghouls:
            g.update(player)



        
      
        if necromancer:
            newGhouls = necromancer.update(player)
            if newGhouls:
                sfx_casting.play()
            ghouls.extend(newGhouls)

        
        allEnemies = slimes + ghouls + ([necromancer] if necromancer else [])

        beam.update(player, allEnemies, camera, renderer)

        
        if beam.weaponMode == "beam" and beam.isAttacking:
            if not beam_channel.get_busy():
                beam_channel.play(sfx_beam, loops=-1)
        else:
            beam_channel.stop()

        
        now = pygame.time.get_ticks()
        for enemy in slimes + ghouls:
            if enemy.hp <= 0:
                continue
            dist = math.hypot(enemy.rect.centerx - player.rect.centerx, enemy.rect.centery - player.rect.centery)
            if dist <= SLIME_HIT_RANGE and now - player.last_hit_time >= SLIME_HIT_COOLDOWN and not dash.is_invincible:
                player.hp = max(0, player.hp - 1)
                player.last_hit_time = now
                player.hitTime = now

       
        window.fill((0, 0, 0))
        trees = tileMap.get_trees_in_range(camera.world_x, camera.world_y, TREE_VIEW_DISTANCE)
        renderList = trees + [toRenderObj(player)]
        renderList.extend(toRenderObj(s) for s in slimes)
        renderList.extend(toRenderObj(g) for g in ghouls)
        if necromancer:
            renderList.append(toRenderObj(necromancer))

        renderer.render(camera, renderList, window)
        dayNight.draw(window)
        beam.draw(window)
        beam.drawHealthBars(window, slimes + ghouls, camera, renderer)
        beam.drawBossHp(window, necromancer)
        beam.drawXpBar(window, player)
        beam.drawPlayerHp(window, player)

        
        if player.hp <= 0:
            pygame.mixer.music.stop()
            pygame.mixer.stop()
            showText(window, clock, "You Died.", sw // 15, 3000)
            running = False

        
        if necromancer and necromancer.hp <= 0:
            pygame.mixer.music.stop()
            pygame.mixer.stop()
            showText(window, clock, "You win, YOU DEFIED AGAINST THE ODDS", sw // 40, 5000)
            running = False

        clock.tick(60)
        pygame.display.flip()

pygame.quit()
