#!/usr/bin/env python3
"""Carnelian Cascade — neon match-3 kiln for ElbowOS."""
import argparse, math, os, random, subprocess, sys

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "CARNELIAN CASCADE"
HANDLE = "x.com/ElbowOS"
COLS, ROWS = 6, 8
CELL = 148
OX = (W - COLS * CELL) // 2
OY = 280
PAL = {
    "bg0": (18, 6, 8),
    "ink": (42, 10, 14),
    "line": (90, 28, 32),
    "carn": (255, 92, 48),
    "gold": (255, 196, 64),
    "teal": (48, 230, 196),
    "rose": (255, 110, 160),
    "vio": (180, 96, 255),
    "ice": (255, 236, 220),
    "dim": (160, 90, 80),
}
GEMS = [
    (255, 86, 42),
    (255, 196, 54),
    (46, 220, 186),
    (255, 108, 168),
    (168, 92, 255),
]


class Game:
    def __init__(self, auto=False):
        self.auto = auto
        self.t = self.score = self.clears = self.combo = 0
        self.sel = None
        self.cur = [2, 3]
        self.lock = 0
        self.flash = 0
        self.sparks = []
        self.floaters = []
        self.motes = [
            (random.randrange(W), random.randrange(H), random.randint(1, 3), random.choice(GEMS))
            for _ in range(64)
        ]
        self.grid = [[random.randrange(len(GEMS)) for _ in range(COLS)] for _ in range(ROWS)]
        self._scrub(40)

    def _scrub(self, n=12):
        for _ in range(n):
            m = self._matches()
            if not m:
                break
            for r, c in m:
                self.grid[r][c] = random.randrange(len(GEMS))

    def _matches(self):
        hit = set()
        for r in range(ROWS):
            run = 1
            for c in range(1, COLS + 1):
                same = c < COLS and self.grid[r][c] == self.grid[r][c - 1] and self.grid[r][c] >= 0
                if same:
                    run += 1
                else:
                    if run >= 3:
                        for k in range(c - run, c):
                            hit.add((r, k))
                    run = 1
        for c in range(COLS):
            run = 1
            for r in range(1, ROWS + 1):
                same = r < ROWS and self.grid[r][c] == self.grid[r - 1][c] and self.grid[r][c] >= 0
                if same:
                    run += 1
                else:
                    if run >= 3:
                        for k in range(r - run, r):
                            hit.add((k, c))
                    run = 1
        return hit

    def _gravity(self):
        moved = False
        for c in range(COLS):
            stack = [self.grid[r][c] for r in range(ROWS) if self.grid[r][c] >= 0]
            pad = ROWS - len(stack)
            col = [-1] * pad + stack
            for r in range(ROWS):
                if col[r] < 0:
                    col[r] = random.randrange(len(GEMS))
                    moved = True
                if col[r] != self.grid[r][c]:
                    moved = True
                self.grid[r][c] = col[r]
        return moved

    def _burst(self, x, y, col, n=14):
        for _ in range(n):
            th = random.random() * 6.283
            s = random.uniform(1.6, 9.0)
            self.sparks.append([x, y, math.cos(th) * s, math.sin(th) * s, 16, col])

    def _cell_xy(self, r, c):
        return OX + c * CELL + CELL // 2, OY + r * CELL + CELL // 2

    def _swap(self, a, b):
        (r1, c1), (r2, c2) = a, b
        if abs(r1 - r2) + abs(c1 - c2) != 1:
            return False
        self.grid[r1][c1], self.grid[r2][c2] = self.grid[r2][c2], self.grid[r1][c1]
        if not self._matches():
            self.grid[r1][c1], self.grid[r2][c2] = self.grid[r2][c2], self.grid[r1][c1]
            return False
        return True

    def _resolve(self):
        total = 0
        chain = 0
        while True:
            hit = self._matches()
            if not hit:
                break
            chain += 1
            total += len(hit)
            for r, c in hit:
                x, y = self._cell_xy(r, c)
                col = GEMS[self.grid[r][c]]
                self._burst(x, y, col, 18)
                self.grid[r][c] = -1
            pts = len(hit) * 25 * chain
            self.score += pts
            self.clears += len(hit)
            cx = OX + COLS * CELL // 2
            self.floaters.append([cx, OY + 40, f"+{pts}", 28, PAL["gold"]])
            self._gravity()
            self.flash = 6
        self.combo = max(self.combo, chain)
        return total

    def _find_swap(self):
        dirs = ((0, 1), (1, 0))
        opts = []
        for r in range(ROWS):
            for c in range(COLS):
                for dr, dc in dirs:
                    rr, cc = r + dr, c + dc
                    if rr >= ROWS or cc >= COLS:
                        continue
                    self.grid[r][c], self.grid[rr][cc] = self.grid[rr][cc], self.grid[r][c]
                    n = len(self._matches())
                    self.grid[r][c], self.grid[rr][cc] = self.grid[rr][cc], self.grid[r][c]
                    if n:
                        opts.append(((r, c), (rr, cc), n))
        if not opts:
            self._scrub(8)
            return None
        opts.sort(key=lambda x: -x[2])
        return opts[0][0], opts[0][1]

    def autoplay(self):
        if self.lock:
            return
        found = self._find_swap()
        if not found:
            return
        a, b = found
        self.cur = list(a)
        self.sel = a
        self.lock = 8
        self._pending = b

    def step(self, keys=None):
        self.t += 1
        if self.flash:
            self.flash -= 1
        if self.lock:
            self.lock -= 1
            if self.lock == 0 and self.auto and hasattr(self, "_pending") and self._pending:
                self._swap(self.sel, self._pending)
                self._resolve()
                self.sel = None
                self._pending = None
        if self.auto:
            if self.t % 22 == 0:
                self.autoplay()
        elif keys and not self.lock:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.cur[1] = max(0, self.cur[1] - 1)
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.cur[1] = min(COLS - 1, self.cur[1] + 1)
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.cur[0] = max(0, self.cur[0] - 1)
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.cur[0] = min(ROWS - 1, self.cur[0] + 1)
        nxt = []
        for sp in self.sparks:
            sp[0] += sp[2]
            sp[1] += sp[3]
            sp[3] += 0.18
            sp[4] -= 1
            if sp[4] > 0:
                nxt.append(sp)
        self.sparks = nxt
        fl = []
        for f in self.floaters:
            f[1] -= 2.2
            f[3] -= 1
            if f[3] > 0:
                fl.append(f)
        self.floaters = fl

    def tap(self):
        pos = tuple(self.cur)
        if self.sel is None:
            self.sel = pos
            return
        if self.sel == pos:
            self.sel = None
            return
        if self._swap(self.sel, pos):
            self._resolve()
        self.sel = None

    def draw(self, surf, font, small, mid):
        for y in range(0, H, 8):
            k = y / H
            pygame.draw.rect(
                surf,
                (int(18 + 28 * k), int(4 + 8 * k), int(8 + 6 * k)),
                (0, y, W, 8),
            )
        for i, (x, y, r, col) in enumerate(self.motes):
            yy = (y + int(self.t * 0.7 + i)) % H
            pygame.draw.circle(surf, col, (x, yy), r)
        board = pygame.Rect(OX - 18, OY - 18, COLS * CELL + 36, ROWS * CELL + 36)
        pygame.draw.rect(surf, PAL["ink"], board, border_radius=28)
        pygame.draw.rect(surf, PAL["carn"], board, 4, border_radius=28)
        pulse = 0.5 + 0.5 * math.sin(self.t * 0.14)
        for r in range(ROWS):
            for c in range(COLS):
                gid = self.grid[r][c]
                x, y = self._cell_xy(r, c)
                pygame.draw.rect(surf, PAL["line"], (x - CELL // 2 + 8, y - CELL // 2 + 8, CELL - 16, CELL - 16), 1, 16)
                if gid < 0:
                    continue
                col = GEMS[gid]
                rad = 46 + int(3 * math.sin(self.t * 0.16 + r + c))
                pygame.draw.circle(surf, col, (x, y), rad)
                pygame.draw.circle(surf, PAL["ice"], (x - 12, y - 14), 12)
                pygame.draw.circle(surf, (20, 6, 8), (x, y), rad, 3)
        cr, cc = self.cur
        cx, cy = self._cell_xy(cr, cc)
        pygame.draw.rect(surf, PAL["gold"], (cx - 68, cy - 68, 136, 136), 5, 18)
        if self.sel:
            sx, sy = self._cell_xy(*self.sel)
            pygame.draw.rect(surf, PAL["teal"], (sx - 62, sy - 62, 124, 124), 4, 16)
        for sp in self.sparks:
            pygame.draw.circle(surf, sp[5], (int(sp[0]), int(sp[1])), max(2, sp[4] // 3))
        for f in self.floaters:
            img = mid.render(f[2], True, f[4])
            surf.blit(img, img.get_rect(center=(int(f[0]), int(f[1]))))
        if self.flash:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((255, 90, 40, 8 * self.flash))
            surf.blit(veil, (0, 0))
        banner = pygame.Surface((W, 150), pygame.SRCALPHA)
        banner.fill((16, 4, 6, 230))
        surf.blit(banner, (0, 0))
        surf.blit(font.render(TITLE, True, PAL["carn"]), (36, 16))
        surf.blit(small.render(HANDLE, True, PAL["gold"]), (36, 88))
        sc = font.render(f"{self.score:05d}", True, PAL["gold"])
        surf.blit(sc, (W - 44 - sc.get_width(), 16))
        meta = small.render(f"CUT {self.clears}   CHAIN {self.combo}   GLOW {int(pulse * 9)}", True, PAL["teal"])
        surf.blit(meta, (W - 44 - meta.get_width(), 90))
        hint = "ARROWS move  SPACE swap" if not self.auto else "AUTO KILN"
        foot = small.render(hint, True, PAL["dim"])
        surf.blit(foot, foot.get_rect(center=(W * 0.5, H - 48)))


def record(path):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    pygame.font.init()
    surf = pygame.Surface((W, H))
    font = pygame.font.SysFont("DejaVu Sans", 52, bold=True)
    mid = pygame.font.SysFont("DejaVu Sans", 44, bold=True)
    small = pygame.font.SysFont("DejaVu Sans", 30, bold=True)
    g = Game(auto=True)
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    frames = FPS * 15
    try:
        for _ in range(frames):
            g.step()
            g.draw(surf, font, small, mid)
            proc.stdin.write(pygame.image.tostring(surf, "RGB"))
        proc.stdin.close()
        err = proc.stderr.read()
        rc = proc.wait(timeout=60)
    except Exception:
        proc.kill()
        raise
    if rc != 0:
        raise RuntimeError(err.decode("utf-8", "ignore")[-800:])
    print("wrote", path)


def play():
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("DejaVu Sans", 52, bold=True)
    mid = pygame.font.SysFont("DejaVu Sans", 44, bold=True)
    small = pygame.font.SysFont("DejaVu Sans", 30, bold=True)
    g = Game(auto=False)
    run = True
    hold = {pygame.K_LEFT: 0, pygame.K_RIGHT: 0, pygame.K_UP: 0, pygame.K_DOWN: 0,
            pygame.K_a: 0, pygame.K_d: 0, pygame.K_w: 0, pygame.K_s: 0}
    while run:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                run = False
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    run = False
                if e.key in (pygame.K_SPACE, pygame.K_RETURN):
                    g.tap()
        keys = pygame.key.get_pressed()
        move = {k: False for k in hold}
        for k in hold:
            if keys[k]:
                hold[k] += 1
                if hold[k] == 1 or hold[k] > 10 and hold[k] % 4 == 0:
                    move[k] = True
            else:
                hold[k] = 0
        g.step(move)
        g.draw(screen, font, small, mid)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record", action="store_true")
    p.add_argument("--play", action="store_true")
    p.add_argument("--out", default="/home/workdir/artifacts/CARNELIAN_CASCADE_ElbowOS.mp4")
    a = p.parse_args()
    if a.record or not a.play:
        record(a.out)
        if a.play:
            play()
    else:
        play()


if __name__ == "__main__":
    main()
