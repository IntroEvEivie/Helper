import os
import sys
import threading
import json
import subprocess
from datetime import datetime
import pygame
import ctypes
from pygame.locals import *
from config import *
from utils import *
from screens import *

'''
if sys.platform == "win32":
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 0)
'''
# Глобальные состояния
current_second = 0
running = True
is_minimized = False
current_screen = "main"
scroll_offset = 0
scroll_dragging = False
scroll_drag_start = 0
scroll_content_height = 0
editing_task = None
editing_subtask = None
editing_field = None
input_text = ""

def time_updater():
    global current_second, running
    while running:
        current_second = get_current_work_second()
        threading.Event().wait(1)

def main():
    global running, is_minimized, current_screen, scroll_offset
    global scroll_dragging, scroll_drag_start, editing_task, editing_subtask
    global editing_field, input_text, scroll_content_height

    os.environ['SDL_VIDEO_WINDOW_POS'] = f"{pos_full[0]},{pos_full[1]}"
    screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE), pygame.NOFRAME)
    pygame.display.set_caption("Рабочий день + Лаунчер + Задачи")
    clock = pygame.time.Clock()

    threading.Thread(target=time_updater, daemon=True).start()

    buttons = {}
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()

                if "close" in buttons and buttons["close"].collidepoint(pos) and not is_minimized:
                    running = False

                if "nav_buttons" in buttons:
                    for btn_type, btn_rect in buttons["nav_buttons"]:
                        if btn_rect.collidepoint(pos):
                            current_screen = btn_type

                if current_screen == "main":
                    if "screen_buttons" in buttons and buttons["screen_buttons"]:
                        btn_type, btn_rect, *_ = buttons["screen_buttons"][0]
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

                elif current_screen == "launcher" and "screen_buttons" in buttons:
                    for btn in buttons["screen_buttons"]:
                        if btn[0] == "app" and btn[1].collidepoint(pos):
                            try:
                                if sys.platform == "win32":
                                    os.startfile(btn[2]["path"])
                                else:
                                    subprocess.Popen(btn[2]["path"])
                            except Exception as e:
                                print(f"Ошибка запуска: {e}")

                elif current_screen == "settings" and "screen_buttons" in buttons:
                    for btn in buttons["screen_buttons"]:
                        if btn[0] == "del_app" and btn[1].collidepoint(pos):
                            config = load_config()
                            if 0 <= btn[2] < len(config["apps"]):
                                config["apps"].pop(btn[2])
                                save_config(config)
                        elif btn[0] == "add_app" and btn[1].collidepoint(pos):
                            config = load_config()
                            config["apps"].append({
                                "name": f"Приложение {len(config['apps']) + 1}",
                                "path": "",
                                "icon": None
                            })
                            save_config(config)

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

            elif event.type == pygame.MOUSEBUTTONUP:
                scroll_dragging = False

                if editing_task is not None:
                    _, ok_rect, cancel_rect = draw_edit_dialog(screen, "Редактирование", input_text)
                    if ok_rect.collidepoint(pos):
                        tasks = load_tasks()
                        if editing_subtask is None:
                            if editing_field == "title":
                                tasks[editing_task]["title"] = input_text
                            elif editing_field == "completed":
                                try: tasks[editing_task]["completed"] = int(input_text)
                                except: pass
                            elif editing_field == "target":
                                try: tasks[editing_task]["target"] = int(input_text)
                                except: pass
                        else:
                            if editing_field == "title":
                                tasks[editing_task]["subtasks"][editing_subtask]["title"] = input_text
                            elif editing_field == "completed":
                                try: tasks[editing_task]["subtasks"][editing_subtask]["completed"] = int(input_text)
                                except: pass
                            elif editing_field == "target":
                                try: tasks[editing_task]["subtasks"][editing_subtask]["target"] = int(input_text)
                                except: pass

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

            elif event.type == pygame.MOUSEWHEEL:
                if current_screen == "tasks":
                    scroll_offset -= event.y * 30
                    scroll_offset = max(0, min(scroll_offset, scroll_content_height))

            elif event.type == pygame.MOUSEMOTION and scroll_dragging:
                delta = event.pos[1] - scroll_drag_start
                scroll_drag_start = event.pos[1]
                scroll_offset += delta * (scroll_content_height / (WINDOW_SIZE - 40))
                scroll_offset = max(0, min(scroll_offset, scroll_content_height))

            elif event.type == pygame.KEYDOWN and editing_task is not None:
                if event.key == pygame.K_RETURN:
                    tasks = load_tasks()
                    if editing_subtask is None:
                        if editing_field == "title": tasks[editing_task]["title"] = input_text
                        elif editing_field == "completed":
                            try: tasks[editing_task]["completed"] = int(input_text)
                            except: pass
                        elif editing_field == "target":
                            try: tasks[editing_task]["target"] = int(input_text)
                            except: pass
                    else:
                        if editing_field == "title": tasks[editing_task]["subtasks"][editing_subtask]["title"] = input_text
                        elif editing_field == "completed":
                            try: tasks[editing_task]["subtasks"][editing_subtask]["completed"] = int(input_text)
                            except: pass
                        elif editing_field == "target":
                            try: tasks[editing_task]["subtasks"][editing_subtask]["target"] = int(input_text)
                            except: pass

                    tasks[editing_task] = calculate_task_progress(tasks[editing_task])
                    save_tasks(tasks)
                    editing_task = None
                    editing_subtask = None
                    editing_field = None
                    input_text = ""

                elif event.key == pygame.K_ESCAPE:
                    editing_task = None
                    editing_subtask = None
                    editing_field = None
                    input_text = ""

                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]

                elif event.key == pygame.K_TAB:
                    fields = ["title", "completed", "target"]
                    current_index = fields.index(editing_field)
                    editing_field = fields[(current_index + 1) % len(fields)]

                    if editing_subtask is None:
                        if editing_field == "title": input_text = tasks[editing_task]["title"]
                        elif editing_field == "completed": input_text = str(tasks[editing_task]["completed"])
                        elif editing_field == "target": input_text = str(tasks[editing_task]["target"])
                    else:
                        if editing_field == "title": input_text = tasks[editing_task]["subtasks"][editing_subtask]["title"]
                        elif editing_field == "completed": input_text = str(tasks[editing_task]["subtasks"][editing_subtask]["completed"])
                        elif editing_field == "target": input_text = str(tasks[editing_task]["subtasks"][editing_subtask]["target"])

                else:
                    input_text += event.unicode

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_m:
                    is_minimized = not is_minimized
                elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
                    screens = ["main", "launcher", "settings", "tasks"]
                    current_screen = screens[event.key - pygame.K_1]

        buttons = draw(screen, current_screen, is_minimized, scroll_offset, scroll_content_height, current_second)

        if editing_task is not None:
            field_title = {
                "title": "Название",
                "completed": "Выполнено",
                "target": "Цель"
            }.get(editing_field, "")

            title = f"Редактирование {'задачи' if editing_subtask is None else 'подзадачи'}: {field_title}"
            draw_edit_dialog(screen, title, input_text)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
