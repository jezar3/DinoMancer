import math
import os
import random
import sys
import pygame
from attacks import BeamAttack, getScreenPos
from enemies import Ghoul, Necromancer, Slime, NecromancerProjectile, NECRO_PROJ_DAMAGE
from main_actor import Player
from renderer import PerspectiveRenderer
from skills import Dash
from tilemap import TileMap
from effects import ScreenShake, LevelUpFlash
from game_systems import (
    XPOrb, LargeXPOrb, HealthPickup, WaveAnnouncer, KillStreak,
    AmmoSystem, RunTimer, DynamicLighting,
    SkillPicker, MapDecorations,
)


def _set_resource_cwd():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        os.chdir(sys._MEIPASS)
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))


_set_resource_cwd()

TREE_VIEW_DISTANCE = 8000
SLIME_HIT_RANGE = 200
SLIME_HIT_COOLDOWN = 500
HEALTH_DROP_CHANCE = 0.08

WAVE_INTERVAL = 1800
TOTAL_WAVES = 25
GHOUL_START_WAVE = 5
BOSS_SPAWN_WAVE = 20

NECRO_FIRE_INTERVAL = 150

MAX_SLIMES = 100
MAX_GHOULS = 50
ENEMY_CULL_DIST = 6000

os.environ["SLD_AUDIODRIVER"] = "dummy"


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


def showText(window, clock, text, size, ms=2000, waitKey=False):
    sw, sh = window.get_size()
    rendered = pygame.font.SysFont("Monocraft", size).render(text, True, (255, 255, 255))
    rect = rendered.get_rect(center=(sw // 2, sh // 2))
    start = pygame.time.get_ticks()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); raise SystemExit
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                if waitKey: return
        if not waitKey and pygame.time.get_ticks() - start >= ms:
            break
        window.fill((0, 0, 0))
        window.blit(rendered, rect)
        pygame.display.flip()
        clock.tick(60)


def pauseMenu(window, clock):
    """Returns 'resume', 'retry', or 'menu'."""
    sw, sh = window.get_size()
    background = window.copy()
    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))

    title_font = pygame.font.SysFont("Monocraft", max(20, sw // 18))
    btn_font = pygame.font.SysFont("Monocraft", max(14, sw // 32))
    hint_font = pygame.font.SysFont("Monocraft", max(9, sw // 55))

    buttons = [
        ("Resume", "resume"),
        ("Retry", "retry"),
        ("Main Menu", "menu"),
    ]
    btn_w = max(200, sw // 3)
    btn_h = max(44, sh // 10)
    btn_gap = max(12, sh // 30)
    total_h = len(buttons) * btn_h + (len(buttons) - 1) * btn_gap
    start_y = sh // 2 - total_h // 2 + max(30, sh // 8)

    btn_rects = []
    for i in range(len(buttons)):
        r = pygame.Rect(sw // 2 - btn_w // 2, start_y + i * (btn_h + btn_gap), btn_w, btn_h)
        btn_rects.append(r)

    selected = 0
    while True:
        mx, my = pygame.mouse.get_pos()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); raise SystemExit
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return "resume"
                if e.key == pygame.K_UP:
                    selected = (selected - 1) % len(buttons)
                if e.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(buttons)
                if e.key == pygame.K_RETURN:
                    return buttons[selected][1]
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, r in enumerate(btn_rects):
                    if r.collidepoint(e.pos):
                        return buttons[i][1]
            if e.type == pygame.MOUSEMOTION:
                for i, r in enumerate(btn_rects):
                    if r.collidepoint(mx, my):
                        selected = i

        t = pygame.time.get_ticks()
        window.blit(background, (0, 0))
        window.blit(overlay, (0, 0))

        pulse = 0.5 + 0.5 * math.sin(t * 0.004)
        title = title_font.render("PAUSED", True, (255, 255, 255))
        title.set_alpha(int(180 + 75 * pulse))
        window.blit(title, title.get_rect(center=(sw // 2, start_y - max(50, sh // 7))))

        for i, (label, _) in enumerate(buttons):
            r = btn_rects[i]
            hovered = r.collidepoint(mx, my)
            is_sel = i == selected or hovered
            if is_sel:
                selected = i

            btn_surf = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            if is_sel:
                glow = int(40 + 25 * pulse)
                btn_surf.fill((140, 100, 255, glow))
            else:
                btn_surf.fill((255, 255, 255, 10))
            window.blit(btn_surf, r.topleft)

            bdr = (180, 140, 255, 200) if is_sel else (100, 100, 120, 100)
            pygame.draw.rect(window, bdr, r, 2, border_radius=8)

            col = (255, 255, 255) if is_sel else (170, 170, 180)
            lbl = btn_font.render(label, True, col)
            window.blit(lbl, lbl.get_rect(center=r.center))

        hint = hint_font.render("Press ESC to resume", True, (140, 140, 160))
        window.blit(hint, hint.get_rect(center=(sw // 2, btn_rects[-1].bottom + max(20, sh // 15))))

        pygame.display.flip()
        clock.tick(60)


def startMenu(window, clock):
    sw, sh = window.get_size()
    bg = pygame.transform.scale(pygame.image.load("assets/start_menu/start_backround.png").convert(), (sw, sh))
    font = pygame.font.SysFont("Monocraft", sw // 30)
    chk_font = pygame.font.SysFont("Monocraft", max(10, sw // 45))
    ctrl_title_font = pygame.font.SysFont("Monocraft", max(12, sw // 38))
    ctrl_font = pygame.font.SysFont("Monocraft", max(9, sw // 55))

    controls = [
        ("WASD", "Move"),
        ("Mouse", "Rotate Camera"),
        ("Left Click", "Attack"),
        ("Q", "Dash"),
        ("E", "Switch Weapon"),
        ("R", "Reload"),
        ("T", "Unlock / Lock Mouse"),
        ("ESC", "Pause"),
    ]

    ctrl_pad = 14
    ctrl_line_h = max(16, sh // 22)
    ctrl_w = max(260, sw // 3)
    ctrl_h = ctrl_line_h * (len(controls) + 1) + ctrl_pad * 2
    ctrl_x = 16
    ctrl_y = sh // 2 - ctrl_h // 2

    ctrl_bg = pygame.Surface((ctrl_w, ctrl_h), pygame.SRCALPHA)
    pygame.draw.rect(ctrl_bg, (0, 0, 0, 160), (0, 0, ctrl_w, ctrl_h), border_radius=8)
    pygame.draw.rect(ctrl_bg, (140, 120, 180, 100), (0, 0, ctrl_w, ctrl_h), 1, border_radius=8)

    selected_mode = None  
    card_font = pygame.font.SysFont("Monocraft", max(14, sw // 38))
    sub_font = pygame.font.SysFont("Monocraft", max(9, sw // 60))
    
    
    card_w = max(200, sw // 4)
    card_h = max(56, sh // 8)
    card_gap = 12
    panel_pad = 16
    panel_w = card_w + panel_pad * 2
    panel_h = card_h * 2 + card_gap + panel_pad * 2 + max(16, sh // 24)
    panel_x = sw - panel_w - 16
    panel_y = sh // 2 - panel_h // 2

    card_x = panel_x + panel_pad
    fast_card_y = panel_y + panel_pad + max(16, sh // 24)
    jesus_card_y = fast_card_y + card_h + card_gap
    chk_rect_fast = pygame.Rect(card_x, fast_card_y, card_w, card_h)
    chk_rect_jesus = pygame.Rect(card_x, jesus_card_y, card_w, card_h)

    particles = []
    for _ in range(25):
        particles.append([random.randint(0, sw), random.randint(0, sh),
                          random.uniform(0.3, 1.0), random.randint(1, 3)])

    vig = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for border in range(min(sw, sh) // 4):
        a = max(0, int(80 * (1 - border / (min(sw, sh) / 4))))
        pygame.draw.rect(vig, (0, 0, 0, a), (border, border, sw - border * 2, sh - border * 2), 1)

    while True:
        mx, my = pygame.mouse.get_pos()
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit(); raise SystemExit
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                return selected_mode
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if chk_rect_jesus.collidepoint(e.pos):
                    selected_mode = None if selected_mode == "jesus" else "jesus"
                elif chk_rect_fast.collidepoint(e.pos):
                    selected_mode = None if selected_mode == "fast" else "fast"

        t = pygame.time.get_ticks()
        window.blit(bg, (0, 0))

        for p in particles:
            p[1] -= p[2]
            if p[1] < -5:
                p[1] = sh + 5
                p[0] = random.randint(0, sw)
            pa = int(60 + 40 * math.sin(t * 0.003 + p[0]))
            pygame.draw.circle(window, (200, 180, 255, pa), (int(p[0]), int(p[1])), p[3])

        window.blit(vig, (0, 0))

        window.blit(ctrl_bg, (ctrl_x, ctrl_y))
        title_surf = ctrl_title_font.render("How To Play", True, (255, 220, 80))
        window.blit(title_surf, (ctrl_x + ctrl_pad, ctrl_y + ctrl_pad))
        for idx, (key, desc) in enumerate(controls):
            ly = ctrl_y + ctrl_pad + ctrl_line_h * (idx + 1)
            key_surf = ctrl_font.render(key, True, (255, 220, 60))
            desc_surf = ctrl_font.render(f"  {desc}", True, (210, 210, 220))
            window.blit(key_surf, (ctrl_x + ctrl_pad, ly))
            window.blit(desc_surf, (ctrl_x + ctrl_pad + key_surf.get_width(), ly))

        alpha = int(130 + 125 * math.sin(t * 0.004))
        txt = font.render("Press ENTER to Play", True, (255, 255, 255))
        txt.set_alpha(alpha)
        window.blit(txt, txt.get_rect(center=(sw // 2, sh - sh // 6)))

        panel_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel_bg, (0, 0, 0, 170), (0, 0, panel_w, panel_h), border_radius=10)
        pygame.draw.rect(panel_bg, (180, 140, 255, 90), (0, 0, panel_w, panel_h), 1, border_radius=10)
        window.blit(panel_bg, (panel_x, panel_y))
        panel_title = ctrl_title_font.render("Pick Game add-ons", True, (255, 220, 80))
        window.blit(panel_title, (panel_x + panel_w // 2 - panel_title.get_width() // 2,
                                  panel_y + panel_pad - 2))

        def _draw_card(rect, active, hovered, color_on, title_text, desc_text):
            pulse = 0.5 + 0.5 * math.sin(t * 0.005)
            card_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            if active:
                bg_a = int(70 + 30 * pulse)
                card_surf.fill((*color_on, bg_a))
            elif hovered:
                card_surf.fill((255, 255, 255, 18))
            else:
                card_surf.fill((255, 255, 255, 8))
            window.blit(card_surf, rect.topleft)
            if active:
                glow_a = int(180 + 75 * pulse)
                border_col = (*color_on[:3], min(255, glow_a))
                pygame.draw.rect(window, border_col, rect, 3, border_radius=8)
                glow_rect = rect.inflate(6, 6)
                glow_s = pygame.Surface((glow_rect.w, glow_rect.h), pygame.SRCALPHA)
                pygame.draw.rect(glow_s, (*color_on[:3], int(40 * pulse)), (0, 0, glow_rect.w, glow_rect.h), 3, border_radius=10)
                window.blit(glow_s, glow_rect.topleft)
            elif hovered:
                pygame.draw.rect(window, (220, 220, 240, 120), rect, 2, border_radius=8)
            else:
                pygame.draw.rect(window, (100, 100, 120, 100), rect, 1, border_radius=8)
            chk_sz = min(22, rect.h - 16)
            chk_bx = rect.x + 10
            chk_by = rect.centery - chk_sz // 2
            chk_r = pygame.Rect(chk_bx, chk_by, chk_sz, chk_sz)
            if active:
                pygame.draw.rect(window, color_on, chk_r, border_radius=4)
                pygame.draw.line(window, (0, 0, 0),
                                 (chk_r.x + 4, chk_r.centery),
                                 (chk_r.centerx - 1, chk_r.bottom - 4), 3)
                pygame.draw.line(window, (0, 0, 0),
                                 (chk_r.centerx - 1, chk_r.bottom - 4),
                                 (chk_r.right - 4, chk_r.y + 4), 3)
            else:
                pygame.draw.rect(window, (160, 160, 180) if hovered else (100, 100, 120), chk_r, 2, border_radius=4)
            txt_x = chk_bx + chk_sz + 10
            t_col = color_on if active else ((240, 240, 250) if hovered else (190, 190, 200))
            title_s = card_font.render(title_text, True, t_col)
            window.blit(title_s, (txt_x, rect.y + 6))
            d_col = (*color_on[:3], 200) if active else (150, 150, 165)
            desc_s = sub_font.render(desc_text, True, d_col)
            window.blit(desc_s, (txt_x, rect.y + 6 + title_s.get_height() + 2))

        fast_hovered = chk_rect_fast.collidepoint(mx, my)
        jesus_hovered = chk_rect_jesus.collidepoint(mx, my)

        _draw_card(chk_rect_fast,
                   selected_mode == "fast", fast_hovered,
                   (60, 200, 255),
                   "N-mancer",""
                   )

        _draw_card(chk_rect_jesus,
                   selected_mode == "jesus", jesus_hovered,
                   (255, 220, 60),
                   "JESUS Mode", "")

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

_cs = 28
_ch = _cs // 2
_cursor_surf = pygame.Surface((_cs, _cs), pygame.SRCALPHA)
_gap = 4
pygame.draw.line(_cursor_surf, (0, 0, 0, 200), (0, _ch), (_ch - _gap - 1, _ch), 3)
pygame.draw.line(_cursor_surf, (0, 0, 0, 200), (_ch + _gap + 1, _ch), (_cs - 1, _ch), 3)
pygame.draw.line(_cursor_surf, (0, 0, 0, 200), (_ch, 0), (_ch, _ch - _gap - 1), 3)
pygame.draw.line(_cursor_surf, (0, 0, 0, 200), (_ch, _ch + _gap + 1), (_ch, _cs - 1), 3)
pygame.draw.line(_cursor_surf, (255, 255, 255), (1, _ch), (_ch - _gap, _ch), 2)
pygame.draw.line(_cursor_surf, (255, 255, 255), (_ch + _gap, _ch), (_cs - 2, _ch), 2)
pygame.draw.line(_cursor_surf, (255, 255, 255), (_ch, 1), (_ch, _ch - _gap), 2)
pygame.draw.line(_cursor_surf, (255, 255, 255), (_ch, _ch + _gap), (_ch, _cs - 2), 2)
pygame.draw.circle(_cursor_surf, (255, 60, 60), (_ch, _ch), 2)
pygame.mouse.set_cursor(pygame.cursors.Cursor((_ch, _ch), _cursor_surf))


def setMouseLock(locked, center=None):
    pygame.event.set_grab(locked)
    pygame.mouse.set_visible(True)
    if locked and center is not None:
        pygame.mouse.set_pos(center)
    pygame.mouse.get_rel()


sfx_casting = pygame.mixer.Sound("assets/Necromancer/SFX/necromancer_casting.mp3")
sfx_death = pygame.mixer.Sound("assets/enemies/slime-SFX/slime_death.mp3")
sfx_beam = pygame.mixer.Sound("assets/attacks/beam-SFX/beam.mp3")
beam_channel = pygame.mixer.Channel(1)

while True:
    setMouseLock(False)
    pygame.mixer.music.stop()
    pygame.mixer.stop()
    selected_mode = startMenu(window, clock)
    god_mode = selected_mode == "jesus"
    fast_mode = selected_mode == "fast"

    pygame.mixer.music.load("assets/Necromancer/SFX/before_boss_themesong.mp3")
    pygame.mixer.music.set_volume(0.67)
    pygame.mixer.music.play(-1)

    player_speed = 100 if fast_mode else 12
    player = Player(700, 700, player_speed, use_nmancer=fast_mode)
    slimes = []
    ghouls = []

    xp_orbs = []
    health_pickups = []
    necro_projectiles = []
    slimeTimer = 0
    necromancer = None
    frameCount = 0
    bossWarned = False
    bossThemePlayed = False
    tileMap = TileMap()
    camera = Camera(sw, sh)
    renderer = PerspectiveRenderer(sw, sh)
    beam = BeamAttack()
    dash = Dash()
    dash_unlocked = False
    screenShake = ScreenShake()
    levelUpFlash = LevelUpFlash()
    necroFireTimer = 0

    waveAnnouncer = WaveAnnouncer()
    killStreak = KillStreak()
    ammoSys = AmmoSystem(clip_size=6)
    runTimer = RunTimer()
    lighting = DynamicLighting(sw, sh)
    skillPicker = SkillPicker()
    mapDecos = MapDecorations()
    currentWave = 0

    if god_mode:
        from main_actor import LEVEL_DAMAGE
        player.level = 5
        player.damage = LEVEL_DAMAGE[5]
        player.speed += 3
        player.max_hp = 999
        player.hp = 999
        beam.has_bullet = True
        beam.weaponMode = "bullet"
        dash_unlocked = True
        ammoSys.clip_size = 99
        ammoSys.ammo = 99
        bossWarned = True
        necromancer = Necromancer(
            player.rect.centerx + 2000,
            player.rect.centery + 2000)
        currentWave = BOSS_SPAWN_WAVE
        pygame.mixer.music.load("assets/Necromancer/SFX/boss_appear_theme.mp3")
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play(-1)
        renderer.setGround("assets/world assets/white_ground.png")
        tileMap.setTreeImage("assets/world assets/magical_spruce_tree.png")

    running = True
    skill_card_rects = []
    mouseLockCenter = (sw // 2, sh // 2)
    mouseLocked = True
    setMouseLock(mouseLocked, mouseLockCenter)

    while running:
        if skillPicker.active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); raise SystemExit
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pause_choice = pauseMenu(window, clock)
                    if pause_choice == "retry":
                        running = False
                        _pause_action = "retry"
                        break
                    elif pause_choice == "menu":
                        running = False
                        _pause_action = "menu"
                        break
                chosen = skillPicker.handle_event(event, skill_card_rects)
                if chosen:
                    result = skillPicker.apply_skill(chosen, player, dash, ammoSys)
                    if result == "unlock_bullet":
                        beam.has_bullet = True
                        beam.weaponMode = "bullet"
                    elif result == "unlock_dash":
                        dash_unlocked = True
                    levelUpFlash.trigger()
            skill_card_rects = skillPicker.draw(window)
            pygame.display.flip()
            clock.tick(60)
            continue

        frameCount += 1

        newWave = min(TOTAL_WAVES, frameCount // WAVE_INTERVAL + 1)
        if newWave > currentWave:
            currentWave = newWave
            waveAnnouncer.announce(currentWave)

        if currentWave >= BOSS_SPAWN_WAVE and necromancer is None and not bossWarned:
            bossWarned = True
            showText(window, clock, "WARNING", sw // 20, 2000)
            showText(window, clock, "A BOSS IS ABOUT TO SPAWN", sw // 50, 2000)
            necromancer = Necromancer(
                player.rect.centerx + 2000,
                player.rect.centery + 2000)
            pygame.mixer.music.load("assets/Necromancer/SFX/boss_appear_theme.mp3")
            pygame.mixer.music.set_volume(1.0)
            pygame.mixer.music.play(-1)
            renderer.setGround("assets/world assets/white_ground.png")
            tileMap.setTreeImage("assets/world assets/magical_spruce_tree.png")

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pause_result = pauseMenu(window, clock)
                if pause_result == "retry":
                    running = False
                    break
                elif pause_result == "menu":
                    running = False
                    break
            if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                if dash_unlocked:
                    dash.try_activate(player, camera.camYAW)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_t:
                mouseLocked = not mouseLocked
                setMouseLock(mouseLocked, mouseLockCenter)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                beam.switchWeapon()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                ammoSys.start_reload()

        mdx, mdy = pygame.mouse.get_rel()
        if mouseLocked:
            camera.camYAW += mdx * 0.002
            camera.camPITCH = max(-250, min(250, camera.camPITCH - mdy * 0.3))
            pygame.mouse.set_pos(mouseLockCenter)
            pygame.mouse.get_rel()
        else:
            mouse = pygame.mouse.get_pressed()
            if mouse[2]:
                camera.camYAW += mdx * 0.002
                camera.camPITCH = max(-250, min(250, camera.camPITCH - mdy * 0.3))

        if necromancer and necromancer.isCasting:
            saved_speed = player.speed
            player.speed = max(2, player.speed // 2)
            player.wasd(camera.camYAW)
            player.speed = saved_speed
        else:
            player.wasd(camera.camYAW)
        if dash_unlocked:
            dash.update(player)
        camera.update(player)
        ammoSys.update()

        prevCount = len(slimes) + len(ghouls)
        slimes = [s for s in slimes if s.hp > 0]
        ghouls = [g for g in ghouls if g.hp > 0]
        if len(slimes) + len(ghouls) < prevCount:
            sfx_death.play()

        is_inv = dash_unlocked and dash.is_invincible

        diff_mult = runTimer.difficulty_mult()

        slimeTimer += 1
        spawn_interval = max(60, int(200 / diff_mult))
        if slimeTimer >= spawn_interval:
            slimeTimer = 0
            if len(slimes) < MAX_SLIMES:
                slimes.append(Slime(*spawnPos(player)))

        if currentWave >= GHOUL_START_WAVE and frameCount % max(100, int(300 / diff_mult)) == 0:
            if len(ghouls) < MAX_GHOULS:
                ghouls.append(Ghoul(*spawnPos(player)))

        px, py = player.rect.centerx, player.rect.centery
        for s in slimes:
            if abs(s.rect.centerx - px) + abs(s.rect.centery - py) < ENEMY_CULL_DIST:
                s.update(player)
        for g in ghouls:
            if abs(g.rect.centerx - px) + abs(g.rect.centery - py) < ENEMY_CULL_DIST:
                g.update(player)

        if necromancer:
            newGhouls = necromancer.update(player)
            if newGhouls:
                sfx_casting.play()
            ghouls.extend(newGhouls)

            if necromancer.cast_just_ended:
                if not is_inv:
                    player.hp = max(0, player.hp - 1)
                    player.last_hit_time = pygame.time.get_ticks()
                    player.hitTime = pygame.time.get_ticks()
                    screenShake.trigger()

            necroFireTimer += 1
            if necroFireTimer >= NECRO_FIRE_INTERVAL:
                necroFireTimer = 0
                necro_projectiles.append(NecromancerProjectile(
                    necromancer.rect.centerx, necromancer.rect.centery,
                    player.rect.centerx, player.rect.centery))

        for proj in necro_projectiles:
            proj.update()
            if proj.alive and proj.check_hit_player(player):
                if not is_inv:
                    player.hp = max(0, player.hp - NECRO_PROJ_DAMAGE)
                    player.last_hit_time = pygame.time.get_ticks()
                    player.hitTime = pygame.time.get_ticks()
                    for _ in range(3):
                        screenShake.trigger()
        necro_projectiles = [p for p in necro_projectiles if p.alive]

        all_enemies = slimes + ghouls
        allEnemies = all_enemies + ([necromancer] if necromancer else [])
        kills = beam.update(player, allEnemies, camera, renderer, ammoSys)

        for enemy in kills:
            xp_orbs.append(XPOrb(enemy.rect.centerx, enemy.rect.centery))
            killStreak.register_kill()
            if random.random() < HEALTH_DROP_CHANCE:
                health_pickups.append(HealthPickup(
                    enemy.rect.centerx + random.randint(-50, 50),
                    enemy.rect.centery + random.randint(-50, 50)))

        for orb in xp_orbs:
            gained = orb.update(player)
            if gained > 0:
                player.addXP(gained)
        xp_orbs = [o for o in xp_orbs if o.alive]

        for hp in health_pickups:
            hp.update(player)
        health_pickups = [hp for hp in health_pickups if hp.alive]

        if player.pending_levelup:
            player.pending_levelup = False
            skillPicker.open(beam.has_bullet, dash_unlocked, window)

        if beam.weaponMode == "beam" and beam.isAttacking:
            if not beam_channel.get_busy():
                beam_channel.play(sfx_beam, loops=-1)
        else:
            beam_channel.stop()

        now = pygame.time.get_ticks()
        if not is_inv and now - player.last_hit_time >= SLIME_HIT_COOLDOWN:
            hit_range_2 = SLIME_HIT_RANGE * 2
            hit_range_sq = SLIME_HIT_RANGE * SLIME_HIT_RANGE
            for enemy in all_enemies:
                if enemy.hp <= 0:
                    continue
                dx = enemy.rect.centerx - player.rect.centerx
                dy = enemy.rect.centery - player.rect.centery
                if abs(dx) + abs(dy) > hit_range_2:
                    continue
                if dx * dx + dy * dy <= hit_range_sq:
                    player.hp = max(0, player.hp - 1)
                    player.last_hit_time = now
                    player.hitTime = now
                    screenShake.trigger()
                    break

        window.fill((0, 0, 0))
        trees = tileMap.get_trees_in_range(camera.world_x, camera.world_y, TREE_VIEW_DISTANCE)
        decos = mapDecos.get_decorations_in_range(camera.world_x, camera.world_y, TREE_VIEW_DISTANCE)
        renderList = trees + decos + [toRenderObj(player)]
        renderList.extend(toRenderObj(s) for s in slimes)
        renderList.extend(toRenderObj(g) for g in ghouls)
        if dash_unlocked:
            renderList.extend(dash.get_ghost_render_objs())

        renderList.extend(o.get_render_obj() for o in xp_orbs)
        renderList.extend(hp.get_render_obj() for hp in health_pickups)
        renderList.extend(p.get_render_obj() for p in necro_projectiles)
        if necromancer:
            renderList.append(toRenderObj(necromancer))

        renderer.render(camera, renderList, window)

        playerSP = getScreenPos(player, camera, renderer)
        if playerSP:
            lighting.draw(window, playerSP["x"], playerSP["y"])

        if necromancer and necromancer.isCasting and necromancer.hp > 0:
            necro_sp = getScreenPos(necromancer, camera, renderer)
            if necro_sp and playerSP:
                bf = necromancer.get_current_beam_frame()
                sx, sy = necro_sp["x"], necro_sp["y"]
                ex, ey = playerSP["x"], playerSP["y"]
                blen = math.hypot(ex - sx, ey - sy)
                if blen > 5:
                    dx_b = (ex - sx) / blen
                    dy_b = (ey - sy) / blen
                    angle = -math.degrees(math.atan2(dy_b, dx_b))
                    n_segs = 10
                    seg_len = blen / n_segs
                    for i in range(n_segs):
                        t = i / n_segs
                        h_scale = max(1.5, min(3.0, necro_sp["scale"] * 1.2)) * (1.0 - t * 0.5)
                        segW = max(4, int(seg_len + 2))
                        segH = max(2, int(bf.get_height() * h_scale))
                        seg = pygame.transform.scale(bf, (segW, segH))
                        tint = pygame.Surface((segW, segH), pygame.SRCALPHA)
                        tint.fill((120, 40, 200, 60))
                        seg.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
                        rotated = pygame.transform.rotate(seg, angle)
                        cx = sx + dx_b * (seg_len * (i + 0.5))
                        cy = sy + dy_b * (seg_len * (i + 0.5))
                        window.blit(rotated, rotated.get_rect(center=(int(cx), int(cy))))

        beam.draw(window)
        beam.drawHealthBars(window, all_enemies, camera, renderer)
        beam.drawBossHp(window, necromancer)
        beam.drawXpBar(window, player)
        beam.drawPlayerHp(window, player)
        levelUpFlash.draw(window)

        waveAnnouncer.draw(window)
        killStreak.draw(window)
        ammoSys.draw(window)
        runTimer.draw(window)

        shake_offset = screenShake.update()
        if shake_offset != (0, 0):
            frame_copy = window.copy()
            window.fill((0, 0, 0))
            window.blit(frame_copy, shake_offset)

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
