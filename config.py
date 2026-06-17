import pygame
import os

# ==========================================
# 1. 核心音频系统初始化与音效工厂劫持（必须最先执行）
# ==========================================
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

global_sfx_vol = [1.0]
all_sounds = []
_original_sound = pygame.mixer.Sound

def hooked_sound(*args, **kwargs):
    snd = _original_sound(*args, **kwargs)
    snd.set_volume(global_sfx_vol[0])
    all_sounds.append(snd)
    return snd

pygame.mixer.Sound = hooked_sound

# ==========================================
# 2. 全局路径与基础配置
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BG_MUSIC_PATH = os.path.join(BASE_DIR, "sounds", "gongyong", "background.mp3")
SFX_PAYMENT_PATH = os.path.join(BASE_DIR, "sounds", "gongyong", "payment.mp3")
SFX_UGH_PATH = os.path.join(BASE_DIR, "sounds", "gongyong", "ugh.mp3")

BET_TABLE = [2000, 2400, 3000, 4000, 5500, 8000, 12000, 18000, 30000, 50000]