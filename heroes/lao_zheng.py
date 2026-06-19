import pygame
import math
import random
import os
import sys

from settings import WIDTH, HEIGHT, GREEN, FONT
from core_classes import Agent, HIT_SOUNDS

# ==========================================
# 1. 资源加载与预处理区
# ==========================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ASSET_DIR = os.path.join(BASE_DIR, "assets", "laozheng")
SOUND_DIR = os.path.join(BASE_DIR, "sounds", "laozheng")

try:
    raw_icon = pygame.image.load(os.path.join(ASSET_DIR, "icon.jpg"))
    ICON_IMG = pygame.transform.smoothscale(raw_icon, (120, 120))
except:
    ICON_IMG = None

try:
    raw_pipe = pygame.image.load(os.path.join(ASSET_DIR, "gangguan.png"))
    GANGGUAN_IMG = pygame.transform.smoothscale(raw_pipe, (50, 280))
except:
    GANGGUAN_IMG = None

try:
    raw_coil = pygame.image.load(os.path.join(ASSET_DIR, "gangjuan.png"))
    GANGJUAN_IMG = pygame.transform.smoothscale(raw_coil, (400, 400))
except:
    GANGJUAN_IMG = None


def load_sound(filename):
    try:
        return pygame.mixer.Sound(os.path.join(SOUND_DIR, filename))
    except:
        return None


PUTONG_SND = load_sound("putong.mp3")
RUSH_SND = load_sound("rush.mp3")

ULT_SND = load_sound("ultimate.mp3")
try:
    ULT_LENGTH_FRAMES = int(ULT_SND.get_length() * 60)
except:
    ULT_LENGTH_FRAMES = 120

GANGJUAN_SND = load_sound("gangjuan.mp3")
GANGJUAN_LENGTH_FRAMES = 480


# ==========================================
# 2. 视觉特效区
# ==========================================
class HeavyShockwaveParticle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(8, 25)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.size = random.randint(8, 20)
        self.color = color
        self.life = 40

    def move(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.85
        self.vy *= 0.85
        self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            pygame.draw.rect(surface, self.color, (int(self.x), int(self.y), self.size, self.size))


# ==========================================
# 3. 牢正 英雄主体逻辑
# ==========================================
class LaoZheng(Agent):
    def __init__(self, x, y, color, faction):
        super().__init__(x, y, color, faction, image=ICON_IMG)

        self.atk = 0
        self.base_speed = 6
        self.knockback_immune = True

        # --- 核心修改：将充能效率降低至 0.5 (即所需总能量翻倍) ---
        self.ult_charge_rate = 0.5

        self.state = "NORMAL"

        self.skill_cooldown = 0
        self.damage_timer = 0

        self.is_swinging = False
        self.swing_timer = 0
        self.swing_max = 30
        self.base_swing_angle = 0

        self.is_dashing = False
        self.dash_timer = 0

        self.active_coils = []
        self.particles = []
        self.ult_timer = 0

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, value):
        if hasattr(self, '_hp') and value < self._hp:
            if self.state == "TIME_STOP":
                return

            self.hit_timer = 20
            if HIT_SOUNDS: random.choice(HIT_SOUNDS).play()
        self._hp = value

    def update_skill(self, bullet_list, agents=None):
        if agents is None: return

        if self.state != "TIME_STOP":
            # --- 核心修改：被动随时间的自然充能也受到 0.5 的效率压缩 ---
            if self.ult_charge < 100:
                self.ult_charge = min(100, self.ult_charge + 0.002 * self.ult_charge_rate)

            for coil in self.active_coils[:]:
                coil['y'] += coil['vy']
                coil['life'] -= 1

                for b in bullet_list[:]:
                    if b.active and b.owner_faction != self.faction:
                        dist_b = math.hypot(coil['x'] - b.x, coil['y'] - b.y)
                        if dist_b < coil['radius'] + b.radius:
                            b.active = False

                for a in agents:
                    if a.faction != self.faction and a.hp > 0:
                        if a not in coil['hit_targets']:
                            dist = math.hypot(coil['x'] - a.x, coil['y'] - a.y)
                            if dist < coil['radius'] + a.radius:
                                a.hp -= 500
                                coil['hit_targets'].add(a)
                                # 受到钢卷伤害的敌人也会按他们各自的充能效率获得部分能量
                                target_rate = getattr(a, 'ult_charge_rate', 1.0)
                                a.ult_charge = min(getattr(a, 'max_ult_charge', 100),
                                                   getattr(a, 'ult_charge', 0) + 20 * target_rate)

                if coil['life'] <= 0 or coil['y'] > HEIGHT + coil['radius']:
                    self.active_coils.remove(coil)

        if self.state == "NORMAL":
            if self.ult_charge >= 100:
                self.trigger_ultimate()
                return

            self.process_normal_combat(agents)

        elif self.state == "TIME_STOP":
            self.ult_timer -= 1
            for p in self.particles:
                p.move()

            if self.ult_timer <= 0:
                self.state = "NORMAL"
                self.spawn_gangjuan(agents)

    def trigger_ultimate(self):
        self.state = "TIME_STOP"
        self.ult_charge = 0
        self.ult_timer = ULT_LENGTH_FRAMES
        self.particles = [HeavyShockwaveParticle(self.x, self.y, self.color) for _ in range(60)]
        if ULT_SND: ULT_SND.play()

    def spawn_gangjuan(self, agents):
        if GANGJUAN_SND: GANGJUAN_SND.play()

        target_x = WIDTH // 2
        enemies = [a for a in agents if a.faction != self.faction and a.hp > 0]
        if enemies:
            target_x = random.choice(enemies).x

        start_y = -400
        end_y = HEIGHT + 400
        total_distance = end_y - start_y
        dynamic_vy = total_distance / GANGJUAN_LENGTH_FRAMES if GANGJUAN_LENGTH_FRAMES > 0 else 5

        self.active_coils.append({
            'x': target_x,
            'y': start_y,
            'vy': dynamic_vy,
            'radius': 200,
            'life': GANGJUAN_LENGTH_FRAMES,
            'hit_targets': set()
        })

    def process_normal_combat(self, agents):
        if self.is_dashing:
            self.dash_timer -= 1
            if self.dash_timer <= 0:
                self.is_dashing = False
                self.normalize_speed()
            else:
                enemies = [a for a in agents if a.faction != self.faction and a.hp > 0]
                hit_enemies = []

                for e in enemies:
                    if math.hypot(self.x - e.x, self.y - e.y) < self.radius + e.radius + 30:
                        hit_enemies.append(e)

                if hit_enemies:
                    if PUTONG_SND: PUTONG_SND.play()
                    self.is_dashing = False
                    self.normalize_speed()
                    self.damage_timer = 0
                    self.skill_cooldown = 120

                    self.is_swinging = True
                    self.swing_timer = self.swing_max

                    closest = min(hit_enemies, key=lambda e: math.hypot(self.x - e.x, self.y - e.y))
                    self.base_swing_angle = math.atan2(closest.y - self.y, closest.x - self.x)

                    for e in hit_enemies:
                        e.hp -= 80
                        # --- 核心修改：冲刺攻击充能受到压缩 ---
                        self.ult_charge = min(100, self.ult_charge + 15 * self.ult_charge_rate)

                        angle = math.atan2(e.y - self.y, e.x - self.x)
                        e.vx = math.cos(angle) * 45
                        e.vy = math.sin(angle) * 45
                        e.is_knocked_back = True
        else:
            self.damage_timer += 1
            if self.skill_cooldown > 0:
                self.skill_cooldown -= 1

            if self.is_swinging:
                self.swing_timer -= 1
                if self.swing_timer <= 0:
                    self.is_swinging = False

            if self.damage_timer >= 600 and self.skill_cooldown == 0:
                enemies = [a for a in agents if a.faction != self.faction and a.hp > 0]
                if enemies:
                    closest = min(enemies, key=lambda e: math.hypot(self.x - e.x, self.y - e.y))
                    angle = math.atan2(closest.y - self.y, closest.x - self.x)

                    self.vx = math.cos(angle) * 22
                    self.vy = math.sin(angle) * 22
                    self.is_dashing = True
                    self.dash_timer = 40
                    self.damage_timer = 0
                    if RUSH_SND: RUSH_SND.play()

            else:
                if self.skill_cooldown == 0 and not self.is_swinging:
                    enemies = [a for a in agents if a.faction != self.faction and a.hp > 0]
                    hit_enemies = []

                    for e in enemies:
                        if math.hypot(self.x - e.x, self.y - e.y) < self.radius + e.radius + 160:
                            hit_enemies.append(e)

                    if hit_enemies:
                        if PUTONG_SND: PUTONG_SND.play()
                        self.damage_timer = 0
                        self.skill_cooldown = 120

                        self.is_swinging = True
                        self.swing_timer = self.swing_max

                        closest = min(hit_enemies, key=lambda e: math.hypot(self.x - e.x, self.y - e.y))
                        self.base_swing_angle = math.atan2(closest.y - self.y, closest.x - self.x)

                        for e in hit_enemies:
                            e.hp -= 40
                            # --- 核心修改：挥管攻击充能受到压缩 ---
                            self.ult_charge = min(100, self.ult_charge + 8 * self.ult_charge_rate)

                            angle = math.atan2(e.y - self.y, e.x - self.x)
                            e.vx = math.cos(angle) * 35
                            e.vy = math.sin(angle) * 35
                            e.is_knocked_back = True

                        self.normalize_speed()

    def normalize_speed(self):
        mag = math.hypot(self.vx, self.vy)
        if mag > 0:
            self.vx = (self.vx / mag) * self.base_speed
            self.vy = (self.vy / mag) * self.base_speed

    def draw(self, surface):
        super().draw(surface)

        if self.state == "TIME_STOP":
            for p in self.particles:
                p.draw(surface)

        if self.is_swinging and GANGGUAN_IMG:
            progress = (self.swing_max - self.swing_timer) / self.swing_max
            current_rad = self.base_swing_angle - math.radians(60) + (progress * math.radians(120))
            rotated_pipe = pygame.transform.rotate(GANGGUAN_IMG, -math.degrees(current_rad) - 90)
            offset_x = self.x + math.cos(current_rad) * (self.radius + 60)
            offset_y = self.y + math.sin(current_rad) * (self.radius + 60)
            rect = rotated_pipe.get_rect(center=(int(offset_x), int(offset_y)))
            surface.blit(rotated_pipe, rect)

        for coil in self.active_coils:
            if GANGJUAN_IMG:
                rect = GANGJUAN_IMG.get_rect(center=(int(coil['x']), int(coil['y'])))
                surface.blit(GANGJUAN_IMG, rect)
            else:
                pygame.draw.circle(surface, (150, 150, 150), (int(coil['x']), int(coil['y'])), coil['radius'])


# ==========================================
# 4. 图鉴数据注册
# ==========================================
from almanac import register_almanac_entry

laozheng_stats = {
    "普攻伤害": "40",
    "冲刺伤害": "80",
    "基础移速": "6",
    "特殊属性": "霸体 (完全免疫击退)",
    "大招充能": "较慢"
}

laozheng_mechanics = (
    "【普攻·钢管横扫】\n"
    "每隔2秒，牢正会挥舞钢管对周围判定范围内的所有敌人造成40点范围AOE伤害与疯狂的击退效果。每扫中一名敌人，能回复少量大招能量。\n\n"
    "【被动·狂暴冲锋】\n"
    "如果在战场上超过10秒未能对敌人造成伤害，牢正将被激怒，锁定最近的敌人发起超高速冲锋。撞击时对范围内所有敌人造成80点范围伤害与强力散射击退，并回复一定大招能量。\n\n"
    "【终极技能·天降钢卷】\n"
    "在敌人头顶召唤一个直径高达400像素的超巨大钢卷自上而下碾压战场。坠落的钢卷在场上存在4秒，对触碰者造成500点毁灭性打击，并可以碾碎所有触碰到的敌方飞行弹幕道具！\n\n"
)

laozheng_lore = (
    "在离开了孟加拉国第一快递公司和他心爱的健身房后，牢正踏上了寻找力量的征途，并得到了指示：“一定不好”。在这句话的指引下，牢正发现，好像还是钢卷和钢管更有力气一点。"
)

register_almanac_entry(
    char_id="LaoZheng",
    name="牢正",
    icon=ICON_IMG,
    stats=laozheng_stats,
    mechanics=laozheng_mechanics,
    lore=laozheng_lore
)