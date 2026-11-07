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

