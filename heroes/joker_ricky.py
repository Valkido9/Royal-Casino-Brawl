import pygame
import math
import random
import os
import sys  # <--- 新增导入 sys

from settings import WIDTH, HEIGHT
from core_classes import Agent, Bullet

# ==========================================
# 1. 资源加载与预处理区 (防弹路径版)
# ==========================================

# --- 核心修复：引入 PyInstaller 的防弹路径判断 ---
if getattr(sys, 'frozen', False):
    # 如果是被打包成了 exe，直接获取 exe 文件所在的根目录
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 源码模式下：退两层到根目录
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 拼接出绝对路径
ASSET_DIR = os.path.join(BASE_DIR, "assets", "jockerrickey")
SOUND_DIR = os.path.join(BASE_DIR, "sounds", "joker_rickey")

# 打印一下路径，确保找对了地方（你可以看控制台输出）
print(f"正在尝试从以下路径加载资源:\n图片: {ASSET_DIR}\n音效: {SOUND_DIR}")

# --- 头像与子弹贴图动态自适应缩放 ---
try:
    icon_path = os.path.join(ASSET_DIR, "icon.jpg")
    raw_icon = pygame.image.load(icon_path)
    ICON_IMG = pygame.transform.smoothscale(raw_icon, (120, 120))
except Exception as e:
    print(f"提示: 未能加载头像贴图，报错: {e}")
    ICON_IMG = None

try:
    bullet_path = os.path.join(ASSET_DIR, "bullet.png")
    raw_bullet = pygame.image.load(bullet_path)
    BULLET_IMG = pygame.transform.smoothscale(raw_bullet, (60, 60))
except Exception as e:
    print(f"提示: 未能加载子弹贴图，报错: {e}")
    BULLET_IMG = pygame.Surface((60, 60), pygame.SRCALPHA)
    pygame.draw.circle(BULLET_IMG, (255, 255, 0), (30, 30), 30)

# --- 常规音效库加载 ---
NORMAL_SOUND_FILES = [
    "aminuos.mp3", "duang.mp3", "hachimi.mp3",
    "hhhh.mp3", "manbo.mp3", "ohyeah.mp3", "wow.mp3"
]

JOKER_SOUNDS = []
for snd_name in NORMAL_SOUND_FILES:
    file_path = os.path.join(SOUND_DIR, snd_name)
    try:
        JOKER_SOUNDS.append(pygame.mixer.Sound(file_path))
    except Exception as e:
        print(f"音效加载失败: {file_path}")

# --- 终极大招音效加载 ---
try:
    ULTIMATE_SOUND = pygame.mixer.Sound(os.path.join(SOUND_DIR, "ultimate.mp3"))
    ULTIMATE_LENGTH_FRAMES = int((ULTIMATE_SOUND.get_length() + 0.5) * 60)
except Exception as e:
    print(f"终极音效加载失败，使用默认时停长度。")
    ULTIMATE_SOUND = None
    ULTIMATE_LENGTH_FRAMES = 150


# ==========================================
# 2. 视觉特效与专属子弹类
# ==========================================

class ExplosionParticle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        # 生成一个向四周随机散开的矢量
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 12)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.size = random.randint(4, 10)
        self.color = color
        self.life = 60  # 粒子存活 60 帧 (1秒)

    def move(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            # 绘制像素风格的小方块
            pygame.draw.rect(surface, self.color, (int(self.x), int(self.y), self.size, self.size))


class JokerBullet(Bullet):
    def __init__(self, x, y, vx, vy, owner_faction, damage, image, infinite_bounce=False, life=None):
        super().__init__(x, y, vx, vy, owner_faction, damage, image)
        self.radius = 30
        self.bounce_count = 0
        self.infinite_bounce = infinite_bounce
        self.life = life

    def move(self):
        self.x += self.vx
        self.y += self.vy

        if self.life is not None:
            self.life -= 1
            if self.life <= 0:
                self.active = False
                return

        bounced = False
        if self.x - self.radius < 0 or self.x + self.radius > WIDTH:
            self.vx *= -1
            self.x = max(self.radius, min(WIDTH - self.radius, self.x))
            bounced = True

        if self.y - self.radius < 0 or self.y + self.radius > HEIGHT:
            self.vy *= -1
            self.y = max(self.radius, min(HEIGHT - self.radius, self.y))
            bounced = True

        # 如果不是无限反弹，则计算反弹次数（反弹3次，第4次碰到墙壁销毁）
        if bounced and not self.infinite_bounce:
            self.bounce_count += 1
            if self.bounce_count > 3:
                self.active = False


# ==========================================
# 3. JokerRicky 英雄主体逻辑
# ==========================================

class JokerRicky(Agent):
    def __init__(self, x, y, color, faction):
        super().__init__(x, y, color, faction, image=ICON_IMG)

        self.atk = 32
        self.bullet_speed = 12
        self.base_speed = 6

        # ---------------- 状态机与技能参数 ----------------
        self.state = "NORMAL"  # 状态池: NORMAL, TIME_STOP, RAMPAGE, EXHAUSTED

        # 小技能参数
        self.skill_cooldown = 300  # 大循环冷却 5 秒
        self.burst_shots_left = 0
        self.burst_interval = 72  # 每发子弹间隔 1.2 秒 (72帧)
        self.burst_timer = 0

        # 大招专属控制变量
        self.particles = []
        self.ult_timer = 0
        self.rampage_sound_pool = []

    def update_skill(self, bullet_list, agents=None):
        # 【被动】：随时间缓慢推移自动充能，每帧0.02，约80秒满充 (受伤会额外加充能)
        if self.ult_charge < 100:
            self.ult_charge = min(100, self.ult_charge + 0.02)

        # ---------------- 状态 1: 常态 ----------------
        if self.state == "NORMAL":
            if self.ult_charge >= 100:
                self.trigger_ultimate()
                return

            if self.skill_cooldown > 0:
                self.skill_cooldown -= 1
            elif self.burst_shots_left == 0:
                self.burst_shots_left = 3
                self.skill_cooldown = 300
                self.fire_bullet(bullet_list, infinite=False)
                self.burst_shots_left -= 1
                self.burst_timer = self.burst_interval

            if self.burst_shots_left > 0:
                if self.burst_timer > 0:
                    self.burst_timer -= 1
                else:
                    self.fire_bullet(bullet_list, infinite=False)
                    self.burst_shots_left -= 1
                    self.burst_timer = self.burst_interval

        # ---------------- 状态 2: 时停装逼 ----------------
        elif self.state == "TIME_STOP":
            self.ult_timer -= 1
            for p in self.particles:
                p.move()

            if self.ult_timer <= 0:
                self.state = "RAMPAGE"
                self.burst_timer = 0
                self.rampage_sound_pool = JOKER_SOUNDS * 3
                random.shuffle(self.rampage_sound_pool)
                self.boost_speed(5.0)

        # ---------------- 状态 3: 暴走弹幕 ----------------
        elif self.state == "RAMPAGE":
            if self.burst_timer > 0:
                self.burst_timer -= 1
            else:
                if len(self.rampage_sound_pool) > 0:
                    snd = self.rampage_sound_pool.pop()
                    snd.play()

                    dynamic_life = len(self.rampage_sound_pool) * 10 + 600

                    self.fire_bullet(bullet_list, infinite=True, silent=True, life=dynamic_life)
                    self.burst_timer = 10
                else:
                    self.state = "EXHAUSTED"
                    self.ult_timer = 600  # 虚弱时间(真实时间5秒对应的600帧)
                    self.boost_speed(1.0)

        # ---------------- 状态 4: 虚弱期 ----------------
        elif self.state == "EXHAUSTED":
            self.ult_timer -= 1
            if self.ult_timer <= 0:
                self.state = "NORMAL"
                self.ult_charge = 0
                self.skill_cooldown = 600

    def trigger_ultimate(self):
        self.state = "TIME_STOP"
        self.ult_charge = 0
        self.ult_timer = ULTIMATE_LENGTH_FRAMES

        self.particles = [ExplosionParticle(self.x, self.y, self.color) for _ in range(50)]

        if ULTIMATE_SOUND:
            ULTIMATE_SOUND.play()

    def boost_speed(self, multiplier):
        speed_mag = math.hypot(self.vx, self.vy)
        if speed_mag > 0:
            new_mag = self.base_speed * multiplier
            self.vx = (self.vx / speed_mag) * new_mag
            self.vy = (self.vy / speed_mag) * new_mag

    def fire_bullet(self, bullet_list, infinite=False, silent=False, life=None):
        if not silent and JOKER_SOUNDS:
            random.choice(JOKER_SOUNDS).play()

        speed_mag = math.hypot(self.vx, self.vy)
        if speed_mag == 0:
            dx, dy = 1, 0
        else:
            dx, dy = self.vx / speed_mag, self.vy / speed_mag

        spread_angle = math.radians(random.uniform(-15, 15))
        cos_a = math.cos(spread_angle)
        sin_a = math.sin(spread_angle)

        final_vx = (dx * cos_a - dy * sin_a) * self.bullet_speed
        final_vy = (dx * sin_a + dy * cos_a) * self.bullet_speed

        new_bullet = JokerBullet(
            self.x, self.y,
            final_vx, final_vy,
            self.faction, self.atk,
            BULLET_IMG,
            infinite_bounce=infinite,
            life=life
        )
        bullet_list.append(new_bullet)

    def draw(self, surface):
        super().draw(surface)

        if self.state == "TIME_STOP":
            for p in self.particles:
                p.draw(surface)

# ==========================================
# 4. 图鉴数据注册
# ==========================================
from almanac import register_almanac_entry

joker_lore = (
    "在学习了过多的电力电子技术、材料科学基础、物理化学和热工基础之后，JockerRickey终于来到了疯狂的边缘。他发现，只有曼波才能拯救全人类，曼波爱世人！"
)

joker_stats = {
    "单发伤害": "32",
    "基础移速": "6",
    "弹道速度": "12",
    "反弹次数": "3次 (常态) / 无限 (大招)",
    "大招充能": "极慢 (约83秒)"
}

joker_mechanics = (
    "【普攻·三连点射】\n"
    "每5秒进行一轮三连发点射，每发间隔1.2秒。射出的子弹可以在墙壁间弹射3次，第4次触墙才会销毁。\n\n"
    "【终极技能·曼波暴走！】\n"
    "移速狂飙至原本的5倍，并以极快的频率向全场倾泻21发“无限反弹”的暴走弹幕。暴走结束后，他会进入长达5秒的「虚弱期」，期间移速恢复正常且完全无法攻击。这批弹幕会一直在场上弹射直到他的虚弱期结束。\n\n"
)

# 注册进入图鉴系统
register_almanac_entry(
    char_id="JokerRicky",
    name="曼波舞王",
    icon=ICON_IMG,
    stats=joker_stats,
    mechanics=joker_mechanics,
    lore=joker_lore
)