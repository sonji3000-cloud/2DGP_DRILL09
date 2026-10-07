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
IDLE_LEFT_ROW = 200
MOVE_RIGHT_ROW = 100
MOVE_LEFT_ROW = 0
ANIMATION_FPS = 10.0
MOVE_SPEED = 200.0
MOVEMENT_KEYS = {p2d.SDLK_LEFT, p2d.SDLK_RIGHT, p2d.SDLK_UP, p2d.SDLK_DOWN}


@dataclass
class Character:
    x: float = WINDOW_WIDTH / 2
    y: float = WINDOW_HEIGHT / 2
    facing: str = "RIGHT"
    state: str = "IDLE"
    frame: int = 0
    animation_time: float = 0.0


def update_character(character, pressed_keys, dt):
    previous_animation = (character.state, character.facing)
    dx = int(p2d.SDLK_RIGHT in pressed_keys) - int(p2d.SDLK_LEFT in pressed_keys)
    dy = int(p2d.SDLK_UP in pressed_keys) - int(p2d.SDLK_DOWN in pressed_keys)
    length = hypot(dx, dy)
    if dx:
        character.facing = "RIGHT" if dx > 0 else "LEFT"
    if length:
        character.x += dx / length * MOVE_SPEED * dt
        character.y += dy / length * MOVE_SPEED * dt
    character.state = "MOVE" if length else "IDLE"
    update_animation(character, previous_animation, dt)


def update_animation(character, previous_animation, dt):
    if previous_animation != (character.state, character.facing):
        character.frame = 0
        character.animation_time = 0.0
        return
    character.animation_time += dt
    steps = int((character.animation_time + 1e-9) * ANIMATION_FPS)
    character.animation_time = max(0.0, character.animation_time - steps / ANIMATION_FPS)
    character.frame = (character.frame + steps) % FRAME_COUNT


def draw_character(sheet, character):
    if character.state == "MOVE":
        row = MOVE_RIGHT_ROW if character.facing == "RIGHT" else MOVE_LEFT_ROW
    else:
        row = IDLE_RIGHT_ROW if character.facing == "RIGHT" else IDLE_LEFT_ROW
    sheet.clip_draw(
        character.frame * FRAME_WIDTH, row, FRAME_WIDTH, FRAME_HEIGHT,
        character.x, character.y,
    )


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
            draw_character(sheet, character)
            p2d.update_canvas()
            p2d.delay(0.01)
    finally:
        background = None
        sheet = None
        p2d.close_canvas()


if __name__ == "__main__":
    main()
