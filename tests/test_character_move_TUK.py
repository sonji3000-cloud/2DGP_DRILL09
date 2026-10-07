"""이동 규칙과 실제 SDL 입력·렌더링의 회귀 검증."""

import ctypes
from contextlib import contextmanager
import math
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import pico2d as p2d
import pico2d.pico2d as engine
from sdl2 import SDL_Event, SDL_PushEvent, SDL_WINDOW_HIDDEN, SDL_WINDOW_SHOWN

import character_move_TUK as game


@contextmanager
def hidden_windows():
    create = engine.SDL_CreateWindow

    def hidden(title, x, y, width, height, flags):
        return create(title, x, y, width, height, (flags & ~SDL_WINDOW_SHOWN) | SDL_WINDOW_HIDDEN)

    with patch.object(engine, "SDL_CreateWindow", hidden):
        yield


def push_event(event_type, key=0, repeat=0):
    event = SDL_Event()
    event.type = event_type
    if event_type in (p2d.SDL_KEYDOWN, p2d.SDL_KEYUP):
        event.key.keysym.sym = key
        event.key.repeat = repeat
    if SDL_PushEvent(ctypes.byref(event)) != 1:
        raise RuntimeError(engine.SDL_GetError())


def rendered_pixels():
    pixels = (ctypes.c_ubyte * (game.WINDOW_WIDTH * game.WINDOW_HEIGHT * 4))()
    result = engine.SDL_RenderReadPixels(
        engine.renderer, None, engine.SDL_PIXELFORMAT_ABGR8888,
        pixels, game.WINDOW_WIDTH * 4,
    )
    if result != 0:
        raise RuntimeError(engine.SDL_GetError())
    return bytes(pixels)


class MovementTests(unittest.TestCase):
    def test_four_directions_and_stop(self):
        for key, expected in (
            (p2d.SDLK_LEFT, (590, 512)), (p2d.SDLK_RIGHT, (690, 512)),
            (p2d.SDLK_DOWN, (640, 462)), (p2d.SDLK_UP, (640, 562)),
        ):
            with self.subTest(key=key):
                character = game.Character()
                game.update_character(character, {key}, 0.25)
                self.assertEqual((character.x, character.y), expected)
                self.assertEqual(character.state, "MOVE")
                game.update_character(character, set(), 0.25)
                self.assertEqual((character.x, character.y), expected)
                self.assertEqual(character.state, "IDLE")

    def test_diagonal_speed(self):
        for horizontal in (p2d.SDLK_LEFT, p2d.SDLK_RIGHT):
            for vertical in (p2d.SDLK_UP, p2d.SDLK_DOWN):
                character = game.Character()
                game.update_character(character, {horizontal, vertical}, 0.25)
                self.assertAlmostEqual(math.hypot(character.x - 640, character.y - 512), 50)

    def test_opposite_inputs_cancel_each_axis(self):
        character = game.Character()
        game.update_character(character, game.MOVEMENT_KEYS, 0.25)
        self.assertEqual((character.x, character.y, character.state), (640, 512, "IDLE"))
        game.update_character(character, {p2d.SDLK_LEFT, p2d.SDLK_RIGHT, p2d.SDLK_UP}, 0.25)
        self.assertEqual((character.x, character.y), (640, 562))

    def test_facing_survives_vertical_movement_and_stop(self):
        for key, facing in ((p2d.SDLK_LEFT, "LEFT"), (p2d.SDLK_RIGHT, "RIGHT")):
            character = game.Character()
            game.update_character(character, {key}, 0.01)
            for keys in ({p2d.SDLK_UP}, {p2d.SDLK_DOWN}, set(), {p2d.SDLK_LEFT, p2d.SDLK_RIGHT}):
                game.update_character(character, keys, 0.01)
                self.assertEqual(character.facing, facing)

    def test_movement_is_independent_of_time_partition(self):
        whole, split = game.Character(), game.Character()
        game.update_character(whole, {p2d.SDLK_RIGHT}, 1.0)
        for _ in range(100):
            game.update_character(split, {p2d.SDLK_RIGHT}, 0.01)
        self.assertAlmostEqual(whole.x, split.x)

    def test_idle_and_move_frames_loop(self):
        for state in ("IDLE", "MOVE"):
            for facing in ("LEFT", "RIGHT"):
                character = game.Character(state=state, facing=facing)
                game.update_animation(character, (state, facing), 0.3)
                self.assertEqual(character.frame, 3)
                game.update_animation(character, (state, facing), 0.5)
                self.assertEqual(character.frame, 0)
                self.assertAlmostEqual(character.animation_time, 0)

    def test_animation_transition_resets_frame_and_time(self):
        character = game.Character(frame=5, animation_time=0.07)
        game.update_character(character, {p2d.SDLK_RIGHT}, 0.01)
        self.assertEqual((character.state, character.frame, character.animation_time), ("MOVE", 0, 0))
        game.update_character(character, {p2d.SDLK_RIGHT}, 0.2)
        self.assertEqual(character.frame, 2)
        game.update_character(character, {p2d.SDLK_LEFT}, 0.01)
        self.assertEqual((character.facing, character.frame, character.animation_time), ("LEFT", 0, 0))
        game.update_character(character, set(), 0.01)
        self.assertEqual((character.state, character.frame, character.animation_time), ("IDLE", 0, 0))

    def test_edges_and_corners_block_and_allow_reverse(self):
        cases = [({p2d.SDLK_LEFT}, (50, 512)), ({p2d.SDLK_RIGHT}, (1230, 512)),
                 ({p2d.SDLK_DOWN}, (640, 50)), ({p2d.SDLK_UP}, (640, 974))]
        for horizontal, x in ((p2d.SDLK_LEFT, 50), (p2d.SDLK_RIGHT, 1230)):
            for vertical, y in ((p2d.SDLK_DOWN, 50), (p2d.SDLK_UP, 974)):
                cases.append(({horizontal, vertical}, (x, y)))
        opposites = {p2d.SDLK_LEFT: p2d.SDLK_RIGHT, p2d.SDLK_RIGHT: p2d.SDLK_LEFT,
                     p2d.SDLK_UP: p2d.SDLK_DOWN, p2d.SDLK_DOWN: p2d.SDLK_UP}
        for keys, expected in cases:
            with self.subTest(keys=keys):
                character = game.Character()
                game.update_character(character, keys, 100)
                self.assertEqual((character.x, character.y), expected)
                game.update_character(character, keys, 0.01)
                self.assertEqual(character.state, "IDLE")
                game.update_character(character, keys, 0.2)
                self.assertEqual(character.frame, 2)
                game.update_character(character, {opposites[key] for key in keys}, 0.1)
                self.assertNotEqual((character.x, character.y), expected)
                self.assertEqual(character.state, "MOVE")

    def test_slide_along_wall_and_face_blocked_direction(self):
        character = game.Character(x=50)
        game.update_character(character, {p2d.SDLK_LEFT, p2d.SDLK_UP}, 0.1)
        self.assertEqual(character.x, 50)
        self.assertGreater(character.y, 512)
        self.assertEqual((character.facing, character.state), ("LEFT", "MOVE"))

    def test_random_input_sequences_stay_inside_screen(self):
        rng = random.Random(20261007)
        character = game.Character()
        for _ in range(500):
            keys = {key for key in sorted(game.MOVEMENT_KEYS) if rng.choice((True, False))}
            game.update_character(character, keys, rng.uniform(0.001, 4.0))
            self.assertTrue(50 <= character.x <= 1230)
            self.assertTrue(50 <= character.y <= 974)
            self.assertTrue(0 <= character.frame < 8)


class SDLIntegrationTests(unittest.TestCase):
    def test_real_key_events_repeat_cancel_and_release(self):
        with hidden_windows():
            p2d.open_canvas(game.WINDOW_WIDTH, game.WINDOW_HEIGHT)
            try:
                p2d.get_events()
                pressed = set()
                for _ in range(10):
                    push_event(p2d.SDL_KEYDOWN, p2d.SDLK_RIGHT)
                push_event(p2d.SDL_KEYDOWN, p2d.SDLK_RIGHT, repeat=1)
                self.assertTrue(game.handle_events(pressed))
                self.assertEqual(pressed, {p2d.SDLK_RIGHT})
                push_event(p2d.SDL_KEYDOWN, p2d.SDLK_LEFT)
                self.assertTrue(game.handle_events(pressed))
                character = game.Character()
                game.update_character(character, pressed, 0.25)
                self.assertEqual(character.x, 640)
                push_event(p2d.SDL_KEYUP, p2d.SDLK_RIGHT)
                self.assertTrue(game.handle_events(pressed))
                game.update_character(character, pressed, 0.25)
                self.assertEqual(character.x, 590)
                push_event(p2d.SDL_KEYUP, p2d.SDLK_LEFT)
                self.assertTrue(game.handle_events(pressed))
                self.assertFalse(pressed)
            finally:
                p2d.close_canvas()

    def test_real_rendering_of_all_animation_rows(self):
        with hidden_windows():
            p2d.open_canvas(game.WINDOW_WIDTH, game.WINDOW_HEIGHT)
            background = sheet = None
            try:
                p2d.hide_lattice()
                background = p2d.load_image(str(game.RESOURCE_DIR / "TUK_GROUND.png"))
                sheet = p2d.load_image(str(game.RESOURCE_DIR / "animation_sheet.png"))
                p2d.clear_canvas()
                background.draw(640, 512)
                base = rendered_pixels()
                outputs = {}
                for state in ("IDLE", "MOVE"):
                    for facing in ("LEFT", "RIGHT"):
                        for frame in range(8):
                            p2d.clear_canvas()
                            background.draw(640, 512)
                            game.draw_character(sheet, game.Character(state=state, facing=facing, frame=frame))
                            pixels = rendered_pixels()
                            self.assertNotEqual(pixels, base)
                            outputs[state, facing, frame] = pixels
                for state in ("IDLE", "MOVE"):
                    self.assertNotEqual(outputs[state, "LEFT", 0], outputs[state, "RIGHT", 0])
                    for facing in ("LEFT", "RIGHT"):
                        self.assertGreater(len({outputs[state, facing, n] for n in range(8)}), 1)
            finally:
                background = sheet = None
                p2d.close_canvas()

    def test_main_loop_external_directory_and_both_exit_events(self):
        for exit_type, exit_key in ((p2d.SDL_QUIT, 0), (p2d.SDL_KEYDOWN, p2d.SDLK_ESCAPE)):
            original_events = p2d.get_events
            original_draw = game.draw_character
            states = []
            ticks = iter(n / 10 for n in range(20))
            calls = 0

            def events():
                nonlocal calls
                calls += 1
                if calls == 1:
                    push_event(p2d.SDL_KEYDOWN, p2d.SDLK_LEFT)
                elif calls == 3:
                    push_event(p2d.SDL_KEYUP, p2d.SDLK_LEFT)
                    push_event(p2d.SDL_KEYDOWN, p2d.SDLK_UP)
                elif calls == 5:
                    push_event(p2d.SDL_KEYUP, p2d.SDLK_UP)
                elif calls == 7:
                    push_event(exit_type, exit_key)
                self.assertLessEqual(calls, 7)
                return original_events()

            def draw(sheet, character):
                original_draw(sheet, character)
                states.append((character.x, character.y, character.facing, character.state, character.frame))

            previous_directory = Path.cwd()
            with tempfile.TemporaryDirectory() as other_directory, hidden_windows():
                try:
                    os.chdir(other_directory)
                    with patch.object(p2d, "get_events", events), patch.object(game, "draw_character", draw), \
                            patch.object(game, "perf_counter", lambda: next(ticks)):
                        game.main()
                finally:
                    os.chdir(previous_directory)
            self.assertEqual(len(states), 6)
            self.assertEqual(states[0][2:], ("LEFT", "MOVE", 0))
            self.assertLess(states[1][0], states[0][0])
            self.assertGreater(states[3][1], states[2][1])
            self.assertTrue(all(state[2] == "LEFT" for state in states))
            self.assertEqual(states[-2][3:], ("IDLE", 0))
            self.assertEqual(states[-1][3:], ("IDLE", 1))


if __name__ == "__main__":
    unittest.main()
