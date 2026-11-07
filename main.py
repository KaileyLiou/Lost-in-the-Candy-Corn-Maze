import heapq
import os
import random
import pygame

COLS, ROWS, CELL = 15, 15, 44
MAZE_W, MAZE_H = COLS * CELL, ROWS * CELL
PANEL_W = 280
WIDTH, HEIGHT = MAZE_W + PANEL_W, MAZE_H

MOVE_DELAY = 0.13

BG = (40, 20, 60)
PANEL_BG = (28, 14, 42)
FLOOR = (250, 240, 215)
WALL = (230, 140, 30)
GOLD = (255, 215, 90)
WHITE = (255, 255, 255)
CANDY_COLOR = (230, 50, 120)
COCOA_COLOR = (120, 70, 30)
SPIDER_COLOR = (30, 30, 30)
WEB_COLOR = (170, 170, 185)
PLAYER_COLOR = (255, 120, 0)
BOSS_COLOR = (120, 60, 160)
GATE_CLOSED = (120, 120, 120)
GATE_OPEN = (60, 200, 90)
DEBUG_GHOST = (60, 220, 60)
DEBUG_BOSS = (255, 60, 160)
DEBUG_PRED = (0, 200, 255)

DIRS = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
DIR_NAMES = {"N": "UP", "S": "DOWN", "W": "LEFT", "E": "RIGHT"}

DEFAULT_SETTINGS = {
    "candy": 0.06, "cocoa": 0.02, "spider": 0.03, "cobweb": 0.04,
    "difficulty": "Normal",
}

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
            stack.pop()
    return grid

def walk_ahead(grid, start, direction, steps):
    col, row = start
    dc, dr = DIRS[direction]
    for _ in range(steps):
        if grid[row][col].walls[direction]:
            break
        col += dc
        row += dr
    return (col, row)

def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar(grid, start, goal):
    open_heap = [(manhattan(start, goal), 0, start)]
    g_cost = {start: 0}
    parent = {start: None}
    closed = set()

    while open_heap:
        f, g, current = heapq.heappop(open_heap)
        if current == goal:
            path = []
            node = goal
            while node != start:
                path.append(node)
                node = parent[node]
            path.reverse()
            return path
        if current in closed:
            continue
        closed.add(current)

        cell = grid[current[1]][current[0]]
        for d, (dc, dr) in DIRS.items():
            if cell.walls[d]:
                continue
            nxt = (current[0] + dc, current[1] + dr)
            new_g = g + 1
            if nxt not in g_cost or new_g < g_cost[nxt]:
                g_cost[nxt] = new_g
                parent[nxt] = current
                heapq.heappush(open_heap, (new_g + manhattan(nxt, goal), new_g, nxt))
    return []

class Player:
    def __init__(self):
        self.col = 0
        self.row = 0
        self.health = 100
        self.score = 0
        self.slow_timer = 0.0
        self.move_cd = 0.0

    @property
    def pos(self):
        return (self.col, self.row)

    def try_move(self, direction, grid):
        if grid[self.row][self.col].walls[direction]:
            return False
        dc, dr = DIRS[direction]
        self.col += dc
        self.row += dr
        return True

class MarkovPredictor:
    ORDER = ["N", "S", "W", "E"]

    def __init__(self):
        self.counts = {a: {b: 0 for b in self.ORDER} for a in self.ORDER}
        self.last = None
        self.total = 0
        self.checked = 0
        self.correct = 0

    def ranked(self):
        if self.last is None:
            return []
        row = self.counts[self.last]
        total = sum(row.values())
        if total == 0:
            return []
        items = [(d, row[d] / total) for d in self.ORDER if row[d] > 0]
        items.sort(key=lambda x: -x[1])
        return items

    def record(self, direction):
        if self.last is not None:
            ranked = self.ranked()
            if ranked:
                self.checked += 1
                if ranked[0][0] == direction:
                    self.correct += 1
            self.counts[self.last][direction] += 1
            self.total += 1
        self.last = direction

    def accuracy(self):
        return 100 * self.correct / self.checked if self.checked else 0.0

class Ghost:
    WANDER, CHASE, SEARCH = "WANDER", "CHASE", "SEARCH"
    COLORS = {"WANDER": (255, 255, 255), "CHASE": (255, 150, 200), "SEARCH": (150, 200, 255)}

    def __init__(self, col, row):
        self.col = col
        self.row = row
        self.state = self.WANDER
        self.path = []
        self.target = None
        self.move_timer = 0.0
        self.repath_timer = 0.0
        self.search_timer = 0.0

    @property
    def pos(self):
        return (self.col, self.row)

    def update(self, dt, player_pos, grid):
        dist = manhattan(self.pos, player_pos)
        if self.state == self.WANDER:
            if dist <= 6:
                self.state = self.CHASE
                self.repath_timer = 0
        elif self.state == self.CHASE:
            if dist > 8:
                self.state = self.SEARCH
                self.search_timer = 0
                self.target = player_pos
                self.path = astar(grid, self.pos, self.target)
        elif self.state == self.SEARCH:
            self.search_timer += dt
            if dist <= 6:
                self.state = self.CHASE
                self.repath_timer = 0
            elif self.search_timer >= 3:
                self.state = self.WANDER
                self.path = []
                self.target = None

        if self.state == self.WANDER:
            if not self.path:
                self.pick_wander_target(grid)
        elif self.state == self.CHASE:
            self.repath_timer -= dt
            if self.repath_timer <= 0:
                self.target = player_pos
                self.path = astar(grid, self.pos, self.target)
                self.repath_timer = 0.5

        step_time = 0.30 if self.state == self.CHASE else 0.50
        self.move_timer += dt
        if self.move_timer >= step_time and self.path:
            self.move_timer = 0
            self.col, self.row = self.path.pop(0)

    def pick_wander_target(self, grid):
        for _ in range(20):
            c = max(0, min(COLS - 1, self.col + random.randint(-6, 6)))
            r = max(0, min(ROWS - 1, self.row + random.randint(-6, 6)))
            if (c, r) != self.pos:
                self.target = (c, r)
                self.path = astar(grid, self.pos, self.target)
                if self.path:
                    return
