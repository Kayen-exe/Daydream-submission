import pygame
import random
import sys

# -------------------
# CONFIG
# -------------------

TILE = 32
MAZE_COLS = 21
MAZE_ROWS = 15
SCREEN_W = TILE * MAZE_COLS
SCREEN_H = TILE * MAZE_ROWS
FPS = 60

PLAYER_SIZE = TILE - 6
PLAYER_BASE_SPEED = 120.0
PLAYER_START_HEALTH = 100

CHOICE_COUNT = 8
WRONG_DEATH_COUNT = 3
FOG_RADIUS_TILES = 2

# colors
WHITE = (250, 250, 250)
BLACK = (20, 20, 20)
WALL_COL = (30, 30, 30)
FLOOR_COL = (200, 200, 200)
PLAYER_COL = (200, 70, 70)
CHOICE_COLOR = (80, 130, 240)
CHOICE_VISITED_CORRECT = (80, 200, 120)
CHOICE_VISITED_WRONG = (220, 80, 80)
TEXT_COL = (0, 255, 255)  # instructions
FOG_COL = (0, 0, 0, 250)


# -------------------
# Maze generation
# -------------------


def make_grid(cols, rows):
    return [[1 for _ in range(cols)] for _ in range(rows)]


def neighbors_for_carve(x, y, cols, rows):
    dirs = [(2, 0), (-2, 0), (0, 2), (0, -2)]
    res = []
    for dx, dy in dirs:
        nx, ny = x + dx, y + dy
        if 0 <= nx < cols and 0 <= ny < rows:
            res.append((nx, ny))
    return res


def carve_maze(cols, rows):
    grid = make_grid(cols, rows)
    start_x, start_y = 1, 1
    stack = [(start_x, start_y)]
    grid[start_y][start_x] = 0
    while stack:
        x, y = stack[-1]
        nbs = []
        for nx, ny in neighbors_for_carve(x, y, cols, rows):
            if grid[ny][nx] == 1:
                nbs.append((nx, ny))
        if nbs:
            nx, ny = random.choice(nbs)
            grid[(y + ny) // 2][(x + nx) // 2] = 0
            grid[ny][nx] = 0
            stack.append((nx, ny))
        else:
            stack.pop()
    return grid


def tile_neighbors_count(grid, x, y):
    count = 0
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < len(grid[0]) and 0 <= ny < len(grid) and grid[ny][nx] == 0:
            count += 1
    return count


def find_intersections(grid):
    inters = []
    for y in range(1, len(grid) - 1):
        for x in range(1, len(grid[0]) - 1):
            if grid[y][x] == 0 and tile_neighbors_count(grid, x, y) >= 3:
                inters.append((x, y))
    return inters


# -------------------
# Player & Choice classes
# -------------------
class Player:
    def __init__(self, x, y):
        self.x = x * TILE + TILE // 2
        self.y = y * TILE + TILE // 2
        self.size = PLAYER_SIZE
        self.base_speed = PLAYER_BASE_SPEED
        self.speed_multiplier = 1.0
        self.speed_timer = 0.0
        self.health = PLAYER_START_HEALTH

    def rect(self):
        half = self.size // 2
        return pygame.Rect(int(self.x - half), int(self.y - half), self.size, self.size)

    def update(self, dt):
        if self.speed_timer > 0:
            self.speed_timer -= dt
            if self.speed_timer <= 0:
                self.speed_multiplier = 1.0

    def move(self, dx, dy, dt, grid):
        if dx == 0 and dy == 0:
            return
        move_px = self.base_speed * self.speed_multiplier * dt
        new_x = self.x + dx * move_px
        new_y = self.y + dy * move_px
        col = int(new_x // TILE)
        row = int(new_y // TILE)
        rows = len(grid)
        cols = len(grid[0])
        if 0 <= col < cols and 0 <= row < rows and grid[row][col] == 0:
            self.x = new_x
            self.y = new_y
        else:
            col_x = int(new_x // TILE)
            row_x = int(self.y // TILE)
            if 0 <= col_x < cols and 0 <= row_x < rows and grid[row_x][col_x] == 0:
                self.x = new_x
            else:
                col_y = int(self.x // TILE)
                row_y = int(new_y // TILE)
                if 0 <= col_y < cols and 0 <= row_y < rows and grid[row_y][col_y] == 0:
                    self.y = new_y


class ChoicePoint:
    def __init__(self, tx, ty, left_opt, right_opt):
        self.tx = tx
        self.ty = ty
        self.left = left_opt
        self.right = right_opt
        self.visited = False
        self.chosen = None
        # steeper side for logic
        left_val = left_opt["value"]
        right_val = right_opt["value"]
        self.steeper = "left" if left_val >= right_val else "right"

    def get_pos(self):
        return (self.tx * TILE + TILE // 2, self.ty * TILE + TILE // 2)


# -------------------
# Choice logic with 80/20 chance & dynamic messages
# -------------------

correct_health_msgs = [
    "Correct but costly: +15 health",
    "Chose bravely! +speed for 6s",
    "Well done! Health increased slightly",
]

correct_speed_msgs = [
    "Speedy! +speed for 6s",
    "Smart choice! Minor health bonus",
    "Quick reflex! +speed boost",
]

wrong_msgs = [
    "Oops! Wrong choice: -10 health",
    "Unlucky! You lost some health",
    "Dangerous move! Health penalty applied",
]

special_wrong_msgs = [
    "Brave, but unlucky! -10 health",
    "Good attempt, wrong outcome! -health",
]


def determine_choice(cp, chosen_side):
    steeper = cp.steeper
    if chosen_side == steeper:
        if random.random() < 0.8:
            is_correct = True
            special_msg = None
        else:
            is_correct = False
            special_msg = random.choice(special_wrong_msgs)
    else:
        if random.random() < 0.2:
            is_correct = True
            special_msg = None
        else:
            is_correct = False
            special_msg = None
    return is_correct, special_msg


# -------------------
# Game loop
# -------------------


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Sacrifice Maze ")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 20)
    bigfont = pygame.font.SysFont(None, 28)

    # maze
    cols = MAZE_COLS
    rows = MAZE_ROWS
    grid = carve_maze(cols, rows)
    start_tile = (1, 1)
    exit_tile = (cols - 2, rows - 2)
    player = Player(start_tile[0], start_tile[1])

    # choice points
    inters = find_intersections(grid)
    random.shuffle(inters)
    chosen_inters = []
    for x, y in inters:
        if (x, y) in [start_tile, exit_tile]:
            continue
        chosen_inters.append((x, y))
        if len(chosen_inters) >= CHOICE_COUNT:
            break

    choice_points = []
    for tx, ty in chosen_inters:
        # assign two options with random severity
        a_type = random.choice(["health", "speed"])
        b_type = "speed" if a_type == "health" else "health"
        if a_type == "health":
            a_val = random.choice([20, 25, 30])
            b_val = random.choice([1, 2, 3, 4])
        else:
            a_val = random.choice([3, 4, 5])
            b_val = random.choice([8, 15, 20])
        if random.random() < 0.5:
            left_opt = {"type": a_type, "value": a_val}
            right_opt = {"type": b_type, "value": b_val}
        else:
            right_opt = {"type": a_type, "value": a_val}
            left_opt = {"type": b_type, "value": b_val}
        cp = ChoicePoint(tx, ty, left_opt, right_opt)
        choice_points.append(cp)

    wrong_count = 0
    total_visited = 0
    in_choice_prompt = None
    show_message = None
    show_message_timer = 0.0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()

        # movement
        if not in_choice_prompt:
            dx = dy = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                dy = -1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1
            if dx != 0 and dy != 0:
                dx *= 0.7071
                dy *= 0.7071
            player.move(dx, dy, dt, grid)
        player.update(dt)

        # check choice points
        px_tile = int(player.x // TILE)
        py_tile = int(player.y // TILE)
        for cp in choice_points:
            if not cp.visited and (px_tile, py_tile) == (cp.tx, cp.ty):
                in_choice_prompt = cp
                break

        # handle choice input
        if in_choice_prompt:
            chosen_side = None
            if keys[pygame.K_1] or keys[pygame.K_KP1]:
                chosen_side = "left"
            elif keys[pygame.K_2] or keys[pygame.K_KP2]:
                chosen_side = "right"
            if chosen_side:
                cp = in_choice_prompt
                cp.visited = True
                cp.chosen = chosen_side
                total_visited += 1
                opt = cp.left if chosen_side == "left" else cp.right

                is_correct, special_msg = determine_choice(cp, chosen_side)

                # apply sacrifice
                if opt["type"] == "health":
                    player.health -= opt["value"]
                    if is_correct:
                        player.speed_multiplier = 1.6
                        player.speed_timer = 6.0
                else:  # speed sacrifice
                    if is_correct:
                        player.speed_multiplier = 0.7
                        player.speed_timer = 3.0
                        player.health = min(PLAYER_START_HEALTH, player.health + 15)
                    else:
                        player.speed_multiplier = 0.5
                        player.speed_timer = 3.0

                # feedback message
                if special_msg:
                    show_message = special_msg
                else:
                    if is_correct:
                        if opt["type"] == "health":
                            show_message = random.choice(correct_health_msgs)
                        else:
                            show_message = random.choice(correct_speed_msgs)
                    else:
                        show_message = random.choice(wrong_msgs)
                        wrong_count += 1
                        player.health -= 10

                show_message_timer = 3.0
                in_choice_prompt = None

        # check death by wrong choices
        if wrong_count >= WRONG_DEATH_COUNT or player.health <= 0:
            draw_game(
                screen,
                grid,
                player,
                choice_points,
                None,
                font,
                bigfont,
                wrong_count,
                total_visited,
                show_message,
            )
            lose_txt = bigfont.render(
                "You died! Press R to restart or Q to quit", True, (220, 20, 20)
            )
            screen.blit(lose_txt, (20, SCREEN_H // 2 - 20))
            pygame.display.flip()
            waiting = True
            while waiting:
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    if ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_r:
                            main()
                            return
                        if ev.key == pygame.K_q:
                            pygame.quit()
                            sys.exit()
                clock.tick(30)

        # check exit
        if (px_tile, py_tile) == (cols - 2, rows - 2):
            draw_game(
                screen,
                grid,
                player,
                choice_points,
                None,
                font,
                bigfont,
                wrong_count,
                total_visited,
                show_message,
            )
            win_txt = bigfont.render(
                "You reached the exit! Press R to restart or Q to quit",
                True,
                (20, 140, 20),
            )
            screen.blit(win_txt, (20, SCREEN_H // 2 - 20))
            pygame.display.flip()
            waiting = True
            while waiting:
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    if ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_r:
                            main()
                            return
                        if ev.key == pygame.K_q:
                            pygame.quit()
                            sys.exit()
                clock.tick(30)

        draw_game(
            screen,
            grid,
            player,
            choice_points,
            in_choice_prompt,
            font,
            bigfont,
            wrong_count,
            total_visited,
            show_message,
        )
        if show_message:
            show_message_timer -= dt
            if show_message_timer <= 0:
                show_message = None
        pygame.display.flip()


# -------------------
# Drawing
# -------------------


def draw_game(
    screen,
    grid,
    player,
    choice_points,
    in_choice_prompt,
    font,
    bigfont,
    wrong_count,
    total_visited,
    show_message,
):
    screen.fill(BLACK)
    rows = len(grid)
    cols = len(grid[0])
    surf = pygame.Surface((SCREEN_W, SCREEN_H))
    surf.fill(FLOOR_COL)
    for r in range(rows):
        for c in range(cols):
            rect = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
            if grid[r][c] == 1:
                pygame.draw.rect(surf, WALL_COL, rect)

    # choice points
    for cp in choice_points:
        cx, cy = cp.get_pos()
        r = 8
        if not cp.visited:
            pygame.draw.circle(surf, CHOICE_COLOR, (cx, cy), r)
        else:
            col = (
                CHOICE_VISITED_CORRECT
                if cp.chosen == cp.steeper
                else CHOICE_VISITED_WRONG
            )
            pygame.draw.circle(surf, col, (cx, cy), r)

    # exit
    exit_rect = pygame.Rect((cols - 2) * TILE, (rows - 2) * TILE, TILE, TILE)
    pygame.draw.rect(surf, (180, 160, 80), exit_rect)

    # player
    pygame.draw.rect(surf, PLAYER_COL, player.rect())

    # fog
    fog = pygame.Surface((SCREEN_W, SCREEN_H), flags=pygame.SRCALPHA)
    fog.fill(FOG_COL)
    radius = FOG_RADIUS_TILES * TILE
    pygame.draw.circle(fog, (0, 0, 0, 0), (int(player.x), int(player.y)), radius)
    screen.blit(surf, (0, 0))
    screen.blit(fog, (0, 0))

    # HUD
    screen.blit(font.render(f"Health: {int(player.health)}", True, TEXT_COL), (6, 6))
    screen.blit(
        font.render(
            f"Wrong choices: {wrong_count}/{WRONG_DEATH_COUNT}", True, TEXT_COL
        ),
        (6, 24),
    )
    screen.blit(
        font.render(f"Visited: {total_visited}/{CHOICE_COUNT}", True, TEXT_COL), (6, 42)
    )
    screen.blit(
        font.render("Move: Arrows/WASD. Choice tile: 1 or 2.", True, TEXT_COL), (6, 60)
    )

    # choice prompt
    if in_choice_prompt:
        cp = in_choice_prompt
        box_w = 420
        box_h = 120
        box = pygame.Rect(
            (SCREEN_W - box_w) // 2, (SCREEN_H - box_h) // 2, box_w, box_h
        )
        pygame.draw.rect(screen, (240, 240, 240), box)
        pygame.draw.rect(screen, (30, 30, 30), box, 3)
        screen.blit(
            bigfont.render("CHOICE POINT", True, (30, 30, 30)), (box.x + 12, box.y + 8)
        )
        left = cp.left
        right = cp.right
        screen.blit(
            font.render(
                f"1) LEFT: Sacrifice {left['value']} {left['type']}", True, BLACK
            ),
            (box.x + 16, box.y + 48),
        )
        screen.blit(
            font.render(
                f"2) RIGHT: Sacrifice {right['value']} {right['type']}", True, BLACK
            ),
            (box.x + 16, box.y + 72),
        )
        screen.blit(
            font.render(
                "The steeper sacrifice is braver but not always correct.",
                True,
                (90, 90, 90),
            ),
            (box.x + 16, box.y + 96),
        )

    # feedback message
    if show_message:
        screen.blit(
            bigfont.render(show_message, True, (220, 20, 20)), (SCREEN_W // 2 - 200, 8)
        )


# -------------------
# RUN
# -------------------
if __name__ == "__main__":
    main()
