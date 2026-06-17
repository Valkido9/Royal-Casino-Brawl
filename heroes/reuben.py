import pygame
import math
import random
import os
import sys

from settings import WIDTH, HEIGHT, RED, BLUE, FPS
from core_classes import Agent, HIT_SOUNDS
from ui_components import get_cn_font

# ==========================================
# 1. 资源加载与路径预处理区
# ==========================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ASSET_DIR = os.path.join(BASE_DIR, "assets", "reuben")
SOUND_DIR = os.path.join(BASE_DIR, "sounds", "reuben")


def load_img(filename, size):
    try:
        img_path = os.path.join(ASSET_DIR, filename)
        raw_img = pygame.image.load(img_path)
        return pygame.transform.smoothscale(raw_img, size)
    except Exception as e:
        print(f"Reuben 加载图片失败: {filename}，错误: {e}")
        return None


ICON_NORMAL = load_img("icon_normal.jpg", (120, 120))
ICON_ANGRY = load_img("icon_angry.png", (120, 120))
ICON_HAQI = load_img("icon_haqi.png", (120, 120))
ICON_ATTACK = load_img("icon_attack.png", (120, 120))

IMG_CLAW = load_img("claw.png", (360, 360))
IMG_CLAW_ULT = load_img("claw.png", (260, 260))
IMG_FIRE = load_img("fire.png", (240, 240))
IMG_PUMP = load_img("daqi.png", (120, 120))

if IMG_CLAW_ULT is None and IMG_CLAW is not None:
    IMG_CLAW_ULT = pygame.transform.smoothscale(IMG_CLAW, (260, 260))


def load_snd(filename):
    try:
        return pygame.mixer.Sound(os.path.join(SOUND_DIR, filename))
    except:
        return None


REVIVE_SND = load_snd("revive.mp3")
HAQI_SND = load_snd("haqi.mp3")
ULT_SND = load_snd("ultimate.mp3")

try:
    REVIVE_FRAMES = int(REVIVE_SND.get_length() * FPS)
except:
    REVIVE_FRAMES = int(2.0 * FPS)

ULT_START_FRAMES = int(0.5 * FPS)


# ==========================================
# 2. 专属弹幕/特殊轨迹类
# ==========================================
class ReubenSonicWave:
    def __init__(self, x, y, angle, damage, owner_faction):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * 10
        self.vy = math.sin(angle) * 10
        self.owner_faction = owner_faction

        self.radius = 0
        self.damage = 0
        self.infinite_bounce = True

        self.real_damage = damage
        self.hit_targets = set()

        self.max_life = 210
        self.life = 210
        self.active = True

    @property
    def real_radius(self):
        return 25 + (self.max_life - self.life) * 1.5

    def move(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.life <= 0:
            self.active = False

    def draw(self, surface):
        alpha = max(0, min(255, int((self.life / self.max_life) * 255)))

        surf = pygame.Surface((800, 800), pygame.SRCALPHA)
        current_r1 = self.real_radius
        current_r2 = 10 + (self.max_life - self.life) * 1.5

        if current_r1 < 400:
            pygame.draw.circle(surf, (0, 190, 255, alpha), (400, 400), int(current_r1), 6)
        if current_r2 > 0 and current_r2 < 400:
            pygame.draw.circle(surf, (100, 220, 255, alpha), (400, 400), int(current_r2), 4)

        surface.blit(surf, (int(self.x) - 400, int(self.y) - 400))


class ReubenUltController:
    def __init__(self, x, y, vx, vy, damage, owner_faction):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.owner_faction = owner_faction

        self.radius = -999
        self.damage = 0
        self.infinite_bounce = True

        self.real_damage = damage
        self.life = FPS * 5
        self.active = True
        self.is_reuben_ult_controller = True

    def move(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.life <= 0:
            self.active = False

        if self.x < 50:
            self.x = 50
            self.vx *= -1
        elif self.x > WIDTH - 50:
            self.x = WIDTH - 50
            self.vx *= -1

        if self.y < 50:
            self.y = 50
            self.vy *= -1
        elif self.y > HEIGHT - 50:
            self.y = HEIGHT - 50
            self.vy *= -1

    def draw(self, surface):
        pass


class ReubenUltClawStationary:
    def __init__(self, x, y, damage, owner_faction):
        self.x = x
        self.y = y
        self.owner_faction = owner_faction

        self.radius = -999
        self.damage = 0
        self.infinite_bounce = True

        self.real_radius = 110
        self.real_damage = damage / FPS

        self.life = 180
        self.max_life = 180
        self.active = True
        self.is_reuben_ult_claw = True

    def move(self):
        self.life -= 1
        if self.life <= 0:
            self.active = False

    def draw(self, surface):
        if IMG_CLAW_ULT:
            temp = IMG_CLAW_ULT.copy()
            if self.life > self.max_life - 15:
                alpha = int((self.max_life - self.life) / 15 * 255)
            else:
                alpha = min(255, int((self.life / (self.max_life - 15)) * 255 * 1.5))
            temp.set_alpha(max(0, min(255, alpha)))
            surface.blit(temp, (int(self.x) - 130, int(self.y) - 130))
        else:
            pygame.draw.circle(surface, (255, 0, 0), (int(self.x), int(self.y)), 110, 5)


class ReubenActiveClaw:
    def __init__(self, x, y, angle, damage, owner_faction):
        self.x = x
        self.y = y

        self.vx = 0
        self.vy = 0
        self.owner_faction = owner_faction

        self.radius = -999
        self.damage = 0
        self.infinite_bounce = True

        self.life = 180
        self.max_life = 180
        self.active = True

        self.is_reuben_claw = True
        self.real_damage = damage
        self.hit_targets = set()

        if IMG_CLAW:
            deg_angle = math.degrees(-angle)
            self.image = pygame.transform.rotate(IMG_CLAW, deg_angle)
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
            self.mask = pygame.mask.from_surface(self.image)
        else:
            self.image = None
            self.mask = None

    def move(self):
        self.life -= 1
        if self.life <= 0:
            self.active = False

    def draw(self, surface):
        if self.image:
            temp_claw = self.image.copy()
            alpha = int((self.life / self.max_life) * 255)
            temp_claw.set_alpha(max(0, alpha))
            surface.blit(temp_claw, self.rect)


# ==========================================
# 3. 英雄主体：肉本 (Reuben)
# ==========================================
class Reuben(Agent):
    def __init__(self, x, y, color, faction):
        self._is_ready = False
        self._reuben_hp = 100
        super().__init__(x, y, color, faction, image=ICON_NORMAL)

        self.original_radius = self.radius

        self.max_hp = 100
        self.base_speed = 5.5
        self.knockback_immune = False
        self.reflects_attacker = False

        self.lives = 9
        self.fatal_shield_used = False

        self.state = "NORMAL"
        self.life_survival_timer = 0
        self.is_angry = False

        self.haqi_cooldown = 0
        self.haqi_action_timer = 0
        self.attack_action_timer = 0
        self.melee_cd = 0

        self.attack_target = None
        self.has_slashed = False

        self.dead_image = ICON_NORMAL

        self.rage_particles = []

        self.hp = 100
        self._is_ready = True

    @property
    def _hp(self):
        return self.hp

    @_hp.setter
    def _hp(self, value):
        self.hp = value

    @property
    def hp(self):
        return getattr(self, '_reuben_hp', 0)

    @hp.setter
    def hp(self, value):
        if not getattr(self, '_is_ready', False):
            self._reuben_hp = value
            return

        current_hp = getattr(self, '_reuben_hp', None)
        if current_hp is not None and value < current_hp:
            if self.state in ["TIME_STOP", "REVIVING"]:
                return

            damage = current_hp - value

            # --- 核心修改：动态关联最大生命值！无论被改成 75HP 还是 3000HP，毒圈恒定2秒必死 ---
            expected_poison_damage = (self.max_hp * 0.05) / FPS
            if abs(damage - expected_poison_damage) < 0.001:
                damage = self.max_hp / (2.0 * FPS)
                value = current_hp - damage

            if current_hp - damage <= 0:
                if self.lives > 1:
                    self.lives -= 1
                    self.state = "REVIVING"

                    self.radius = -999
                    self.dead_image = getattr(self, 'image', ICON_NORMAL)

                    self.action_timer = REVIVE_FRAMES
                    self.stop_sounds()

                    if REVIVE_SND:
                        channel = pygame.mixer.find_channel(True)
                        if channel:
                            channel.play(REVIVE_SND)
                        else:
                            REVIVE_SND.play()

                    value = 1
                    self.life_survival_timer = 0
                    self.is_angry = False
                else:
                    value = 0

            if damage >= 1 and value > 0:
                self.hit_timer = 20
                if HIT_SOUNDS: random.choice(HIT_SOUNDS).play()

        self._reuben_hp = value

    def stop_sounds(self):
        for snd in [HAQI_SND, REVIVE_SND, ULT_SND]:
            if snd: snd.stop()

    def update_skill(self, bullet_list, agents=None):
        if agents is None: return

        if self.haqi_cooldown > 0: self.haqi_cooldown -= 1
        if self.melee_cd > 0: self.melee_cd -= 1

        if self.state == "REVIVING":
            self.vx, self.vy = 0, 0
            self.action_timer -= 1
            if self.action_timer <= 0:
                self.hp = getattr(self, 'max_hp', 100)

                self.state = "NORMAL"
                self.radius = getattr(self, 'original_radius', 60)
            return

        if self.state == "TIME_STOP":
            self.vx, self.vy = 0, 0
            self.ult_start_timer -= 1

            for _ in range(3):
                self.rage_particles.append({
                    "x": self.x + random.uniform(-40, 40),
                    "y": self.y + random.uniform(-20, 40),
                    "vx": random.uniform(-1.5, 1.5),
                    "vy": random.uniform(-6, -2),
                    "radius": random.randint(3, 7),
                    "life": 40
                })

            if self.ult_start_timer <= 0:
                self.state = "NORMAL"

                enemies = [a for a in agents if a.faction != self.faction and a.hp > 0 and getattr(a, 'radius', 0) > 0]
                base_angle = random.uniform(0, 2 * math.pi)
                if enemies:
                    target = min(enemies, key=lambda e: math.hypot(self.x - e.x, self.y - e.y))
                    base_angle = math.atan2(target.y - self.y, target.x - self.x)

                ult_speed = 4.0
                vx_front = math.cos(base_angle) * ult_speed
                vy_front = math.sin(base_angle) * ult_speed
                vx_back = math.cos(base_angle + math.pi) * ult_speed
                vy_back = math.sin(base_angle + math.pi) * ult_speed

                ult_dmg = 20 if self.is_angry else 10
                bullet_list.append(ReubenUltController(self.x, self.y, vx_front, vy_front, ult_dmg, self.faction))
                bullet_list.append(ReubenUltController(self.x, self.y, vx_back, vy_back, ult_dmg, self.faction))
            return

        self.life_survival_timer += 1
        if self.life_survival_timer >= FPS * 3.5:
            self.is_angry = True

        if self.ult_charge >= 100:
            self.trigger_reuben_ultimate()
            return

        enemies = [a for a in agents if a.faction != self.faction and a.hp > 0 and getattr(a, 'radius', 0) > 0]

        for b in bullet_list:
            if getattr(b, 'is_reuben_ult_controller', False) and b.owner_faction == self.faction:
                if b.life % 60 == 0:
                    bullet_list.append(ReubenUltClawStationary(b.x, b.y, b.real_damage, self.faction))

            elif getattr(b, 'is_reuben_ult_claw', False) and b.owner_faction == self.faction:
                for e in enemies:
                    if math.hypot(b.x - e.x, b.y - e.y) < b.real_radius + e.radius:
                        e.hp -= b.real_damage
                        e.ult_charge = max(0, getattr(e, 'ult_charge', 0) - 2.0)

            elif isinstance(b, ReubenSonicWave) and b.owner_faction == self.faction:
                if b.active:
                    for e in enemies:
                        if e not in b.hit_targets:
                            if math.hypot(b.x - e.x, b.y - e.y) < b.real_radius + e.radius:
                                e.hp -= b.real_damage
                                b.hit_targets.add(e)

                                self.melee_cd = 0
                                self.state = "CHASE"
                                self.attack_target = e
                                self.haqi_action_timer = 0

                                b.active = False
                                break

            elif getattr(b, 'is_reuben_claw', False) and b.owner_faction == self.faction and b.image:
                for e in enemies:
                    if e not in b.hit_targets:
                        if math.hypot(b.x - e.x, b.y - e.y) < max(b.rect.width, b.rect.height) / 2 + e.radius:
                            e_surf = pygame.Surface((int(e.radius * 2), int(e.radius * 2)), pygame.SRCALPHA)
                            pygame.draw.circle(e_surf, (255, 255, 255, 255), (int(e.radius), int(e.radius)),
                                               int(e.radius))
                            e_mask = pygame.mask.from_surface(e_surf)

                            offset_x = int((e.x - e.radius) - b.rect.x)
                            offset_y = int((e.y - e.radius) - b.rect.y)

                            if b.mask.overlap(e_mask, (offset_x, offset_y)):
                                e.hp -= b.real_damage
                                e.vx *= 0.4
                                e.vy *= 0.4
                                b.hit_targets.add(e)

        if not enemies:
            self.wander_around()
            return

        closest_enemy = min(enemies, key=lambda e: math.hypot(self.x - e.x, self.y - e.y))
        dist = math.hypot(self.x - closest_enemy.x, self.y - closest_enemy.y)

        if self.state == "HAQI":
            self.vx *= 0.4
            self.vy *= 0.4
            self.haqi_action_timer -= 1

            trigger_frames = [int(0.4 * FPS), int(0.2 * FPS), 0]
            if self.haqi_action_timer in trigger_frames:
                angle = math.atan2(closest_enemy.y - self.y, closest_enemy.x - self.x)
                angle += random.uniform(-0.15, 0.15)
                sonic_dmg = 12 if self.is_angry else 8
                bullet_list.append(ReubenSonicWave(self.x, self.y, angle, sonic_dmg, self.faction))

            if self.haqi_action_timer <= 0:
                self.state = "NORMAL"
            return

        elif self.state == "CHASE":
            if self.attack_target and self.attack_target.hp > 0 and getattr(self.attack_target, 'radius', 0) > 0:
                dist_to_target = math.hypot(self.x - self.attack_target.x, self.y - self.attack_target.y)
                angle = math.atan2(self.attack_target.y - self.y, self.attack_target.x - self.x)
                self.vx = math.cos(angle) * self.base_speed
                self.vy = math.sin(angle) * self.base_speed

                if dist_to_target < 140 and self.melee_cd <= 0:
                    self.state = "ATTACK"
                    self.has_slashed = False
                    self.attack_action_timer = int(0.6 * FPS)
            else:
                self.state = "NORMAL"
            return

        elif self.state == "ATTACK":
            self.attack_action_timer -= 1

            if self.attack_target and self.attack_target.hp > 0 and getattr(self.attack_target, 'radius', 0) > 0:
                target_x, target_y = self.attack_target.x, self.attack_target.y
            else:
                target_x, target_y = closest_enemy.x, closest_enemy.y

            angle = math.atan2(target_y - self.y, target_x - self.x)

            self.vx = math.cos(angle) * self.base_speed
            self.vy = math.sin(angle) * self.base_speed

            if not self.has_slashed and self.attack_action_timer <= int(0.3 * FPS):
                self.has_slashed = True
                dmg = 90 if self.is_angry else 65

                real_target = self.attack_target if (
                        self.attack_target and self.attack_target.hp > 0 and getattr(self.attack_target, 'radius',
                                                                                     0) > 0) else closest_enemy

                spawn_x = self.x + math.cos(angle) * 70
                spawn_y = self.y + math.sin(angle) * 70
                claw = ReubenActiveClaw(spawn_x, spawn_y, angle, dmg, self.faction)

                if math.hypot(self.x - real_target.x, self.y - real_target.y) <= 180 + getattr(real_target, 'radius',
                                                                                               0):
                    real_target.hp -= dmg
                    claw.hit_targets.add(real_target)

                bullet_list.append(claw)

            if self.attack_action_timer <= 0:
                self.state = "NORMAL"
                self.melee_cd = int(0.5 * FPS)
            return

        elif self.state == "NORMAL":
            self.wander_around()
            if dist < 140 and self.melee_cd <= 0:
                self.state = "ATTACK"
                self.attack_target = closest_enemy
                self.has_slashed = False
                self.attack_action_timer = int(0.6 * FPS)
            elif dist >= 140 and self.haqi_cooldown <= 0:
                self.state = "HAQI"
                self.haqi_action_timer = int(0.5 * FPS)
                self.haqi_cooldown = int(8.0 * FPS)
                if HAQI_SND: HAQI_SND.play()

    def wander_around(self):
        speed = math.hypot(self.vx, self.vy)
        if speed < 1:
            angle = random.uniform(0, 2 * math.pi)
            self.vx = math.cos(angle) * self.base_speed
            self.vy = math.sin(angle) * self.base_speed
        else:
            self.vx = (self.vx / speed) * self.base_speed
            self.vy = (self.vy / speed) * self.base_speed

    def trigger_reuben_ultimate(self):
        self.stop_sounds()
        self.state = "TIME_STOP"
        self.ult_charge = 0
        self.ult_start_timer = int(0.5 * FPS)
        self.vx, self.vy = 0, 0

        if ULT_SND:
            channel = pygame.mixer.find_channel(True)
            if channel:
                channel.play(ULT_SND)
            else:
                ULT_SND.play()

    def draw(self, surface):
        for p in list(self.rage_particles):
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
            size = max(1, int(p["radius"] * (p["life"] / 40)))
            pygame.draw.circle(surface, (255, random.randint(50, 160), 0), (int(p["x"]), int(p["y"])), size)
            if p["life"] <= 0:
                self.rage_particles.remove(p)

        if self.is_angry and self.state != "REVIVING":
            if IMG_FIRE:
                f_rect = IMG_FIRE.get_rect(center=(int(self.x), int(self.y)))
                surface.blit(IMG_FIRE, f_rect)
            else:
                pygame.draw.circle(surface, (255, 60, 0), (int(self.x), int(self.y)), max(0, self.radius) + 15, 6)

        current_frame_img = ICON_NORMAL
        if self.state in ["HAQI", "TIME_STOP"]:
            current_frame_img = ICON_HAQI
        elif self.state == "ATTACK":
            current_frame_img = ICON_ATTACK
        elif self.is_angry:
            current_frame_img = ICON_ANGRY

        if self.state == "REVIVING":
            flat_h = max(12, int(120 * (1.0 - (self.action_timer / REVIVE_FRAMES))))

            if getattr(self, 'dead_image', None):
                flat_img = pygame.transform.smoothscale(self.dead_image, (120, flat_h))
                rect = flat_img.get_rect(center=(int(self.x), int(self.y) + (60 - flat_h // 2)))
                surface.blit(flat_img, rect)

            if IMG_PUMP:
                pulse_factor = 1.0 + 0.18 * math.sin((REVIVE_FRAMES - self.action_timer) * 0.85)
                scaled_w = int(120 * pulse_factor)
                scaled_h = int(120 * pulse_factor)
                scaled_pump = pygame.transform.smoothscale(IMG_PUMP, (scaled_w, scaled_h))

                pump_rect = scaled_pump.get_rect(center=(int(self.x + 85), int(self.y + 10)))
                surface.blit(scaled_pump, pump_rect)
            else:
                pump_x = int(self.x + 55)
                pump_y = int(self.y - 10)
                handle_bounce = int(math.sin(self.action_timer * 0.4) * 15)

                pygame.draw.rect(surface, (220, 40, 40), (pump_x, pump_y, 16, 45))
                pygame.draw.rect(surface, (70, 70, 70), (pump_x - 4, pump_y + 40, 24, 6))
                pygame.draw.line(surface, (180, 180, 180), (pump_x + 8, pump_y),
                                 (pump_x + 8, pump_y - 15 + handle_bounce), 4)
                pygame.draw.line(surface, (30, 30, 30), (pump_x - 6, pump_y - 15 + handle_bounce),
                                 (pump_x + 22, pump_y - 15 + handle_bounce), 5)
                pygame.draw.line(surface, (20, 20, 20), (pump_x, pump_y + 35), (int(self.x), int(self.y + 20)), 2)
        else:
            if current_frame_img:
                self.image = current_frame_img
            super().draw(surface)

        if self.hp > 0 and self.state != "REVIVING":
            font = get_cn_font(18)
            lives_txt = font.render(f"猫命 x{self.lives}", True, (255, 165, 0))
            surface.blit(lives_txt, (self.x - lives_txt.get_width() // 2, self.y - 105))

# ==========================================
# 4. 图鉴数据注册
# ==========================================
from almanac import register_almanac_entry

reuben_stats = {
    "常态伤害": "声波(8) / 爪击(65)",
    "暴怒伤害": "声波(12) / 爪击(90)",
    "基础移速": "5.5",
}

reuben_mechanics = (
    "【被动·九命耄耋】\n"
    "肉本天生拥有9条命。当生命值归零时，她会原地变成一张“猫饼”并进入打气复活状态。2秒后满血复活并消耗一条命。作为惩罚，肉本在毒圈外每秒流失50%的血量。\n\n"
    "【被动·狂暴沸血】\n"
    "在场上存活超过3.5秒后，肉本将被激怒进入【暴怒状态】（伴随烈火特效）。她的所有技能伤害将获得全面提升。\n\n"
    "【普攻·哈气 / 抓人】\n"
    "距离较远时，她会向敌人连续哈出三道不断扩大的声波环（造成8点伤害，暴怒12点）。当她利用声波击中敌人时，肉本将会主动向敌人靠近。当肉本离敌人足够近时，将会发起猛烈的近战撕咬（造成65点伤害，暴怒90点）。如果肉本哈气哈到了人，将会立刻重置抓人的CD。\n\n"
    "【终极技能·耄耋天王阵】\n"
    "肉本向前后两个方向射出两道狂暴的终极爪击控制器（伤害10点，暴怒20点）。这两道控制器会在全场蔓延，并且每隔1秒就会在它们当前的位置留下一个巨大的“血色抓痕阵”。\n"
    "抓痕阵会在场上存在整整3秒，对误入其中的敌人造成高频持续伤害，并极其霸道地抹除敌人的大招能量！"
)

reuben_lore = (
    "肉本在一家动漫公司上班，平时一直在给日漫做外包。但是她的拼好饭经常被偷，有些时候，这让她非常暴怒，于是她会化身耄耋。\n\n"
)

# 注册进入图鉴系统
register_almanac_entry(
    char_id="Reuben",
    name="肉本",
    icon=ICON_NORMAL,
    stats=reuben_stats,
    mechanics=reuben_mechanics,
    lore=reuben_lore
)