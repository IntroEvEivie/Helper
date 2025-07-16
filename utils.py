import os
import json
import pygame
from datetime import datetime, time
from config import WORK_START, WORK_END, BREAKS, COLOR_PROGRESS_BG, COLOR_PROGRESS_FG, COLOR_TEXT, COLOR_GRID

# Расчёт времени в секундах
def to_secs(t):
    return t.hour * 3600 + t.minute * 60 + t.second

work_start_s = to_secs(WORK_START)
work_end_s   = to_secs(WORK_END)
work_duration = work_end_s - work_start_s

def get_current_work_second():
    now = datetime.now().time()
    sec = to_secs(now)
    if sec < work_start_s:
        return 0
    if sec >= work_end_s:
        return work_duration
    return sec - work_start_s

def is_during_break(sec):
    t = work_start_s + sec
    tt = time(hour=t//3600, minute=(t%3600)//60)
    for a, b in BREAKS:
        if a <= tt < b:
            return True
    return False

# Конфигурация лаунчера
def load_config():
    config = {
        "apps": [
            {"name": "Блокнот", "path": "notepad.exe", "icon": None},
            {"name": "Калькулятор", "path": "calc.exe", "icon": None},
            {"name": "Проводник", "path": "explorer.exe", "icon": None},
        ]
    }

    try:
        if os.path.exists("launcher_config.json"):
            with open("launcher_config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
    except:
        pass

    # Загрузка иконок
    for app in config["apps"]:
        if app.get("icon") and os.path.exists(app["icon"]):
            try:
                icon = pygame.image.load(app["icon"])
                app["icon_surface"] = pygame.transform.scale(icon, (APP_ICON_SIZE, APP_ICON_SIZE))
            except:
                app["icon_surface"] = None
        else:
            app["icon_surface"] = None

    return config

def save_config(config):
    try:
        with open("launcher_config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except:
        pass

# Управление задачами
def load_tasks():
    try:
        if os.path.exists("tasks.json"):
            with open("tasks.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass

    # Пример задач по умолчанию
    return [
        {
            "title": "Проект А",
            "target": 100,
            "completed": 30,
            "expanded": True,
            "subtasks": [
                {"title": "Анализ требований", "target": 30, "completed": 20},
                {"title": "Проектирование", "target": 40, "completed": 10},
                {"title": "Тестирование", "target": 30, "completed": 0}
            ]
        },
        {
            "title": "Проект Б",
            "target": 80,
            "completed": 10,
            "expanded": False,
            "subtasks": [
                {"title": "Исследование", "target": 40, "completed": 10},
                {"title": "Разработка", "target": 40, "completed": 0}
            ]
        }
    ]

def save_tasks(tasks):
    try:
        with open("tasks.json", "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
    except:
        pass

def calculate_task_progress(task):
    total_target = 0
    total_completed = 0
    for subtask in task["subtasks"]:
        total_target += subtask["target"]
        total_completed += subtask["completed"]

    task["target"] = total_target
    task["completed"] = total_completed
    return task

# Рисование прогресс-бара
def draw_progress_bar(surface, x, y, width, height, completed, target):
    pygame.draw.rect(surface, COLOR_PROGRESS_BG, (x, y, width, height), border_radius=3)

    if target > 0:
        progress_width = max(5, int(width * min(1, completed / target)))
        pygame.draw.rect(surface, COLOR_PROGRESS_FG, (x, y, progress_width, height), border_radius=3)

    font = pygame.font.SysFont(None, 16)
    progress_text = f"{completed}/{target}"
    text_surf = font.render(progress_text, True, COLOR_TEXT)
    text_rect = text_surf.get_rect(center=(x + width // 2, y + height // 2))
    surface.blit(text_surf, text_rect)

    pygame.draw.rect(surface, COLOR_GRID, (x, y, width, height), 1, border_radius=3)
