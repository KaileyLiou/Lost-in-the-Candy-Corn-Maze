import random
import pygame

COLS, ROWS, CELL = 15, 15, 40
WIDTH, HEIGHT = COLS * CELL, ROWS * CELL

BG = (40, 20, 60) # purple
FLOOR = (250, 240, 215) # cream
WALL = (230, 140, 30) # orange
PLAYER = (255, 120, 0)

DIRS = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}

class Cell:
    def __init__(self, col, row):
        self.col = col
        self.row = row
        self.walls = {"N": True, "S": True, "E": True, "W": True}
        self.visited = False

def generate_maze():
    grid = [[Cell(c, r) for c in range(COLS)] for r in range(ROWS)]

    start = grid[0][0]
    start.visited = True
    stack = [start]

    while stack:
        current = stack[-1]

        neighbors = []
        for d, (dc, dr) in DIRS.items():
            nc, nr = current.col + dc, current.row + dr
            if 0 <= nc < COLS and 0 <= nr < ROWS and not grid[nr][nc].visited:
                neighbors.append((d, grid[nr][nc]))

        if neighbors:
            d, nxt = random.choice(neighbors)
            current.walls[d] = False
            nxt.walls[OPPOSITE[d]] = False
            nxt.visited = True
            stack.append(nxt)
        else:
            stack.pop()  # backtrack

    return grid

def draw_maze(screen, grid):
    screen.fill(BG)
    for row in grid:
        for cell in row:
            x, y = cell.col * CELL, cell.row * CELL
            pygame.draw.rect(screen, FLOOR, (x, y, CELL, CELL))
            if cell.walls["N"]:
                pygame.draw.line(screen, WALL, (x, y), (x + CELL, y), 3)
            if cell.walls["S"]:
                pygame.draw.line(screen, WALL, (x, y + CELL), (x + CELL, y + CELL), 3)
            if cell.walls["W"]:
                pygame.draw.line(screen, WALL, (x, y), (x, y + CELL), 3)
            if cell.walls["E"]:
                pygame.draw.line(screen, WALL, (x + CELL, y), (x + CELL, y + CELL), 3)

class Player:
    def __init__(self):
        self.col = 0
        self.row = 0

    def try_move(self, direction, grid):
        if not grid[self.row][self.col].walls[direction]:
            dc, dr = DIRS[direction]
            self.col += dc
            self.row += dr

    def draw(self, screen):
        cx = self.col * CELL + CELL // 2
        cy = self.row * CELL + CELL // 2
        pygame.draw.circle(screen, PLAYER, (cx, cy), CELL // 3)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Lost in the Candy Corn Maze")
    clock = pygame.time.Clock()

    grid = generate_maze()
    player = Player()

    keymap = {
        pygame.K_w: "N", pygame.K_UP: "N",
        pygame.K_s: "S", pygame.K_DOWN: "S",
        pygame.K_a: "W", pygame.K_LEFT: "W",
        pygame.K_d: "E", pygame.K_RIGHT: "E",
    }

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in keymap:
                    player.try_move(keymap[event.key], grid)

        draw_maze(screen, grid)
        player.draw(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()