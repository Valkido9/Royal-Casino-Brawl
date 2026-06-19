import pygame
import math
import random
import os
import sys

try:
    from settings import WIDTH, HEIGHT, FPS
except ImportError:
    WIDTH, HEIGHT, FPS = 1920, 1080, 60

from core_classes import Agent, Bullet

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)

ASSET_DIR = os.path.join(BASE_DIR, "assets", "langou")
SOUND_DIR = os.path.join(BASE_DIR, "sounds", "langou")


def load_img(filename, size):
    try:
        img_path = os.path.join(ASSET_DIR, filename)
        raw_img = pygame.image.load(img_path)
        return pygame.transform.smoothscale(raw_img, size)
    except Exception as e:
        print(f"Langou 加载图片失败: {filename}，错误: {e}")
        return None


ICON_LANGOU = load_img("icon-langou.jpg", (120, 120)) or load_img("icon-langou.png", (120, 120))
ICON_ZILONG = load_img("icon-zilong.jpg", (80, 80)) or load_img("icon-zilong.png", (80, 80))
IMG_BOOK = load_img("book.png", (250, 250))
IMG_CLAW = load_img("claw.png", (120, 120))


def load_snd(filename):
    try:
        return pygame.mixer.Sound(os.path.join(SOUND_DIR, filename))
    except:
        return None

ULT_SND = load_snd("ultimate.mp3")
ATTACK_SND = load_snd("attack.mp3")
ZILONG_ATTACK_SND = load_snd("zilongattack.mp3")

PREPARE_SUMMON_SNDS = [load_snd("prepare_summon2.mp3"), load_snd("prepare_summon3.mp3")]
PREPARE_SUMMON_SNDS = [s for s in PREPARE_SUMMON_SNDS if s is not None]

for s in PREPARE_SUMMON_SNDS:
    try:
        current_vol = s.get_volume()
        s.set_volume(min(1.0, current_vol * 1.4))
    except:
        pass


class ArtbookTrap:
    def __init__(self, x, y, angle, damage, owner_faction):
        self.x = x
        self.y = y
        speed = random.uniform(15, 25)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

        self.owner_faction = owner_faction
        self.real_damage = damage
        self.damage = 0
        self.infinite_bounce = True

        self.radius = 45
        self.active = True
        self.is_artbook = True

        self.rotation = 0

    def move(self):
        self.vx *= 0.96
        self.vy *= 0.96
        self.x += self.vx
        self.y += self.vy

        if self.x - self.radius < 0 or self.x + self.radius > WIDTH:
            self.vx *= -1
            self.x = max(self.radius, min(WIDTH - self.radius, self.x))
        if self.y - self.radius < 0 or self.y + self.radius > HEIGHT:
            self.vy *= -1
            self.y = max(self.radius, min(HEIGHT - self.radius, self.y))

    def draw(self, surface):
        current_speed = math.hypot(self.vx, self.vy)
        self.rotation = (self.rotation + current_speed * 3) % 360

        if IMG_BOOK:
            rotated = pygame.transform.rotate(IMG_BOOK, self.rotation)
            rect = rotated.get_rect(center=(int(self.x), int(self.y)))
            surface.blit(rotated, rect)
        else:
            pygame.draw.circle(surface, (150, 50, 255), (int(self.x), int(self.y)), self.radius)
            pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), self.radius - 5, 2)


class ZilongActiveClaw:
    def __init__(self, x, y, angle, damage, owner_faction, owner_agent=None):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.owner_faction = owner_faction
        self.owner_agent = owner_agent
        self.damage = 0
        self.real_damage = damage
        self.radius = -999
        self.active = True
        self.life = 15
        self.max_life = 15
        self.hit_targets = set()

        if IMG_CLAW:
            deg_angle = math.degrees(-angle)
            self.image = pygame.transform.rotate(IMG_CLAW, deg_angle)
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        else:
            self.image = None

    def move(self):
        if self.owner_agent is not None and getattr(self.owner_agent, 'hp', 0) <= 0:
            self.active = False
            return

        self.life -= 1
        if self.life <= 0:
            self.active = False

    def draw(self, surface):
        if self.image:
            temp_claw = self.image.copy()
            alpha = int((self.life / self.max_life) * 255)
            temp_claw.set_alpha(max(0, alpha))
            surface.blit(temp_claw, self.rect)


class Zilong(Agent):
    def __init__(self, x, y, color, faction, owner, is_ult=False):
        super().__init__(x, y, color, faction, image=ICON_ZILONG)
        self.radius = 40
        self.owner = owner
        self.is_ult = is_ult

        self.max_hp = max(1, int(self.owner.max_hp / 20.0))
        self.hp = self.max_hp

        self.atk = 10.0
        self.base_speed = self.owner.base_speed * 1.5
        self.life_timer = int(5.0 * FPS) if is_ult else 0
        self.melee_cd = 0

    def draw(self, surface):
        if self.hp <= 0:
            return
        super().draw(surface)

    def update_skill(self, bullet_list, agents=None):
        if agents is None: return

        if self.owner is None or getattr(self.owner, 'hp', 0) <= 0:
            self.hp = 0
            return

        if getattr(self, 'langou_stun_timer', 0) > 0:
            self.vx, self.vy = 0, 0
            return

        if self.is_ult:
            self.life_timer -= 1
            if self.life_timer <= 0:
                self.hp = 0
                return

        enemies = [a for a in agents if a.faction != self.faction and a.hp > 0]
        if not enemies:
            speed = math.hypot(self.vx, self.vy)
            if speed < 1:
                angle = random.uniform(0, 2 * math.pi)
                self.vx = math.cos(angle) * self.base_speed
                self.vy = math.sin(angle) * self.base_speed
            return

        target = min(enemies, key=lambda e: math.hypot(self.x - e.x, self.y - e.y))
        angle = math.atan2(target.y - self.y, target.x - self.x)

        self.vx = math.cos(angle) * self.base_speed
        self.vy = math.sin(angle) * self.base_speed
        dist = math.hypot(self.x - target.x, self.y - target.y)

        if self.melee_cd > 0:
            self.melee_cd -= 1

        if dist < 140 and self.melee_cd <= 0:
            if ZILONG_ATTACK_SND:
                ZILONG_ATTACK_SND.play()

            collision_dmg = self.atk * 0.0
            claw_dmg = self.atk * 1.0

            if dist <= 140 + target.radius:
                claw = ZilongActiveClaw(self.x + math.cos(angle) * 40, self.y + math.sin(angle) * 40, angle, claw_dmg,
                                        self.faction, owner_agent=self)
                bullet_list.append(claw)

                # ---------------- 核心修复：执行抽能前，打上禁止受伤充能标签 ----------------
                target.prevent_charge_this_frame = True

                target.hp -= collision_dmg
                target.hp -= claw_dmg

                if hasattr(target, 'ult_charge'):
                    target.ult_charge = max(0, target.ult_charge - 35)

                if hasattr(self.owner, 'ult_charge') and getattr(self.owner, 'hp', 0) > 0:
                    self.owner.ult_charge = min(100, getattr(self.owner, 'ult_charge', 0) + 3.0)

                target.vx *= 0.4
                target.vy *= 0.4
                claw.hit_targets.add(target)

            self.melee_cd = int(0.8 * FPS)


class Langou(Agent):
    def __init__(self, x, y, color, faction):
        super().__init__(x, y, color, faction, image=ICON_LANGOU)
        self.base_speed = 6
        self.atk = 20
        self.state = "NORMAL"
        self.my_zilong = None
        self.zilong_respawn_timer = 0
        self.book_timer = int(3.0 * FPS)
        self.ult_timer = 0

    def spawn_zilong(self, is_ult=False):
        edge = random.randint(0, 3)
        if edge == 0:
            zx, zy = random.uniform(0, WIDTH), 0
        elif edge == 1:
            zx, zy = random.uniform(0, WIDTH), HEIGHT
        elif edge == 2:
            zx, zy = 0, random.uniform(0, HEIGHT)
        else:
            zx, zy = WIDTH, random.uniform(0, HEIGHT)
        return Zilong(zx, zy, self.color, self.faction, owner=self, is_ult=is_ult)

    def update_skill(self, bullet_list, agents=None):
        if agents is None: return

        any_stunned = False
        for a in agents:
            if a.faction != self.faction and a.hp > 0:
                if getattr(a, 'langou_stun_timer', 0) > 0:
                    any_stunned = True
                    a.langou_stun_timer -= 1

                    if a.langou_stun_timer <= 0:
                        angle = random.uniform(0, 2 * math.pi)
                        burst_speed = getattr(a, 'base_speed', 6) * 2.8
                        a.vx = math.cos(angle) * burst_speed
                        a.vy = math.sin(angle) * burst_speed
                        a.is_knocked_back = True
                    else:
                        a.vx = 0
                        a.vy = 0
                        a.is_knocked_back = False

        is_stunned = getattr(self, 'langou_stun_timer', 0) > 0
        if is_stunned:
            self.vx, self.vy = 0, 0

        for b in bullet_list:
            if getattr(b, 'is_artbook', False) and b.owner_faction == self.faction:
                if not b.active:
                    continue

                for a in agents:
                    if a.faction != self.faction and a.hp > 0:
                        if math.hypot(b.x - a.x, b.y - a.y) < b.radius + a.radius:
                            a.hp -= b.real_damage

                            if getattr(a, 'langou_stun_timer', 0) <= 0:
                                if PREPARE_SUMMON_SNDS:
                                    random.choice(PREPARE_SUMMON_SNDS).play()
                                extra_zilong = self.spawn_zilong(is_ult=False)
                                agents.append(extra_zilong)

                            a.langou_stun_timer = int(0.8 * FPS)
                            b.active = False
                            break

        if self.state == "TIME_STOP":
            self.vx, self.vy = 0, 0
            self.ult_timer -= 1
            if self.ult_timer <= 0:
                self.state = "NORMAL"
                if PREPARE_SUMMON_SNDS:
                    random.choice(PREPARE_SUMMON_SNDS).play()
                for _ in range(2):
                    agents.append(self.spawn_zilong(is_ult=True))
                for a in agents:
                    if a.faction != self.faction and a.hp > 0:
                        if getattr(a, 'langou_stun_timer', 0) <= 0:
                            agents.append(self.spawn_zilong(is_ult=False))
                        a.langou_stun_timer = int(5.0 * FPS)
            return

        if is_stunned: return

        if self.ult_charge < 100:
            self.ult_charge = min(100, self.ult_charge + 0.02)
        else:
            self.state = "TIME_STOP"
            self.ult_charge = 0
            self.ult_timer = int(1.0 * FPS)
            self.vx, self.vy = 0, 0
            if ULT_SND: ULT_SND.play()
            return

        if not any_stunned:
            if self.my_zilong is None or getattr(self.my_zilong, 'hp', 0) <= 0:
                self.zilong_respawn_timer -= 1
                if self.zilong_respawn_timer <= 0:
                    if PREPARE_SUMMON_SNDS:
                        random.choice(PREPARE_SUMMON_SNDS).play()
                    self.my_zilong = self.spawn_zilong(is_ult=False)
                    agents.append(self.my_zilong)
                    self.zilong_respawn_timer = int(8.0 * FPS)
            else:
                self.zilong_respawn_timer = int(8.0 * FPS)

        self.book_timer -= 1
        if self.book_timer <= 0:
            if ATTACK_SND:
                ATTACK_SND.play()
            angle = random.uniform(0, 2 * math.pi)
            dmg = 15
            book = ArtbookTrap(self.x, self.y, angle, dmg, self.faction)
            bullet_list.append(book)
            self.book_timer = int(3.0 * FPS)

        speed = math.hypot(self.vx, self.vy)
        if speed < 1:
            angle = random.uniform(0, 2 * math.pi)
            self.vx = math.cos(angle) * self.base_speed
            self.vy = math.sin(angle) * self.base_speed
        else:
            self.vx = (self.vx / speed) * self.base_speed
            self.vy = (self.vy / speed) * self.base_speed

# ==========================================
# 4. 图鉴数据注册
# ==========================================
from almanac import register_almanac_entry

langou_stats = {
    "设定集伤害": "15",
    "召唤物斩击": "10 (并附带减速与扣除35点大招能量)",
    "基础移速": "6",
    "大招充能": "正常 (自然恢复与召唤物攻击均可充能)"
}

langou_mechanics = (
    "【被动·双人成行】\n"
    "蓝狗在场上时，如果场上没有紫龙，蓝狗每隔8秒会自动召唤一只移动速度极快的紫龙协助作战（如果场上已有存活的紫龙，则停止召唤倒计时）。注意：一旦蓝狗阵亡，全场属于他的紫龙将会瞬间消散。\n\n"
    "【战术道具·永恒流光设定集】\n"
    "每隔3秒，蓝狗会向随机方向投掷一本信息量爆炸的“永恒流光设定集”。设定集会在场上如冰球般无休止地反弹，留在原地不会消失。一旦命中敌人，蓝狗会立刻造成15点伤害并强制眩晕敌人0.8秒，并额外召唤一只紫龙直接加入战场！眩晕结束时，敌人会被随机弹飞。\n\n"
    "【终极技能·全军出击】\n"
    "立刻召唤两只强化紫龙，所有未处于眩晕状态的敌人会被立刻强行眩晕5秒，并且每眩晕一个敌人，就会再次召唤一只紫龙。"
)

langou_lore = (
    "“咱决定在下个版本往时空里加超形上学的设定，不知道狗男会不会同意”\n\n"
)

register_almanac_entry(
    char_id="Langou",
    name="蓝狗",
    icon=ICON_LANGOU,
    stats=langou_stats,
    mechanics=langou_mechanics,
    lore=langou_lore
)