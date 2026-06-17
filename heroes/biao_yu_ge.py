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

ASSET_DIR = os.path.join(BASE_DIR, "assets", "biaoyuge")
SOUND_DIR = os.path.join(BASE_DIR, "sounds", "biaoyuge")


def load_img(filename, size):
    try:
        img_path = os.path.join(ASSET_DIR, filename)
        raw_img = pygame.image.load(img_path)
        return pygame.transform.smoothscale(raw_img, size)
    except Exception as e:
        print(f"BiaoYuGe 加载图片失败: {filename}，错误: {e}")
        return None


ICON_FISH = load_img("icon-fish.jpg", (120, 120))
ICON_RIDER = load_img("icon-rider.jpg", (120, 120))
WEAPON_FISH = load_img("weapon-fish.png", (280, 140))
WEAPON_SWORD = load_img("weapon-sword.png", (80, 240))
GUAZI_IMG = load_img("guazi.png", (170, 170))
SHOE_IMG = load_img("shoe.png", (60, 60))


def load_snd(filename):
    try:
        return pygame.mixer.Sound(os.path.join(SOUND_DIR, filename))
    except:
        return None


ULT_SND = load_snd("ultimate.mp3")
try:
    ULT_LENGTH_FRAMES = int((ULT_SND.get_length() * 120) / 2)
except:
    ULT_LENGTH_FRAMES = 120

KICK_SND = load_snd("riderkick.mp3")
SHIELD_SND = load_snd("shield.mp3")


# ==========================================
# 2. 特效与道具类
# ==========================================
class GuaziSeed:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.life = 1200
        self.delay = 60


class TransformParticle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(8, 25)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.size = random.randint(5, 15)
        self.color = (random.randint(0, 50), random.randint(200, 255), random.randint(200, 255))
        self.life = random.randint(40, 100)

    def move(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.88
        self.vy *= 0.88
        self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            pygame.draw.rect(surface, self.color, (int(self.x), int(self.y), self.size, self.size))


# ==========================================
# 3. 标·鱼哥 英雄主体 logic
# ==========================================
class BiaoYuGe(Agent):
    def __init__(self, x, y, color, faction):
        super().__init__(x, y, color, faction, image=ICON_FISH)

        self.atk = 0
        self.base_speed = 6
        self.knockback_immune = True
        self.shield = 0

        self.fish_angle = 0
        self.fish_base_dmg = 25
        self.fish_hit_cd = {}

        self.state = "NORMAL"

        self.kick_count = 0
        self.kick_phase = "WAIT"
        self.kick_timer = 0
        self.dash_target = None
        self.seeds = []

        self.current_fish_count = 1

        self.ult_timer = 0
        self.particles = []

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, value):
        if hasattr(self, '_hp') and value < self._hp:
            damage = self._hp - value

            if getattr(self, 'state', 'NORMAL') == "RIDER":
                damage *= 0.5
                self._rider_pending_reflect = getattr(self, '_rider_pending_reflect', 0) + damage

            if getattr(self, 'shield', 0) > 0:
                if self.shield >= damage:
                    self.shield -= damage
                    damage = 0
                else:
                    damage -= self.shield
                    self.shield = 0

            value = self._hp - damage
            if damage > 0:
                self.hit_timer = 20
                if HIT_SOUNDS: random.choice(HIT_SOUNDS).play()
        self._hp = value

    def update_skill(self, bullet_list, agents=None):
        if agents is None: return

        if self.shield > self.max_hp:
            self.shield = self.max_hp

        if self.state in ["RIDER", "TIME_STOP"]:
            self.ult_charge = 0
        else:
            if self.ult_charge < 100:
                self.ult_charge = min(100, self.ult_charge + 0.020)

        is_stunned = getattr(self, 'langou_stun_timer', 0) > 0

        # --- 1. 种子生命周期与食用逻辑 ---
        for seed in self.seeds[:]:
            seed.life -= 1
            if seed.delay > 0:
                seed.delay -= 1

            if seed.life <= 0:
                self.seeds.remove(seed)
            # 如果处于眩晕状态，绝对禁止拾取/消化身边的瓜子
            elif not is_stunned and seed.delay <= 0 and math.hypot(self.x - seed.x, self.y - seed.y) < max(0,
                                                                                                           self.radius) + 15:
                self.shield += 80 * getattr(self, 'shield_multiplier', 1)

                if SHIELD_SND: SHIELD_SND.play()
                self.seeds.remove(seed)
                if self.state == "NORMAL":
                    self.ult_charge = min(100, self.ult_charge + 5)

        for e in list(self.fish_hit_cd.keys()):
            if self.fish_hit_cd[e] > 0:
                self.fish_hit_cd[e] -= 1

        hp_ratio = self.hp / self.max_hp

        # ==============================================================
        # --- 2. 无论是否眩晕，都需要强制执行的视觉与被动反伤逻辑 ---
        # ==============================================================

        if self.state == "RIDER":
            # 反伤逻辑：即使被眩晕，只要装甲在身被摸到就会反伤
            reflect_dmg = getattr(self, '_rider_pending_reflect', 0)
            if reflect_dmg > 0:
                for a in agents:
                    if a.faction != self.faction and a.hp > 0 and getattr(a, 'radius', 0) > 0:
                        if math.hypot(self.x - a.x, self.y - a.y) <= max(0, self.radius) + a.radius + 15:
                            a.hp -= reflect_dmg
                self._rider_pending_reflect = 0

            # 挡子弹逻辑
            for b in bullet_list[:]:
                if b.active and b.owner_faction != self.faction:
                    if math.hypot(self.x - b.x, self.y - b.y) < max(0, self.radius) + max(0, getattr(b, 'radius', 0)):
                        b.active = False
                        self.hp -= b.damage

        elif self.state == "NORMAL":
            # 鱼群旋转与判定逻辑：即使被眩晕，鱼群依然会转动并造成伤害
            self.current_fish_count = 1
            current_move_speed = 6
            current_fish_speed = 0.04
            current_fish_dmg = self.fish_base_dmg

            if hp_ratio <= 0.7:
                current_move_speed = 6 * 1.3
                current_fish_speed = 0.04 * 1.3
            if hp_ratio <= 0.5:
                self.current_fish_count = 2
            if hp_ratio <= 0.3:
                self.current_fish_count = 3
            if hp_ratio <= 0.1:
                self.current_fish_count = 4
                current_fish_dmg = self.fish_base_dmg * 2

            self.base_speed = current_move_speed

            orbit_radius = max(0, self.radius) + 80
            self.fish_angle += current_fish_speed

            enemies = [a for a in agents if a.faction != self.faction and a.hp > 0 and getattr(a, 'radius', 0) > 0]

            enemy_masks = {}
            if WEAPON_FISH:
                for e in enemies:
                    surf = pygame.Surface((int(e.radius * 2), int(e.radius * 2)), pygame.SRCALPHA)
                    pygame.draw.circle(surf, (255, 255, 255), (int(e.radius), int(e.radius)), int(e.radius))
                    enemy_masks[e] = pygame.mask.from_surface(surf)

            for i in range(self.current_fish_count):
                angle = self.fish_angle + i * (2 * math.pi / self.current_fish_count)
                fx = self.x + math.cos(angle) * orbit_radius
                fy = self.y + math.sin(angle) * orbit_radius

                fish_rect = None
                rotated_mask = None
                if WEAPON_FISH:
                    rotated_fish = pygame.transform.rotate(WEAPON_FISH, -math.degrees(angle))
                    fish_rect = rotated_fish.get_rect(center=(int(fx), int(fy)))
                    rotated_mask = pygame.mask.from_surface(rotated_fish)

                for e in enemies:
                    if self.fish_hit_cd.get(e, 0) <= 0:
                        hit = False
                        if rotated_mask and fish_rect and e in enemy_masks:
                            offset = (int(e.x - e.radius - fish_rect.x), int(e.y - e.radius - fish_rect.y))
                            if rotated_mask.overlap(enemy_masks[e], offset):
                                hit = True
                        else:
                            if math.hypot(fx - e.x, fy - e.y) < 40 + e.radius:
                                hit = True

                        if hit:
                            e.hp -= current_fish_dmg
                            self.ult_charge = min(100, self.ult_charge + 2)
                            self.fish_hit_cd[e] = 30

        # ==============================================================
        # --- 3. 眩晕拦截器：冻结主动状态机，强制停止物理移动 ---
        # ==============================================================
        if is_stunned:
            self.vx = 0
            self.vy = 0
            return

        # ==============================================================
        # --- 4. 主动状态机 (只在未眩晕时执行，完美冻结节奏) ---
        # ==============================================================

        if self.state == "TIME_STOP":
            self.ult_timer -= 1
            for p in self.particles:
                p.move()

            if self.ult_timer <= 0:
                self.state = "RIDER"
                self.image = ICON_RIDER if ICON_RIDER else None
                self.kick_phase = "WAIT"
                self.kick_timer = 0
                self.base_speed = 12
                self.normalize_speed()

        elif self.state == "RIDER":
            if self.kick_phase == "WAIT":
                self.kick_timer -= 1

                if math.hypot(self.vx, self.vy) < 1:
                    angle = random.uniform(0, 2 * math.pi)
                    self.vx = math.cos(angle) * self.base_speed
                    self.vy = math.sin(angle) * self.base_speed

                if self.kick_timer <= 0:
                    enemies = [a for a in agents if
                               a.faction != self.faction and a.hp > 0 and getattr(a, 'radius', 0) > 0]
                    if enemies:
                        self.dash_target = min(enemies, key=lambda e: math.hypot(self.x - e.x, self.y - e.y))
                        self.kick_phase = "DASH"
                        self.kick_timer = 80
                    else:
                        self.kick_timer = 30
                        self.normalize_speed()

            elif self.kick_phase == "DASH":
                self.kick_timer -= 1

                if self.dash_target and self.dash_target.hp > 0 and getattr(self.dash_target, 'radius', 0) > 0:
                    angle = math.atan2(self.dash_target.y - self.y, self.dash_target.x - self.x)
                    self.vx = math.cos(angle) * 35
                    self.vy = math.sin(angle) * 35
                else:
                    self.kick_phase = "WAIT"
                    self.kick_timer = 30
                    self.normalize_speed()
                    return

                # 这里正常掉落瓜子，因为只要进来这里说明没有被晕
                if self.kick_timer % 5 == 0:
                    self.seeds.append(GuaziSeed(self.x, self.y))

                enemies = [a for a in agents if a.faction != self.faction and a.hp > 0 and getattr(a, 'radius', 0) > 0]
                hit_enemy = None
                for e in enemies:
                    if math.hypot(self.x - e.x, self.y - e.y) < max(0, self.radius) + getattr(e, 'radius', 0) + 30:
                        hit_enemy = e
                        break

                if hit_enemy or self.kick_timer <= 0:
                    if hit_enemy:
                        if KICK_SND: KICK_SND.play()
                        sword_dmg = self.fish_base_dmg * self.current_fish_count * 2.1
                        hit_enemy.hp -= sword_dmg
                        kick_angle = math.atan2(self.vy, self.vx)
                        hit_enemy.vx = math.cos(kick_angle) * 45
                        hit_enemy.vy = math.sin(kick_angle) * 45
                        hit_enemy.is_knocked_back = True

                    self.kick_count += 1
                    self.normalize_speed()
                    if self.kick_count >= 3:
                        self.end_ultimate()
                    else:
                        self.kick_phase = "WAIT"
                        self.kick_timer = 360

        elif self.state == "NORMAL":
            if self.ult_charge >= 100:
                self.trigger_ultimate()
                return
            self.normalize_speed()

    def trigger_ultimate(self):
        self.state = "TIME_STOP"
        self.ult_charge = 0
        self.ult_timer = ULT_LENGTH_FRAMES
        self.kick_count = 0
        self.particles = [TransformParticle(self.x, self.y) for _ in range(100)]
        self.vx, self.vy = 0, 0
        if ULT_SND: ULT_SND.play()

    def end_ultimate(self):
        self.state = "NORMAL"
        self.image = ICON_FISH if ICON_FISH else None
        self.base_speed = 6
        self.normalize_speed()

    def normalize_speed(self):
        mag = math.hypot(self.vx, self.vy)
        if mag > 0:
            self.vx = (self.vx / mag) * self.base_speed
            self.vy = (self.vy / mag) * self.base_speed
        else:
            # --- 核心修改：防卡死补丁，在解除眩晕后如果速度完全归零，手动重启引擎 ---
            angle = random.uniform(0, 2 * math.pi)
            self.vx = math.cos(angle) * self.base_speed
            self.vy = math.sin(angle) * self.base_speed

    def draw(self, surface):
        if self.hp / self.max_hp <= 0.1 and self.state not in ["RIDER", "TIME_STOP"]:
            pulse = math.sin(pygame.time.get_ticks() / 50) * 5
            aura_radius = int(max(0, self.radius) + 15 + pulse)
            pygame.draw.circle(surface, (255, 50, 50), (int(self.x), int(self.y)), aura_radius, width=5)

        super().draw(surface)

        if self.state == "TIME_STOP":
            for p in self.particles:
                p.draw(surface)

            if ICON_RIDER and ULT_LENGTH_FRAMES > 0:
                progress = 1.0 - max(0, self.ult_timer / ULT_LENGTH_FRAMES)
                alpha = int(255 * progress)
                temp_rider = ICON_RIDER.copy()
                temp_rider.set_alpha(alpha)
                rect = temp_rider.get_rect(center=(int(self.x), int(self.y)))
                surface.blit(temp_rider, rect)

        if getattr(self, 'shield', 0) > 0:
            shield_ratio = self.shield / self.max_hp
            bar_width = max(0, self.radius) * 1.8
            bar_x = self.x - bar_width / 2
            bar_y = self.y - max(0, self.radius) - 20
            pygame.draw.rect(surface, (0, 200, 255), (bar_x, bar_y, bar_width * shield_ratio, 4))

        for seed in self.seeds:
            if GUAZI_IMG:
                rect = GUAZI_IMG.get_rect(center=(int(seed.x), int(seed.y)))
                surface.blit(GUAZI_IMG, rect)

        if self.state == "NORMAL":
            orbit_radius = max(0, self.radius) + 80
            for i in range(self.current_fish_count):
                angle = self.fish_angle + i * (2 * math.pi / self.current_fish_count)
                fx = self.x + math.cos(angle) * orbit_radius
                fy = self.y + math.sin(angle) * orbit_radius

                if WEAPON_FISH:
                    rotated_fish = pygame.transform.rotate(WEAPON_FISH, -math.degrees(angle))
                    rect = rotated_fish.get_rect(center=(int(fx), int(fy)))
                    surface.blit(rotated_fish, rect)

        elif self.state == "RIDER":
            move_angle = math.atan2(self.vy, self.vx)
            if self.kick_phase == "DASH" and self.dash_target and self.dash_target.hp > 0:
                move_angle = math.atan2(self.dash_target.y - self.y, self.dash_target.x - self.x)

            if WEAPON_SWORD:
                sword_x = self.x + math.cos(move_angle + math.pi / 2) * (max(0, self.radius) + 40)
                sword_y = self.y + math.sin(move_angle + math.pi / 2) * (max(0, self.radius) + 40)
                rotated_sword = pygame.transform.rotate(WEAPON_SWORD, -math.degrees(move_angle) - 45)
                rect = rotated_sword.get_rect(center=(int(sword_x), int(sword_y)))
                surface.blit(rotated_sword, rect)

            if self.kick_phase == "DASH" and SHOE_IMG:
                shoe_x = self.x + math.cos(move_angle) * (max(0, self.radius) + 70)
                shoe_y = self.y + math.sin(move_angle) * (max(0, self.radius) + 70)
                rotated_shoe = pygame.transform.rotate(SHOE_IMG, -math.degrees(move_angle))
                rect = rotated_shoe.get_rect(center=(int(shoe_x), int(shoe_y)))
                surface.blit(rotated_shoe, rect)

# ==========================================
# 4. 图鉴数据注册
# ==========================================
from almanac import register_almanac_entry

biaoyuge_stats = {
    "飞鱼伤害": "25 ~ 50 (随血量翻倍)",
    "骑士踢伤害": "52.5 ~ 210 (受飞鱼数量加成)",
    "基础移速": "6 (常态) / 12 (骑士形态)",
    "特殊属性": "全程霸体、护盾机制、受击反弹",
    "大招充能": "缓慢 (可吃瓜子加速充能)"
}

biaoyuge_mechanics = (
    "【被动·背水一战】\n"
    "鱼哥天生拥有霸体。常态下他的身边环绕着飞鱼，对触碰的敌人造成伤害。随着生命值不断降低（70%/50%/30%/10%），他的移速和飞鱼转速会越来越快，飞鱼数量也会逐渐增加至最多4条。当血量低于10%时，他会进入红温状态，飞鱼伤害将会直接翻倍！\n\n"
    "【战术道具·蟹黄瓜子仁】\n"
    "拾取掉落在地上的“瓜子”可以瞬间恢复80点护盾（受Boss词条增幅），并额外增加5点大招能量。不过，如果鱼哥处于被眩晕状态，将无法吃蟹黄瓜子仁。\n\n"
    "【终极技能·蟹黄瓜子仁味骑士踢】\n"
    "满能量时，鱼哥将会化身“假面骑士otto”！他的移速会飙升至原本的2倍，并自动锁定敌人发动3次势大力沉的“骑士飞踢”，将敌人猛烈击退。飞踢的伤害受当前环绕的飞鱼数量加成，且会在冲刺的沿途生成蟹黄味瓜子仁！\n\n"
    "【骑士特权·装甲反伤】\n"
    "在假面骑士形态下，鱼哥能用肉身直接撞碎敌人的飞行弹幕；同时，他受到的所有伤害都会获得 50% 的高额硬减免，并且这 50% 会被转化为能量反震，全额反弹给周围所有贴身的敌人！"
)

biaoyuge_lore = (
    "身为孟加拉国的首席大将军，鱼哥虽然在大部分情况下都是一个喜欢打英雄联盟的普通青年，但某些时候，他也会以假面骑士otto的身份出现，拯救世界，守护人间！"
)

# 注册进入图鉴系统
register_almanac_entry(
    char_id="BiaoYuGe",
    name="标·鱼哥",
    icon=ICON_FISH,  # 使用常态的鱼哥头像
    stats=biaoyuge_stats,
    mechanics=biaoyuge_mechanics,
    lore=biaoyuge_lore
)