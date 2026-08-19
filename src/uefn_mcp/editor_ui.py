"""Drive the UEFN window itself, for the things the Python API cannot reach.

Everything else in this package talks to the editor through Epic's remote
execution channel. This module does not: it presses keys on the editor's
window the way a person would, using only `ctypes` and Win32.

It exists for exactly one job. Compiling Verse has no scriptable trigger --
`unreal` exposes no build subsystem, Epic's Lore CLI has no build verb and
refuses to run while the project is open, and the Verse VS Code extension's
debug protocol is undocumented. But Verse is the only route to device-to-device
event wiring, so "one human click" was the ceiling on how far a session could
get on its own. Sending the editor its own keyboard shortcut is not a private
protocol being reverse-engineered; it is the documented, public gesture.

The window is matched by its **executable path**, never by title alone: the
consequence of matching the wrong window is a keystroke sent somewhere it was
not meant to go.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

UEFN_EXE = "UnrealEditorFortnite-Win64-Shipping.exe"

# Verse > Build Verse Code
BUILD_VERSE_CHORD = (0x11, 0x10, 0x42)  # VK_CONTROL, VK_SHIFT, 'B'

_KEYEVENTF_KEYUP = 0x0002
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_SW_RESTORE = 9


class EditorWindowError(RuntimeError):
    """The UEFN window could not be found or could not be brought forward."""


def _process_image(pid: int) -> str:
    k32 = ctypes.windll.kernel32
    handle = k32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(32768)
        if not k32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return ""
        return buf.value
    finally:
        k32.CloseHandle(handle)


def find_editor_window() -> tuple[int, str]:
    """Return `(hwnd, window_title)` of the running UEFN editor."""
    if sys.platform != "win32":
        raise EditorWindowError(
            "Driving the editor window is implemented for Windows only; "
            f"this is {sys.platform}."
        )
    user32 = ctypes.windll.user32
    found: list[tuple[int, str]] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _visit(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if not length:
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if _process_image(pid.value).endswith(UEFN_EXE):
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            found.append((int(hwnd), buf.value))
        return True

    user32.EnumWindows(_visit, 0)
    if not found:
        raise EditorWindowError(
            "No visible UEFN window found. The editor must be open, with a "
            "project loaded, and not minimised to the tray."
        )
    # The main frame is the one carrying a title; tool windows come and go.
    return found[0]


def send_chord(hwnd: int, keys: tuple[int, ...]) -> None:
    """Focus `hwnd` and press `keys` together, in order, releasing in reverse."""
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, _SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    if user32.GetForegroundWindow() != hwnd:
        # Windows refuses foreground changes from a process that does not
        # already own it. Attaching to the target's input queue is the
        # documented way to be allowed.
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)
        this_thread = ctypes.windll.kernel32.GetCurrentThreadId()
        user32.AttachThreadInput(this_thread, target_thread, True)
        try:
            user32.SetForegroundWindow(hwnd)
        finally:
            user32.AttachThreadInput(this_thread, target_thread, False)
    if user32.GetForegroundWindow() != hwnd:
        raise EditorWindowError(
            "Could not bring the UEFN window to the foreground, so the "
            "keystroke would have gone to whatever is focused instead. This "
            "usually means another window is holding focus (a UAC prompt, a "
            "full-screen app). Nothing was sent."
        )
    for key in keys:
        user32.keybd_event(key, 0, 0, 0)
    for key in reversed(keys):
        user32.keybd_event(key, 0, _KEYEVENTF_KEYUP, 0)


def build_verse_code() -> str:
    """Press Verse > Build Verse Code in the editor. Returns the window title.

    Says nothing about whether the build succeeded -- the keystroke is fire
    and forget. The caller must confirm by looking for a class that should
    exist afterwards.
    """
    hwnd, title = find_editor_window()
    send_chord(hwnd, BUILD_VERSE_CHORD)
    return title
