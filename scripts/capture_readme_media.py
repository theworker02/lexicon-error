#!/usr/bin/env python3
"""Capture real LexiconError desktop screenshots and README demo media on Windows."""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
import subprocess
import time
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageGrab


USER32 = ctypes.windll.user32
VK_CONTROL = 0x11
VK_RETURN = 0x0D
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
SW_RESTORE = 9
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002


def find_window(process_id: int, timeout: float = 20.0) -> int:
    result: list[int] = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    @callback_type
    def callback(window: int, _: int) -> bool:
        candidate_pid = ctypes.c_ulong()
        USER32.GetWindowThreadProcessId(window, ctypes.byref(candidate_pid))
        if candidate_pid.value == process_id and USER32.IsWindowVisible(window):
            result.append(window)
            return False
        return True

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result.clear()
        USER32.EnumWindows(callback, 0)
        if result:
            return result[0]
        time.sleep(0.2)
    raise RuntimeError("LexiconError did not create a visible window")


def focus_window(window: int) -> None:
    USER32.ShowWindow(window, SW_RESTORE)
    # Keep unrelated desktop windows from contaminating the product capture.
    USER32.SetWindowPos(window, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    USER32.SetWindowPos(window, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    USER32.BringWindowToTop(window)
    USER32.SetForegroundWindow(window)
    time.sleep(0.25)


def window_bounds(window: int) -> tuple[int, int, int, int]:
    rect = ctypes.wintypes.RECT()
    if not USER32.GetWindowRect(window, ctypes.byref(rect)):
        raise ctypes.WinError()
    return rect.left, rect.top, rect.right, rect.bottom


def key_event(key: int, up: bool = False) -> None:
    USER32.keybd_event(key, 0, KEYEVENTF_KEYUP if up else 0, 0)


def press_key(key: int) -> None:
    key_event(key)
    key_event(key, up=True)


def press_ctrl_k() -> None:
    key_event(VK_CONTROL)
    press_key(ord("K"))
    key_event(VK_CONTROL, up=True)


def click_relative(window: int, x: int, y: int) -> None:
    left, top, _, _ = window_bounds(window)
    previous = ctypes.wintypes.POINT()
    USER32.GetCursorPos(ctypes.byref(previous))
    USER32.SetCursorPos(left + x, top + y)
    USER32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    USER32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.25)
    USER32.SetCursorPos(previous.x, previous.y)


def type_text(value: str) -> None:
    for character in value:
        encoded = USER32.VkKeyScanW(ord(character))
        if encoded == -1:
            raise ValueError(f"cannot synthesize character: {character!r}")
        virtual_key = encoded & 0xFF
        modifiers = (encoded >> 8) & 0xFF
        if modifiers & 1:
            key_event(0x10)
        press_key(virtual_key)
        if modifiers & 1:
            key_event(0x10, up=True)
        time.sleep(0.12)


def capture(window: int) -> Image.Image:
    focus_window(window)
    USER32.SetCursorPos(4, 4)
    time.sleep(0.15)
    return ImageGrab.grab(bbox=window_bounds(window), all_screens=True).convert("RGB")


def save_animation(frames: list[Image.Image], output: Path) -> None:
    target_size = (1120, 700)
    resized = [frame.resize(target_size, Image.Resampling.LANCZOS) for frame in frames]
    gif_frames = [frame.quantize(colors=128, method=Image.Quantize.MEDIANCUT) for frame in resized]
    gif_frames[0].save(
        output / "lexiconerror-search-demo.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=[900, 500, *([240] * (len(frames) - 4)), 700, 1500],
        loop=0,
        optimize=True,
        disposal=2,
    )

    video_frames: list[Image.Image] = []
    holds = [8, 5, *([2] * (len(frames) - 4)), 6, 14]
    for frame, hold in zip(resized, holds):
        video_frames.extend([frame] * hold)
    writer = imageio.get_writer(
        output / "lexiconerror-search-demo.mp4",
        fps=10,
        codec="libx264",
        quality=8,
        macro_block_size=None,
        ffmpeg_log_level="error",
    )
    try:
        for frame in video_frames:
            writer.append_data(np.asarray(frame))
    finally:
        writer.close()


def capture_media(executable: Path, output: Path) -> None:
    if not executable.is_file():
        raise FileNotFoundError(executable)
    output.mkdir(parents=True, exist_ok=True)
    USER32.SetProcessDPIAware()
    process = subprocess.Popen([str(executable)])
    try:
        window = find_window(process.pid)
        USER32.MoveWindow(window, 70, 55, 1440, 900, True)
        focus_window(window)
        time.sleep(5)

        # A real palette open/close cycle establishes reliable foreground ownership on Windows.
        click_relative(window, 555, 64)
        time.sleep(0.35)
        press_key(0x1B)
        time.sleep(0.35)
        window = find_window(process.pid)
        catalog = capture(window)
        catalog.save(output / "lexiconerror-catalog.png", optimize=True)
        frames = [catalog, catalog]

        # A physical click is more reliable than global shortcuts in automated Windows sessions.
        click_relative(window, 555, 64)
        time.sleep(0.5)
        palette = capture(window)
        frames.append(palette)

        for character in "E0382":
            type_text(character)
            frames.append(capture(window))
        search = frames[-1]
        search.save(output / "lexiconerror-command-palette.png", optimize=True)

        press_key(VK_RETURN)
        time.sleep(1)
        # WebView navigation can recreate the native window on some Windows builds.
        window = find_window(process.pid)
        detail = capture(window)
        detail.save(output / "lexiconerror-diagnostic-detail.png", optimize=True)
        frames.extend([detail, detail])
        save_animation(frames, output)

        # Exercise and capture each functional inspector workspace.
        for name, x in [("remediation", 850), ("context", 950), ("failure-state", 1060)]:
            window = find_window(process.pid)
            click_relative(window, x, 286)
            time.sleep(0.45)
            capture(window).save(output / f"lexiconerror-{name}.png", optimize=True)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--executable",
        type=Path,
        default=Path("src-tauri/target/release/lexicon-error.exe"),
    )
    parser.add_argument("--output", type=Path, default=Path("docs/media"))
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    capture_media(arguments.executable.resolve(), arguments.output.resolve())
