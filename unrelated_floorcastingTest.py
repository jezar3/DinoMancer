import pygame as pg
import numpy as np

pg.init()

screen = pg.display.set_mode((800, 600))

running = True 
half_HorizontalResolution = 800 / 2
half_VerticalResolution = 600 / 2

mod = half_VerticalResolution / 60
posx, posy, rot = 0, 0, 0
randomcolors = np.random.uniform(0.5, 1, (80, 60, 3))
while running:
    
    for event in pg.event.get():
        if event.type == pg.QUIT:
            
            running = False 
    
    
    
    surf = pg.surfarray.make_surface(randomcolors*255)
    surf = pg.transform.scale(surf, (800, 600))
    
    screen.blit(surf, (0,0))

    pg.display.update()
    