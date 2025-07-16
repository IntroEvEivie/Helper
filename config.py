import os
import pygame
from datetime import time

# Конфиг рабочего дня и перерывов
WORK_START = time(8, 30)
WORK_END   = time(17, 0)
BREAKS     = [
    (time(10, 0), time(10, 10)),
    (time(12, 0), time(12, 30)),
    (time(14, 0), time(14, 10)),
    (time(16, 0), time(16, 10)),
]

# Цвета
COLOR_WORKED    = (50, 205, 50)
COLOR_REMAINING = (0x1E, 0x1F, 0x22)
COLOR_BREAK     = (255, 140, 0)
COLOR_CURRENT   = (220, 20, 60)
COLOR_BG        = (20, 20, 20)
COLOR_GRID      = (60, 60, 60)
COLOR_BTN       = (100, 100, 100)
COLOR_BTN_DARK  = (0x1B, 0x1D, 0x23)
COLOR_BTN_HL    = (150, 150, 150)
COLOR_TEXT      = (200, 200, 200)
COLOR_PANEL     = (50, 50, 70)
COLOR_PROGRESS_BG = (60, 60, 80)
COLOR_PROGRESS_FG = (70, 130, 180)
COLOR_SCROLLBAR = (100, 100, 120)

# Размеры
WINDOW_SIZE = 350
PIXEL_SIZE  = 175
ICON_SIZE   = 25
APP_ICON_SIZE = 64
TASK_ITEM_HEIGHT = 60
SUBTASK_ITEM_HEIGHT = 45
SCROLLBAR_WIDTH = 15
PROGRESS_BAR_HEIGHT = 20
PROGRESS_BAR_WIDTH = 200

# Позиция окна
pygame.init()
scr_info = pygame.display.Info()
SCREEN_W, SCREEN_H = scr_info.current_w, scr_info.current_h
pos_full = (SCREEN_W - WINDOW_SIZE, SCREEN_H - WINDOW_SIZE)
pos_icon = (SCREEN_W - ICON_SIZE,   SCREEN_H - ICON_SIZE - 40)
