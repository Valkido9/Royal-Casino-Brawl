import pygame
import math
import random
import os
import sys

try:
    from settings import WIDTH, HEIGHT, FPS
except ImportError:
    WIDTH, HEIGHT, FPS = 1920, 1080, 60

from core_classes import Agent, Bullet, HIT_SOUNDS
from almanac import register_almanac_entry
from ui_components import get_cn_font

# ==========================================
# 1. 资源加载与预处理区 (防弹路径版)
# ==========================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ASSET_DIR = os.path.join(BASE_DIR, "assets", "liuba")
SOUND_DIR = os.path.join(BASE_DIR, "sounds", "liuba")


def load_img(filename, size=None):
    try:
        raw_img = pygame.image.load(os.path.join(ASSET_DIR, filename))
        if size:
            return pygame.transform.smoothscale(raw_img, size)
        return raw_img
    except Exception as e:
        print(f"68 加载图片失败: {filename}, 错误: {e}")
        return None


ICON_IMG = load_img("icon.jpg", (120, 120)) or load_img("icon.png", (120, 120))
IMG_ATTACK = load_img("attack.png", (300, 300))
IMG_HAND = load_img("hand.png", (180, 180))
IMG_METEOR = load_img("meteor.png", (200, 200))
IMG_OUHE = load_img("ouhe.png", (80, 80))


def load_snd(filename):
    try:
        return pygame.mixer.Sound(os.path.join(SOUND_DIR, filename))
    except:
        return None


def get_snd_text(filename):
    """助手函数：返回 (声音对象, 台词文本)"""
    snd = load_snd(filename)
    if snd:
        text = filename.rsplit('.', 1)[0]
        return (snd, text)
    return None


# --- 常态语音 ---
SND_MELEE = [get_snd_text("影分身十字斩.wav"), get_snd_text("海文十字.wav"), get_snd_text("一刀一刀燃烧刀.wav")]
SND_RANGED = [get_snd_text("欧内的手.wav"), get_snd_text("使用罗汉手.wav"), get_snd_text("豌豆射手.wav"),
              get_snd_text("死神的手.wav")]
SND_DODGE = [get_snd_text("哎呦卧槽闪现.wav"), get_snd_text("hana我闪现切你的手.wav")]
SND_FLASH = load_snd("flash.mp3")

# --- 大招语音 ---
SND_ULT_START = get_snd_text("吓我一跳我释放忍术.wav")
SND_ULTS = {
    1: get_snd_text("啊彗星.wav"),
    2: get_snd_text("好男人也没的身手.wav"),
    3: get_snd_text("藕盒.wav"),
    4: get_snd_text("啊我不是人类我和梅西赛跑.wav"),
    5: get_snd_text("毒火焰.wav"),
    6: get_snd_text("令神龙造成烟雾.wav"),
    7: get_snd_text("磨刀我杀他去.wav"),
    8: get_snd_text("纳米悠悠球.wav"),
    9: [get_snd_text("欧内死手.wav"), get_snd_text("我夺取心脏.wav")],
    10: get_snd_text("岩石耐击术.wav")
}

SND_EATING = load_snd("eating.mp3")

# 过滤空音效
SND_MELEE = [s for s in SND_MELEE if s]
SND_RANGED = [s for s in SND_RANGED if s]
SND_DODGE = [s for s in SND_DODGE if s]


# ==========================================
# 2. 视觉特效与衍生子弹类
# ==========================================
class SubtitleParticle:
    """漫画风实体台词字幕"""

    def __init__(self, text, x, y, is_ult=False):
        self.text = text
        self.x = x
        self.y = y
        self.angle = random.uniform(-50, 50)
        self.max_life = 90  # 存在 1.5 秒
        self.life = self.max_life

        font_size = 52 if is_ult else 38
        font = get_cn_font(font_size)

        text_color = (255, 0, 0) if is_ult else (255, 255, 0)

        text_surf = font.render(self.text, True, text_color)
        outline_surf = font.render(self.text, True, (0, 0, 0))

        w, h = text_surf.get_size()
        self.surf = pygame.Surface((w + 6, h + 4), pygame.SRCALPHA)
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
            self.surf.blit(outline_surf, (dx + 3, dy + 2))
        self.surf.blit(text_surf, (3, 2))

        self.surf = pygame.transform.rotate(self.surf, self.angle)

    def draw(self, surface):
        self.life -= 1
        if self.life > 0:
            alpha = 255
            if self.life < self.max_life * 0.5:
                alpha = int((self.life / (self.max_life * 0.5)) * 255)

            temp = self.surf.copy()
            temp.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
            rect = temp.get_rect(center=(int(self.x), int(self.y)))
            surface.blit(temp, rect)


class DodgeParticle:
    def __init__(self, x, y, vx=0, vy=0, color=(100, 200, 255)):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = 20
        self.color = color
        self.size = random.randint(12, 24)

    def draw(self, surface):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.92
        self.vy *= 0.92
        self.life -= 1
        alpha = int((self.life / 20) * 255)
        surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (self.size // 2, self.size // 2), self.size // 2)
        surface.blit(surf, (self.x - self.size // 2, self.y - self.size // 2))


class LiuBaHand(Bullet):
    """远程：预判手"""

    def __init__(self, x, y, vx, vy, owner_faction):
        super().__init__(x, y, vx, vy, owner_faction, 15, IMG_HAND)
        self.radius = 80
        self.life = 120

    def move(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.life <= 0: self.active = False
        if self.x < 0 or self.x > WIDTH or self.y < 0 or self.y > HEIGHT:
            self.active = False


class CometStrike:
    """大招1：彗星撞地"""

    def __init__(self, x, y, faction):
        self.x = x
        self.y = y
        self.faction = faction
        self.timer = 120  # 2秒警告
        self.active = True
        self.radius = -999
        self.damage = 0
        self.owner_faction = faction
        self.infinite_bounce = True
        self.phase = "WARN"
        self.shockwave_radius = 0

    def move(self):
        if self.phase == "WARN":
            self.timer -= 1
            if self.timer <= 0:
                self.phase = "IMPACT"
                self.timer = 30
        elif self.phase == "IMPACT":
            self.shockwave_radius += 30
            self.timer -= 1
            if self.timer <= 0:
                self.active = False

    def draw(self, surface):
        if self.phase == "WARN":
            blink_rate = max(2, int(self.timer / 10))
            if (self.timer // blink_rate) % 2 == 0:
                pygame.draw.circle(surface, (255, 50, 50), (int(self.x), int(self.y)), 150, 4)
                pygame.draw.line(surface, (255, 50, 50), (self.x - 20, self.y), (self.x + 20, self.y), 4)
                pygame.draw.line(surface, (255, 50, 50), (self.x, self.y - 20), (self.x, self.y + 20), 4)
        elif self.phase == "IMPACT":
            if IMG_METEOR:
                rect = IMG_METEOR.get_rect(center=(int(self.x), int(self.y)))
                surface.blit(IMG_METEOR, rect)
            pygame.draw.circle(surface, (255, 200, 100), (int(self.x), int(self.y)), int(self.shockwave_radius), 8)


class PoisonFireball:
    """大招5：分裂毒火焰"""

    def __init__(self, x, y, vx, vy, gen, faction):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.gen = gen
        self.faction = faction
        self.active = True
        self.radius = max(10, 40 - gen * 10)
        self.damage = 5
        self.owner_faction = faction
        self.infinite_bounce = True
        self.hit_targets = set()
        self.wait_for_split = False

    def move(self):
        if getattr(self, 'wait_for_split', False):
            return

        self.x += self.vx
        self.y += self.vy
        hit_wall = False
        if self.x - self.radius <= 0 or self.x + self.radius >= WIDTH: hit_wall = True
        if self.y - self.radius <= 0 or self.y + self.radius >= HEIGHT: hit_wall = True

        if hit_wall:
            self.x = max(self.radius + 2, min(WIDTH - self.radius - 2, self.x))
            self.y = max(self.radius + 2, min(HEIGHT - self.radius - 2, self.y))

            if self.gen < 2:
                self.wait_for_split = True
                self.spawn_children = True
            else:
                self.active = False

    # --- 核心修复：找回被误删的渲染逻辑！ ---
    def draw(self, surface):
        if getattr(self, 'wait_for_split', False):
            return
        pygame.draw.circle(surface, (50, 200, 50), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (100, 255, 100), (int(self.x), int(self.y)), max(1, self.radius - 4))


# ==========================================
# 3. 68 英雄主体
# ==========================================
class LiuBa(Agent):
    def __init__(self, x, y, color, faction):
        self._is_ready = False
        super().__init__(x, y, color, faction, image=ICON_IMG)

        self.atk = 25
        self.base_speed = 6.5

        self.max_hp = 1000
        self.hp = 1000
        self._hp = 1000

        # --- 被动：闪避 ---
        self.passive_dodge_cd = 10 * FPS
        self.dodge_timer = self.passive_dodge_cd
        self.has_passive_dodge = False
        self.extra_dodges = 0
        self.particles = []
        self.subtitles = []

        # --- 技能 CD ---
        self.melee_cd = 0
        self.ranged_cd = 0

        # --- 大招系统 ---
        self.state = "NORMAL"
        self.ult_choice = 0
        self.ult_timer = 0
        self.ult_phase = 0
        self.target_enemy = None
        self.temp_bullets = []

        # 各大招计时器
        self.messi_timer = 0
        self.shenlong_timer = 0
        self.yoyo_timer = 0
        self.yoyo_angle = 0
        self.rock_timer = 0

        self.modao_hits = 0
        self.display_ouhe = 0

        # 挥砍动作控制变量
        self.display_melee = 0
        self.swing_max = 15
        self.base_swing_angle = 0

        self._is_ready = True

    def play_voice(self, snd_data, volume=1.0, is_ult=False):
        """统一语音控制台：播放声音并在脚下生成台词实体"""
        if not snd_data: return
        snd, text = snd_data

        if snd:
            snd.set_volume(1.0)
            channel = pygame.mixer.find_channel(True)
            if channel:
                channel.play(snd)
            else:
                snd.play()

            if volume >= 2.0:
                channel2 = pygame.mixer.find_channel(True)
                if channel2: channel2.play(snd)

        if text and text not in ["flash", "eating"]:
            ox = random.randint(-15, 15)
            oy = random.randint(40, 70)
            self.subtitles.append(SubtitleParticle(text, self.x + ox, self.y + oy, is_ult=is_ult))

    # ================= 拦截生命值，实现闪避与无敌 =================
    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, value):
        if not getattr(self, '_is_ready', False):
            self._hp = value
            return

        curr = getattr(self, '_hp', None)
        if curr is not None and value < curr:
            damage = curr - value

            if self.state in ["TIME_STOP", "MODAO_DASH", "MODAO_UP", "MODAO_DOWN"]:
                return
            if getattr(self, 'shenlong_timer', 0) > 0:
                return

            if getattr(self, 'rock_timer', 0) > 0:
                damage *= 0.2

            can_dodge = (self.state not in ["OUNEI_WAIT", "OUNEI_DASH"])
            if can_dodge and (self.has_passive_dodge or self.extra_dodges > 0):
                if self.extra_dodges > 0:
                    self.extra_dodges -= 1
                else:
                    self.has_passive_dodge = False
                self.trigger_dodge()
                return

            value = curr - damage
            if damage > 0:
                self.hit_timer = 20
                try:
                    from core_classes import HIT_SOUNDS
                    if HIT_SOUNDS: random.choice(HIT_SOUNDS).play()
                except:
                    pass

        self._hp = min(self.max_hp, max(0, value))

    def trigger_dodge(self):
        if SND_DODGE:
            self.play_voice(random.choice(SND_DODGE))

        if SND_FLASH:
            channel = pygame.mixer.find_channel(True)
            if channel: channel.play(SND_FLASH)

        for _ in range(15):
            self.particles.append(DodgeParticle(self.x, self.y))

        self.dodge_blink_flag = True

    # ================= 核心更新逻辑 =================
    def update_skill(self, bullet_list, agents=None):
        if agents is None: return

        if self.ult_charge < 100 and self.state == "NORMAL":
            self.ult_charge = min(100, self.ult_charge + 0.15)

        if not self.has_passive_dodge:
            self.dodge_timer -= 1
            if self.dodge_timer <= 0:
                self.has_passive_dodge = True
                self.dodge_timer = self.passive_dodge_cd

        enemies = [a for a in agents if a.faction != self.faction and a.hp > 0]
        if getattr(self, 'dodge_blink_flag', False):
            self.dodge_blink_flag = False
            if enemies:
                closest = min(enemies, key=lambda e: math.hypot(self.x - e.x, self.y - e.y))
                angle = math.atan2(self.y - closest.y, self.x - closest.x)
                self.x += math.cos(angle) * 150
                self.y += math.sin(angle) * 150
                self.x = max(self.radius, min(WIDTH - self.radius, self.x))
                self.y = max(self.radius, min(HEIGHT - self.radius, self.y))

        if self.temp_bullets:
            for b in self.temp_bullets: bullet_list.append(b)
            self.temp_bullets.clear()

        # ================= 状态机分支 =================
        if self.state == "TIME_STOP":
            self.vx, self.vy = 0, 0
            self.ult_timer -= 1
            if self.ult_timer <= 0:
                self.execute_ultimate(bullet_list, agents)
            return

        elif self.state == "OUNEI_WAIT":
            self.vx, self.vy = 0, 0
            self.ult_timer -= 1

            if self.ult_timer == 60:
                if len(SND_ULTS[9]) > 1:
                    self.play_voice(SND_ULTS[9][1], volume=2.0, is_ult=True)

            if self.ult_timer <= 0:
                self.state = "OUNEI_DASH"
                if enemies:
                    self.target_enemy = min(enemies, key=lambda e: math.hypot(self.x - e.x, self.y - e.y))
            return

        elif self.state == "OUNEI_DASH":
            if not self.target_enemy or self.target_enemy.hp <= 0:
                self.state = "NORMAL"
                return
            angle = math.atan2(self.target_enemy.y - self.y, self.target_enemy.x - self.x)
            self.vx = math.cos(angle) * self.base_speed * 8
            self.vy = math.sin(angle) * self.base_speed * 8
            for b in bullet_list:
                if b.owner_faction != self.faction and math.hypot(self.x - b.x, self.y - b.y) < 80 + b.radius:
                    b.active = False
            if math.hypot(self.x - self.target_enemy.x,
                          self.y - self.target_enemy.y) < self.radius + self.target_enemy.radius + 30:
                self.target_enemy.hp = 0
                self.state = "NORMAL"
            return

        elif self.state == "MODAO_DASH":
            if not self.target_enemy or self.target_enemy.hp <= 0:
                self.state = "NORMAL"
                return
            angle = math.atan2(self.target_enemy.y - self.y, self.target_enemy.x - self.x)
            self.vx = math.cos(angle) * self.base_speed * 4
            self.vy = math.sin(angle) * self.base_speed * 4
            self.display_melee = 15
            if math.hypot(self.x - self.target_enemy.x, self.y - self.target_enemy.y) < 80 + self.target_enemy.radius:
                self.target_enemy.hp -= 70
                self.target_enemy.vx = 0
                self.target_enemy.vy = -30
                self.target_enemy.is_knocked_back = True
                self.state = "MODAO_UP"
                self.ult_timer = 20
                self.vx, self.vy = 0, -30
            return

        elif self.state == "MODAO_UP":
            self.display_melee = 15
            self.ult_timer -= 1
            if self.ult_timer <= 0:
                self.state = "MODAO_DOWN"
                self.ult_timer = 20
                self.vx, self.vy = 0, 30
                if self.target_enemy: self.target_enemy.vy = 30
            return

        elif self.state == "MODAO_DOWN":
            self.display_melee = 15
            self.ult_timer -= 1
            if self.ult_timer <= 0:
                self.state = "NORMAL"
                if self.target_enemy and self.target_enemy.hp > 0:
                    self.target_enemy.hp -= 70
                    self.target_enemy.vx = 0
                    self.target_enemy.vy = 0
            return

        # ================= 倒计时被动刷新 =================
        if self.display_ouhe > 0: self.display_ouhe -= 1
        if self.display_melee > 0: self.display_melee -= 1
        if self.messi_timer > 0: self.messi_timer -= 1
        if self.shenlong_timer > 0: self.shenlong_timer -= 1
        if self.rock_timer > 0: self.rock_timer -= 1

        for b in bullet_list:
            if isinstance(b, PoisonFireball) and b.owner_faction == self.faction:
                if getattr(b, 'spawn_children', False):
                    b.spawn_children = False
                    b.active = False
                    base_a = math.atan2(-b.vy, -b.vx)
                    for off in [-0.6, 0, 0.6]:
                        speed = 10
                        vx = math.cos(base_a + off) * speed
                        vy = math.sin(base_a + off) * speed
                        self.temp_bullets.append(PoisonFireball(b.x, b.y, vx, vy, b.gen + 1, self.faction))

        for b in bullet_list:
            if isinstance(b, CometStrike) and b.owner_faction == self.faction:
                if b.phase == "IMPACT" and b.timer == 30:
                    for e in enemies:
                        if math.hypot(b.x - e.x, b.y - e.y) < 150: e.hp -= 150
                elif b.phase == "IMPACT":
                    for a in agents:
                        if a != self and a.hp > 0:
                            dist = math.hypot(b.x - a.x, b.y - a.y)
                            if abs(dist - b.shockwave_radius) < 40:
                                a.hp -= 5
                                ang = math.atan2(a.y - b.y, a.x - b.x)
                                a.vx = math.cos(ang) * 40
                                a.vy = math.sin(ang) * 40
                                a.is_knocked_back = True

        # ================= 常规/大招混合逻辑 =================
        if self.state == "NORMAL":
            if self.ult_charge >= 100:
                self.start_ultimate()
                return

            self.melee_cd = max(0, self.melee_cd - 1)
            self.ranged_cd = max(0, self.ranged_cd - 1)

            current_base_speed = self.base_speed
            if self.messi_timer > 0: current_base_speed *= 3
            if self.rock_timer > 0: current_base_speed *= 0.5

            speed = math.hypot(self.vx, self.vy)
            if speed < 1:
                ang = random.uniform(0, 2 * math.pi)
                self.vx = math.cos(ang) * current_base_speed
                self.vy = math.sin(ang) * current_base_speed
            else:
                self.vx = (self.vx / speed) * current_base_speed
                self.vy = (self.vy / speed) * current_base_speed

            if not enemies: return
            closest = min(enemies, key=lambda e: math.hypot(self.x - e.x, self.y - e.y))
            dist = math.hypot(self.x - closest.x, self.y - closest.y)

            if self.yoyo_timer > 0:
                self.yoyo_timer -= 1
                self.yoyo_angle += 0.15
                y_x = self.x + math.cos(self.yoyo_angle) * 200
                y_y = self.y + math.sin(self.yoyo_angle) * 200
                for e in enemies:
                    if math.hypot(e.x - y_x, e.y - y_y) < e.radius + 30:
                        e.hp -= 5
                    else:
                        d1 = math.hypot(e.x - self.x, e.y - self.y)
                        d2 = math.hypot(e.x - y_x, e.y - y_y)
                        if d1 + d2 < 200 + e.radius + 10:
                            e.hp -= 2
                return

            if dist < 200 and self.melee_cd <= 0:
                self.display_melee = 15
                self.base_swing_angle = math.atan2(closest.y - self.y, closest.x - self.x)
                if SND_MELEE: self.play_voice(random.choice(SND_MELEE))
                closest.hp -= self.atk * 2
                self.ult_charge = min(100, self.ult_charge + 5)
                self.melee_cd = 60

            elif dist >= 200 and self.ranged_cd <= 0:
                time_to_hit = dist / 15
                pred_x = closest.x + closest.vx * time_to_hit
                pred_y = closest.y + closest.vy * time_to_hit
                ang = math.atan2(pred_y - self.y, pred_x - self.x)

                bullet_list.append(LiuBaHand(self.x, self.y, math.cos(ang) * 15, math.sin(ang) * 15, self.faction))

                if SND_RANGED: self.play_voice(random.choice(SND_RANGED))
                self.ranged_cd = 180

    def start_ultimate(self):
        self.state = "TIME_STOP"
        self.ult_charge = 0
        self.ult_timer = int(0.5 * FPS)
        self.vx, self.vy = 0, 0
        if SND_ULT_START: self.play_voice(SND_ULT_START, is_ult=True)

        for _ in range(40):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(6, 18)
            self.particles.append(DodgeParticle(
                self.x, self.y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=(255, 60, 40)
            ))

    def execute_ultimate(self, bullet_list, agents):
        self.state = "NORMAL"
        self.ult_choice = random.randint(1, 10)
        enemies = [a for a in agents if a.faction != self.faction and a.hp > 0]

        if self.ult_choice != 9:
            self.play_voice(SND_ULTS[self.ult_choice], is_ult=True)

        if self.ult_choice == 1:
            tx, ty = WIDTH // 2, HEIGHT // 2
            if enemies:
                target = random.choice(enemies)
                tx, ty = target.x, target.y
            bullet_list.append(CometStrike(tx, ty, self.faction))

        elif self.ult_choice == 2:
            self.extra_dodges += 1

        elif self.ult_choice == 3:
            self.hp = min(self.max_hp, self.hp + 200)
            self.display_ouhe = 60
            if SND_EATING: SND_EATING.play()

        elif self.ult_choice == 4:
            self.messi_timer = 5 * FPS

        elif self.ult_choice == 5:
            if enemies:
                target = random.choice(enemies)
                ang = math.atan2(target.y - self.y, target.x - self.x)
            else:
                ang = random.uniform(0, 2 * math.pi)
            bullet_list.append(PoisonFireball(self.x, self.y, math.cos(ang) * 12, math.sin(ang) * 12, 0, self.faction))

        elif self.ult_choice == 6:
            self.shenlong_timer = 1 * FPS

        elif self.ult_choice == 7:
            if enemies:
                self.target_enemy = min(enemies, key=lambda e: math.hypot(self.x - e.x, self.y - e.y))
                self.base_swing_angle = math.atan2(self.target_enemy.y - self.y, self.target_enemy.x - self.x)
                self.state = "MODAO_DASH"

        elif self.ult_choice == 8:
            self.yoyo_timer = 3 * FPS
            self.yoyo_angle = 0

        elif self.ult_choice == 9:
            self.state = "OUNEI_WAIT"
            self.ult_timer = 5 * FPS
            if len(SND_ULTS[9]) > 0:
                self.play_voice(SND_ULTS[9][0], is_ult=True)

        elif self.ult_choice == 10:
            self.rock_timer = 4 * FPS

    def draw(self, surface):
        if self.shenlong_timer > 0:
            if ICON_IMG:
                temp = ICON_IMG.copy()
                temp.set_alpha(80)
                rect = temp.get_rect(center=(int(self.x), int(self.y)))
                surface.blit(temp, rect)
        elif self.state == "OUNEI_WAIT":
            old_x, old_y = self.x, self.y
            self.x += random.randint(-15, 15)
            self.y += random.randint(-15, 15)
            super().draw(surface)
            self.x, self.y = old_x, old_y
        else:
            super().draw(surface)

        for sub in list(self.subtitles):
            sub.draw(surface)
            if sub.life <= 0:
                self.subtitles.remove(sub)

        for p in list(self.particles):
            p.draw(surface)
            if p.life <= 0: self.particles.remove(p)

        if self.display_ouhe > 0 and IMG_OUHE:
            rect = IMG_OUHE.get_rect(center=(int(self.x), int(self.y) - 60))
            surface.blit(IMG_OUHE, rect)

        if self.display_melee > 0 and IMG_ATTACK:
            progress = (self.swing_max - max(0, self.display_melee)) / self.swing_max
            current_rad = self.base_swing_angle - math.radians(60) + (progress * math.radians(120))
            rotated_sword = pygame.transform.rotate(IMG_ATTACK, -math.degrees(current_rad) - 90)

            offset_x = self.x + math.cos(current_rad) * (self.radius + 110)
            offset_y = self.y + math.sin(current_rad) * (self.radius + 110)
            rect = rotated_sword.get_rect(center=(int(offset_x), int(offset_y)))
            surface.blit(rotated_sword, rect)

        if self.yoyo_timer > 0:
            y_x = self.x + math.cos(self.yoyo_angle) * 200
            y_y = self.y + math.sin(self.yoyo_angle) * 200
            pygame.draw.line(surface, (200, 200, 200), (int(self.x), int(self.y)), (int(y_x), int(y_y)), 2)
            pygame.draw.circle(surface, (150, 50, 200), (int(y_x), int(y_y)), 20)
            pygame.draw.circle(surface, (255, 150, 255), (int(y_x), int(y_y)), 10)

        if self.state == "OUNEI_DASH" and IMG_HAND:
            huge_hand = pygame.transform.scale(IMG_HAND, (200, 200))
            huge_hand.fill((255, 0, 0, 100), special_flags=pygame.BLEND_RGBA_ADD)
            rect = huge_hand.get_rect(center=(int(self.x), int(self.y)))
            surface.blit(huge_hand, rect)

        if self.has_passive_dodge or self.extra_dodges > 0:
            total_dodges = self.extra_dodges + (1 if self.has_passive_dodge else 0)
            pygame.draw.circle(surface, (100, 255, 255), (int(self.x + 40), int(self.y - 40)), 12)
            font = get_cn_font(24)
            txt = font.render(str(total_dodges), True, (0, 0, 0))
            surface.blit(txt, (int(self.x + 34), int(self.y - 48)))


# ==========================================
# 4. 图鉴数据注册
# ==========================================
liuba_stats = {
    "近战伤害": "20x2 (动态巨化大太刀)",
    "远程伤害": "15 (巨大忍者手预判)",
    "基础移速": "6.5",
    "特异功能": "自动生成绝对闪避盾",
    "大招充能": "极快 (极其频繁的忍术释放)"
}

liuba_mechanics = (
    "【被动·忍术替身】\n"
    "每隔10秒自动获得一次闪避充能。遭受攻击时消耗充能，完全免疫本次伤害，并瞬间向远离敌人的方向闪现突进一段距离拉开身位。\n\n"
    "【普攻·太刀弧斩/巨大忍者手】\n"
    "远距离时每3秒抛射一次能精准预判敌人移速的巨大“忍者之手”，伤害虽低但大招充能极快。近身200码范围内使用200%尺寸的大太刀打出120度扇形大范围动态弧线斩击。\n\n"
    "【终极技能·十重大忍术！】\n"
    "充能极快，会在10种截然不同的强力忍术中随机释放一种：\n"
    "1. 啊彗星：天降陨石，并在落地后炸开一圈极其强力的清场击退冲击波。\n"
    "2. 好男人也没的身手：叠加1次无敌闪避。\n"
    "3. 藕盒：吃下藕盒，瞬间回复200点生命值。\n"
    "4. 我和梅西赛跑：移速暴增至300%，持续5秒。\n"
    "5. 毒火焰：抛出毒火，触壁后会不断几何分裂的清场弹幕。\n"
    "6. 令神龙造成烟雾：隐身1秒，期间进入绝对无敌状态（毒圈都毒不死）。\n"
    "7. 磨刀我杀他去：高速突进将敌人挑飞再砸地，造成两次削弱后的平衡连击。\n"
    "8. 纳米悠悠球：放弃普攻，掏出绞肉悠悠球进行360度大范围横扫。\n"
    "9. 欧内死手，我夺取心脏：原地蓄力颤抖5秒，期间可以受到一切伤害。随后化作红光以800%速度冲刺并清除沿途弹幕，对撞到的敌人执行【即死秒杀】。\n"
    "10. 岩石耐击术：移速减半，但获得高达80%的恐怖减伤，持续4秒。"
)

liuba_lore = (
    "“吓我一跳，我释放忍术！”\n\n"
    "作为一名来自楚国的神秘武士，68自称“楚庄王”。他精通百家武学与忍术，口中总是吟唱着常人无法理解的咒语。在这个赌场里，没有他一个闪现切不到的手，如果有，那就再放个彗星。"
)

register_almanac_entry(
    char_id="LiuBa",
    name="68",
    icon=ICON_IMG,
    stats=liuba_stats,
    mechanics=liuba_mechanics,
    lore=liuba_lore
)