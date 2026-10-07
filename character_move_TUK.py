"""Pico2D로 실행하는 TUK 캐릭터 이동 프로그램."""

from pathlib import Path

import pico2d as p2d

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 1024
RESOURCE_DIR = Path(__file__).resolve().parent


def handle_events():
    for event in p2d.get_events():
        if event.type == p2d.SDL_QUIT:
            return False
        if event.type == p2d.SDL_KEYDOWN and event.key == p2d.SDLK_ESCAPE:
            return False
    return True


def main():
    p2d.open_canvas(WINDOW_WIDTH, WINDOW_HEIGHT)
    background = None
    try:
        p2d.hide_lattice()
        background = p2d.load_image(str(RESOURCE_DIR / "TUK_GROUND.png"))
        while handle_events():
            p2d.clear_canvas()
            background.draw(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
            p2d.update_canvas()
            p2d.delay(0.01)
    finally:
        background = None
        p2d.close_canvas()


if __name__ == "__main__":
    main()
