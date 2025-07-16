import os
import sys
import threading
import json
import subprocess
from datetime import datetime, time
import pygame, ctypes
from pygame.locals import *


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
COLOR_WORKED    = (50, 205, 50)  # Прогрессбар дня (отработано) (0x11, 0x13, 0x17) (0x4A, 0xFF, 0x87) (250, 205, 50) #24F2BFFF #2F2F2F
COLOR_REMAINING = (0x1E, 0x1F, 0x22) # #1E1F22(40, 40, 40)
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
WINDOW_SIZE = 350 # 350
PIXEL_SIZE  = 175 # 175
ICON_SIZE   = 25   # размер окна при «сворачивании»
APP_ICON_SIZE = 64 # размер иконок приложений
TASK_ITEM_HEIGHT = 60
SUBTASK_ITEM_HEIGHT = 45
SCROLLBAR_WIDTH = 15
PROGRESS_BAR_HEIGHT = 20
PROGRESS_BAR_WIDTH = 200

# Позиция (нижний правый угол экрана)
pygame.init()
scr_info = pygame.display.Info()
SCREEN_W, SCREEN_H = scr_info.current_w, scr_info.current_h
pos_full = (SCREEN_W - WINDOW_SIZE, SCREEN_H - WINDOW_SIZE)
pos_icon = (SCREEN_W - ICON_SIZE,   SCREEN_H - ICON_SIZE - 40)

# Глобальные состояния
current_second = 0
running        = True
is_minimized   = False
current_screen = "main"  # "main", "launcher", "settings", "tasks"
scroll_offset = 0
scroll_dragging = False
scroll_drag_start = 0
scroll_content_height = 0
editing_task = None
editing_subtask = None
editing_field = None
input_text = ""

# Расчёт в секундах
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

# Фоновый поток обновления времени
def time_updater():
    global current_second, running
    while running:
        current_second = get_current_work_second()
        threading.Event().wait(1)

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

    # Создаем пример задач, если файл не существует
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
    """Пересчитывает прогресс задачи на основе подзадач"""
    total_target = 0
    total_completed = 0
    for subtask in task["subtasks"]:
        total_target += subtask["target"]
        total_completed += subtask["completed"]

    task["target"] = total_target
    task["completed"] = total_completed
    return task

# Рисуем прогресс-бар
def draw_progress_bar(surface, x, y, width, height, completed, target):
    # Фон прогресс-бара
    pygame.draw.rect(surface, COLOR_PROGRESS_BG, (x, y, width, height), border_radius=3)

    # Заполнение прогресс-бара
    if target > 0:
        progress_width = max(5, int(width * min(1, completed / target)))
        pygame.draw.rect(surface, COLOR_PROGRESS_FG, (x, y, progress_width, height), border_radius=3)

    # Текст прогресса
    font = pygame.font.SysFont(None, 16)
    progress_text = f"{completed}/{target}"
    text_surf = font.render(progress_text, True, COLOR_TEXT)
    text_rect = text_surf.get_rect(center=(x + width // 2, y + height // 2))
    surface.blit(text_surf, text_rect)

    # Граница
    pygame.draw.rect(surface, COLOR_GRID, (x, y, width, height), 1, border_radius=3)

# Рисуем интерфейс
def draw(surface):
    surface.fill(COLOR_BG)

    # Заголовок для всех экранов
    pygame.draw.rect(surface, COLOR_PANEL, (0, 0, surface.get_width(), 30))
    font = pygame.font.SysFont(None, 24)
    title = ""
    if current_screen == "main":
        title = "Рабочий день"
    elif current_screen == "launcher":
        title = "Запуск программ"
    elif current_screen == "settings":
        title = "Настройки"
    elif current_screen == "tasks":
        title = "Управление задачами"

    title_text = font.render(title, True, COLOR_TEXT)
    surface.blit(title_text, (10, 5))

    # Кнопка закрытия
    close_rect = pygame.Rect(surface.get_width() - 40, 5, 30, 20)
    pygame.draw.rect(surface, (200, 0, 0), close_rect)
    close_text = font.render("X", True, (255, 255, 255))
    surface.blit(close_text, (close_rect.x + 10, close_rect.y - 2))

    # Кнопки переключения экранов
    buttons = []
    if current_screen != "main":
        main_btn = pygame.Rect(surface.get_width() - 120, 5, 30, 20)
        pygame.draw.rect(surface, COLOR_BTN, main_btn)
        main_text = font.render("Д", True, COLOR_TEXT)
        surface.blit(main_text, (main_btn.x + 8, main_btn.y - 2))
        buttons.append(("main", main_btn))
    else:
        main_btn = None

    if current_screen != "launcher":
        apps_btn = pygame.Rect(surface.get_width() - 80, 5, 30, 20)
        pygame.draw.rect(surface, COLOR_BTN, apps_btn)
        apps_text = font.render("П", True, COLOR_TEXT)
        surface.blit(apps_text, (apps_btn.x + 8, apps_btn.y - 2))
        buttons.append(("launcher", apps_btn))
    else:
        apps_btn = None

    if current_screen != "settings":
        settings_btn = pygame.Rect(surface.get_width() - 160, 5, 30, 20)
        pygame.draw.rect(surface, COLOR_BTN, settings_btn)
        settings_text = font.render("Н", True, COLOR_TEXT)
        surface.blit(settings_text, (settings_btn.x + 8, settings_btn.y - 2))
        buttons.append(("settings", settings_btn))
    else:
        settings_btn = None

    if current_screen != "tasks":
        tasks_btn = pygame.Rect(surface.get_width() - 200, 5, 30, 20)
        pygame.draw.rect(surface, COLOR_BTN, tasks_btn)
        tasks_text = font.render("З", True, COLOR_TEXT)
        surface.blit(tasks_text, (tasks_btn.x + 8, tasks_btn.y - 2))
        buttons.append(("tasks", tasks_btn))
    else:
        tasks_btn = None

    # Отрисовка текущего экрана
    screen_buttons = []
    if current_screen == "main":
        min_btn = draw_main_screen(surface)
        screen_buttons.append(("min", min_btn))
    elif current_screen == "launcher":
        app_rects = draw_launcher_screen(surface)
        screen_buttons.extend([("app", rect, app) for rect, app in app_rects])
    elif current_screen == "settings":
        app_rects, add_rect = draw_settings_screen(surface)
        screen_buttons.extend([("del_app", rect, idx) for rect, idx in app_rects])
        screen_buttons.append(("add_app", add_rect))
    elif current_screen == "tasks":
        task_buttons = draw_tasks_screen(surface)
        screen_buttons.extend(task_buttons)

    # Возвращаем все кнопки
    return {
        "close": close_rect,
        "nav_buttons": buttons,
        "screen_buttons": screen_buttons
    }

def draw_main_screen(surface):
    global is_minimized

    # Если окно свернуто, рисуем кнопку восстановления
    if is_minimized:
        restore_btn = pygame.Rect(0, 0, ICON_SIZE, ICON_SIZE)
        pygame.draw.rect(surface, COLOR_BTN_DARK, restore_btn)
        restore_text = font = pygame.font.SysFont(None, 24).render("_", True, COLOR_TEXT)
        surface.blit(restore_text, (restore_btn.x + 5, restore_btn.y + 2))
        return restore_btn

    size = PIXEL_SIZE
    off = (surface.get_width() - size) // 2
    """
    # Сетка
    step = size // 5
    for i in range(0, size + 1, step):
        pygame.draw.line(surface, COLOR_GRID, (off, off + i), (off + size, off + i), 1)
        pygame.draw.line(surface, COLOR_GRID, (off + i, off), (off + i, off + size), 1)
        """
    # Пиксели
    for y in range(size):
        for x in range(size):
            pos = y * size + x
            if pos >= work_duration:
                continue

            # Выбираем цвет
            if pos < current_second:
                c = COLOR_WORKED
            else:
                c = COLOR_REMAINING
            if is_during_break(pos):
                c = COLOR_BREAK
            if pos == current_second:
                c = COLOR_CURRENT

            surface.set_at((off + x, off + y), c)

    # Время
    font = pygame.font.SysFont(None, 24)
    ts = datetime.now().strftime("%H:%M:%S")
    txt = font.render(ts, True, COLOR_TEXT)
    surface.blit(txt, ((WINDOW_SIZE - txt.get_width()) // 2, 40))

    # Легенда
    legends = [
        ("Отработано", COLOR_WORKED),
        ("Перерыв", COLOR_BREAK),
        ("Осталось", COLOR_REMAINING),
        ("Сейчас", COLOR_CURRENT)
    ]

    for i, (lbl, col) in enumerate(legends):
        x0 = 20 + i * 80
        pygame.draw.rect(surface, col, (x0, WINDOW_SIZE - 30, 15, 15))
        t = font.render(lbl, True, COLOR_TEXT)
        surface.blit(t, (x0 + 20, WINDOW_SIZE - 30))

    # Кнопка свернуть
    min_btn = pygame.Rect(WINDOW_SIZE - 80, 40, 30, 30)
    pygame.draw.rect(surface, COLOR_BTN, min_btn)
    min_text = font.render("_", True, COLOR_TEXT)
    surface.blit(min_text, (min_btn.x + 10, min_btn.y + 5))

    return min_btn

def draw_launcher_screen(surface):
    config = load_config()
    apps = config["apps"]

    # Сетка для иконок (3x3)
    cols = 3
    rows = (len(apps) + cols - 1) // cols
    start_y = 50

    app_rects = []

    for i, app in enumerate(apps):
        row = i // cols
        col = i % cols

        x = 30 + col * (APP_ICON_SIZE + 40)
        y = start_y + row * (APP_ICON_SIZE + 40)

        # Область иконки
        icon_rect = pygame.Rect(x, y, APP_ICON_SIZE, APP_ICON_SIZE)

        # Фон иконки
        pygame.draw.rect(surface, COLOR_BTN, icon_rect, border_radius=10)

        # Иконка приложения
        if app.get("icon_surface"):
            surface.blit(app["icon_surface"], (x, y))
        else:
            # Заглушка для приложений без иконки
            font = pygame.font.SysFont(None, 20)
            app_text = font.render("APP", True, COLOR_TEXT)
            surface.blit(app_text, (x + APP_ICON_SIZE//2 - app_text.get_width()//2,
                                   y + APP_ICON_SIZE//2 - app_text.get_height()//2))

        # Название приложения
        name_text = pygame.font.SysFont(None, 16).render(app["name"], True, COLOR_TEXT)
        surface.blit(name_text, (x + APP_ICON_SIZE//2 - name_text.get_width()//2,
                                y + APP_ICON_SIZE + 5))

        app_rects.append((icon_rect, app))

    return app_rects

def draw_settings_screen(surface):
    config = load_config()
    apps = config["apps"]

    font = pygame.font.SysFont(None, 20)
    y_offset = 40

    # Заголовок
    title = font.render("Настройки приложений:", True, COLOR_TEXT)
    surface.blit(title, (10, y_offset))
    y_offset += 30

    app_rects = []

    for i, app in enumerate(apps):
        # Название приложения
        name_text = font.render(f"{i+1}. {app['name']}", True, COLOR_TEXT)
        surface.blit(name_text, (20, y_offset))

        # Кнопка удаления
        del_rect = pygame.Rect(WINDOW_SIZE - 50, y_offset, 30, 20)
        pygame.draw.rect(surface, (200, 50, 50), del_rect, border_radius=5)
        del_text = font.render("X", True, (255, 255, 255))
        surface.blit(del_text, (del_rect.x + 10, del_rect.y))

        # Путь приложения
        path_text = font.render(app["path"], True, (150, 150, 150))
        surface.blit(path_text, (20, y_offset + 25))

        app_rects.append((del_rect, i))
        y_offset += 60

    # Разделитель
    pygame.draw.line(surface, COLOR_GRID, (10, y_offset), (WINDOW_SIZE - 10, y_offset), 1)
    y_offset += 20

    # Кнопка добавления
    add_rect = pygame.Rect(WINDOW_SIZE - 150, y_offset, 140, 30)
    pygame.draw.rect(surface, COLOR_BTN, add_rect, border_radius=5)
    add_text = font.render("+ Добавить приложение", True, COLOR_TEXT)
    surface.blit(add_text, (add_rect.x + 10, add_rect.y + 5))

    return app_rects, add_rect

def draw_tasks_screen(surface):
    global scroll_offset, scroll_content_height
    tasks = load_tasks()
    font = pygame.font.SysFont(None, 22)
    small_font = pygame.font.SysFont(None, 18)

    y = 40
    buttons = []
    scroll_content_height = 0

    # Рисуем заголовки колонок
    pygame.draw.rect(surface, COLOR_PANEL, (0, y, WINDOW_SIZE, 30))
    title_task = font.render("Задача", True, COLOR_TEXT)
    title_progress = font.render("Прогресс", True, COLOR_TEXT)
    surface.blit(title_task, (10, y + 5))
    surface.blit(title_progress, (WINDOW_SIZE - 220, y + 5))
    y += 35

    # Рассчитываем общую высоту контента
    for task in tasks:
        scroll_content_height += TASK_ITEM_HEIGHT
        if task["expanded"]:
            scroll_content_height += len(task["subtasks"]) * SUBTASK_ITEM_HEIGHT

    # Ограничиваем скролл
    max_scroll = max(0, scroll_content_height - (WINDOW_SIZE - y))
    scroll_offset = max(0, min(scroll_offset, max_scroll))

    # Рисуем задачи
    visible_y = y - scroll_offset
    for task_idx, task in enumerate(tasks):
        if visible_y < -TASK_ITEM_HEIGHT or visible_y > WINDOW_SIZE:
            visible_y += TASK_ITEM_HEIGHT
            if task["expanded"]:
                visible_y += len(task["subtasks"]) * SUBTASK_ITEM_HEIGHT
            continue

        # Фон задачи
        task_rect = pygame.Rect(5, visible_y, WINDOW_SIZE - 10, TASK_ITEM_HEIGHT - 5)
        pygame.draw.rect(surface, COLOR_BTN, task_rect, border_radius=5)
        pygame.draw.rect(surface, COLOR_GRID, task_rect, 1, border_radius=5)

        # Иконка раскрытия/скрытия подзадач
        expand_rect = pygame.Rect(10, visible_y + 10, 20, 20)
        pygame.draw.rect(surface, COLOR_PROGRESS_BG, expand_rect, border_radius=3)
        expand_text = font.render("▼" if task["expanded"] else "▶", True, COLOR_TEXT)
        surface.blit(expand_text, (expand_rect.x + 5, expand_rect.y))
        buttons.append(("expand", expand_rect, task_idx))

        # Название задачи
        task_title = small_font.render(task["title"], True, COLOR_TEXT)
        surface.blit(task_title, (40, visible_y + 10))

        # Прогресс-бар задачи
        progress_x = WINDOW_SIZE - PROGRESS_BAR_WIDTH - 10
        progress_y = visible_y + (TASK_ITEM_HEIGHT - PROGRESS_BAR_HEIGHT) // 2
        draw_progress_bar(surface, progress_x, progress_y, PROGRESS_BAR_WIDTH, PROGRESS_BAR_HEIGHT,
                         task["completed"], task["target"])

        # Кнопка редактирования задачи
        edit_rect = pygame.Rect(WINDOW_SIZE - 40, visible_y + 10, 25, 25)
        pygame.draw.rect(surface, COLOR_PROGRESS_BG, edit_rect, border_radius=3)
        edit_text = small_font.render("✎", True, COLOR_TEXT)
        surface.blit(edit_text, (edit_rect.x + 5, edit_rect.y))
        buttons.append(("edit_task", edit_rect, task_idx))

        visible_y += TASK_ITEM_HEIGHT

        # Подзадачи
        if task["expanded"]:
            for subtask_idx, subtask in enumerate(task["subtasks"]):
                if visible_y < -SUBTASK_ITEM_HEIGHT or visible_y > WINDOW_SIZE:
                    visible_y += SUBTASK_ITEM_HEIGHT
                    continue

                # Фон подзадачи
                subtask_rect = pygame.Rect(20, visible_y, WINDOW_SIZE - 25, SUBTASK_ITEM_HEIGHT - 5)
                pygame.draw.rect(surface, COLOR_PROGRESS_BG, subtask_rect, border_radius=3)
                pygame.draw.rect(surface, COLOR_GRID, subtask_rect, 1, border_radius=3)

                # Название подзадачи
                subtask_title = small_font.render(subtask["title"], True, COLOR_TEXT)
                surface.blit(subtask_title, (30, visible_y + 10))

                # Прогресс-бар подзадачи
                progress_x = WINDOW_SIZE - PROGRESS_BAR_WIDTH - 10
                progress_y = visible_y + (SUBTASK_ITEM_HEIGHT - PROGRESS_BAR_HEIGHT) // 2
                draw_progress_bar(surface, progress_x, progress_y, PROGRESS_BAR_WIDTH,
                                 PROGRESS_BAR_HEIGHT // 2, subtask["completed"], subtask["target"])

                # Кнопки редактирования подзадачи
                edit_rect = pygame.Rect(WINDOW_SIZE - 40, visible_y + 5, 25, 20)
                pygame.draw.rect(surface, COLOR_BTN, edit_rect, border_radius=3)
                edit_text = small_font.render("✎", True, COLOR_TEXT)
                surface.blit(edit_text, (edit_rect.x + 5, edit_rect.y))
                buttons.append(("edit_subtask", edit_rect, task_idx, subtask_idx))

                visible_y += SUBTASK_ITEM_HEIGHT

    # Кнопка добавления новой задачи
    add_rect = pygame.Rect(WINDOW_SIZE - 150, WINDOW_SIZE - 40, 140, 30)
    pygame.draw.rect(surface, COLOR_BTN, add_rect, border_radius=5)
    add_text = font.render("+ Новая задача", True, COLOR_TEXT)
    surface.blit(add_text, (add_rect.x + 10, add_rect.y + 5))
    buttons.append(("add_task", add_rect))

    # Рисуем скроллбар, если контент не помещается
    if scroll_content_height > WINDOW_SIZE - y:
        scrollbar_height = (WINDOW_SIZE - y) * (WINDOW_SIZE - y) // scroll_content_height
        scrollbar_height = max(30, scrollbar_height)
        scrollbar_y = y + (scroll_offset / scroll_content_height) * (WINDOW_SIZE - y - scrollbar_height)

        scrollbar_rect = pygame.Rect(WINDOW_SIZE - SCROLLBAR_WIDTH - 5, scrollbar_y,
                                    SCROLLBAR_WIDTH, scrollbar_height)
        pygame.draw.rect(surface, COLOR_SCROLLBAR, scrollbar_rect, border_radius=5)

    return buttons

# Функция для отображения редактора задач
def draw_edit_dialog(surface, title, value):
    # Затемнение фона
    s = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 180))
    surface.blit(s, (0, 0))

    # Диалоговое окно
    dialog_rect = pygame.Rect(50, 100, WINDOW_SIZE - 100, 200)
    pygame.draw.rect(surface, COLOR_BG, dialog_rect, border_radius=10)
    pygame.draw.rect(surface, COLOR_GRID, dialog_rect, 2, border_radius=10)

    font = pygame.font.SysFont(None, 24)
    title_text = font.render(title, True, COLOR_TEXT)
    surface.blit(title_text, (dialog_rect.x + 20, dialog_rect.y + 20))

    # Поле ввода
    input_rect = pygame.Rect(dialog_rect.x + 20, dialog_rect.y + 60, dialog_rect.width - 40, 40)
    pygame.draw.rect(surface, COLOR_BTN, input_rect, border_radius=5)
    pygame.draw.rect(surface, COLOR_GRID, input_rect, 1, border_radius=5)

    input_font = pygame.font.SysFont(None, 22)
    text_surf = input_font.render(input_text, True, COLOR_TEXT)
    surface.blit(text_surf, (input_rect.x + 10, input_rect.y + 10))

    # Кнопки
    ok_rect = pygame.Rect(dialog_rect.x + 50, dialog_rect.y + 140, 100, 40)
    pygame.draw.rect(surface, COLOR_PROGRESS_FG, ok_rect, border_radius=5)
    ok_text = font.render("OK", True, COLOR_TEXT)
    surface.blit(ok_text, (ok_rect.x + 35, ok_rect.y + 10))

    cancel_rect = pygame.Rect(dialog_rect.x + 170, dialog_rect.y + 140, 100, 40)
    pygame.draw.rect(surface, COLOR_BTN, cancel_rect, border_radius=5)
    cancel_text = font.render("Отмена", True, COLOR_TEXT)
    surface.blit(cancel_text, (cancel_rect.x + 20, cancel_rect.y + 10))

    return input_rect, ok_rect, cancel_rect

def main():
    global running, is_minimized, current_screen, scroll_offset
    global scroll_dragging, scroll_drag_start, editing_task, editing_subtask
    global editing_field, input_text, scroll_content_height

    # Создаем окно
    os.environ['SDL_VIDEO_WINDOW_POS'] = f"{pos_full[0]},{pos_full[1]}"
    screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE), pygame.NOFRAME)
    pygame.display.set_caption("Рабочий день + Лаунчер + Задачи")
    clock = pygame.time.Clock()

    # Запускаем фоновый поток
    threading.Thread(target=time_updater, daemon=True).start()

    # Основной цикл
    buttons = {}  # Будем хранить кнопки здесь
    while running:
        # Обработка событий
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Обработка нажатия кнопки мыши
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()

                # Проверка клика по кнопкам заголовка
                if "close" in buttons and buttons["close"].collidepoint(pos) and not is_minimized:
                    running = False

                # Навигационные кнопки
                if "nav_buttons" in buttons:
                    for btn_type, btn_rect in buttons["nav_buttons"]:
                        if btn_rect.collidepoint(pos):
                            current_screen = btn_type

                # Основной экран
                if current_screen == "main":
                    # Сворачивание/разворачивание
                    if "screen_buttons" in buttons and buttons["screen_buttons"]:
                        btn_type, btn_rect, *z = buttons["screen_buttons"][0]
                        if btn_type == "min" and btn_rect.collidepoint(pos):
                            is_minimized = not is_minimized
                            if is_minimized:
                                os.environ['SDL_VIDEO_WINDOW_POS'] = f"{pos_icon[0]},{pos_icon[1]}"
                                pygame.display.quit()
                                pygame.display.init()
                                screen = pygame.display.set_mode((ICON_SIZE, ICON_SIZE), pygame.NOFRAME)
                            else:
                                os.environ['SDL_VIDEO_WINDOW_POS'] = f"{pos_full[0]},{pos_full[1]}"
                                pygame.display.quit()
                                pygame.display.init()
                                screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE), pygame.NOFRAME)

                # Экран лаунчера
                elif current_screen == "launcher" and "screen_buttons" in buttons:
                    for btn in buttons["screen_buttons"]:
                        if btn[0] == "app" and btn[1].collidepoint(pos):
                            # Запуск приложения
                            try:
                                if sys.platform == "win32":
                                    os.startfile(btn[2]["path"])
                                else:
                                    subprocess.Popen(btn[2]["path"])
                            except Exception as e:
                                print(f"Ошибка запуска приложения: {e}")

                # Экран настроек
                elif current_screen == "settings" and "screen_buttons" in buttons:
                    for btn in buttons["screen_buttons"]:
                        if btn[0] == "del_app" and btn[1].collidepoint(pos):
                            # Удаление приложения
                            config = load_config()
                            if 0 <= btn[2] < len(config["apps"]):
                                config["apps"].pop(btn[2])
                                save_config(config)
                        elif btn[0] == "add_app" and btn[1].collidepoint(pos):
                            # Простое добавление приложения (заглушка)
                            config = load_config()
                            config["apps"].append({
                                "name": f"Приложение {len(config['apps']) + 1}",
                                "path": "",
                                "icon": None
                            })
                            save_config(config)

                # Экран задач
                elif current_screen == "tasks" and "screen_buttons" in buttons:
                    for btn in buttons["screen_buttons"]:
                        if btn[0] == "expand" and btn[1].collidepoint(pos):
                            tasks = load_tasks()
                            tasks[btn[2]]["expanded"] = not tasks[btn[2]]["expanded"]
                            save_tasks(tasks)
                        elif btn[0] == "add_task" and btn[1].collidepoint(pos):
                            tasks = load_tasks()
                            tasks.append({
                                "title": "Новая задача",
                                "target": 100,
                                "completed": 0,
                                "expanded": True,
                                "subtasks": [
                                    {"title": "Первая подзадача", "target": 50, "completed": 0}
                                ]
                            })
                            save_tasks(tasks)
                        elif btn[0] == "edit_task" and btn[1].collidepoint(pos):
                            editing_task = btn[2]
                            editing_subtask = None
                            editing_field = "title"
                            input_text = load_tasks()[editing_task]["title"]
                        elif btn[0] == "edit_subtask" and btn[1].collidepoint(pos):
                            editing_task = btn[2]
                            editing_subtask = btn[3]
                            editing_field = "title"
                            input_text = load_tasks()[editing_task]["subtasks"][editing_subtask]["title"]

                # Начало перетаскивания скроллбара
                if current_screen == "tasks" and scroll_content_height > WINDOW_SIZE - 40:
                    scrollbar_height = (WINDOW_SIZE - 40) * (WINDOW_SIZE - 40) // scroll_content_height
                    scrollbar_height = max(30, scrollbar_height)
                    scrollbar_y = 40 + (scroll_offset / scroll_content_height) * (WINDOW_SIZE - 40 - scrollbar_height)

                    scrollbar_rect = pygame.Rect(WINDOW_SIZE - SCROLLBAR_WIDTH - 5, scrollbar_y,
                                               SCROLLBAR_WIDTH, scrollbar_height)
                    if scrollbar_rect.collidepoint(pos):
                        scroll_dragging = True
                        scroll_drag_start = pos[1]

            # Отпускание кнопки мыши
            elif event.type == pygame.MOUSEBUTTONUP:
                scroll_dragging = False

                # Обработка диалога редактирования
                if editing_task is not None:
                    input_rect, ok_rect, cancel_rect = draw_edit_dialog(screen, "Редактирование", input_text)
                    if ok_rect.collidepoint(pos):
                        tasks = load_tasks()
                        if editing_subtask is None:
                            # Редактирование задачи
                            if editing_field == "title":
                                tasks[editing_task]["title"] = input_text
                            elif editing_field == "completed":
                                try:
                                    tasks[editing_task]["completed"] = int(input_text)
                                except:
                                    pass
                            elif editing_field == "target":
                                try:
                                    tasks[editing_task]["target"] = int(input_text)
                                except:
                                    pass
                        else:
                            # Редактирование подзадачи
                            if editing_field == "title":
                                tasks[editing_task]["subtasks"][editing_subtask]["title"] = input_text
                            elif editing_field == "completed":
                                try:
                                    tasks[editing_task]["subtasks"][editing_subtask]["completed"] = int(input_text)
                                except:
                                    pass
                            elif editing_field == "target":
                                try:
                                    tasks[editing_task]["subtasks"][editing_subtask]["target"] = int(input_text)
                                except:
                                    pass

                        # Пересчитать прогресс задачи
                        tasks[editing_task] = calculate_task_progress(tasks[editing_task])
                        save_tasks(tasks)

                        editing_task = None
                        editing_subtask = None
                        editing_field = None
                        input_text = ""

                    elif cancel_rect.collidepoint(pos):
                        editing_task = None
                        editing_subtask = None
                        editing_field = None
                        input_text = ""

            # Прокрутка колесика мыши
            elif event.type == pygame.MOUSEWHEEL:
                if current_screen == "tasks" and scroll_content_height > WINDOW_SIZE - 40:
                    scroll_offset -= event.y * 30
                    max_scroll = max(0, scroll_content_height - (WINDOW_SIZE - 40))
                    scroll_offset = max(0, min(scroll_offset, max_scroll))

            # Перетаскивание скроллбара
            elif event.type == pygame.MOUSEMOTION and scroll_dragging:
                delta = event.pos[1] - scroll_drag_start
                scroll_drag_start = event.pos[1]

                scroll_offset += delta * (scroll_content_height / (WINDOW_SIZE - 40))
                max_scroll = max(0, scroll_content_height - (WINDOW_SIZE - 40))
                scroll_offset = max(0, min(scroll_offset, max_scroll))

                # Где «кликнуть» внутри окна (координаты относительно левого верхнего угла)
                # ctypes.windll.user32.SetForegroundWindow(screen)
            # Ввод текста в диалоге редактирования
            elif event.type == pygame.KEYDOWN and editing_task is not None:
                if event.key == pygame.K_RETURN:
                    # Обработка нажатия Enter (аналогично кнопке OK)
                    tasks = load_tasks()
                    if editing_subtask is None:
                        if editing_field == "title":
                            tasks[editing_task]["title"] = input_text
                        elif editing_field == "completed":
                            try:
                                tasks[editing_task]["completed"] = int(input_text)
                            except:
                                pass
                        elif editing_field == "target":
                            try:
                                tasks[editing_task]["target"] = int(input_text)
                            except:
                                pass
                    else:
                        if editing_field == "title":
                            tasks[editing_task]["subtasks"][editing_subtask]["title"] = input_text
                        elif editing_field == "completed":
                            try:
                                tasks[editing_task]["subtasks"][editing_subtask]["completed"] = int(input_text)
                            except:
                                pass
                        elif editing_field == "target":
                            try:
                                tasks[editing_task]["subtasks"][editing_subtask]["target"] = int(input_text)
                            except:
                                pass

                    tasks[editing_task] = calculate_task_progress(tasks[editing_task])
                    save_tasks(tasks)

                    editing_task = None
                    editing_subtask = None
                    editing_field = None
                    input_text = ""

                elif event.key == pygame.K_ESCAPE:
                    # Отмена редактирования
                    editing_task = None
                    editing_subtask = None
                    editing_field = None
                    input_text = ""

                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]

                elif event.key == pygame.K_TAB:
                    # Переключение между полями редактирования
                    if editing_field == "title":
                        editing_field = "completed"
                        if editing_subtask is None:
                            input_text = str(load_tasks()[editing_task]["completed"])
                        else:
                            input_text = str(load_tasks()[editing_task]["subtasks"][editing_subtask]["completed"])
                    elif editing_field == "completed":
                        editing_field = "target"
                        if editing_subtask is None:
                            input_text = str(load_tasks()[editing_task]["target"])
                        else:
                            input_text = str(load_tasks()[editing_task]["subtasks"][editing_subtask]["target"])
                    elif editing_field == "target":
                        editing_field = "title"
                        if editing_subtask is None:
                            input_text = load_tasks()[editing_task]["title"]
                        else:
                            input_text = load_tasks()[editing_task]["subtasks"][editing_subtask]["title"]

                else:
                    # Добавление символа
                    input_text += event.unicode

            # Обработка клавиатуры
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_m:  # Минимизация по клавише M
                    is_minimized = not is_minimized
                elif event.key == pygame.K_1:  # Переключение на главный экран
                    current_screen = "main"
                elif event.key == pygame.K_2:  # Переключение на лаунчер
                    current_screen = "launcher"
                elif event.key == pygame.K_3:  # Переключение на настройки
                    current_screen = "settings"
                elif event.key == pygame.K_4:  # Переключение на задачи
                    current_screen = "tasks"

        # Рисуем интерфейс и получаем кнопки
        buttons = draw(screen)

        # Рисуем диалог редактирования, если он активен
        if editing_task is not None:
            field_title = ""
            if editing_field == "title":
                field_title = "Название"
            elif editing_field == "completed":
                field_title = "Выполнено"
            elif editing_field == "target":
                field_title = "Цель"

            if editing_subtask is None:
                title = f"Редактирование задачи: {field_title}"
            else:
                title = f"Редактирование подзадачи: {field_title}"

            input_rect, ok_rect, cancel_rect = draw_edit_dialog(screen, title, input_text)

        # Обновляем экран
        pygame.display.flip()
        clock.tick(60)  # 60 FPS для отзывчивости

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
