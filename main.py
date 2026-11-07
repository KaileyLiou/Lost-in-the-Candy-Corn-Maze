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

class Boss:
    PRESETS = {
        "Easy":   {"label": "Sleepy", "wa": 40,  "wb": 8, "replan": 2.0, "step": 0.40},
        "Normal": {"label": "Grumpy", "wa": 100, "wb": 5, "replan": 1.0, "step": 0.30},
        "Hard":   {"label": "Sneaky", "wa": 150, "wb": 3, "replan": 0.5, "step": 0.22},
    }

    def __init__(self, col, row, difficulty):
        self.col = col
        self.row = row
        self.preset = self.PRESETS[difficulty]
        self.path = []
        self.target = None
        self.mode = "CHASE"
        self.candidates = []
        self.chosen = None
        self.chosen_util = 0.0
        self.replan_timer = 0.0
        self.move_timer = 0.0

    @property
    def pos(self):
        return (self.col, self.row)

    def update(self, dt, player_pos, markov, grid):
        self.replan_timer -= dt
        if self.replan_timer <= 0:
            self.replan(player_pos, markov, grid)
            self.replan_timer = self.preset["replan"]

        self.move_timer += dt
        if self.move_timer >= self.preset["step"] and self.path:
            self.move_timer = 0
            self.col, self.row = self.path.pop(0)

    def replan(self, player_pos, markov, grid):
        wa, wb = self.preset["wa"], self.preset["wb"]
        ranked = markov.ranked()

        found = {}
        if ranked:
            top_dir, top_p = ranked[0]
            for steps in (2, 3):
                cell = walk_ahead(grid, player_pos, top_dir, steps)
                if cell != player_pos:
                    found[cell] = (top_p, top_dir)
            if len(ranked) > 1:
                second_dir, second_p = ranked[1]
                cell = walk_ahead(grid, player_pos, second_dir, 3)
                if cell != player_pos and cell not in found:
                    found[cell] = (second_p, second_dir)

        self.candidates = []
        for cell, (prob, direction) in found.items():
            path = astar(grid, self.pos, cell)
            dist = len(path)
            util = wa * prob - wb * dist
            self.candidates.append({
                "cell": cell, "prob": prob, "dir": direction,
                "dist": dist, "util": util, "path": path,
            })

        best = max(self.candidates, key=lambda c: c["util"], default=None)
        if best is not None and best["util"] > 0:
            self.mode = "AMBUSH"
            self.target = best["cell"]
            self.path = best["path"]
            self.chosen = best["cell"]
            self.chosen_util = best["util"]
        else:
            self.mode = "CHASE"
            self.target = player_pos
            self.path = astar(grid, self.pos, player_pos)
            self.chosen = None
            self.chosen_util = 0.0

def center(col, row):
    return (col * CELL + CELL // 2, row * CELL + CELL // 2)

def random_far_cell(from_pos, min_dist):
    while True:
        c, r = random.randint(0, COLS - 1), random.randint(0, ROWS - 1)
        if manhattan((c, r), from_pos) >= min_dist:
            return (c, r)

def spawn_items(settings, exit_pos):
    used = {(0, 0), exit_pos}
    result = {}
    for name in ["candy", "cocoa", "spider", "cobweb"]:
        cells = set()
        for r in range(ROWS):
            for c in range(COLS):
                if (c, r) in used:
                    continue
                if random.random() < settings[name]:
                    cells.add((c, r))
        used |= cells
        result[name] = cells
    if not result["candy"]:
        while True:
            c, r = random.randint(0, COLS - 1), random.randint(0, ROWS - 1)
            if (c, r) not in used:
                result["candy"].add((c, r))
                for name in ["cocoa", "spider", "cobweb"]:
                    result[name].discard((c, r))
                break
    return result

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

SPRITE_SIZES = {"player": 38, "ghost": 38, "boss": 44, "candy": 30,
                "cocoa": 30, "spider": 28, "cobweb": 32, "gate": 44}

def load_sprites():
    base = ASSET_DIR
    sprites = {}
    for name in ["player", "ghost", "boss", "candy", "cocoa", "spider", "cobweb", "gate"]:
        path = os.path.join(base, name + ".png")
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            size = SPRITE_SIZES[name]
            sprites[name] = pygame.transform.smoothscale(img, (size, size))
    return sprites

SOUND_NAMES = ["candy", "cocoa", "hurt", "web", "boo", "ambush", "win", "lose"]

def load_sounds():
    sounds = {}
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
    except pygame.error:
        return sounds
    for name in SOUND_NAMES:
        path = os.path.join(ASSET_DIR, name + ".ogg")
        if os.path.exists(path):
            try:
                sounds[name] = pygame.mixer.Sound(path)
            except pygame.error:
                print(f"Could not load {name}.ogg")
    return sounds

class Game:
    MENU_ITEMS = [
        ("Candy chance", "candy"),
        ("Warm cocoa chance", "cocoa"),
        ("Spider chance", "spider"),
        ("Cobweb chance", "cobweb"),
        ("Boss difficulty", "difficulty"),
    ]

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Lost in the Candy Corn Maze")
        self.clock = pygame.time.Clock()
        self.sprites = load_sprites()
        self.sounds = load_sounds()
        self.font = pygame.font.SysFont(None, 22)
        self.small_font = pygame.font.SysFont(None, 18)
        self.med_font = pygame.font.SysFont(None, 30)
        self.big_font = pygame.font.SysFont(None, 64)

        self.keymap = {
            pygame.K_w: "N", pygame.K_UP: "N",
            pygame.K_s: "S", pygame.K_DOWN: "S",
            pygame.K_a: "W", pygame.K_LEFT: "W",
            pygame.K_d: "E", pygame.K_RIGHT: "E",
        }
        self.settings = dict(DEFAULT_SETTINGS)
        self.menu_index = 0
        self.debug = False
        self.state = "menu"
        self.end_reason = ""

    def start_game(self):
        self.grid = generate_maze()
        self.exit_pos = (COLS - 1, ROWS - 1)
        self.player = Player()
        self.markov = MarkovPredictor()

        items = spawn_items(self.settings, self.exit_pos)
        self.candy = items["candy"]
        self.cocoa = items["cocoa"]
        self.spiders = items["spider"]
        self.webs = items["cobweb"]

        self.ghosts = []
        for _ in range(2):
            c, r = random_far_cell(self.player.pos, 8)
            self.ghosts.append(Ghost(c, r))
        bc, br = random_far_cell(self.player.pos, 10)
        self.boss = Boss(bc, br, self.settings["difficulty"])

        self.invincible = 0.0
        self.ambush_cd = 0.0
        self.end_reason = ""
        self.state = "play"

        music = os.path.join(ASSET_DIR, "music.ogg")
        if pygame.mixer.get_init() and os.path.exists(music):
            try:
                pygame.mixer.music.load(music)
                pygame.mixer.music.set_volume(0.3)
                pygame.mixer.music.play(-1)
            except pygame.error:
                print("Could not load music.ogg")

    def play(self, name):
        if name in self.sounds:
            self.sounds[name].play()

    def finish(self, result, reason):
        self.state = result
        self.end_reason = reason
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        self.play(result)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return True
        if event.key == pygame.K_ESCAPE:
            return False

        if self.state == "menu":
            self.menu_event(event.key)
        else:
            if event.key == pygame.K_TAB:
                self.debug = not self.debug
            if event.key == pygame.K_r and self.state in ("win", "lose"):
                self.state = "menu"
        return True

    def menu_event(self, key):
        if key in (pygame.K_UP, pygame.K_w):
            self.menu_index = (self.menu_index - 1) % len(self.MENU_ITEMS)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.menu_index = (self.menu_index + 1) % len(self.MENU_ITEMS)
        elif key in (pygame.K_LEFT, pygame.K_a):
            self.change_setting(-1)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.change_setting(+1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.start_game()

    def change_setting(self, direction):
        key = self.MENU_ITEMS[self.menu_index][1]
        if key == "difficulty":
            names = list(Boss.PRESETS.keys())
            i = (names.index(self.settings[key]) + direction) % len(names)
            self.settings[key] = names[i]
        else:
            value = self.settings[key] + 0.02 * direction
            self.settings[key] = round(max(0.0, min(0.30, value)), 2)

    def update(self, dt):
        if self.state != "play":
            return
        p = self.player
        self.invincible = max(0.0, self.invincible - dt)
        self.ambush_cd = max(0.0, self.ambush_cd - dt)
        p.slow_timer = max(0.0, p.slow_timer - dt)
        p.move_cd -= dt

        if p.move_cd <= 0:
            keys = pygame.key.get_pressed()
            for key, d in self.keymap.items():
                if keys[key]:
                    if p.try_move(d, self.grid):
                        self.markov.record(d)
                        self.enter_cell()
                        p.move_cd = MOVE_DELAY * (2 if p.slow_timer > 0 else 1)
                    break

        for g in self.ghosts:
            before = g.state
            g.update(dt, p.pos, self.grid)
            if before != g.CHASE and g.state == g.CHASE:
                self.play("boo")
            if g.pos == p.pos and self.invincible == 0:
                p.health -= 10
                self.invincible = 1.5
                self.play("hurt")

        before = self.boss.mode
        self.boss.update(dt, p.pos, self.markov, self.grid)
        if before != "AMBUSH" and self.boss.mode == "AMBUSH" and self.ambush_cd == 0:
            self.play("ambush")
            self.ambush_cd = 5.0

        if self.boss.pos == p.pos:
            self.finish("lose", "The scarecrow caught you!")
        elif p.health <= 0:
            self.finish("lose", "You ran out of health.")
        elif p.pos == self.exit_pos and not self.candy:
            self.finish("win", f"Final score: {p.score}")

    def enter_cell(self):
        p = self.player
        pos = p.pos
        if pos in self.candy:
            self.candy.remove(pos)
            p.score += 10
            self.play("candy")
        if pos in self.cocoa:
            self.cocoa.remove(pos)
            p.health = min(100, p.health + 25)
            self.play("cocoa")
        if pos in self.spiders:
            p.health -= 20
            self.play("hurt")
        if pos in self.webs:
            p.slow_timer = 2.0
            self.play("web")

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        else:
            self.draw_game()
        pygame.display.flip()

    def draw_thing(self, name, pos, color, radius, ring=None):
        cx, cy = center(*pos)
        if ring:
            pygame.draw.circle(self.screen, ring, (cx, cy), CELL // 2 - 2, 3)
        if name in self.sprites:
            img = self.sprites[name]
            self.screen.blit(img, img.get_rect(center=(cx, cy)))
        else:
            pygame.draw.circle(self.screen, color, (cx, cy), radius)

    def draw_game(self):
        self.screen.fill(BG)
        for row in self.grid:
            for cell in row:
                x, y = cell.col * CELL, cell.row * CELL
                pygame.draw.rect(self.screen, FLOOR, (x, y, CELL, CELL))
                if cell.walls["N"]:
                    pygame.draw.line(self.screen, WALL, (x, y), (x + CELL, y), 3)
                if cell.walls["S"]:
                    pygame.draw.line(self.screen, WALL, (x, y + CELL), (x + CELL, y + CELL), 3)
                if cell.walls["W"]:
                    pygame.draw.line(self.screen, WALL, (x, y), (x, y + CELL), 3)
                if cell.walls["E"]:
                    pygame.draw.line(self.screen, WALL, (x + CELL, y), (x + CELL, y + CELL), 3)

        if "gate" in self.sprites:
            img = self.sprites["gate"].copy()
            if self.candy:
                img.set_alpha(110)
            self.screen.blit(img, img.get_rect(center=center(*self.exit_pos)))
        else:
            gate_color = GATE_OPEN if not self.candy else GATE_CLOSED
            gx, gy = self.exit_pos[0] * CELL, self.exit_pos[1] * CELL
            pygame.draw.rect(self.screen, gate_color, (gx + 6, gy + 6, CELL - 12, CELL - 12))

        for pos in self.webs:
            self.draw_thing("cobweb", pos, WEB_COLOR, CELL // 3)
        for pos in self.spiders:
            self.draw_thing("spider", pos, SPIDER_COLOR, CELL // 5)
        for pos in self.cocoa:
            self.draw_thing("cocoa", pos, COCOA_COLOR, CELL // 5)
        for pos in self.candy:
            self.draw_thing("candy", pos, CANDY_COLOR, CELL // 6)

        for g in self.ghosts:
            self.draw_thing("ghost", g.pos, g.COLORS[g.state], CELL // 3, ring=g.COLORS[g.state])
        self.draw_thing("boss", self.boss.pos, BOSS_COLOR, CELL // 2 - 4)
        self.draw_thing("player", self.player.pos, PLAYER_COLOR, CELL // 3)

        if self.debug:
            self.draw_debug_overlay()
        self.draw_panel()

        if self.state in ("win", "lose"):
            self.draw_end_overlay()

    def draw_debug_overlay(self):
        for g in self.ghosts:
            points = [center(*g.pos)] + [center(c, r) for c, r in g.path]
            if len(points) >= 2:
                pygame.draw.lines(self.screen, DEBUG_GHOST, False, points, 2)
            if g.target:
                pygame.draw.circle(self.screen, DEBUG_GHOST, center(*g.target), 8, 2)
            self.label(f"{g.state} -> {g.target}", g.pos)

        b = self.boss
        for cand in b.candidates:
            tile = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
            tile.fill((255, 230, 0, 110))
            cx, cy = cand["cell"]
            self.screen.blit(tile, (cx * CELL, cy * CELL))
            if cand["cell"] == b.chosen:
                pygame.draw.rect(self.screen, (255, 140, 0),
                                 (cx * CELL, cy * CELL, CELL, CELL), 3)
            text = self.small_font.render(f"{cand['util']:.0f}", True, (0, 0, 0))
            self.screen.blit(text, text.get_rect(center=center(cx, cy)))

        points = [center(*b.pos)] + [center(c, r) for c, r in b.path]
        if len(points) >= 2:
            pygame.draw.lines(self.screen, DEBUG_BOSS, False, points, 3)
        if b.target:
            pygame.draw.circle(self.screen, DEBUG_BOSS, center(*b.target), 9, 3)
        self.label(f"{b.mode} -> {b.target}", b.pos)

        ranked = self.markov.ranked()
        if ranked:
            d = ranked[0][0]
            px, py = center(*self.player.pos)
            dc, dr = DIRS[d]
            pygame.draw.line(self.screen, DEBUG_PRED, (px, py),
                             (px + dc * CELL, py + dr * CELL), 4)

    def label(self, text, pos):
        img = self.small_font.render(text, True, (0, 0, 0))
        x, y = center(*pos)
        bg = img.get_rect(center=(x, y - CELL // 2 - 4)).inflate(6, 2)
        pygame.draw.rect(self.screen, (255, 255, 255), bg)
        self.screen.blit(img, img.get_rect(center=bg.center))

    def draw_panel(self):
        pygame.draw.rect(self.screen, PANEL_BG, (MAZE_W, 0, PANEL_W, HEIGHT))
        x, y = MAZE_W + 14, 14

        def line(text, color=WHITE, font=None, gap=24):
            nonlocal y
            img = (font or self.font).render(text, True, color)
            self.screen.blit(img, (x, y))
            y += gap

        p = self.player
        line("Candy Corn Maze", GOLD, self.med_font, 34)
        line(f"HP: {p.health}")
        line(f"Score: {p.score}")
        line(f"Candy left: {len(self.candy)}")
        if p.slow_timer > 0:
            line("Stuck in a cobweb!", (200, 200, 255))
        y += 6
        line("Tab = AI debug   Esc = quit", (190, 170, 210), self.small_font, 28)

        if not self.debug:
            return

        pygame.draw.line(self.screen, GOLD, (x, y), (x + PANEL_W - 28, y), 1)
        y += 10
        line("[DEBUG PANEL]", GOLD, self.med_font, 28)

        ranked = self.markov.ranked()
        if ranked:
            line(f"Prediction: {DIR_NAMES[ranked[0][0]]} ({ranked[0][1] * 100:.0f}%)")
        else:
            line("Prediction: none yet")
        line(f"Markov accuracy: {self.markov.accuracy():.1f}%")
        line(f"Transitions: {self.markov.total}")
        y += 4

        line("Matrix (from \\ to)  U  D  L  R", (190, 170, 210), self.small_font, 20)
        for a in MarkovPredictor.ORDER:
            row = self.markov.counts[a]
            nums = "".join(f"{row[b]:>4}" for b in MarkovPredictor.ORDER)
            line(f"{DIR_NAMES[a]:<6}{nums}", WHITE, self.small_font, 20)
        y += 6

        b = self.boss
        line(f"Boss: {b.preset['label']}", DEBUG_BOSS)
        line(f"Mode: {b.mode} -> {b.target}")
        line(f"Path nodes: {len(b.path)}   Replan: {max(0, b.replan_timer):.1f}s")
        line(f"Utility = {b.preset['wa']}*prob - {b.preset['wb']}*dist",
             WHITE, self.small_font, 20)
        for cand in b.candidates:
            mark = "*" if cand["cell"] == b.chosen else " "
            line(f"{mark}{cand['cell']} p={cand['prob'] * 100:.0f}% "
                 f"d={cand['dist']} u={cand['util']:.0f}", WHITE, self.small_font, 18)
        y += 6
        for i, g in enumerate(self.ghosts, 1):
            line(f"Ghost {i}: {g.state} ({len(g.path)} nodes)", DEBUG_GHOST, self.small_font, 20)

    def draw_end_overlay(self):
        overlay = pygame.Surface((MAZE_W, MAZE_H), pygame.SRCALPHA)
        overlay.fill((20, 10, 30, 200))
        self.screen.blit(overlay, (0, 0))
        cx, cy = MAZE_W // 2, MAZE_H // 2
        title = "YOU ESCAPED!" if self.state == "win" else "GAME OVER"
        t1 = self.big_font.render(title, True, GOLD)
        t2 = self.med_font.render(self.end_reason, True, WHITE)
        t3 = self.font.render("Press R for the start screen  |  Esc to quit", True, WHITE)
        self.screen.blit(t1, t1.get_rect(center=(cx, cy - 50)))
        self.screen.blit(t2, t2.get_rect(center=(cx, cy + 10)))
        self.screen.blit(t3, t3.get_rect(center=(cx, cy + 55)))

    def draw_menu(self):
        self.screen.fill(BG)
        cx = WIDTH // 2
        title = self.big_font.render("Lost in the Candy Corn Maze", True, GOLD)
        self.screen.blit(title, title.get_rect(center=(cx, 90)))
        sub = self.font.render("Choose an option and then press Enter", True, WHITE)
        self.screen.blit(sub, sub.get_rect(center=(cx, 140)))

        y = 210
        for i, (label, key) in enumerate(self.MENU_ITEMS):
            selected = (i == self.menu_index)
            color = GOLD if selected else WHITE
            if key == "difficulty":
                value = f"{self.settings[key]}  ({Boss.PRESETS[self.settings[key]]['label']})"
            else:
                value = f"{round(self.settings[key] * 100)}%"
            prefix = "> " if selected else "  "
            left = self.med_font.render(prefix + label, True, color)
            right = self.med_font.render(f"< {value} >", True, color)
            self.screen.blit(left, (cx - 300, y))
            self.screen.blit(right, (cx + 40, y))
            y += 56

        hints = [
            "Up/Down: choose     Left/Right: change     Enter: start",
            "In game: WASD or arrows to move (hold to keep walking)",
            "Collect all the candy, then reach the gate. Press tab to see the AI think.",
        ]
        y = HEIGHT - 120
        for h in hints:
            img = self.font.render(h, True, (200, 180, 220))
            self.screen.blit(img, img.get_rect(center=(cx, y)))
            y += 28

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif not self.handle_event(event):
                    running = False
            self.update(dt)
            self.draw()
        pygame.quit()

if __name__ == "__main__":
    Game().run()