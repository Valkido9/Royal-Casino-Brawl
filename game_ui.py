import pygame
import math
import random
from settings import WIDTH, HEIGHT, BG_COLOR, RED, BLUE
from config import BET_TABLE, global_sfx_vol
from ui_components import draw_button, get_rainbow_color, FallingParticle
from game_logic import start_new_round, AVAILABLE_CLASSES, HERO_NAME_MAP


def draw_side_supporters(app, current_time):
    ry, by = 150, 150
    for n, d in app.gamblers.items():
        if d["status"] == "已淘汰": continue
        c = d["last_choice"]
        bt = d["bet_type"]
        display_name = app.player_name if n == "玩家" else n

        if c in ["红方", "蓝方"]:
            txt = f"{display_name} {'(ALL)' if bt == 'ALL' else ''}"
            col = get_rainbow_color(current_time, 0.2) if bt == "ALL" else (
                (255, 100, 100) if c == "红方" else (100, 150, 255))
            sf = app.font_small.render(txt, True, col)
            if c == "红方":
                app.logical_surface.blit(sf, (30, ry));
                ry += 35
            else:
                app.logical_surface.blit(sf, (WIDTH - 30 - sf.get_width(), by));
                by += 35


def render_start_screen(app):
    app.logical_surface.fill((15, 15, 25))

    title = app.font_huge.render("任地狱明星大乱斗", True, (255, 50, 50))
    app.logical_surface.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 3 - 100))
    subtitle = app.font_large.render("—— 孟加拉国皇家赌场 ——", True, (255, 200, 0))
    app.logical_surface.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, HEIGHT // 3 - 10))

    input_box_rect = pygame.Rect(WIDTH // 2 - 200, HEIGHT // 3 + 70, 400, 60)
    color_active = pygame.Color('dodgerblue2')
    color_inactive = pygame.Color('lightskyblue3')
    box_color = color_active if getattr(app, 'input_active', False) else color_inactive

    if app.mouse_click and not app.show_settings:
        if input_box_rect.collidepoint(app.mouse_pos):
            app.input_active = True
            pygame.key.start_text_input()
            actual_x = int(input_box_rect.x * (app.current_res[0] / WIDTH))
            actual_y = int(input_box_rect.y * (app.current_res[1] / HEIGHT))
            actual_w = int(input_box_rect.w * (app.current_res[0] / WIDTH))
            actual_h = int(input_box_rect.h * (app.current_res[1] / HEIGHT))
            pygame.key.set_text_input_rect(pygame.Rect(actual_x, actual_y, actual_w, actual_h))
        else:
            app.input_active = False
            pygame.key.stop_text_input()

    pygame.draw.rect(app.logical_surface, box_color, input_box_rect, border_radius=8)
    pygame.draw.rect(app.logical_surface, (255, 255, 255), input_box_rect, width=2, border_radius=8)

    prompt_surf = app.font_normal.render("你的名字是：", True, (255, 255, 255))
    app.logical_surface.blit(prompt_surf, (input_box_rect.x - prompt_surf.get_width() - 20, input_box_rect.y + 15))

    display_text = app.player_name
    if getattr(app, 'input_active', False) and (pygame.time.get_ticks() // 500) % 2 == 0: display_text += "|"

    txt_surf = app.font_normal.render(display_text, True, (255, 255, 255))
    app.logical_surface.blit(txt_surf, (input_box_rect.x + 20, input_box_rect.y + 15))

    mode_prompt = app.font_normal.render("选择对决模式：", True, (255, 255, 255))
    app.logical_surface.blit(mode_prompt, (input_box_rect.x - mode_prompt.get_width() - 20, input_box_rect.y + 100))

    rect_1v1 = pygame.Rect(WIDTH // 2 - 250, HEIGHT // 3 + 155, 150, 50)
    rect_2v2 = pygame.Rect(WIDTH // 2 - 75, HEIGHT // 3 + 155, 150, 50)
    rect_boss = pygame.Rect(WIDTH // 2 + 100, HEIGHT // 3 + 155, 150, 50)

    if draw_button(app.logical_surface, rect_1v1, "1v1 单挑", app.font_small, (40, 50, 60), (60, 80, 100),
                   app.mouse_pos, app.mouse_click, active=(app.game_mode == "1v1"), disabled=app.show_settings):
        app.game_mode = "1v1"
    if draw_button(app.logical_surface, rect_2v2, "2v2 组队", app.font_small, (40, 50, 60), (60, 80, 100),
                   app.mouse_pos, app.mouse_click, active=(app.game_mode == "2v2"), disabled=app.show_settings):
        app.game_mode = "2v2"
    if draw_button(app.logical_surface, rect_boss, "Boss战 (1v4)", app.font_small, (80, 40, 40), (120, 60, 60),
                   app.mouse_pos, app.mouse_click, active=(app.game_mode == "Boss战"), disabled=app.show_settings):
        app.game_mode = "Boss战"

    # --- 新增位置：英雄图鉴按钮放置于模式选择下方居中 ---
    btn_almanac = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 3 + 240, 200, 60)
    if draw_button(app.logical_surface, btn_almanac, "英雄图鉴", app.font_normal, (100, 80, 150), (130, 100, 200),
                   app.mouse_pos, app.mouse_click, disabled=app.show_settings):
        app.game_state = "ALMANAC"
        pygame.key.stop_text_input()

    btn_settings = pygame.Rect(WIDTH - 200, HEIGHT - 100, 160, 60)
    if draw_button(app.logical_surface, btn_settings, "系统设置", app.font_normal, (60, 60, 80), (100, 100, 150),
                   app.mouse_pos, app.mouse_click, disabled=app.show_settings):
        app.show_settings = True
        pygame.key.stop_text_input()

    btn_start = pygame.Rect(WIDTH // 2 - 150, HEIGHT - 230, 300, 80)
    if draw_button(app.logical_surface, btn_start, "进入赌场", app.font_large, (50, 150, 50), (80, 200, 80),
                   app.mouse_pos, app.mouse_click, disabled=app.show_settings):
        if app.player_name.strip() == "": app.player_name = "无名氏"
        pygame.key.stop_text_input()
        from game_logic import start_new_round
        start_new_round(app)
        app.game_state = "BETTING"


def render_debug_select(app):
    app.logical_surface.fill((20, 30, 40))
    title = app.font_large.render("=== 开发者测试后台 (DEBUG) ===", True, (255, 255, 0))
    app.logical_surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 40))

    mode_prompt = app.font_normal.render("强制测试模式:", True, (255, 255, 255))
    app.logical_surface.blit(mode_prompt, (WIDTH // 2 - 320, 115))

    rect_1v1 = pygame.Rect(WIDTH // 2 - 150, 105, 120, 45)
    rect_2v2 = pygame.Rect(WIDTH // 2 - 10, 105, 120, 45)
    rect_boss = pygame.Rect(WIDTH // 2 + 130, 105, 150, 45)

    if draw_button(app.logical_surface, rect_1v1, "1v1 单挑", app.font_small, (40, 50, 60), (60, 80, 100),
                   app.mouse_pos, app.mouse_click, active=(app.game_mode == "1v1")):
        app.game_mode = "1v1"
    if draw_button(app.logical_surface, rect_2v2, "2v2 组队", app.font_small, (40, 50, 60), (60, 80, 100),
                   app.mouse_pos, app.mouse_click, active=(app.game_mode == "2v2")):
        app.game_mode = "2v2"
    if draw_button(app.logical_surface, rect_boss, "Boss战 (1v4)", app.font_small, (80, 40, 40), (120, 60, 60),
                   app.mouse_pos, app.mouse_click, active=(app.game_mode == "Boss战")):
        app.game_mode = "Boss战"

    red_title = app.font_normal.render("红方 (左) 强制英雄:", True, RED)
    app.logical_surface.blit(red_title, (WIDTH // 4 - red_title.get_width() // 2, 190))
    for i, cls in enumerate(AVAILABLE_CLASSES):
        cname = HERO_NAME_MAP.get(cls.__name__, cls.__name__)
        rect = pygame.Rect(WIDTH // 4 - 100, 240 + i * 65, 200, 50)
        is_active = (app.debug_left_hero == cls)
        if draw_button(app.logical_surface, rect, cname, app.font_small, (80, 40, 40), (150, 50, 50), app.mouse_pos,
                       app.mouse_click, active=is_active):
            app.debug_left_hero = cls

    blue_title = app.font_normal.render("蓝方 (右) 强制英雄:", True, BLUE)
    app.logical_surface.blit(blue_title, (WIDTH * 3 // 4 - blue_title.get_width() // 2, 190))
    for i, cls in enumerate(AVAILABLE_CLASSES):
        cname = HERO_NAME_MAP.get(cls.__name__, cls.__name__)
        rect = pygame.Rect(WIDTH * 3 // 4 - 100, 240 + i * 65, 200, 50)
        is_active = (app.debug_right_hero == cls)
        if draw_button(app.logical_surface, rect, cname, app.font_small, (40, 40, 80), (50, 50, 150), app.mouse_pos,
                       app.mouse_click, active=is_active):
            app.debug_right_hero = cls

    btn_start = pygame.Rect(WIDTH // 2 - 170, HEIGHT - 150, 340, 60)
    can_start = app.debug_left_hero is not None and app.debug_right_hero is not None

    if draw_button(app.logical_surface, btn_start, "强制开始对决 (跳过下注)", app.font_normal, (50, 150, 50),
                   (80, 200, 80),
                   app.mouse_pos, app.mouse_click, disabled=not can_start):
        start_new_round(app, force_left_cls=app.debug_left_hero, force_right_cls=app.debug_right_hero)

        for n in app.gamblers:
            app.gamblers[n]["last_choice"] = "观望"
            app.gamblers[n]["bet_type"] = "普通"

        app.game_state = "FIGHTING"
        app.fight_start_ticks = pygame.time.get_ticks()

    btn_back = pygame.Rect(50, HEIGHT - 100, 150, 50)
    if draw_button(app.logical_surface, btn_back, "退出 Debug", app.font_small, (100, 100, 100), (150, 150, 150),
                   app.mouse_pos, app.mouse_click):
        app.game_state = "START_SCREEN"
        app.debug_buffer = ""


def render_betting(app):
    app.logical_surface.fill(BG_COLOR)
    for agent in app.agents:
        agent.draw(app.logical_surface)

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    app.logical_surface.blit(overlay, (0, 0))

    req_bet = BET_TABLE[app.current_round - 1]
    p_money = app.gamblers["玩家"]["taka"]
    current_time = pygame.time.get_ticks()
    if not app.paused:
        elapsed = current_time - app.betting_start_time
    else:
        app.betting_start_time += app.clock.get_time()
        elapsed = current_time - app.betting_start_time

    title = app.font_large.render(f"=== 第 {app.current_round} 轮比赛下注 ({app.game_mode}) ===", True, (255, 200, 0))
    app.logical_surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 40))

    vs_text_1 = app.font_large.render(f"【红方】 {app.current_hero_left_name}", True, RED)
    vs_text_mid = app.font_large.render(f" VS ", True, (255, 255, 255))
    vs_text_2 = app.font_large.render(f"{app.current_hero_right_name} 【蓝方】", True, BLUE)
    start_x = WIDTH // 2 - (vs_text_1.get_width() + vs_text_mid.get_width() + vs_text_2.get_width()) // 2
    app.logical_surface.blit(vs_text_1, (start_x, 110))
    app.logical_surface.blit(vs_text_mid, (start_x + vs_text_1.get_width(), 110))
    app.logical_surface.blit(vs_text_2, (start_x + vs_text_1.get_width() + vs_text_mid.get_width(), 110))

    cost_text = app.font_normal.render(f"当前余额: {p_money} | 本轮入场需: {req_bet} pt", True, (150, 255, 150))
    app.logical_surface.blit(cost_text, (WIDTH // 2 - cost_text.get_width() // 2, 180))

    red_y, blue_y, watch_y = 260, 260, 260
    for name, data in app.gamblers.items():
        if data["status"] == "已淘汰": continue

        choice = data["last_choice"]
        b_type = data["bet_type"]
        is_revealed = False
        display_name = app.player_name if name == "玩家" else name

        if name == "玩家":
            if choice is not None: is_revealed = True
        else:
            dec = app.ai_decisions.get(name)
            if dec and elapsed > dec["delay"]:
                dec["revealed"] = True
                data["last_choice"] = dec["choice"]
                data["bet_type"] = dec["type"]
                choice = dec["choice"]
                b_type = dec["type"]
                is_revealed = True

        if is_revealed:
            tag = "(ALL)" if b_type == "ALL" else ""
            txt = f"{display_name} {tag}"
            color = get_rainbow_color(current_time, 0.3) if b_type == "ALL" else (
                (255, 100, 100) if choice == "红方" else ((100, 150, 255) if choice == "蓝方" else (200, 200, 200)))
            surf = app.font_normal.render(txt, True, color)
            if choice == "红方":
                app.logical_surface.blit(surf, (150, red_y));
                red_y += 40
            elif choice == "蓝方":
                app.logical_surface.blit(surf, (WIDTH - 150 - surf.get_width(), blue_y));
                blue_y += 40
            elif choice == "观望":
                app.logical_surface.blit(surf, (WIDTH // 2 - surf.get_width() // 2, watch_y));
                watch_y += 40

    btn_w, btn_h = 240, 60
    is_all_allowed = (app.current_round >= 6 or p_money < req_bet)
    is_player_dead = app.gamblers["玩家"]["status"] == "已淘汰"
    rect_red = pygame.Rect(WIDTH // 4 - btn_w // 2, HEIGHT - 180, btn_w, btn_h)
    rect_blue = pygame.Rect(WIDTH * 3 // 4 - btn_w // 2, HEIGHT - 180, btn_w, btn_h)
    rect_watch = pygame.Rect(WIDTH // 2 - btn_w // 2, HEIGHT - 180, btn_w, btn_h)
    rect_all_red = pygame.Rect(WIDTH // 4 - btn_w // 2, HEIGHT - 100, btn_w, btn_h)
    rect_all_blue = pygame.Rect(WIDTH * 3 // 4 - btn_w // 2, HEIGHT - 100, btn_w, btn_h)

    cur_choice = app.gamblers["玩家"]["last_choice"]
    cur_type = app.gamblers["玩家"]["bet_type"]

    if draw_button(app.logical_surface, rect_red, "支持 红方", app.font_normal, (150, 50, 50), (200, 50, 50),
                   app.mouse_pos, app.mouse_click, disabled=is_player_dead or app.show_settings,
                   active=(cur_choice == "红方" and cur_type == "普通")):
        app.gamblers["玩家"]["last_choice"] = "红方"
        app.gamblers["玩家"]["bet_type"] = "普通"
    if draw_button(app.logical_surface, rect_blue, "支持 蓝方", app.font_normal, (50, 80, 150), (50, 100, 200),
                   app.mouse_pos, app.mouse_click, disabled=is_player_dead or app.show_settings,
                   active=(cur_choice == "蓝方" and cur_type == "普通")):
        app.gamblers["玩家"]["last_choice"] = "蓝方"
        app.gamblers["玩家"]["bet_type"] = "普通"

    obs_disabled = is_player_dead or (app.spectate_count >= 2) or app.show_settings
    obs_text = "不思观望 (已限次)" if app.spectate_count >= 2 else f"不思观望 ({2 - app.spectate_count}次剩余)"
    if draw_button(app.logical_surface, rect_watch, obs_text, app.font_normal, (80, 80, 80), (120, 120, 120),
                   app.mouse_pos, app.mouse_click, disabled=obs_disabled, active=(cur_choice == "观望")):
        app.gamblers["玩家"]["last_choice"] = "观望"
        app.gamblers["玩家"]["bet_type"] = "普通"

    if draw_button(app.logical_surface, rect_all_red, "全力 ALL 红方", app.font_normal, (180, 30, 30), (220, 30, 30),
                   app.mouse_pos, app.mouse_click, disabled=not is_all_allowed or is_player_dead or app.show_settings,
                   active=(cur_choice == "红方" and cur_type == "ALL")):
        app.gamblers["玩家"]["last_choice"] = "红方"
        app.gamblers["玩家"]["bet_type"] = "ALL"
    if draw_button(app.logical_surface, rect_all_blue, "全力 ALL 蓝方", app.font_normal, (30, 50, 180), (30, 80, 220),
                   app.mouse_pos, app.mouse_click, disabled=not is_all_allowed or is_player_dead or app.show_settings,
                   active=(cur_choice == "蓝方" and cur_type == "ALL")):
        app.gamblers["玩家"]["last_choice"] = "蓝方"
        app.gamblers["玩家"]["bet_type"] = "ALL"

    rem_time = max(0, 10000 - elapsed)
    seconds_left = math.ceil(rem_time / 1000)
    color_timer = (255, 50, 50) if seconds_left <= 3 else (255, 255, 255)
    timer_txt = app.font_large.render(f"锁定倒计时: {seconds_left} 秒", True, color_timer)
    app.logical_surface.blit(timer_txt, (WIDTH // 2 - timer_txt.get_width() // 2, HEIGHT // 2 - 100))

    if elapsed > 10000 and not app.paused:
        if not is_player_dead:
            final_choice = app.gamblers["玩家"]["last_choice"]
            if final_choice is None:
                if app.spectate_count < 2:
                    app.gamblers["玩家"]["last_choice"] = "观望"
                    app.gamblers["玩家"]["bet_type"] = "普通"
                    app.spectate_count += 1
                else:
                    app.gamblers["玩家"]["last_choice"] = random.choice(["红方", "蓝方"])
                    app.gamblers["玩家"]["bet_type"] = "普通"
            elif final_choice == "观望":
                app.spectate_count += 1

        app.game_state = "FIGHTING"
        app.fight_start_ticks = pygame.time.get_ticks()


def render_fighting(app):
    app.logical_surface.fill(BG_COLOR)

    if hasattr(app, 'elapsed_fight') and app.elapsed_fight > 30000:
        pygame.draw.circle(app.logical_surface, (255, 30, 30), (WIDTH // 2, HEIGHT // 2), app.safe_zone_radius, width=6)
        pygame.draw.circle(app.logical_surface, (255, 80, 80), (WIDTH // 2, HEIGHT // 2), app.safe_zone_radius + 4,
                           width=2)
        pygame.draw.circle(app.logical_surface, (180, 20, 20), (WIDTH // 2, HEIGHT // 2), app.safe_zone_radius - 4,
                           width=2)

        if (pygame.time.get_ticks() // 400) % 2 == 0:
            warn_txt = app.font_normal.render("毒圈收缩中！圈外造成伤害翻倍并持续扣血！", True, (255, 80, 80))
            app.logical_surface.blit(warn_txt, (WIDTH // 2 - warn_txt.get_width() // 2, 50))

    for agent in app.agents:
        agent.draw(app.logical_surface)

    for bullet in app.bullets:
        bullet.draw(app.logical_surface)

    draw_side_supporters(app, pygame.time.get_ticks())

    if getattr(app, 'is_time_stopped', False) and getattr(app, 'time_stop_owner', None):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))

        hole_radius = 80
        pygame.draw.circle(overlay, (0, 0, 0, 0), (int(app.time_stop_owner.x), int(app.time_stop_owner.y)), hole_radius)
        app.logical_surface.blit(overlay, (0, 0))
        app.time_stop_owner.draw(app.logical_surface)

    if getattr(app, 'hunter_text_timer', 0) > 0 and getattr(app, 'hunter_text', ""):
        hunter_surf = app.font_huge.render(app.hunter_text, True, (255, 50, 50))
        outline_surf = app.font_huge.render(app.hunter_text, True, (255, 255, 255))

        offset = 3
        app.logical_surface.blit(outline_surf,
                                 (WIDTH // 2 - outline_surf.get_width() // 2 - offset, HEIGHT // 3 - offset))
        app.logical_surface.blit(outline_surf,
                                 (WIDTH // 2 - outline_surf.get_width() // 2 + offset, HEIGHT // 3 + offset))
        app.logical_surface.blit(outline_surf,
                                 (WIDTH // 2 - outline_surf.get_width() // 2 - offset, HEIGHT // 3 + offset))
        app.logical_surface.blit(outline_surf,
                                 (WIDTH // 2 - outline_surf.get_width() // 2 + offset, HEIGHT // 3 - offset))

        app.logical_surface.blit(hunter_surf, (WIDTH // 2 - hunter_surf.get_width() // 2, HEIGHT // 3))


def render_round_over(app):
    app.logical_surface.fill(BG_COLOR)

    if hasattr(app, 'safe_zone_radius'):
        pygame.draw.circle(app.logical_surface, (150, 50, 50), (WIDTH // 2, HEIGHT // 2), app.safe_zone_radius, width=4)

    for agent in app.agents:
        agent.draw(app.logical_surface)
    for bullet in app.bullets:
        bullet.draw(app.logical_surface)

    over_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    over_overlay.fill((0, 0, 0, 200))
    app.logical_surface.blit(over_overlay, (0, 0))

    for particle in app.feedback_particles: particle.update(); particle.draw(app.logical_surface)
    app.feedback_particles = [p for p in app.feedback_particles if p.active]

    draw_side_supporters(app, pygame.time.get_ticks())

    win_color = RED if app.winner_text == "红方" else BLUE if app.winner_text == "蓝方" else (150, 150, 150)
    res_txt = app.font_huge.render(f"【{app.winner_text}】 获胜！", True, win_color)
    app.logical_surface.blit(res_txt, (WIDTH // 2 - res_txt.get_width() // 2, 40))

    kill_txt = app.font_large.render(app.kill_log_text, True, (255, 215, 0))
    app.logical_surface.blit(kill_txt, (WIDTH // 2 - kill_txt.get_width() // 2, 115))

    p_status = app.gamblers["玩家"]["status"]
    if app.bet_result_type == "赢":
        res_feedback = app.font_large.render("收款成功！", True, (100, 255, 100))
    elif app.bet_result_type == "输":
        res_feedback = app.font_large.render("输了……", True, (255, 100, 100))
    else:
        res_feedback = app.font_large.render("本回合观望", True, (200, 200, 200))
    app.logical_surface.blit(res_feedback, (WIDTH // 2 - res_feedback.get_width() // 2, 175))

    if p_status == "已淘汰":
        p_txt = app.font_large.render("您已破产淘汰！", True, (255, 50, 50))
    else:
        p_txt = app.font_large.render(f"你的余额: {app.gamblers['玩家']['taka']} 孟加拉塔卡", True, (100, 255, 100))
    app.logical_surface.blit(p_txt, (WIDTH // 2 - p_txt.get_width() // 2, 235))

    elapsed_over = pygame.time.get_ticks() - app.round_over_start_ticks
    wait_time = 4000

    if elapsed_over > wait_time:
        app.feedback_particles.clear()
        app.lb_data.clear()
        sorted_initial = sorted(app.gamblers.keys(), key=lambda n: app.gamblers[n]["prev_taka"], reverse=True)
        for i, n in enumerate(sorted_initial):
            app.lb_data[n] = {
                "display_taka": app.gamblers[n]["prev_taka"],
                "taka": app.gamblers[n]["taka"],
                "display_y": 200 + i * 60
            }
        app.lb_start_time = pygame.time.get_ticks()
        app.game_state = "ROUND_LEADERBOARD"
    else:
        rem_sec = math.ceil((wait_time - elapsed_over) / 1000)
        auto_txt = app.font_normal.render(f"{rem_sec} 秒后自动进入结算大厅...", True, (200, 200, 200))
        app.logical_surface.blit(auto_txt, (WIDTH // 2 - auto_txt.get_width() // 2, HEIGHT - 100))


def render_leaderboard(app):
    app.logical_surface.fill((20, 20, 30))
    title_str = "最终荣誉结算" if app.current_round >= 10 else f"=== 第 {app.current_round} 轮动态结算 ==="
    title = app.font_huge.render(title_str, True, (255, 215, 0))
    app.logical_surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))

    elapsed_lb = pygame.time.get_ticks() - app.lb_start_time
    progress = min(1.0, elapsed_lb / 2500.0)
    ease_p = 1 - (1 - progress) ** 3

    for n in app.lb_data:
        app.lb_data[n]["display_taka"] = int(
            app.gamblers[n]["prev_taka"] + (app.lb_data[n]["taka"] - app.gamblers[n]["prev_taka"]) * ease_p)

    current_sorted = sorted(app.lb_data.keys(), key=lambda n: app.lb_data[n]["display_taka"], reverse=True)

    for i, n in enumerate(current_sorted):
        target_y = 200 + i * 65
        app.lb_data[n]["display_y"] += (target_y - app.lb_data[n]["display_y"]) * 0.15

    for i, n in enumerate(current_sorted):
        d_name = app.player_name if n == "玩家" else n
        color = (0, 255, 255) if n == "玩家" else ((255, 215, 0) if i == 0 else (200, 200, 200))
        txt = f"No.{i + 1} {d_name} - {app.lb_data[n]['display_taka']} pt"

        if app.gamblers[n]["status"] == "已淘汰":
            color = (100, 100, 100)
            txt = f"No.{i + 1} {d_name} - 已破产淘汰"

        surf = app.font_large.render(txt, True, color)
        app.logical_surface.blit(surf, (WIDTH // 2 - 250, app.lb_data[n]["display_y"]))

    if progress >= 1.0:
        btn_w, btn_h = 300, 60
        rect_next = pygame.Rect(WIDTH // 2 - btn_w // 2, HEIGHT - 120, btn_w, btn_h)
        btn_txt = "进入下一轮" if app.current_round < 10 else "查看最终排名"

        if draw_button(app.logical_surface, rect_next, btn_txt, app.font_large, (50, 150, 50), (80, 180, 80),
                       app.mouse_pos, app.mouse_click, disabled=app.show_settings):
            active_npcs = sum(1 for k, v in app.gamblers.items() if k != "玩家" and v["status"] != "已淘汰")
            if app.current_round < 10 and app.gamblers["玩家"]["status"] != "已淘汰" and active_npcs > 0:
                app.current_round += 1
                start_new_round(app)
                app.game_state = "BETTING"
            else:
                app.game_state = "GAME_OVER"


def render_game_over(app):
    app.logical_surface.fill((10, 10, 20))

    sorted_gamblers = sorted(app.gamblers.items(), key=lambda x: x[1]['taka'], reverse=True)

    if sorted_gamblers[0][0] == "玩家":
        rgb_color = get_rainbow_color(pygame.time.get_ticks(), 0.3)
        res_txt = app.font_huge.render("你是孟加拉国之王！", True, rgb_color)

        if random.random() < 0.15:
            app.feedback_particles.append(FallingParticle("money"))
    else:
        res_txt = app.font_huge.render("游戏结束：最终荣誉榜", True, (255, 200, 0))

    for particle in app.feedback_particles:
        particle.update()
        particle.draw(app.logical_surface)
    app.feedback_particles = [p for p in app.feedback_particles if p.active]

    app.logical_surface.blit(res_txt, (WIDTH // 2 - res_txt.get_width() // 2, 80))

    for idx, (name, data) in enumerate(sorted_gamblers):
        d_name = app.player_name if name == "玩家" else name
        color = (0, 255, 255) if name == "玩家" else ((255, 215, 0) if idx == 0 else (200, 200, 200))
        if data["status"] == "已淘汰": color = (100, 100, 100)
        money_txt = "已破产" if data["status"] == "已淘汰" else f"{data['taka']} pt"
        rank_str = f"No.{idx + 1} {d_name} - {money_txt}"
        r_txt = app.font_large.render(rank_str, True, color)
        app.logical_surface.blit(r_txt, (WIDTH // 2 - r_txt.get_width() // 2, 200 + idx * 60))

    version_surf = app.font_small.render("v0.4.2", True, (150, 150, 150))
    author_surf = app.font_small.render("Author: ValkyDoge & Gemini", True, (150, 150, 150))
    app.logical_surface.blit(version_surf, (WIDTH - version_surf.get_width() - 20, HEIGHT - 70))
    app.logical_surface.blit(author_surf, (WIDTH - author_surf.get_width() - 20, HEIGHT - 40))

    btn_w, btn_h = 240, 60
    rect_restart = pygame.Rect(WIDTH // 2 - btn_w // 2, HEIGHT - 120, btn_w, btn_h)
    if draw_button(app.logical_surface, rect_restart, "再来一次", app.font_large, (50, 150, 50), (80, 180, 80),
                   app.mouse_pos, app.mouse_click, disabled=app.show_settings):
        app.current_round = 1
        app.spectate_count = 0
        for n in app.gamblers:
            app.gamblers[n]["taka"] = 10000
            app.gamblers[n]["status"] = "正常"
            app.gamblers[n]["last_choice"] = None
            app.gamblers[n]["bet_type"] = "普通"
            app.gamblers[n]["prev_taka"] = 10000
            if "spectate_count" in app.gamblers[n]:
                app.gamblers[n]["spectate_count"] = 0
        app.feedback_particles.clear()
        app.game_state = "START_SCREEN"


def render_settings(app):
    pause_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pause_overlay.fill((0, 0, 0, 220))
    app.logical_surface.blit(pause_overlay, (0, 0))

    pause_text = app.font_huge.render("游戏设置 / 暂停", True, (255, 255, 255))
    app.logical_surface.blit(pause_text, pause_text.get_rect(center=(WIDTH // 2, 150)))

    slider_w = 400
    bgm_y = 300
    sfx_y = 400
    start_x = WIDTH // 2 - slider_w // 2 + 60

    bgm_txt = app.font_normal.render("BGM 音量:", True, (200, 200, 200))
    app.logical_surface.blit(bgm_txt, (start_x - 170, bgm_y - 15))
    sfx_txt = app.font_normal.render("SFX 音量:", True, (200, 200, 200))
    app.logical_surface.blit(sfx_txt, (start_x - 170, sfx_y - 15))

    pygame.draw.rect(app.logical_surface, (100, 100, 100), (start_x, bgm_y, slider_w, 10), border_radius=5)
    pygame.draw.rect(app.logical_surface, (100, 255, 100), (start_x, bgm_y, int(slider_w * app.bgm_volume), 10),
                     border_radius=5)
    pygame.draw.circle(app.logical_surface, (255, 255, 255), (start_x + int(slider_w * app.bgm_volume), bgm_y + 5), 12)

    pygame.draw.rect(app.logical_surface, (100, 100, 100), (start_x, sfx_y, slider_w, 10), border_radius=5)
    pygame.draw.rect(app.logical_surface, (100, 200, 255), (start_x, sfx_y, int(slider_w * global_sfx_vol[0]), 10),
                     border_radius=5)
    pygame.draw.circle(app.logical_surface, (255, 255, 255), (start_x + int(slider_w * global_sfx_vol[0]), sfx_y + 5),
                       12)

    if app.is_mouse_held:
        mx_pos = app.mouse_pos[0]
        my_pos = app.mouse_pos[1]
        if start_x - 20 <= mx_pos <= start_x + slider_w + 20:
            if bgm_y - 20 <= my_pos <= bgm_y + 30:
                app.bgm_volume = max(0.0, min(1.0, (mx_pos - start_x) / slider_w))
                pygame.mixer.music.set_volume(app.bgm_volume)
            elif sfx_y - 20 <= my_pos <= sfx_y + 30:
                global_sfx_vol[0] = max(0.0, min(1.0, (mx_pos - start_x) / slider_w))

    res_title = app.font_normal.render("--- 常见分辨率选项 ---", True, (150, 150, 150))
    app.logical_surface.blit(res_title, (WIDTH // 2 - res_title.get_width() // 2, 520))

    res_btns = [
        ("1280x720", lambda: app.set_resolution(1280, 720)),
        ("1366x768", lambda: app.set_resolution(1366, 768)),
        ("1440x900", lambda: app.set_resolution(1440, 900)),
        ("1600x900", lambda: app.set_resolution(1600, 900)),
        ("1920x1080", lambda: app.set_resolution(1920, 1080)),
        ("2560x1440", lambda: app.set_resolution(2560, 1440))
    ]

    bw, bh = 220, 55
    gap_x, gap_y = 30, 25
    grid_start_x = WIDTH // 2 - (bw * 3 + gap_x * 2) // 2
    grid_start_y = 590

    for i, (text, action) in enumerate(res_btns):
        row = i // 3
        col = i % 3
        bx = grid_start_x + col * (bw + gap_x)
        by = grid_start_y + row * (bh + gap_y)
        rect = pygame.Rect(bx, by, bw, bh)
        if draw_button(app.logical_surface, rect, text, app.font_small, (50, 50, 60), (80, 80, 100), app.mouse_pos,
                       app.mouse_click):
            action()

    btn_w = 260
    btn_h = 60

    # --- 修改点：返回主菜单按钮 ---
    btn_main = pygame.Rect(WIDTH // 2 - btn_w - 20, HEIGHT - 160, btn_w, btn_h)
    if draw_button(app.logical_surface, btn_main, "返回主菜单", app.font_normal, (150, 50, 50), (200, 80, 80),
                   app.mouse_pos, app.mouse_click):
        app.show_settings = False
        app.paused = False
        app.game_state = "START_SCREEN"

        # 核心逻辑：重置赌场以及战场所有的属性，确保新一轮状态干净
        app.current_round = 1
        app.spectate_count = 0
        for n in app.gamblers:
            app.gamblers[n]["taka"] = 10000
            app.gamblers[n]["status"] = "正常"
            app.gamblers[n]["last_choice"] = None
            app.gamblers[n]["bet_type"] = "普通"
            app.gamblers[n]["prev_taka"] = 10000
            if "spectate_count" in app.gamblers[n]:
                app.gamblers[n]["spectate_count"] = 0
        app.feedback_particles.clear()
        app.bullets.clear()
        app.agents.clear()

    # --- 原先的关闭/继续游戏按钮移到了右边 ---
    btn_close = pygame.Rect(WIDTH // 2 + 20, HEIGHT - 160, btn_w, btn_h)
    if draw_button(app.logical_surface, btn_close, "继续游戏 / RESUME", app.font_normal, (50, 150, 50), (80, 180, 80),
                   app.mouse_pos, app.mouse_click):
        app.show_settings = False
        app.paused = False