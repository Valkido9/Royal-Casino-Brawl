import pygame
import math
import random
import os
import sys

# --- 引入全局帧率 FPS ---
from settings import WIDTH, HEIGHT, RED, BLUE, FPS
from core_classes import Agent, HIT_SOUNDS
from ui_components import get_cn_font

# ==========================================
# 1. 资源加载与预处理区
# ==========================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ASSET_DIR = os.path.join(BASE_DIR, "assets", "mao")
SOUND_DIR = os.path.join(BASE_DIR, "sounds", "mao")


def load_img(filename, size):
    try:
        img_path = os.path.join(ASSET_DIR, filename)
        raw_img = pygame.image.load(img_path)
        return pygame.transform.smoothscale(raw_img, size)
    except Exception as e:
        print(f"Mao 加载图片失败: {filename}，错误: {e}")
        return None


ICON_MAO = load_img("icon_mao.jpg", (120, 120))
ICON_SLEEP = load_img("icon_sleep.jpg", (120, 120))
IMG_AK47 = load_img("ak47.png", (100, 40))
IMG_EXPERIMENT = load_img("experiment.png", (140, 140))
IMG_HOMEWORK = load_img("homework.png", (140, 140))
IMG_SHIP = load_img("ship.png", (360, 360))
IMG_AMMO = load_img("ammo.png", (45, 15))


def load_snd(filename):
    try:
        return pygame.mixer.Sound(os.path.join(SOUND_DIR, filename))
    except:
        return None


SLEEP_SND = load_snd("sleep.mp3")
BATTLEFIELD_SND = load_snd("battlefield.mp3")
EXPERIMENT_SND = load_snd("experiment.mp3")
HOMEWORK_SND = load_snd("homework.mp3")
AMMO_SND = load_snd("ammo.mp3")
ULT_SND = load_snd("ultimate.mp3")
SHIP_SND = load_snd("ship.mp3")

# --- 修改：将大招的时停前摇固定为 2.5 秒（减半） ---
ULT_START_FRAMES = int(3 * FPS)

try:
    SHIP_RUN_FRAMES = int(SHIP_SND.get_length() * FPS)
except:
    SHIP_RUN_FRAMES = FPS * 10


# ==========================================
# 2. 专属弹幕类：ZZZ与AK子弹
# ==========================================
class MaoBullet:
    _zzz_surf = None

    def __init__(self, x, y, vx, vy, b_type, owner_faction):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.b_type = b_type
        self.owner_faction = owner_faction
        self.active = True
        self.is_boosted = False

        if self.b_type == "ZZZ":
            self.radius = 45
            self.damage = 20
            self.life = 240

            if MaoBullet._zzz_surf is None:
                font = get_cn_font(60)
                MaoBullet._zzz_surf = font.render("Zzz", True, (200, 200, 255))

        elif self.b_type == "AK47":
            self.radius = 16
            self.damage = 85
            self.life = 120

    def move(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.life <= 0:
            self.active = False

        if self.b_type == "ZZZ":
            self.vx += random.uniform(-0.5, 0.5)
            self.vy += random.uniform(-0.5, 0.5)
            speed = math.hypot(self.vx, self.vy)
            if speed > 10:
                self.vx = (self.vx / speed) * 10
                self.vy = (self.vy / speed) * 10

    def draw(self, surface):
        if self.b_type == "ZZZ":
            if MaoBullet._zzz_surf:
                surface.blit(MaoBullet._zzz_surf, (self.x - 30, self.y - 30))
        elif self.b_type == "AK47":
            if IMG_AMMO:
                angle = math.degrees(math.atan2(-self.vy, self.vx))
                rotated_ammo = pygame.transform.rotate(IMG_AMMO, angle)
                rect = rotated_ammo.get_rect(center=(int(self.x), int(self.y)))
                surface.blit(rotated_ammo, rect)
            else:
                pygame.draw.circle(surface, (255, 200, 0), (int(self.x), int(self.y)), self.radius)
                pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), self.radius - 3)


# ==========================================
# 3. 英雄主体：猫
# ==========================================
class Mao(Agent):
    def __init__(self, x, y, color, faction):
        super().__init__(x, y, color, faction, image=ICON_MAO)

        self.atk = 0
        self.base_speed = 7
        self.knockback_immune = False
        self.reflects_attacker = False

        self.state = "ROULETTE"
        self.roulette_timer = 300
        self.roulette_options = ["SLEEP", "BATTLEFIELD", "EXPERIMENT", "HOMEWORK"]
        self.roulette_labels = ["猫睡觉", "猫打战地", "猫做实验", "猫写作业"]
        self.current_option_idx = 0
        self.roulette_angle = 0

        self.action_timer = 0
        self.ak_bullets = 0

        self.ult_start_timer = 0
        self.ult_timer = 0
        self.ship_hit_cd = {}

        self.sub_action = None
        self.sub_action_timer = 0
        self.sub_step_timer = 0

        self.ult_invincible_timer = 0

        self._real_ult_charge = 0

    def stop_sounds(self):
        for snd in [SLEEP_SND, BATTLEFIELD_SND, EXPERIMENT_SND, HOMEWORK_SND, ULT_SND, SHIP_SND]:
            if snd: snd.stop()

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, value):
        if hasattr(self, '_hp') and value < self._hp:
            if self.state == "TIME_STOP":
                return

            if self.state == "ULTIMATE" and self.ult_invincible_timer > 0:
                return

            damage = self._hp - value
            value = self._hp - damage

            if damage > 0:
                self.hit_timer = 20
                if self.state == "ULTIMATE":
                    self.ult_invincible_timer = 5
                if HIT_SOUNDS: random.choice(HIT_SOUNDS).play()

        if hasattr(self, '_hp') and value <= 0 and self._hp > 0:
            self.stop_sounds()

        self._hp = value

    @property
    def ult_charge(self):
        return self._real_ult_charge

    @ult_charge.setter
    def ult_charge(self, value):
        if value <= 0:
            self._real_ult_charge = 0
            return
        diff = value - self._real_ult_charge
        if diff > 0:
            self._real_ult_charge += diff / 1.3
        else:
            self._real_ult_charge = value

        if self._real_ult_charge >= 99.0:
            self._real_ult_charge = 100.0
        else:
            self._real_ult_charge = min(100.0, self._real_ult_charge)

    def update_skill(self, bullet_list, agents=None):
        if agents is None: return

        if self.ult_invincible_timer > 0:
            self.ult_invincible_timer -= 1

        if self.state in ["SLEEP", "BATTLEFIELD", "EXPERIMENT", "HOMEWORK"]:
            self.reflects_attacker = True
        else:
            self.reflects_attacker = False

        if self.ult_charge >= 100 and self.state not in ["TIME_STOP", "ULTIMATE"]:
            self.trigger_ultimate()
            return

        enemies = [a for a in agents if a.faction != self.faction and a.hp > 0]

        if self.state == "TIME_STOP":
            self.ult_start_timer -= 1
            if self.ult_start_timer <= 0:
                self.state = "ULTIMATE"
                self.ult_timer = SHIP_RUN_FRAMES
                self.ship_hit_cd.clear()

                start_angle = random.uniform(0, 2 * math.pi)
                self.vx = math.cos(start_angle) * 26
                self.vy = math.sin(start_angle) * 26

                if SHIP_SND:
                    channel = pygame.mixer.find_channel(True)
                    if channel:
                        channel.play(SHIP_SND)
                    else:
                        SHIP_SND.play()
            return

        if self.state == "ROULETTE":
            self.image = ICON_MAO if ICON_MAO else None

            speed = math.hypot(self.vx, self.vy)
            if speed < 1:
                angle = random.uniform(0, 2 * math.pi)
                self.vx = math.cos(angle) * self.base_speed
                self.vy = math.sin(angle) * self.base_speed
            else:
                self.vx = (self.vx / speed) * self.base_speed
                self.vy = (self.vy / speed) * self.base_speed

            self.roulette_angle += 0.05
            self.roulette_timer -= 1

            if self.roulette_timer % 8 == 0:
                self.current_option_idx = random.randint(0, 3)

            if self.roulette_timer <= 0:
                self.state = self.roulette_options[self.current_option_idx]

                if self.state == "SLEEP":
                    self.action_timer = 360
                    self.image = ICON_SLEEP if ICON_SLEEP else ICON_MAO
                    if SLEEP_SND: SLEEP_SND.play()

                elif self.state == "BATTLEFIELD":
                    self.action_timer = 360
                    self.ak_bullets = 0
                    if BATTLEFIELD_SND: BATTLEFIELD_SND.play()

                elif self.state == "EXPERIMENT":
                    self.action_timer = 480
                    if EXPERIMENT_SND: EXPERIMENT_SND.play()

                elif self.state == "HOMEWORK":
                    self.action_timer = 480
                    if HOMEWORK_SND: HOMEWORK_SND.play()

        elif self.state == "SLEEP":
            self.vx *= 0.8
            self.vy *= 0.8
            self.action_timer -= 1

            if self.action_timer in [270, 180, 90]:
                self.fire_zzz(bullet_list, enemies)

            if self.action_timer <= 0:
                self.hp = min(self.max_hp, self.hp + 200)
                self.state = "ROULETTE"
                self.roulette_timer = 300

        elif self.state == "BATTLEFIELD":
            self.vx *= 0.8
            self.vy *= 0.8
            self.action_timer -= 1

            if self.action_timer in [288, 216, 144, 72]:
                self.ak_bullets = 4

            if self.ak_bullets > 0 and self.action_timer % 6 == 0:
                self.fire_ak(bullet_list, enemies)
                self.ak_bullets -= 1

            if self.action_timer <= 0:
                self.state = "ROULETTE"
                self.roulette_timer = 300

        elif self.state == "EXPERIMENT":
            self.vx *= 0.8
            self.vy *= 0.8
            self.action_timer -= 1
            if self.action_timer <= 0:
                self.ult_charge += 20
                self.state = "ROULETTE"
                self.roulette_timer = 300

        elif self.state == "HOMEWORK":
            self.vx *= 0.8
            self.vy *= 0.8
            self.action_timer -= 1
            if self.action_timer <= 0:
                self.state = "ROULETTE"
                self.roulette_timer = 300

        elif self.state == "ULTIMATE":
            self.ult_timer -= 1
            self.image = None

            if self.x < 150:
                self.x = 150
                self.vx *= -1
            elif self.x > WIDTH - 150:
                self.x = WIDTH - 150
                self.vx *= -1

            if self.y < 150:
                self.y = 150
                self.vy *= -1
            elif self.y > HEIGHT - 150:
                self.y = HEIGHT - 150
                self.vy *= -1

            current_angle = math.atan2(self.vy, self.vx)
            current_angle += random.uniform(-0.05, 0.05)
            self.vx = math.cos(current_angle) * 26
            self.vy = math.sin(current_angle) * 26

            for e in list(self.ship_hit_cd.keys()):
                if self.ship_hit_cd[e] > 0: self.ship_hit_cd[e] -= 1

            for e in enemies:
                if math.hypot(self.x - e.x, self.y - e.y) < 160 + e.radius:
                    if self.ship_hit_cd.get(e, 0) <= 0:
                        e.hp -= 60
                        e.vx = self.vx * 1.5
                        e.vy = self.vy * 1.5
                        e.is_knocked_back = True
                        self.ship_hit_cd[e] = 40

            self.sub_action_timer -= 1
            if self.sub_action_timer <= 0:
                self.sub_action = random.choice(["SLEEP", "BATTLEFIELD", "EXPERIMENT", "HOMEWORK"])
                self.sub_action_timer = 240

                if self.sub_action == "SLEEP":
                    self.sub_step_timer = 150
                elif self.sub_action == "BATTLEFIELD":
                    self.sub_step_timer = 150
                    self.ak_bullets = 0
                elif self.sub_action == "EXPERIMENT":
                    self.sub_step_timer = 150
                elif self.sub_action == "HOMEWORK":
                    self.sub_step_timer = 150

            if self.sub_action == "SLEEP":
                self.sub_step_timer -= 1
                if self.sub_step_timer in [120, 80, 40]:
                    self.fire_zzz(bullet_list, enemies)
            elif self.sub_action == "BATTLEFIELD":
                self.sub_step_timer -= 1
                if self.sub_step_timer in [120, 90, 60, 30]:
                    self.ak_bullets = 4
                if self.ak_bullets > 0 and self.sub_step_timer % 5 == 0:
                    self.fire_ak(bullet_list, enemies)
                    self.ak_bullets -= 1
            elif self.sub_action == "EXPERIMENT":
                self.sub_step_timer -= 1
                if self.sub_step_timer == 0:
                    self.ult_charge += 20
            elif self.sub_action == "HOMEWORK":
                self.sub_step_timer -= 1

            if self.ult_timer <= 0:
                self.state = "ROULETTE"
                self.roulette_timer = 300
                self.sub_action = None
                self.image = ICON_MAO if ICON_MAO else None

    def fire_zzz(self, bullet_list, enemies):
        base_angle = random.uniform(0, 2 * math.pi)
        if enemies:
            closest = min(enemies, key=lambda e: math.hypot(self.x - e.x, self.y - e.y))
            base_angle = math.atan2(closest.y - self.y, closest.x - self.x)

        for offset in [-0.5, 0, 0.5]:
            vx = math.cos(base_angle + offset) * 6
            vy = math.sin(base_angle + offset) * 6
            bullet_list.append(MaoBullet(self.x, self.y, vx, vy, "ZZZ", self.faction))

    def fire_ak(self, bullet_list, enemies):
        if AMMO_SND: AMMO_SND.play()

        angle = random.uniform(0, 2 * math.pi)
        if enemies:
            closest = min(enemies, key=lambda e: math.hypot(self.x - e.x, self.y - e.y))
            angle = math.atan2(closest.y - self.y, closest.x - self.x) + random.uniform(-0.1, 0.1)

        vx = math.cos(angle) * 30
        vy = math.sin(angle) * 30
        bullet_list.append(MaoBullet(self.x, self.y, vx, vy, "AK47", self.faction))

    def trigger_ultimate(self):
        self.stop_sounds()
        self.state = "TIME_STOP"
        self.ult_charge = 0
        self.ult_start_timer = ULT_START_FRAMES
        self.vx, self.vy = 0, 0

        if ULT_SND:
            channel = pygame.mixer.find_channel(True)
            if channel:
                channel.play(ULT_SND)
            else:
                ULT_SND.play()

    def draw(self, surface):
        if self.state == "ULTIMATE":
            if IMG_SHIP:
                angle = math.atan2(self.vy, self.vx)
                rotated_ship = pygame.transform.rotate(IMG_SHIP, -math.degrees(angle))
                rect = rotated_ship.get_rect(center=(int(self.x), int(self.y)))
                surface.blit(rotated_ship, rect)
            else:
                pygame.draw.circle(surface, (100, 100, 255), (int(self.x), int(self.y)), 120)

            if self.sub_action == "SLEEP" and ICON_SLEEP:
                surface.blit(pygame.transform.scale(ICON_SLEEP, (60, 60)), (self.x - 30, self.y - 120))
            elif self.sub_action == "BATTLEFIELD" and IMG_AK47:
                surface.blit(IMG_AK47, (self.x - 50, self.y - 120))
            elif self.sub_action == "EXPERIMENT" and IMG_EXPERIMENT:
                surface.blit(pygame.transform.scale(IMG_EXPERIMENT, (60, 60)), (self.x - 30, self.y - 120))
            elif self.sub_action == "HOMEWORK" and IMG_HOMEWORK:
                surface.blit(pygame.transform.scale(IMG_HOMEWORK, (60, 60)), (self.x - 30, self.y - 120))

            # --- 修改：利用 1x1 的透明贴图骗过父类，强制渲染出底层的血条、等级等 UI 信息 ---
            old_img = self.image
            self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
            super().draw(surface)
            self.image = old_img

        else:
            if self.state == "TIME_STOP" and IMG_SHIP and ULT_START_FRAMES > 0:
                progress = 1.0 - max(0, self.ult_start_timer / ULT_START_FRAMES)
                alpha = int(255 * progress)
                temp_ship = IMG_SHIP.copy()
                temp_ship.set_alpha(alpha)
                rotated_ship = pygame.transform.rotate(temp_ship, 0)
                rect = rotated_ship.get_rect(center=(int(self.x), int(self.y)))
                surface.blit(rotated_ship, rect)

            super().draw(surface)

        if self.state == "ROULETTE":
            font = get_cn_font(20)
            for i, text in enumerate(self.roulette_labels):
                angle = self.roulette_angle + i * (math.pi / 2)
                px = self.x + math.cos(angle) * 90
                py = self.y + math.sin(angle) * 90

                if i == self.current_option_idx:
                    color = (255, 255, 0)
                    pygame.draw.circle(surface, (255, 255, 0), (int(px), int(py)), 30, 2)
                else:
                    color = (150, 150, 150)

                txt_surf = font.render(text, True, color)
                surface.blit(txt_surf, (px - txt_surf.get_width() // 2, py - txt_surf.get_height() // 2))

        elif self.state == "BATTLEFIELD":
            if IMG_AK47:
                shake_offset = random.randint(-5, 5) if self.ak_bullets > 0 else 0
                surface.blit(IMG_AK47, (self.x + 10, self.y - 20 + shake_offset))

        elif self.state == "EXPERIMENT":
            if IMG_EXPERIMENT:
                rect = IMG_EXPERIMENT.get_rect(center=(int(self.x), int(self.y) + 120))
                surface.blit(IMG_EXPERIMENT, rect)
            progress = (480 - self.action_timer) / 480
            pygame.draw.rect(surface, (0, 255, 255), (self.x - 40, self.y + 195, 80 * progress, 8))

        elif self.state == "HOMEWORK":
            if IMG_HOMEWORK:
                rect = IMG_HOMEWORK.get_rect(center=(int(self.x), int(self.y) + 120))
                surface.blit(IMG_HOMEWORK, rect)
            progress = (480 - self.action_timer) / 480
            pygame.draw.rect(surface, (100, 100, 100), (self.x - 40, self.y + 195, 80 * progress, 8))

# ==========================================
# 4. 图鉴数据注册
# ==========================================
from almanac import register_almanac_entry

mao_stats = {
    "基础移速": "7 (较高)",
    "弹道伤害": "Zzz(20) / AK47(85)",
    "战舰撞击": "60 + 极强击退",
    "大招充能": "极慢 (自身获取能量效率降低约23%)"
}

mao_mechanics = (
    "【被动·猫的一天】\n"
    "每隔5秒，猫会在头顶进行一次轮盘抽奖，随机决定接下来的行动。在执行抽签结果期间，猫全身布满防备，反弹敌人的近战伤害。\n\n"
    "【抽签·猫睡觉，享受这片刻的宁静】\n"
    "持续6秒。猫睡觉，期间向敌人发射带有漂移追踪效果的“Zzz”弹幕（20点伤害）。睡醒后，猫恢复200点生命值。\n\n"
    "【抽签·在战场上，猫展现猫身手，猫打战地，铸就永恒的传奇】\n"
    "持续6秒。猫起ak，向敌人精准倾泻4轮致命的点射子弹（每轮3发子弹，单发高达85点伤害），弹道极快，火力凶猛。\n\n"
    "【抽签·猫做实验 / 猫写作业】\n"
    "持续8秒。“做实验”结束后，猫会获得20点大招能量；而如果猫不幸地需要写作业，那么猫只会绝望地写作业整整8秒，什么都不干。\n\n"
    "【终极技能·猫焊电路板，打造未来的航船】\n"
    "猫召唤一艘体积庞大的无敌战舰在全场疯狂弹射冲撞。战舰移速极快，享有5帧的无敌帧，撞击敌人时造成60点伤害与猛烈击退。在驾驶战舰期间，猫还会一边飙船一边继续高频抽签。"
)

mao_lore = (
    "我是猫！"
)

# 注册进入图鉴系统
register_almanac_entry(
    char_id="Mao",
    name="猫",
    icon=ICON_MAO,
    stats=mao_stats,
    mechanics=mao_mechanics,
    lore=mao_lore
)