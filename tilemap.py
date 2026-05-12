import random
import pygame


class TileMap:
    def __init__(self):
        self.chunk_size = 256
        self.trees_by_chunk = {}
        self.tree_image = pygame.transform.scale(
            pygame.image.load("assets/world assets/tree_classic.png").convert_alpha(), (750, 750))

    def setTreeImage(self, path):
        self.tree_image = pygame.transform.scale(
            pygame.image.load(path).convert_alpha(), (750, 750))

    def _get_chunk_trees(self, col, row):
        key = (col, row)

        if key not in self.trees_by_chunk:
            
            rng = random.Random(col * 73856093 + row * 19349669)

            trees = []
            if rng.random() < 0.01:
                lx = rng.randint(0, self.chunk_size - 256)
                ly = rng.randint(0, self.chunk_size - 256)

                trees.append((col * self.chunk_size + lx + 128, row * self.chunk_size + ly + 256))
            

            self.trees_by_chunk[key] = trees
            
        return self.trees_by_chunk[key]

    def get_trees_in_range(self, cx, cy, view_dist):

        c1 = int((cx - view_dist) // self.chunk_size) - 1
        c2 = int((cx + view_dist) // self.chunk_size) + 2
        r1 = int((cy - view_dist) // self.chunk_size) - 1
        r2 = int((cy + view_dist) // self.chunk_size) + 2

        return [
            {"world_x": wx, "world_y": wy, "image": self.tree_image}
            for row in range(r1, r2)
            for col in range(c1, c2)
            for wx, wy in self._get_chunk_trees(col, row)
        ]