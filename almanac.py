import pygame
import os
import sys

try:
    from settings import WIDTH, HEIGHT
except ImportError:
    WIDTH, HEIGHT = 1920, 1080

from ui_components import draw_button

# ==========================================
# 图鉴数据注册表
# ==========================================
ALMANAC_DATA = {}


def register_almanac_entry(char_id, name, icon, stats, mechanics, lore):
    ALMANAC_DATA[char_id] = {
        "name": name,
        "icon": icon,
        "stats": stats,
        "mechanics": mechanics,
        "lore": lore
    }


# ==========================================
# 图鉴 UI 渲染系统
# ==========================================
class AlmanacUI:
    def __init__(self, app):
        self.app = app
        self.selected_id = None
        self.scroll_y = 0  # 右侧面板滚动偏移量

        # 布局坐标：左侧网格 (800宽) | 右侧详情 (950宽)
        self.grid_rect = pygame.Rect(50, 120, 800, 800)
        self.detail_rect = pygame.Rect(900, 120, 950, 800)

    def draw_wrapped_text(self, surface, text, font, color, rect, y_offset_start=0):
        if not text: return 0
        words = text.split('\n')
        y_offset = rect.y + y_offset_start
        for line in words:
            chars = list(line)
            current_line = ""
            for char in chars:
                test_line = current_line + char
                if font.size(test_line)[0] < rect.width:
                    current_line = test_line
                else:
                    surf = font.render(current_line, True, color)
                    surface.blit(surf, (rect.x, y_offset))
                    y_offset += font.get_linesize() + 10
                    current_line = char
            if current_line:
                surf = font.render(current_line, True, color)
                surface.blit(surf, (rect.x, y_offset))
                y_offset += font.get_linesize() + 10
        return y_offset - (rect.y + y_offset_start)

    def handle_scroll(self, event):
        if event.type == pygame.MOUSEWHEEL:
            # 只有鼠标在右侧面板内时才能滚动
            if self.detail_rect.collidepoint(self.app.mouse_pos):
                self.scroll_y += event.y * 40

    def render(self):
        surf = self.app.logical_surface
        surf.fill((20, 25, 35))

        title = self.app.font_huge.render("孟加拉国皇家情报局", True, (255, 215, 0))
        surf.blit(title, (WIDTH // 2 - title.get_width() // 2, 30))

        # ---------------- 左侧：头像网格 ----------------
        pygame.draw.rect(surf, (35, 45, 60), self.grid_rect, border_radius=15)
        pygame.draw.rect(surf, (100, 120, 150), self.grid_rect, width=3, border_radius=15)

        if self.selected_id is None and ALMANAC_DATA:
            self.selected_id = list(ALMANAC_DATA.keys())[0]

        icon_size = 120
        padding = 25
        cols = self.grid_rect.width // (icon_size + padding)
        start_x = self.grid_rect.x + 30
        start_y = self.grid_rect.y + 30

        for i, (cid, data) in enumerate(ALMANAC_DATA.items()):
            row = i // cols
            col = i % cols
            ix = start_x + col * (icon_size + padding)
            iy = start_y + row * (icon_size + padding)
            icon_rect = pygame.Rect(ix, iy, icon_size, icon_size)

            if self.selected_id == cid:
                pygame.draw.rect(surf, (255, 215, 0), icon_rect.inflate(16, 16), border_radius=12)
                pygame.draw.rect(surf, (255, 255, 255), icon_rect.inflate(6, 6), border_radius=10)

            if data["icon"]:
                scaled_icon = pygame.transform.smoothscale(data["icon"], (icon_size, icon_size))
                surf.blit(scaled_icon, icon_rect)
            else:
                pygame.draw.rect(surf, (80, 80, 80), icon_rect, border_radius=10)

            if self.app.mouse_click and icon_rect.collidepoint(self.app.mouse_pos):
                if self.selected_id != cid:
                    self.selected_id = cid
                    self.scroll_y = 0  # 切换角色时重置滚动条
                if hasattr(self.app, 'sfx_payment') and self.app.sfx_payment:
                    self.app.sfx_payment.play()

        # ---------------- 右侧：详情面板 ----------------
        pygame.draw.rect(surf, (35, 45, 60), self.detail_rect, border_radius=15)
        pygame.draw.rect(surf, (100, 120, 150), self.detail_rect, width=3, border_radius=15)

        if self.selected_id and self.selected_id in ALMANAC_DATA:
            # 创建一个用于裁剪滚动的内部 Surface
            clip_surface = pygame.Surface((self.detail_rect.width - 20, self.detail_rect.height - 20), pygame.SRCALPHA)
            clip_surface.fill((0, 0, 0, 0))  # 透明背景

            char_data = ALMANAC_DATA[self.selected_id]
            dx, dy = 10, 10  # 相对 clip_surface 的坐标
            current_y = dy + self.scroll_y

            # 1. 大头像与名称
            if char_data["icon"]:
                large_icon = pygame.transform.smoothscale(char_data["icon"], (180, 180))
                pygame.draw.rect(clip_surface, (200, 200, 200), pygame.Rect(dx - 5, current_y - 5, 190, 190),
                                 border_radius=10)
                clip_surface.blit(large_icon, (dx, current_y))

            name_surf = self.app.font_huge.render(char_data["name"], True, (255, 255, 255))
            clip_surface.blit(name_surf, (dx + 220, current_y + 20))

            current_y += 210

            # 4. 背景故事
            lore_title = self.app.font_large.render("【背景故事】", True, (150, 255, 150))
            clip_surface.blit(lore_title, (dx, current_y))
            current_y += 50

            lore_rect = pygame.Rect(dx + 20, 0, clip_surface.get_width() - 40, 1000)
            text_height = self.draw_wrapped_text(clip_surface, char_data["lore"], self.app.font_normal, (180, 180, 180),
                                                 lore_rect, current_y)
            current_y += text_height + 40

            # 2. 基础面板属性
            stats_title = self.app.font_large.render("【基础面板】", True, (150, 200, 255))
            clip_surface.blit(stats_title, (dx, current_y))
            current_y += 50

            for stat_name, stat_val in char_data["stats"].items():
                s_txt = self.app.font_normal.render(f"◆ {stat_name}: {stat_val}", True, (220, 220, 220))
                clip_surface.blit(s_txt, (dx + 20, current_y))
                current_y += 45

            current_y += 20

            # 3. 战斗机制
            mech_title = self.app.font_large.render("【战斗机制】", True, (255, 150, 150))
            clip_surface.blit(mech_title, (dx, current_y))
            current_y += 50

            mech_rect = pygame.Rect(dx + 20, 0, clip_surface.get_width() - 40, 1000)
            text_height = self.draw_wrapped_text(clip_surface, char_data["mechanics"], self.app.font_normal,
                                                 (200, 200, 200), mech_rect, current_y)
            current_y += text_height + 40



            # 限制滚动范围
            max_scroll = 0
            min_scroll = min(0, -(current_y - self.scroll_y - self.detail_rect.height + 40))
            self.scroll_y = max(min_scroll, min(self.scroll_y, max_scroll))

            # 将裁剪的 Surface 贴回主屏幕
            surf.blit(clip_surface, (self.detail_rect.x + 10, self.detail_rect.y + 10))

        # ---------------- 退出按钮 ----------------
        btn_back = pygame.Rect(50, HEIGHT - 100, 200, 60)
        if draw_button(surf, btn_back, "返回主菜单", self.app.font_normal, (150, 50, 50), (200, 80, 80),
                       self.app.mouse_pos, self.app.mouse_click):
            self.app.game_state = "START_SCREEN"


# 维护单例与滚轮事件分发
almanac_ui_instance = None


def get_almanac_instance(app):
    global almanac_ui_instance
    if almanac_ui_instance is None or almanac_ui_instance.app != app:
        almanac_ui_instance = AlmanacUI(app)
    return almanac_ui_instance


def render_almanac(app):
    get_almanac_instance(app).render()


def handle_almanac_event(app, event):
    if app.game_state == "ALMANAC":
        get_almanac_instance(app).handle_scroll(event)