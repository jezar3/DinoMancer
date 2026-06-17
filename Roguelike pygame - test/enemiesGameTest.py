utf-8import pygame

from enemies import Necromancer


WINDOW_SIZE = (1600, 900)
BACKGROUND_COLOR = (18, 18, 24)


def main():
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("Enemy Animation Test")
    clock = pygame.time.Clock()

    necromancer = Necromancer(0, 0)
    necromancer.rect.midbottom = (WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2 + 80)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        necromancer.animate()

        screen.fill(BACKGROUND_COLOR)
        screen.blit(necromancer.current_image, necromancer.rect)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
