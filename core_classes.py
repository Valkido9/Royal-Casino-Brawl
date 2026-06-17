import pygame
import math
import random
import os
from settings import WIDTH, HEIGHT, GREEN, FONT
from ui_components import get_cn_font  # 引入字体用于渲染猎手称号


# ==========================================
# 新增：RGB 霓虹色彩生成器 (用于终极猎手)
# ==========================================
def get_rainbow_color(current_time, speed=0.002):
    # 【修改】：默认速度调整为平滑的 0.002，避免光敏性频闪
    r = int((math.sin(current_time * speed) + 1) * 127.5)
    g = int((math.sin(current_time * speed + 2) + 1) * 127.5)
    b = int((math.sin(current_time * speed + 4) + 1) * 127.5)
    return (r, g, b)


# ==========================================
# 1. 公共受击资源加载 (gongyong)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GONGYONG_DIR = os.path.join(BASE_DIR, "sounds", "gongyong")

HIT_SOUNDS = []
# 自动检测并加载 shouji1, 2, 3，同时兼容 mp3 和 wav 格式
for ext in ['.mp3', '.wav']:
    for i in range(1, 4):
        try:
            file_path = os.path.join(GONGYONG_DIR, f"shouji{i}{ext}")
            if os.path.exists(file_path):
                HIT_SOUNDS.append(pygame.mixer.Sound(file_path))
        except Exception as e:
            pass

print(f"成功加载了 {len(HIT_SOUNDS)} 个受击音效！")


# ==========================================
# 2. 基础实体类 (所有英雄的基础)
# ==========================================
class Agent:
    def __init__(self, x, y, color, faction, image=None):
        self.x = x
        self.y = y
        self.radius = 60
        self.color = color
        self.faction = faction
        self.image = image

        self.max_hp = 1000
        # 将原本的 self.hp 改为内部私有变量 self._hp
        self._hp = self.max_hp

        self.atk = 20
        self.attack_cooldown = 0
        self.ult_charge = 0
        self.max_ult_charge = 100

        # 受击特效状态计时器
        self.hit_timer = 0

        self.knockback_immune = False
        self.base_speed = 6
        self.is_knocked_back = False

        # --- 新增：系统模式联动标记 ---
        self.out_of_zone = False  # 毒圈判定
        self.is_hunter = False  # 终极猎手判定

        angle = random.uniform(0, 2 * math.pi)
        self.vx = math.cos(angle) * self.base_speed
        self.vy = math.sin(angle) * self.base_speed

    # ----------------------------------------------------
    # 黑科技：属性拦截器
    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, value):
        if hasattr(self, '_hp') and value < self._hp:
            # 20 帧，适配 120 帧率
            self.hit_timer = 20
            if HIT_SOUNDS:
                random.choice(HIT_SOUNDS).play()
        self._hp = value

    # ----------------------------------------------------

    def move(self):
        self.x += self.vx
        self.y += self.vy

        hit_wall = False
        if self.x - self.radius < 0 or self.x + self.radius > WIDTH:
            self.vx *= -1
            self.x = max(self.radius, min(WIDTH - self.radius, self.x))
            hit_wall = True

        if self.y - self.radius < 0 or self.y + self.radius > HEIGHT:
            self.vy *= -1
            self.y = max(self.radius, min(HEIGHT - self.radius, self.y))
            hit_wall = True

        if hit_wall and getattr(self, 'is_knocked_back', False):
            self.is_knocked_back = False
            current_speed = math.hypot(self.vx, self.vy)
            if current_speed > 0:
                self.vx = (self.vx / current_speed) * self.base_speed
                self.vy = (self.vy / current_speed) * self.base_speed

    def update_cooldown(self):
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        # 每帧递减受击闪烁时间
        if self.hit_timer > 0:
            self.hit_timer -= 1

    def draw(self, surface):
        # ==========================================
        # 视觉核心修改区
        # ==========================================

        # --- 1. 绘制底层阵营辨认圆环 (在角色下方) ---
        ring_color = (255, 100, 100, 100) if self.faction == "Faction_A" else (100, 100, 255, 100)
        ring_surf = pygame.Surface((self.radius * 2 + 20, self.radius * 2 + 20), pygame.SRCALPHA)
        pygame.draw.circle(ring_surf, ring_color, (self.radius + 10, self.radius + 10), self.radius + 10, width=8)
        surface.blit(ring_surf, (self.x - self.radius - 10, self.y - self.radius - 10))

        # --- 2. 死亡/尸体判定 ---
        if self.hp <= 0:
            sfx_surf = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
            r, g, b = self.color[:3]  # 提取英雄的主题色
            # 画一个大范围的半透明血迹/残骸底色
            pygame.draw.circle(sfx_surf, (r, g, b, 50), (self.radius * 2, self.radius * 2), self.radius * 2)
            # 随机散落几个深色碎块
            for _ in range(5):
                off_x = random.randint(-self.radius, self.radius)
                off_y = random.randint(-self.radius, self.radius)
                s_radius = random.randint(3, 8)
                pygame.draw.circle(sfx_surf, (r, g, b, 120), (self.radius * 2 + off_x, self.radius * 2 + off_y),
                                   s_radius)
            surface.blit(sfx_surf, (self.x - self.radius * 2, self.y - self.radius * 2))

            # 【核心逻辑】：死了就不继续往下画贴图和血条了，直接返回！
            return

        # --- 3. 正常存活时的绘制 (贴图、闪红、毒圈红框) ---
        if self.image:
            rect = self.image.get_rect(center=(int(self.x), int(self.y)))
            surface.blit(self.image, rect)

            # 渲染图像时的红盖特效
            if self.hit_timer > 0:
                flash_surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(flash_surf, (255, 0, 0, 150), (self.radius, self.radius), self.radius)
                surface.blit(flash_surf, rect.topleft)
        else:
            current_color = (255, 50, 50) if self.hit_timer > 0 else self.color
            pygame.draw.circle(surface, current_color, (int(self.x), int(self.y)), self.radius)

        # --- 新增：毒圈边界高危红框指示器 ---
        if self.out_of_zone:
            pygame.draw.circle(surface, (255, 0, 0), (int(self.x), int(self.y)), self.radius + 5, width=3)

        # --- 4. 绘制 UI (血条与能量条) ---
        hp_ratio = max(0, self.hp / self.max_hp)
        bar_width = self.radius * 1.8
        bar_height = 6
        bar_x = self.x - bar_width / 2
        bar_y = self.y - self.radius - 12

        # 画血条
        pygame.draw.rect(surface, (80, 80, 80), (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(surface, GREEN, (bar_x, bar_y, bar_width * hp_ratio, bar_height))

        # 画具体血量数值
        hp_text = FONT.render(f"{int(self.hp)}", True, (255, 255, 255))
        text_rect = hp_text.get_rect(center=(self.x, bar_y - 10))
        surface.blit(hp_text, text_rect)

        # 画大招能量条 (补充功能)
        pygame.draw.rect(surface, (100, 100, 100), (bar_x, bar_y - 7, bar_width, 4))
        ult_ratio = min(1.0, max(0, self.ult_charge / self.max_ult_charge))
        pygame.draw.rect(surface, (255, 215, 0), (bar_x, bar_y - 7, bar_width * ult_ratio, 4))

        # --- 5. 修改：终极猎手专属 RGB 发光称号 (平滑呼吸变色) ---
        if getattr(self, 'is_hunter', False):
            hunter_font = get_cn_font(24)
            # 【核心修改】：将速度从 0.3 降低到 0.002，实现极为平稳流畅的呼吸变色
            rgb_color = get_rainbow_color(pygame.time.get_ticks(), 0.002)
            hunter_text_surf = hunter_font.render("★ 终极猎手 ★", True, rgb_color)

            # 渲染在血量数字的正上方
            surface.blit(hunter_text_surf, (self.x - hunter_text_surf.get_width() // 2, bar_y - 45))


# ==========================================
# 4. 基础子弹类
# ==========================================
class Bullet:
    def __init__(self, x, y, vx, vy, owner_faction, damage, image):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = 12
        self.owner_faction = owner_faction
        self.damage = damage
        self.image = image
        self.active = True

    def move(self):
        self.x += self.vx
        self.y += self.vy

        if (self.x - self.radius < 0 or self.x + self.radius > WIDTH or
                self.y - self.radius < 0 or self.y + self.radius > HEIGHT):
            self.active = False

    def draw(self, surface):
        rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(self.image, rect)