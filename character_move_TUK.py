"""Pico2D로 실행하는 TUK 캐릭터 이동 프로그램."""

from dataclasses import dataclass
from math import hypot
from pathlib import Path
from time import perf_counter

import pico2d as p2d

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 1024
RESOURCE_DIR = Path(__file__).resolve().parent
FRAME_WIDTH = 100
FRAME_HEIGHT = 100
FRAME_COUNT = 8
IDLE_RIGHT_ROW = 300
MOVE_SPEED = 200.0
MOVEMENT_KEYS = {p2d.SDLK_LEFT, p2d.SDLK_RIGHT, p2d.SDLK_UP, p2d.SDLK_DOWN}


@dataclass
class Character:
    x: float = WINDOW_WIDTH / 2
    y: float = WINDOW_HEIGHT / 2


def update_character(character, pressed_keys, dt):
    dx = int(p2d.SDLK_RIGHT in pressed_keys) - int(p2d.SDLK_LEFT in pressed_keys)
    dy = int(p2d.SDLK_UP in pressed_keys) - int(p2d.SDLK_DOWN in pressed_keys)
    length = hypot(dx, dy)
    if length:
        character.x += dx / length * MOVE_SPEED * dt
        character.y += dy / length * MOVE_SPEED * dt


def draw_character(sheet, x, y):
    sheet.clip_draw(0, IDLE_RIGHT_ROW, FRAME_WIDTH, FRAME_HEIGHT, x, y)


def handle_events(pressed_keys):
    for event in p2d.get_events():
        if event.type == p2d.SDL_QUIT:
            return False
        if event.type == p2d.SDL_KEYDOWN and event.key == p2d.SDLK_ESCAPE:
            return False
        if event.type == p2d.SDL_KEYDOWN and event.key in MOVEMENT_KEYS:
            pressed_keys.add(event.key)
        elif event.type == p2d.SDL_KEYUP:
            pressed_keys.discard(event.key)
    return True


def main():
    p2d.open_canvas(WINDOW_WIDTH, WINDOW_HEIGHT)
    background = None
    sheet = None
    try:
        p2d.hide_lattice()
        background = p2d.load_image(str(RESOURCE_DIR / "TUK_GROUND.png"))
        sheet = p2d.load_image(str(RESOURCE_DIR / "animation_sheet.png"))
        character = Character()
        pressed_keys = set()
        previous_time = perf_counter()
        while handle_events(pressed_keys):
            current_time = perf_counter()
            dt = current_time - previous_time
            previous_time = current_time
            update_character(character, pressed_keys, dt)
            p2d.clear_canvas()
            background.draw(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
            draw_character(sheet, character.x, character.y)
            p2d.update_canvas()
            p2d.delay(0.01)
    finally:
        background = None
        sheet = None
        p2d.close_canvas()


if __name__ == "__main__":
    main()
