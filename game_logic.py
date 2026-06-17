import pygame
import math
import random
import os
import sys

from settings import WIDTH, HEIGHT, RED, BLUE, FPS
from config import BET_TABLE, BG_MUSIC_PATH
from combat_system import resolve_combat
from ui_components import FallingParticle

from heroes.joker_ricky import JokerRicky
from heroes.lao_zheng import LaoZheng
from heroes.biao_yu_ge import BiaoYuGe
from heroes.mao import Mao
from heroes.reuben import Reuben
from heroes.langou import Langou
from heroes.liuba import LiuBa

AVAILABLE_CLASSES = [LaoZheng, BiaoYuGe, JokerRicky, Mao, Reuben, Langou, LiuBa]
HERO_NAME_MAP = {"BiaoYuGe": "鱼哥", "LaoZheng": "牢正", "JokerRicky": "曼波舞王", "Mao": "猫", "Reuben": "肉本", "Langou": "蓝狗", "LiuBa": "68"}


def start_new_round(app, force_left_cls=None, force_right_cls=None):
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.load(BG_MUSIC_PATH)
        pygame.mixer.music.set_volume(app.bgm_volume)
        pygame.mixer.music.play(-1)
    except:
        pass

    app.bullets.clear()
    app.scaled_bullets.clear()
    app.has_played_result_sfx = False
    app.kill_log_text = ""

    if app.game_mode == "1v1":
        left_cls = force_left_cls if force_left_cls else random.choice(AVAILABLE_CLASSES)
        right_cls = force_right_cls if force_right_cls else random.choice(AVAILABLE_CLASSES)

        hero_left = left_cls(400, 540, RED, "Faction_A")
        hero_right = right_cls(1520, 540, BLUE, "Faction_B")
        app.agents = [hero_left, hero_right]

        app.current_hero_left_name = HERO_NAME_MAP.get(hero_left.__class__.__name__, hero_left.__class__.__name__)
        app.current_hero_right_name = HERO_NAME_MAP.get(hero_right.__class__.__name__, hero_right.__class__.__name__)

    elif app.game_mode == "2v2":
        left_cls1 = force_left_cls if force_left_cls else random.choice(AVAILABLE_CLASSES)
        left_cls2 = random.choice(AVAILABLE_CLASSES)
        right_cls1 = force_right_cls if force_right_cls else random.choice(AVAILABLE_CLASSES)
        right_cls2 = random.choice(AVAILABLE_CLASSES)

        hero_left1 = left_cls1(350, 420, RED, "Faction_A")
        hero_left2 = left_cls2(450, 660, RED, "Faction_A")
        hero_right1 = right_cls1(1570, 420, BLUE, "Faction_B")
        hero_right2 = right_cls2(1470, 660, BLUE, "Faction_B")

        app.agents = [hero_left1, hero_left2, hero_right1, hero_right2]

        name_l1 = HERO_NAME_MAP.get(hero_left1.__class__.__name__, hero_left1.__class__.__name__)
        name_l2 = HERO_NAME_MAP.get(hero_left2.__class__.__name__, hero_left2.__class__.__name__)
        name_r1 = HERO_NAME_MAP.get(hero_right1.__class__.__name__, hero_right1.__class__.__name__)
        name_r2 = HERO_NAME_MAP.get(hero_right2.__class__.__name__, hero_right2.__class__.__name__)

        app.current_hero_left_name = f"{name_l1} & {name_l2}"
        app.current_hero_right_name = f"{name_r1} & {name_r2}"

        for agent in app.agents:
            agent.max_hp = int(agent.max_hp * 0.75)
            if hasattr(agent, '_reuben_hp'):
                agent._reuben_hp = agent.max_hp
            else:
                agent._hp = agent.max_hp

            if agent.__class__.__name__ == "BiaoYuGe":
                agent.shield_multiplier = 2

    elif app.game_mode == "Boss战":
        boss_cls = force_right_cls if force_right_cls else random.choice(AVAILABLE_CLASSES)

        challenger_classes = [c for c in AVAILABLE_CLASSES if c != boss_cls]
        selected_challengers = random.sample(challenger_classes, min(4, len(challenger_classes)))

        hero_left1 = selected_challengers[0](200, 200, RED, "Faction_A")
        hero_left2 = selected_challengers[1](200, 520, RED, "Faction_A")
        hero_left3 = selected_challengers[2](400, 360, RED, "Faction_A")
        hero_left4 = selected_challengers[3](300, 680, RED, "Faction_A")

        hero_boss = boss_cls(1100, 360, BLUE, "Faction_B")

        app.agents = [hero_left1, hero_left2, hero_left3, hero_left4, hero_boss]

        app.current_hero_left_name = "全英雄联军"
        app.current_hero_right_name = f"【BOSS】{HERO_NAME_MAP.get(boss_cls.__name__, boss_cls.__name__)}"

        app.previous_alive_challengers_count = 4
        app.hunter_triggered = False
        app.hunter_text = ""
        app.hunter_text_timer = 0

        hero_boss.max_hp *= 3
        if hasattr(hero_boss, '_reuben_hp'):
            hero_boss._reuben_hp = hero_boss.max_hp
        else:
            hero_boss._hp = hero_boss.max_hp
        hero_boss.base_speed *= 1.15

        if hero_boss.__class__.__name__ == "BiaoYuGe":
            hero_boss.shield_multiplier = 5

    app.gamblers["玩家"]["last_choice"] = None
    app.betting_start_time = pygame.time.get_ticks()
    app.ai_decisions.clear()
    app.safe_zone_radius = 1100

    req_bet = BET_TABLE[app.current_round - 1]
    for name, data in app.gamblers.items():
        if name == "玩家" or data["status"] == "已淘汰": continue
        delay = random.randint(2000, 8000)
        ai_choices = ["红方", "蓝方"]
        if data.get("spectate_count", 0) < 2:
            ai_choices.append("观望")
        choice = random.choice(ai_choices)
        if choice == "观望":
            data["spectate_count"] = data.get("spectate_count", 0) + 1

        b_type = "ALL" if (app.current_round >= 6 or data["taka"] < req_bet) else "普通"
        app.ai_decisions[name] = {"delay": delay, "choice": choice, "type": b_type, "revealed": False}


def evaluate_bets(app, winning_faction):
    req_bet = BET_TABLE[app.current_round - 1]
    winner_tag = "红方" if winning_faction == "Faction_A" else "蓝方"
    app.bet_result_type = None

    for name, data in app.gamblers.items():
        data["prev_taka"] = data["taka"]

    for name, data in app.gamblers.items():
        if data["status"] == "已淘汰": continue
        choice = data["last_choice"]
        b_type = data["bet_type"]

        if choice is None:
            data["last_choice"] = "观望"
            choice = "观望"

        if choice == "观望":
            if name == "玩家": app.bet_result_type = "观望"
            continue

        if choice == winner_tag:
            win_money = (req_bet * 2) if b_type == "ALL" else req_bet
            data["taka"] += win_money
            if name == "玩家": app.bet_result_type = "赢"
        else:
            if b_type == "ALL":
                data["taka"] = 0
            else:
                data["taka"] -= req_bet
            if name == "玩家": app.bet_result_type = "输"

        if data["taka"] <= 0:
            data["taka"] = 0
            data["status"] = "已淘汰"


def update_fighting_logic(app):
    if getattr(app, 'hunter_text_timer', 0) > 0:
        app.hunter_text_timer -= 1

    if not app.paused:
        if app.game_mode == "Boss战":
            challengers = [a for a in app.agents if a.faction == "Faction_A"]
            boss = next((a for a in app.agents if a.faction == "Faction_B"), None)
            alive_challengers = [c for c in challengers if c.hp > 0]

            if len(alive_challengers) < getattr(app, 'previous_alive_challengers_count', 4):
                deaths = app.previous_alive_challengers_count - len(alive_challengers)
                app.previous_alive_challengers_count = len(alive_challengers)

                for c in alive_challengers:
                    c.hp = min(c.max_hp, c.hp + c.max_hp * 0.20 * deaths)
                    c.ult_charge = min(100, getattr(c, 'ult_charge', 0) + 20 * deaths)

            if len(alive_challengers) == 1 and not getattr(app, 'hunter_triggered', False) and boss and boss.hp > 0:
                is_boss_healthy = False
                if boss.__class__.__name__ == "Reuben":
                    if getattr(boss, 'lives', 0) > 4:
                        is_boss_healthy = True
                else:
                    if boss.hp > boss.max_hp * 0.5:
                        is_boss_healthy = True

                if is_boss_healthy:
                    app.hunter_triggered = True
                    hunter = alive_challengers[0]
                    hunter.is_hunter = True
                    hunter.hp = hunter.max_hp
                    hunter.base_speed *= 1.15

                    if hunter.__class__.__name__ == "Reuben":
                        hunter.lives = 9

                    hunter_name = HERO_NAME_MAP.get(hunter.__class__.__name__, hunter.__class__.__name__)
                    app.hunter_text = f"{hunter_name} 成为了终极猎手！"
                    app.hunter_text_timer = int(FPS * 3)

                    pygame.mixer.music.stop()
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    if getattr(sys, 'frozen', False):
                        base_dir = os.path.dirname(sys.executable)
                    possible_paths = [
                        os.path.join(base_dir, "gongyong", "maolei.mp3"),
                        os.path.join(base_dir, "sounds", "gongyong", "maolei.mp3"),
                        os.path.join(base_dir, "assets", "gongyong", "maolei.mp3")
                    ]
                    for p in possible_paths:
                        if os.path.exists(p):
                            try:
                                pygame.mixer.music.load(p)
                                pygame.mixer.music.play(-1)
                            except:
                                pass
                            break

        app.is_time_stopped = False
        app.time_stop_owner = None
        for agent in app.agents:
            if agent.hp > 0 and getattr(agent, 'state', None) == "TIME_STOP":
                app.is_time_stopped = True
                app.time_stop_owner = agent
                break

        if app.is_time_stopped: app.fight_start_ticks += app.clock.get_time()
        app.elapsed_fight = pygame.time.get_ticks() - app.fight_start_ticks

        if app.elapsed_fight > 30000:
            time_past_30s = app.elapsed_fight - 30000
            app.safe_zone_radius = max(150, int(1100 - (time_past_30s / 1000) * 23.75))

        for agent in app.agents:
            if agent.hp <= 0: continue
            if app.is_time_stopped and agent != app.time_stop_owner: continue

            dist_to_center = math.hypot(agent.x - WIDTH // 2, agent.y - HEIGHT // 2)
            if app.elapsed_fight > 30000 and dist_to_center > app.safe_zone_radius:
                agent.out_of_zone = True
                if getattr(agent, 'state', 'NORMAL') not in ["TIME_STOP", "RIDER"]:
                    agent._hp -= (agent.max_hp * 0.05) / FPS
            else:
                agent.out_of_zone = False

            agent.move()
            agent.update_cooldown()

            if hasattr(agent, 'update_skill'):
                hp_before = {a: a.hp for a in app.agents}

                old_bullet_count = len(app.bullets)
                agent.update_skill(app.bullets, app.agents)

                if app.game_mode == "2v2":
                    for a in app.agents:
                        if a.faction != agent.faction and a.hp < hp_before[a]:
                            diff = hp_before[a] - a.hp
                            a.hp -= (diff * 1.5)
                elif app.game_mode == "Boss战":
                    for a in app.agents:
                        if a.faction != agent.faction and a.hp < hp_before[a]:
                            diff = hp_before[a] - a.hp
                            if agent.faction == "Faction_B":
                                a.hp -= (diff * 2.0)
                            elif getattr(agent, 'is_hunter', False):
                                # --- 核心修改：近战/特殊攻击的终极猎手补偿提升为总计 2.0 倍 (即多扣1.0倍) ---
                                a.hp -= (diff * 1.0)

                new_bullet_count = len(app.bullets) - old_bullet_count

                if new_bullet_count > 0 and getattr(agent, 'out_of_zone', False):
                    for b in app.bullets[-new_bullet_count:]:
                        if not getattr(b, 'is_boosted', False): b.damage *= 2; b.is_boosted = True

                if getattr(agent, 'request_clear_bullets', False):
                    app.bullets.clear()
                    agent.request_clear_bullets = False

        dmg_mult = 1.0
        if app.game_mode == "2v2":
            dmg_mult = 2.5

        if not app.is_time_stopped:
            for bullet in app.bullets:
                if not bullet.active: continue
                bullet.move()
                for agent in app.agents:
                    if agent.hp > 0 and bullet.owner_faction != agent.faction:
                        dist = math.hypot(bullet.x - agent.x, bullet.y - agent.y)
                        if dist < getattr(bullet, 'radius', 0) + getattr(agent, 'radius', 0):
                            current_dmg_mult = dmg_mult
                            if app.game_mode == "Boss战":
                                if bullet.owner_faction == "Faction_B":
                                    current_dmg_mult = 3.0
                                elif bullet.owner_faction == "Faction_A" and getattr(app, 'hunter_triggered', False):
                                    # --- 核心修改：弹幕/波纹的终极猎手补偿直接放大为 2.0 倍 ---
                                    current_dmg_mult = 2.0

                            agent.hp -= (bullet.damage * current_dmg_mult)

                            if not getattr(bullet, 'infinite_bounce', False): bullet.active = False
                            agent.ult_charge = min(100, agent.ult_charge + 8)
                            break
            resolve_combat(app.agents)

        app.bullets = [b for b in app.bullets if b.active]

        alive_agents = [agent for agent in app.agents if agent.hp > 0]
        alive_factions = set(agent.faction for agent in alive_agents)

        if len(alive_factions) <= 1:
            win_fac = alive_agents[0].faction if alive_agents else "Draw"

            if len(alive_factions) == 1:
                if win_fac == "Faction_A":
                    app.kill_log_text = f"红方联军 【{app.current_hero_left_name}】 击败了对手！" if app.game_mode != "Boss战" else f"全英雄联军击败了BOSS！"
                else:
                    app.kill_log_text = f"蓝方 【{app.current_hero_right_name}】 击败了对手！" if app.game_mode != "Boss战" else f"BOSS 【{app.current_hero_right_name}】 碾压了全场！"
            else:
                app.kill_log_text = "双方鏖战至终，同归于尽！"

            evaluate_bets(app, win_fac)
            app.winner_text = "红方" if win_fac == "Faction_A" else ("蓝方" if win_fac == "Faction_B" else "平局")

            pygame.mixer.stop()
            app.feedback_particles.clear()

            if app.bet_result_type == "赢":
                if app.sfx_payment and not app.has_played_result_sfx:
                    app.sfx_payment.play()
                    app.has_played_result_sfx = True
                for _ in range(50): app.feedback_particles.append(FallingParticle("money"))
            elif app.bet_result_type == "输":
                if app.sfx_ugh and not app.has_played_result_sfx:
                    app.sfx_ugh.play()
                    app.has_played_result_sfx = True
                for _ in range(40): app.feedback_particles.append(FallingParticle("poop"))

            app.round_over_start_ticks = pygame.time.get_ticks()
            app.game_state = "ROUND_OVER"

    else:
        app.fight_start_ticks += app.clock.get_time()