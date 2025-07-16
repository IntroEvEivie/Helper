import pygame
from config import *
from utils import load_config, load_tasks, draw_progress_bar, work_duration, is_during_break
from datetime import datetime

def draw(surface, current_screen, is_minimized, scroll_offset, scroll_content_height, current_second):
    surface.fill(COLOR_BG)

    # Заголовок окна
    pygame.draw.rect(surface, COLOR_PANEL, (0, 0, surface.get_width(), 30))
    font = pygame.font.SysFont(None, 24)
    titles = {
        "main": "Рабочий день",
        "launcher": "Запуск программ",
        "settings": "Настройки",
        "tasks": "Управление задачами"
    }
    title_text = font.render(titles.get(current_screen, ""), True, COLOR_TEXT)
    surface.blit(title_text, (10, 5))

    # Кнопка закрытия
    close_rect = pygame.Rect(surface.get_width() - 40, 5, 30, 20)
    pygame.draw.rect(surface, (200, 0, 0), close_rect)
    close_text = font.render("X", True, (255, 255, 255))
    surface.blit(close_text, (close_rect.x + 10, close_rect.y - 2))

    # Навигационные кнопки
    buttons = []
    screens = ["main", "launcher", "settings", "tasks"]
    labels = ["Д", "П", "Н", "З"]
    positions = [surface.get_width() - 120, surface.get_width() - 80,
                surface.get_width() - 160, surface.get_width() - 200]

    for i, screen in enumerate(screens):
        if current_screen != screen:
            btn_rect = pygame.Rect(positions[i], 5, 30, 20)
            pygame.draw.rect(surface, COLOR_BTN, btn_rect)
            btn_text = font.render(labels[i], True, COLOR_TEXT)
            surface.blit(btn_text, (btn_rect.x + 8, btn_rect.y - 2))
            buttons.append((screen, btn_rect))

    # Отрисовка текущего экрана
    screen_buttons = []
    if current_screen == "main":
        min_btn = draw_main_screen(surface, is_minimized, current_second)
        screen_buttons.append(("min", min_btn))
    elif current_screen == "launcher":
        app_rects = draw_launcher_screen(surface)
        screen_buttons.extend([("app", rect, app) for rect, app in app_rects])
    elif current_screen == "settings":
        app_rects, add_rect = draw_settings_screen(surface)
        screen_buttons.extend([("del_app", rect, idx) for rect, idx in app_rects])
        screen_buttons.append(("add_app", add_rect))
    elif current_screen == "tasks":
        task_buttons = draw_tasks_screen(surface, scroll_offset, scroll_content_height)
        screen_buttons.extend(task_buttons)

    return {
        "close": close_rect,
        "nav_buttons": buttons,
        "screen_buttons": screen_buttons
    }

def draw_main_screen(surface, is_minimized, current_second):
    if is_minimized:
        restore_btn = pygame.Rect(0, 0, ICON_SIZE, ICON_SIZE)
        pygame.draw.rect(surface, COLOR_BTN_DARK, restore_btn)
        restore_text = pygame.font.SysFont(None, 24).render("_", True, COLOR_TEXT)
        surface.blit(restore_text, (restore_btn.x + 5, restore_btn.y + 2))
        return restore_btn

    size = PIXEL_SIZE
    off = (surface.get_width() - size) // 2

    for y in range(size):
        for x in range(size):
            pos = y * size + x
            if pos >= work_duration:
                continue

            if pos < current_second:
                c = COLOR_WORKED
            else:
                c = COLOR_REMAINING
            if is_during_break(pos):
                c = COLOR_BREAK
            if pos == current_second:
                c = COLOR_CURRENT

            surface.set_at((off + x, off + y), c)

    font = pygame.font.SysFont(None, 24)
    ts = datetime.now().strftime("%H:%M:%S")
    txt = font.render(ts, True, COLOR_TEXT)
    surface.blit(txt, ((WINDOW_SIZE - txt.get_width()) // 2, 40))

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

    min_btn = pygame.Rect(WINDOW_SIZE - 80, 40, 30, 30)
    pygame.draw.rect(surface, COLOR_BTN, min_btn)
    min_text = font.render("_", True, COLOR_TEXT)
    surface.blit(min_text, (min_btn.x + 10, min_btn.y + 5))

    return min_btn

def draw_launcher_screen(surface):
    config = load_config()
    apps = config["apps"]
    cols = 3
    start_y = 50
    app_rects = []

    for i, app in enumerate(apps):
        row = i // cols
        col = i % cols
        x = 30 + col * (APP_ICON_SIZE + 40)
        y = start_y + row * (APP_ICON_SIZE + 40)

        icon_rect = pygame.Rect(x, y, APP_ICON_SIZE, APP_ICON_SIZE)
        pygame.draw.rect(surface, COLOR_BTN, icon_rect, border_radius=10)

        if app.get("icon_surface"):
            surface.blit(app["icon_surface"], (x, y))
        else:
            font = pygame.font.SysFont(None, 20)
            app_text = font.render("APP", True, COLOR_TEXT)
            surface.blit(app_text, (x + APP_ICON_SIZE//2 - app_text.get_width()//2,
                                y + APP_ICON_SIZE//2 - app_text.get_height()//2))

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
    app_rects = []

    title = font.render("Настройки приложений:", True, COLOR_TEXT)
    surface.blit(title, (10, y_offset))
    y_offset += 30

    for i, app in enumerate(apps):
        name_text = font.render(f"{i+1}. {app['name']}", True, COLOR_TEXT)
        surface.blit(name_text, (20, y_offset))

        del_rect = pygame.Rect(WINDOW_SIZE - 50, y_offset, 30, 20)
        pygame.draw.rect(surface, (200, 50, 50), del_rect, border_radius=5)
        del_text = font.render("X", True, (255, 255, 255))
        surface.blit(del_text, (del_rect.x + 10, del_rect.y))

        path_text = font.render(app["path"], True, (150, 150, 150))
        surface.blit(path_text, (20, y_offset + 25))

        app_rects.append((del_rect, i))
        y_offset += 60

    pygame.draw.line(surface, COLOR_GRID, (10, y_offset), (WINDOW_SIZE - 10, y_offset), 1)
    y_offset += 20

    add_rect = pygame.Rect(WINDOW_SIZE - 150, y_offset, 140, 30)
    pygame.draw.rect(surface, COLOR_BTN, add_rect, border_radius=5)
    add_text = font.render("+ Добавить приложение", True, COLOR_TEXT)
    surface.blit(add_text, (add_rect.x + 10, add_rect.y + 5))

    return app_rects, add_rect

def draw_tasks_screen(surface, scroll_offset, scroll_content_height):
    tasks = load_tasks()
    font = pygame.font.SysFont(None, 22)
    small_font = pygame.font.SysFont(None, 18)
    y = 40
    buttons = []

    pygame.draw.rect(surface, COLOR_PANEL, (0, y, WINDOW_SIZE, 30))
    title_task = font.render("Задача", True, COLOR_TEXT)
    title_progress = font.render("Прогресс", True, COLOR_TEXT)
    surface.blit(title_task, (10, y + 5))
    surface.blit(title_progress, (WINDOW_SIZE - 220, y + 5))
    y += 35

    visible_y = y - scroll_offset
    for task_idx, task in enumerate(tasks):
        if visible_y < -TASK_ITEM_HEIGHT or visible_y > WINDOW_SIZE:
            visible_y += TASK_ITEM_HEIGHT
            if task["expanded"]:
                visible_y += len(task["subtasks"]) * SUBTASK_ITEM_HEIGHT
            continue

        task_rect = pygame.Rect(5, visible_y, WINDOW_SIZE - 10, TASK_ITEM_HEIGHT - 5)
        pygame.draw.rect(surface, COLOR_BTN, task_rect, border_radius=5)
        pygame.draw.rect(surface, COLOR_GRID, task_rect, 1, border_radius=5)

        expand_rect = pygame.Rect(10, visible_y + 10, 20, 20)
        pygame.draw.rect(surface, COLOR_PROGRESS_BG, expand_rect, border_radius=3)
        expand_text = font.render("▼" if task["expanded"] else "▶", True, COLOR_TEXT)
        surface.blit(expand_text, (expand_rect.x + 5, expand_rect.y))
        buttons.append(("expand", expand_rect, task_idx))

        task_title = small_font.render(task["title"], True, COLOR_TEXT)
        surface.blit(task_title, (40, visible_y + 10))

        progress_x = WINDOW_SIZE - PROGRESS_BAR_WIDTH - 10
        progress_y = visible_y + (TASK_ITEM_HEIGHT - PROGRESS_BAR_HEIGHT) // 2
        draw_progress_bar(surface, progress_x, progress_y, PROGRESS_BAR_WIDTH,
                         PROGRESS_BAR_HEIGHT, task["completed"], task["target"])

        edit_rect = pygame.Rect(WINDOW_SIZE - 40, visible_y + 10, 25, 25)
        pygame.draw.rect(surface, COLOR_PROGRESS_BG, edit_rect, border_radius=3)
        edit_text = small_font.render("✎", True, COLOR_TEXT)
        surface.blit(edit_text, (edit_rect.x + 5, edit_rect.y))
        buttons.append(("edit_task", edit_rect, task_idx))

        visible_y += TASK_ITEM_HEIGHT

        if task["expanded"]:
            for subtask_idx, subtask in enumerate(task["subtasks"]):
                if visible_y < -SUBTASK_ITEM_HEIGHT or visible_y > WINDOW_SIZE:
                    visible_y += SUBTASK_ITEM_HEIGHT
                    continue

                subtask_rect = pygame.Rect(20, visible_y, WINDOW_SIZE - 25, SUBTASK_ITEM_HEIGHT - 5)
                pygame.draw.rect(surface, COLOR_PROGRESS_BG, subtask_rect, border_radius=3)
                pygame.draw.rect(surface, COLOR_GRID, subtask_rect, 1, border_radius=3)

                subtask_title = small_font.render(subtask["title"], True, COLOR_TEXT)
                surface.blit(subtask_title, (30, visible_y + 10))

                progress_x = WINDOW_SIZE - PROGRESS_BAR_WIDTH - 10
                progress_y = visible_y + (SUBTASK_ITEM_HEIGHT - PROGRESS_BAR_HEIGHT) // 2
                draw_progress_bar(surface, progress_x, progress_y, PROGRESS_BAR_WIDTH,
                                 PROGRESS_BAR_HEIGHT // 2, subtask["completed"], subtask["target"])

                edit_rect = pygame.Rect(WINDOW_SIZE - 40, visible_y + 5, 25, 20)
                pygame.draw.rect(surface, COLOR_BTN, edit_rect, border_radius=3)
                edit_text = small_font.render("✎", True, COLOR_TEXT)
                surface.blit(edit_text, (edit_rect.x + 5, edit_rect.y))
                buttons.append(("edit_subtask", edit_rect, task_idx, subtask_idx))

                visible_y += SUBTASK_ITEM_HEIGHT

    add_rect = pygame.Rect(WINDOW_SIZE - 150, WINDOW_SIZE - 40, 140, 30)
    pygame.draw.rect(surface, COLOR_BTN, add_rect, border_radius=5)
    add_text = font.render("+ Новая задача", True, COLOR_TEXT)
    surface.blit(add_text, (add_rect.x + 10, add_rect.y + 5))
    buttons.append(("add_task", add_rect))

    return buttons

def draw_edit_dialog(surface, title, value):
    s = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 180))
    surface.blit(s, (0, 0))

    dialog_rect = pygame.Rect(50, 100, WINDOW_SIZE - 100, 200)
    pygame.draw.rect(surface, COLOR_BG, dialog_rect, border_radius=10)
    pygame.draw.rect(surface, COLOR_GRID, dialog_rect, 2, border_radius=10)

    font = pygame.font.SysFont(None, 24)
    title_text = font.render(title, True, COLOR_TEXT)
    surface.blit(title_text, (dialog_rect.x + 20, dialog_rect.y + 20))

    input_rect = pygame.Rect(dialog_rect.x + 20, dialog_rect.y + 60, dialog_rect.width - 40, 40)
    pygame.draw.rect(surface, COLOR_BTN, input_rect, border_radius=5)
    pygame.draw.rect(surface, COLOR_GRID, input_rect, 1, border_radius=5)

    input_font = pygame.font.SysFont(None, 22)
    text_surf = input_font.render(value, True, COLOR_TEXT)
    surface.blit(text_surf, (input_rect.x + 10, input_rect.y + 10))

    ok_rect = pygame.Rect(dialog_rect.x + 50, dialog_rect.y + 140, 100, 40)
    pygame.draw.rect(surface, COLOR_PROGRESS_FG, ok_rect, border_radius=5)
    ok_text = font.render("OK", True, COLOR_TEXT)
    surface.blit(ok_text, (ok_rect.x + 35, ok_rect.y + 10))

    cancel_rect = pygame.Rect(dialog_rect.x + 170, dialog_rect.y + 140, 100, 40)
    pygame.draw.rect(surface, COLOR_BTN, cancel_rect, border_radius=5)
    cancel_text = font.render("Отмена", True, COLOR_TEXT)
    surface.blit(cancel_text, (cancel_rect.x + 20, cancel_rect.y + 10))

    return input_rect, ok_rect, cancel_rect
