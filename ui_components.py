import pygame
import random
import os
from settings import WIDTH, HEIGHT
from config import BASE_DIR


def get_rainbow_color(time_ms, speed=0.2):
    """根据时间生成平滑过渡的 RGB 炫彩颜色"""
    hue = int(time_ms * speed) % 360
    color = pygame.Color(0)
    color.hsva = (hue, 100, 100, 100)
    return color


class FallingParticle:
    """完美跨平台的反馈粒子系统 (支持多路径健壮图片检索缓存)"""
    cached_shit_img = None

    def __init__(self, p_type):
        self.type = p_type
        self.x = random.randint(50, WIDTH - 50)
        self.y = random.randint(-200, -50)
        self.vy = random.uniform(4, 10)
        self.vx = random.uniform(-2, 2)
        self.angle = random.randint(0, 360)
        self.active = True

        if self.type == "money":
            self.surf = pygame.Surface((40, 24), pygame.SRCALPHA)
            pygame.draw.rect(self.surf, (50, 180, 50), (0, 0, 40, 24), border_radius=4)
            pygame.draw.rect(self.surf, (20, 100, 20), (0, 0, 40, 24), 2, border_radius=4)
            pygame.draw.circle(self.surf, (200, 255, 200), (20, 12), 6)
        else:
            if FallingParticle.cached_shit_img is None:
                possible_paths = [
                    os.path.join(BASE_DIR, "assets", "gongyong", "shit.png"),
                    os.path.join(BASE_DIR, "asset", "gongyong", "shit.png"),
                    os.path.join(BASE_DIR, "assets", "shit.png"),
                    os.path.join(BASE_DIR, "asset", "shit.png"),
                    os.path.join(BASE_DIR, "shit.png")
                ]
                loaded = False
                for path in possible_paths:
                    if os.path.exists(path):
                        try:
                            raw_img = pygame.image.load(path).convert_alpha()
                            FallingParticle.cached_shit_img = pygame.transform.smoothscale(raw_img, (40, 40))
                            loaded = True
                            print(f"[粒子系统] 成功关联图片素材: {path}")
                            break
                        except:
                            pass

                if not loaded:
                    print(f"[粒子系统] 警告: 未检索到目标图片，已自动启用手绘几何图形兜底。")
                    FallingParticle.cached_shit_img = pygame.Surface((30, 30), pygame.SRCALPHA)
                    pygame.draw.circle(FallingParticle.cached_shit_img, (100, 50, 20), (15, 22), 10)
                    pygame.draw.circle(FallingParticle.cached_shit_img, (100, 50, 20), (10, 15), 8)
                    pygame.draw.circle(FallingParticle.cached_shit_img, (100, 50, 20), (20, 15), 8)
                    pygame.draw.circle(FallingParticle.cached_shit_img, (100, 50, 20), (15, 8), 6)

            self.surf = FallingParticle.cached_shit_img

    def update(self):
        self.y += self.vy
        self.x += self.vx
        self.angle += 3
        if self.y > HEIGHT + 50:
            self.active = False

    def draw(self, screen):
        rotated = pygame.transform.rotate(self.surf, self.angle)
        rect = rotated.get_rect(center=(int(self.x), int(self.y)))
        screen.blit(rotated, rect)


def get_cn_font(size):
    common_paths = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/System/Library/Fonts/STHeiti Light.ttc"
    ]
    for path in common_paths:
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def draw_button(surface, rect, text, font, base_color, hover_color, mouse_pos, mouse_click, disabled=False,
                active=False):
    is_hovered = rect.collidepoint(mouse_pos)
    color = (80, 80, 80) if disabled else (hover_color if is_hovered else base_color)
    if active: color = (255, 180, 0)
    pygame.draw.rect(surface, color, rect, border_radius=12)
    pygame.draw.rect(surface, (255, 255, 255), rect, width=2, border_radius=12)
    txt_color = (150, 150, 150) if disabled else (255, 255, 255)
    txt_surf = font.render(text, True, txt_color)
    surface.blit(txt_surf, (rect.centerx - txt_surf.get_width() // 2, rect.centery - txt_surf.get_height() // 2))
    return not disabled and is_hovered and mouse_click