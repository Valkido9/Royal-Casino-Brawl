import pygame
import os

# --- 最优先导入 config 以劫持音频 ---
import config
from config import BG_MUSIC_PATH, SFX_PAYMENT_PATH, SFX_UGH_PATH

from settings import WIDTH, HEIGHT, FPS
from ui_components import get_cn_font

from game_logic import update_fighting_logic
from game_ui import (
    render_start_screen, render_debug_select, render_betting,
    render_fighting, render_round_over, render_leaderboard,
    render_game_over, render_settings
)
from almanac import render_almanac, handle_almanac_event

class GameApp:
    def __init__(self):
        pygame.display.init()

        self.bgm_volume = 0.5
        try:
            pygame.mixer.music.load(BG_MUSIC_PATH)
            pygame.mixer.music.set_volume(self.bgm_volume)
            pygame.mixer.music.play(-1)
        except:
            pass

        try:
            self.sfx_payment = pygame.mixer.Sound(SFX_PAYMENT_PATH)
            self.sfx_ugh = pygame.mixer.Sound(SFX_UGH_PATH)
        except:
            self.sfx_payment = self.sfx_ugh = None

        self.current_res = (1280, 720)
        self.screen = pygame.display.set_mode(self.current_res, pygame.RESIZABLE)
        self.logical_surface = pygame.Surface((WIDTH, HEIGHT))

        pygame.key.set_repeat(400, 50)
        pygame.display.set_caption("孟加拉国皇家赌场")
        self.clock = pygame.time.Clock()

        self.font_huge = get_cn_font(80)
        self.font_large = get_cn_font(40)
        self.font_normal = get_cn_font(28)
        self.font_small = get_cn_font(22)

        self.gamblers = {
            "玩家": {"taka": 10000, "status": "正常", "last_choice": None, "bet_type": "普通", "prev_taka": 10000},
            "孟加拉国总统": {"taka": 10000, "status": "正常", "last_choice": None, "bet_type": "普通",
                             "prev_taka": 10000},
            "狗男": {"taka": 10000, "status": "正常", "last_choice": None, "bet_type": "普通", "prev_taka": 10000},
            "守望先锋玩家": {"taka": 10000, "status": "正常", "last_choice": None, "bet_type": "普通",
                             "prev_taka": 10000},
            "运气守恒定律": {"taka": 10000, "status": "正常", "last_choice": None, "bet_type": "普通",
                             "prev_taka": 10000},
            "我是鸿荧厨": {"taka": 10000, "status": "正常", "last_choice": None, "bet_type": "普通",
                           "prev_taka": 10000},
            "帝者战神": {"taka": 10000, "status": "正常", "last_choice": None, "bet_type": "普通", "prev_taka": 10000},
            "标杆Hyucen": {"taka": 10000, "status": "正常", "last_choice": None, "bet_type": "普通",
                           "prev_taka": 10000},
            "AutumnGoose": {"taka": 10000, "status": "正常", "last_choice": None, "bet_type": "普通",
                            "prev_taka": 10000}
        }

        # 核心状态机控制变量
        self.game_state = "START_SCREEN"
        self.game_mode = "1v1"
        self.current_round = 1
        self.agents = []
        self.bullets = []
        self.scaled_bullets = set()

        self.show_settings = False
        self.paused = False

        self.current_hero_left_name = ""
        self.current_hero_right_name = ""
        self.winner_text = ""
        self.kill_log_text = ""

        self.betting_start_time = 0
        self.ai_decisions = {}
        self.fight_start_ticks = 0
        self.round_over_start_ticks = 0
        self.safe_zone_radius = 1100

        self.feedback_particles = []
        self.bet_result_type = None
        self.spectate_count = 0
        self.has_played_result_sfx = False

        self.lb_data = {}
        self.lb_start_time = 0

        self.player_name = "玩家"
        self.input_active = False

        self.debug_buffer = ""
        self.debug_left_hero = None
        self.debug_right_hero = None

        # 战斗状态相关
        self.is_time_stopped = False
        self.time_stop_owner = None
        self.elapsed_fight = 0

        # 用户交互控制相关
        self.mouse_pos = (0, 0)
        self.mouse_click = False
        self.is_mouse_held = False
        self.scale_x = 1
        self.scale_y = 1

    def set_resolution(self, w, h):
        self.current_res = (w, h)
        self.screen = pygame.display.set_mode(self.current_res, pygame.RESIZABLE)

    def run(self):
        running = True
        while running:
            # 1. 解析动态分辨率
            if self.screen.get_size() != self.current_res:
                self.current_res = self.screen.get_size()

            raw_mx, raw_my = pygame.mouse.get_pos()
            if self.current_res[0] > 0 and self.current_res[1] > 0:
                self.scale_x = WIDTH / self.current_res[0]
                self.scale_y = HEIGHT / self.current_res[1]
            else:
                self.scale_x, self.scale_y = 1, 1

            self.mouse_pos = (int(raw_mx * self.scale_x), int(raw_my * self.scale_y))
            self.mouse_click = False
            self.is_mouse_held = pygame.mouse.get_pressed()[0]

            # 2. 全局事件捕获
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.current_res = (event.w, event.h)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.game_state in ["FIGHTING", "BETTING"]:
                            self.paused = not self.paused
                            self.show_settings = self.paused
                        else:
                            self.show_settings = not self.show_settings

                    # --- 修改点：处理玩家名字输入逻辑与 Debug 指令的隔离 ---
                    if self.game_state == "START_SCREEN" and not self.show_settings and getattr(self, 'input_active', False):
                        if event.key == pygame.K_BACKSPACE:
                            self.player_name = self.player_name[:-1]
                        elif event.key == pygame.K_RETURN:
                            self.input_active = False
                            pygame.key.stop_text_input()
                    else:
                        # 监听 debug 指令：在 START_SCREEN (未处于输入状态时) 或 暂停设置界面(show_settings) 均可触发
                        if (self.game_state == "START_SCREEN" and not getattr(self, 'input_active', False)) or self.show_settings:
                            if event.unicode.isprintable() and len(event.unicode) > 0:
                                self.debug_buffer += event.unicode
                                if len(self.debug_buffer) > 5: self.debug_buffer = self.debug_buffer[-5:]
                                if self.debug_buffer.lower() == "debug":
                                    self.game_state = "DEBUG_SELECT"
                                    self.debug_buffer = ""
                                    self.show_settings = False  # 关闭可能处于打开状态的设置界面
                                    self.paused = False         # 解除由于打开设置引发的暂停

                elif event.type == pygame.TEXTINPUT:
                    if self.game_state == "START_SCREEN" and not self.show_settings:
                        if getattr(self, 'input_active', False):
                            self.player_name += event.text
                            if len(self.player_name) > 12:
                                self.player_name = self.player_name[:12]

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.mouse_click = True

                elif event.type == pygame.MOUSEWHEEL:
                    handle_almanac_event(self, event)

            # 3. 状态路由渲染
            if self.game_state == "START_SCREEN":
                render_start_screen(self)
            elif self.game_state == "DEBUG_SELECT":
                render_debug_select(self)
            elif self.game_state == "BETTING":
                render_betting(self)
            elif self.game_state == "FIGHTING":
                update_fighting_logic(self)
                render_fighting(self)
            elif self.game_state == "ROUND_OVER":
                render_round_over(self)
            elif self.game_state == "ROUND_LEADERBOARD":
                render_leaderboard(self)
            elif self.game_state == "GAME_OVER":
                render_game_over(self)
            elif self.game_state == "ALMANAC":
                render_almanac(self)

            if self.show_settings:
                render_settings(self)

            # 4. 主画布拉伸至实际窗口投射
            if self.current_res == (WIDTH, HEIGHT):
                self.screen.blit(self.logical_surface, (0, 0))
            else:
                scaled_surf = pygame.transform.scale(self.logical_surface, self.current_res)
                self.screen.blit(scaled_surf, (0, 0))

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


def main():
    app = GameApp()
    app.run()


if __name__ == "__main__":
    main()