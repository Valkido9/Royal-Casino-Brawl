# Created by: EternityBoundary on Jun 18, 2026
# AI注解還是沒修好，所以這是這份腳本最後一條注解，祝你好運
from __future__ import annotations

import math
import random
from typing import Any, List, MutableSequence, Optional, Sequence, Tuple

import pygame

from settings import FPS, HEIGHT, WIDTH
from core_classes import Agent, Bullet, HIT_SOUNDS


Color = Tuple[int, int, int]


def _build_boundary_icon() -> pygame.Surface:
    surface = pygame.Surface((120, 120), pygame.SRCALPHA)
    center = (60, 60)

    for radius, color in [
        (58, (20, 22, 34, 255)),
        (52, (64, 48, 110, 255)),
        (44, (30, 170, 190, 240)),
        (34, (250, 210, 82, 235)),
        (24, (18, 26, 40, 255)),
    ]:
        pygame.draw.circle(surface, color, center, radius)

    pygame.draw.circle(surface, (255, 255, 255, 160), center, 56, width=3)
    pygame.draw.circle(surface, (255, 220, 90, 230), center, 36, width=4)

    font = pygame.font.Font(None, 40)
    text = font.render("boundary", True, (255, 255, 255))
    surface.blit(text, text.get_rect(center=center))
    return surface


def _build_card_image() -> pygame.Surface:
    surface = pygame.Surface((54, 70), pygame.SRCALPHA)
    points = [(27, 0), (53, 12), (47, 69), (1, 58), (7, 10)]
    pygame.draw.polygon(surface, (255, 244, 180, 255), points)
    pygame.draw.polygon(surface, (34, 196, 214, 255), points, width=3)
    pygame.draw.line(surface, (118, 78, 210, 255), (15, 18), (40, 52), width=4)
    pygame.draw.line(surface, (118, 78, 210, 255), (39, 18), (14, 52), width=4)
    pygame.draw.circle(surface, (255, 210, 74, 255), (27, 35), 8)
    return surface


ICON_IMG = _build_boundary_icon()
CARD_IMG = _build_card_image()


class boundaryCard(Bullet):
    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        owner_faction: str,
        damage: float,
        target: Optional[Agent],
    ) -> None:
        super().__init__(x, y, vx, vy, owner_faction, damage, CARD_IMG)
        self.radius = 24
        self.target = target
        self.life = int(2.8 * FPS)
        self.max_life = self.life
        self.turn_rate = 0.12
        self.trail: List[Tuple[float, float]] = []

    def move(self) -> None:
        if self.target is not None and self.target.hp > 0:
            dx = self.target.x - self.x
            dy = self.target.y - self.y
            distance = math.hypot(dx, dy)
            if distance > 0:
                speed = max(13.0, math.hypot(self.vx, self.vy))
                wanted_vx = dx / distance * speed
                wanted_vy = dy / distance * speed
                self.vx = self.vx * (1.0 - self.turn_rate) + wanted_vx * self.turn_rate
                self.vy = self.vy * (1.0 - self.turn_rate) + wanted_vy * self.turn_rate

        speed_now = math.hypot(self.vx, self.vy)
        if speed_now > 0:
            self.vx = self.vx / speed_now * min(22.0, speed_now)
            self.vy = self.vy / speed_now * min(22.0, speed_now)

        self.trail.append((self.x, self.y))
        if len(self.trail) > 7:
            self.trail.pop(0)

        self.x += self.vx
        self.y += self.vy
        self.life -= 1

        if self.life <= 0:
            self.active = False
        elif (
            self.x < -self.radius
            or self.x > WIDTH + self.radius
            or self.y < -self.radius
            or self.y > HEIGHT + self.radius
        ):
            self.active = False

    def draw(self, surface: pygame.Surface) -> None:
        for idx, (tx, ty) in enumerate(self.trail):
            alpha = int(30 + idx * 18)
            pygame.draw.circle(surface, (80, 220, 235, alpha), (int(tx), int(ty)), max(2, idx + 2))

        angle = -math.degrees(math.atan2(self.vy, self.vx)) - 90
        rotated = pygame.transform.rotate(CARD_IMG, angle)
        rect = rotated.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rotated, rect)


class boundary(Agent):
    def __init__(self, x: float, y: float, color: Color, faction: str) -> None:
        self._shield = 0.0
        self._recent_damage = 0.0
        self._royal_guard_timer = 0
        super().__init__(x, y, color, faction, image=ICON_IMG)

        self.max_hp = 1350
        self._hp = self.max_hp
        self.atk = 38
        self.base_speed = 7.4
        self.knockback_immune = False

        self.state = "NORMAL"
        self.fire_cooldown = 24
        self.pulse_cooldown = int(1.6 * FPS)
        self.retaliation_cooldown = 0
        self.ultimate_timer = 0
        self.ultimate_fire_timer = 0
        self.ultimate_pulse_timer = 0
        self.visual_pulses: List[Tuple[float, int, Color]] = []

        self._shield = self._shield_capacity()
        self._normalize_speed(self.base_speed)

    @property
    def hp(self) -> float:
        return self._hp

    @hp.setter
    def hp(self, value: float) -> None:
        if hasattr(self, "_hp") and value < self._hp:
            current_hp = float(self._hp)
            incoming_damage = current_hp - float(value)
            poison_tick = getattr(self, "max_hp", 1000) * 0.05 / FPS
            is_poison_tick = getattr(self, "out_of_zone", False) and abs(incoming_damage - poison_tick) < 0.01

            if is_poison_tick:
                final_damage = incoming_damage
            else:
                mitigation = 0.42 if self._royal_guard_timer > 0 else 0.30
                reduced_damage = incoming_damage * (1.0 - mitigation)
                absorbed = min(self._shield, reduced_damage * 0.70)
                self._shield -= absorbed
                final_damage = max(0.0, reduced_damage - absorbed)
                self._recent_damage += incoming_damage
                self.ult_charge = min(100, self.ult_charge + min(12.0, incoming_damage * 0.045))

            if final_damage > 0 or incoming_damage > 0:
                self.hit_timer = 20
                if HIT_SOUNDS:
                    random.choice(HIT_SOUNDS).play()

            self._hp = current_hp - final_damage
            return

        max_hp = getattr(self, "max_hp", value)
        self._hp = min(float(value), float(max_hp))

    def update_skill(self, bullet_list: MutableSequence[Any], agents: Optional[Sequence[Agent]] = None) -> None:
        if agents is None:
            return

        enemies = [agent for agent in agents if agent.faction != self.faction and agent.hp > 0]
        self._update_timers()
        self._normalize_speed(self.base_speed * (1.18 if self.state == "ULTIMATE" else 1.0))
        self._recharge_shield()

        if self.state != "ULTIMATE":
            self.ult_charge = min(100, self.ult_charge + 0.038)
            if self.ult_charge >= 100:
                self.trigger_ultimate()
                return

        if self.retaliation_cooldown <= 0 and self._recent_damage >= 90 and enemies:
            self._retaliate(enemies)

        if self.state == "ULTIMATE":
            self._update_ultimate(bullet_list, enemies)
            return

        if enemies and self.fire_cooldown <= 0:
            self._fire_cards(bullet_list, enemies, count=3, damage=58.0)
            self.fire_cooldown = int(0.72 * FPS)

        if enemies and self.pulse_cooldown <= 0:
            self._pulse(enemies, radius=480.0, damage=92.0, drain=9.0, heal_ratio=0.42)
            self.pulse_cooldown = int(1.9 * FPS)

    def trigger_ultimate(self) -> None:
        self.state = "ULTIMATE"
        self.ult_charge = 0
        self.ultimate_timer = int(6.0 * FPS)
        self.ultimate_fire_timer = 0
        self.ultimate_pulse_timer = 0
        self._royal_guard_timer = self.ultimate_timer
        self._shield = self._shield_capacity()
        self.knockback_immune = True
        self.request_clear_bullets = True
        self.visual_pulses.append((760.0, 55, (255, 220, 80)))

    def _update_timers(self) -> None:
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
        if self.pulse_cooldown > 0:
            self.pulse_cooldown -= 1
        if self.retaliation_cooldown > 0:
            self.retaliation_cooldown -= 1
        if self._royal_guard_timer > 0:
            self._royal_guard_timer -= 1

        self._recent_damage *= 0.985
        self.visual_pulses = [
            (radius, life - 1, color) for radius, life, color in self.visual_pulses if life > 1
        ]

    def _update_ultimate(self, bullet_list: MutableSequence[Any], enemies: Sequence[Agent]) -> None:
        self.ultimate_timer -= 1
        self.hp = min(self.max_hp, self.hp + 0.45)

        if enemies and self.ultimate_fire_timer <= 0:
            self._fire_cards(bullet_list, enemies, count=6, damage=72.0, radial=True)
            self.ultimate_fire_timer = 12
        else:
            self.ultimate_fire_timer -= 1

        if enemies and self.ultimate_pulse_timer <= 0:
            self._pulse(enemies, radius=620.0, damage=125.0, drain=14.0, heal_ratio=0.50)
            self.ultimate_pulse_timer = int(0.85 * FPS)
        else:
            self.ultimate_pulse_timer -= 1

        if self.ultimate_timer <= 0:
            self.state = "NORMAL"
            self.knockback_immune = False
            self.fire_cooldown = int(0.4 * FPS)
            self.pulse_cooldown = int(1.2 * FPS)
            self._royal_guard_timer = int(1.0 * FPS)

    def _fire_cards(
        self,
        bullet_list: MutableSequence[Any],
        enemies: Sequence[Agent],
        count: int,
        damage: float,
        radial: bool = False,
    ) -> None:
        if not enemies:
            return

        base_target = min(enemies, key=lambda agent: math.hypot(self.x - agent.x, self.y - agent.y))
        base_angle = math.atan2(base_target.y - self.y, base_target.x - self.x)

        for idx in range(count):
            if radial:
                angle = (math.tau / count) * idx + random.uniform(-0.04, 0.04)
                target = enemies[idx % len(enemies)]
            else:
                spread = (idx - (count - 1) / 2.0) * 0.18
                angle = base_angle + spread + random.uniform(-0.05, 0.05)
                target = enemies[idx % len(enemies)]

            speed = 16.5 if self.state != "ULTIMATE" else 19.0
            bullet_list.append(
                boundaryCard(
                    self.x,
                    self.y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    self.faction,
                    damage,
                    target,
                )
            )

    def _pulse(
        self,
        enemies: Sequence[Agent],
        radius: float,
        damage: float,
        drain: float,
        heal_ratio: float,
    ) -> None:
        hits = 0
        for enemy in enemies:
            distance = math.hypot(self.x - enemy.x, self.y - enemy.y)
            if distance <= radius + enemy.radius:
                falloff = 1.0 - min(0.35, distance / max(radius, 1.0) * 0.35)
                dealt = damage * falloff
                enemy.hp -= dealt
                enemy.ult_charge = max(0, getattr(enemy, "ult_charge", 0) - drain)

                angle = math.atan2(enemy.y - self.y, enemy.x - self.x)
                enemy.vx = math.cos(angle) * 24
                enemy.vy = math.sin(angle) * 24
                enemy.is_knocked_back = True
                hits += 1

        if hits > 0:
            self.hp = min(self.max_hp, self.hp + damage * heal_ratio * hits)
            self._shield = min(self._shield_capacity(), self._shield + 24 * hits)
            self.visual_pulses.append((radius, 34, (34, 196, 214)))

    def _retaliate(self, enemies: Sequence[Agent]) -> None:
        retaliation_damage = min(155.0, 55.0 + self._recent_damage * 0.34)
        self._pulse(enemies, radius=520.0, damage=retaliation_damage, drain=6.0, heal_ratio=0.30)
        self._recent_damage = 0.0
        self.retaliation_cooldown = int(2.2 * FPS)
        self._royal_guard_timer = int(0.9 * FPS)

    def _recharge_shield(self) -> None:
        cap = self._shield_capacity()
        recharge = 0.34 if self._recent_damage < 8 else 0.12
        if self.state == "ULTIMATE":
            recharge *= 2.0
        self._shield = min(cap, self._shield + recharge)

    def _shield_capacity(self) -> float:
        return max(220.0, self.max_hp * 0.22)

    def _normalize_speed(self, target_speed: float) -> None:
        speed = math.hypot(self.vx, self.vy)
        if speed <= 0.01:
            angle = random.uniform(0, math.tau)
            self.vx = math.cos(angle) * target_speed
            self.vy = math.sin(angle) * target_speed
        else:
            self.vx = self.vx / speed * target_speed
            self.vy = self.vy / speed * target_speed

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        if self.hp <= 0:
            return

        shield_ratio = max(0.0, min(1.0, self._shield / self._shield_capacity()))
        ring_alpha = int(55 + 140 * shield_ratio)
        ring_radius = int(self.radius + 15 + 8 * math.sin(pygame.time.get_ticks() * 0.006))
        ring_surface = pygame.Surface((ring_radius * 2 + 8, ring_radius * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(
            ring_surface,
            (34, 196, 214, ring_alpha),
            (ring_radius + 4, ring_radius + 4),
            ring_radius,
            width=4,
        )
        surface.blit(ring_surface, (self.x - ring_radius - 4, self.y - ring_radius - 4))

        if self.state == "ULTIMATE":
            crown_font = pygame.font.Font(None, 30)
            crown = crown_font.render("HOUSE EDGE", True, (255, 226, 96))
            surface.blit(crown, crown.get_rect(center=(int(self.x), int(self.y - self.radius - 72))))

        for radius, life, color in self.visual_pulses:
            progress = 1.0 - life / 55.0
            current_radius = int(radius * max(0.15, progress))
            alpha = max(0, min(190, int(life / 55.0 * 190)))
            pulse_surface = pygame.Surface((current_radius * 2 + 8, current_radius * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(
                pulse_surface,
                (color[0], color[1], color[2], alpha),
                (current_radius + 4, current_radius + 4),
                current_radius,
                width=5,
            )
            surface.blit(pulse_surface, (self.x - current_radius - 4, self.y - current_radius - 4))


from almanac import register_almanac_entry


boundary_stats = {
    "生命值": "1350 + 可再生護盾",
    "近戰傷害": "38",
    "基礎移速": "7.4",
    "追蹤牌傷害": "58 / 大招期間72",
    "範圍脈沖": "92 / 大招期間125",
    "特殊屬性": "非毒圈傷害減免、受擊反擊、清彈開大",
}

boundary_mechanics = (
    "【第一權能・莊家優勢】\n"
    "自群星沉寂之夜起，Boundary便持有那份不可追溯的契約。祂的身軀被無形的護壁所環繞，猶如命運親手堆砌的高牆。\n"
    "凡俗的刀劍與術法，大多會在觸及本體之前被其吞沒。唯有來自終焉與腐朽的力量，仍能穿越那道屏障。\n"
    "據說，這並非防禦。而是世界本身對契約持有者的偏袒。\n\n"
    "【戒律之牌・校驗牌陣】\n"
    "Boundary將拋出三枚承載戒律的聖牌。它們循著因果的絲線飛行，追逐距離最近的靈魂。一旦被標記，獵物便如同被寫入預言，難以逃離其軌跡。\n"
    "古老文獻曾如此記載：「牌並非追逐敵人。」「而是命運將敵人送往牌前。」\n\n"
    "【天啟・藍金脈衝】\n"
    "當藍與金的聖輝在其體內交匯時，Boundary會釋放象徵裁決的波動。\n"
    "那光芒將震碎血肉、驅離不敬之人，並奪走其積蓄的力量。\n"
    "然而對於契約的持有者而言，眾生的痛苦亦是供奉。每一位受創者，都將為祂獻上新的生命與庇護。故而越是被眾人圍攻，祂便越接近完整。\n\n"
    "【逆律・風控回滾】\n"
    "古老契約從不允許天秤徹底失衡。當Boundary在短時間內承受過量傷害時，那份沉睡的條款便會自行甦醒。更加強大的裁決脈衝將自虛空降臨，而祂的身軀也將暫時被神聖律法覆蓋。\n"
    "世人將其視作反擊。但在殘缺石碑所記載的原文中，它被稱為：「世界對錯誤結果的修正。」\n\n"
    "【終極權能・House Edge】\n"
    "當契約完成最後一次輪轉之時，Boundary將接管整個戰場。所有飛行之物皆會被抹除。所有既定軌跡皆會被改寫。所有勝負皆將重新結算。六秒之內，祂將化作「莊家」。\n"
    "在那段被神諭稱為「優勢時刻」的時間裡：\n"
    "肉身不受撼動；\n"
    "護壁重歸圓滿；\n"
    "生命永不斷絕；\n"
    "戒律之牌如群星墜落；\n"
    "裁決脈衝如潮汐降臨。\n"
    "古代賭城的祭司們相信：世上並不存在真正的勝利。\n"
    "因為在一切遊戲開始之前，命運早已決定籌碼最終流向何處。而Boundary——正是那份命運的代行者。"
)

boundary_lore = (
    "在黃金尚未誕生、群星仍未被命名的時代，眾生曾向命運祈求公平。\n"
    "命運沒有回應。於是有人向更高之處獻上籌碼——記憶、壽命、王國，乃至自身的靈魂。\n"
    "最終，契約得以成立。而Boundary，便是那份契約的第一位見證者。祂不司掌財富，也不司掌勝利。\n"
    "祂所執掌的，乃是更古老的法則：「賭局可以開始。」「但結果從不平等。」"
)


register_almanac_entry(
    char_id="boundary",
    name="boundary",
    icon=ICON_IMG,
    stats=boundary_stats,
    mechanics=boundary_mechanics,
    lore=boundary_lore,
)
