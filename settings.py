import pygame

pygame.init()
pygame.font.init()
pygame.mixer.init()

# --- 修改这里：将 800, 600 改为 1920, 1080 ---
WIDTH, HEIGHT = 1920, 1080
FPS = 120

# 颜色常量保持不变
BG_COLOR = (30, 30, 30)
RED = (255, 80, 80)
BLUE = (80, 150, 255)
GREEN = (80, 255, 80)

FONT = pygame.font.Font(None, 22)