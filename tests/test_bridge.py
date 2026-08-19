#!/usr/bin/env python3
"""Self-check for the parts of bridge.py that don't need a live editor.

Run: python tests/test_bridge.py
"""

import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uefn_mcp import remote_execution as re  # noqa: E402
from uefn_mcp.bridge import UEFNBridge, _free_port  # noqa: E402


def test_free_port_is_actually_bindable():
    port = _free_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))  # raises if _free_port handed back a used one


def test_free_ports_differ():
    ports = {_free_port() for _ in range(10)}
    assert len(ports) > 1, f"_free_port kept returning the same port: {ports}"


def test_no_bridge_uses_epics_shared_default():
    """The whole point: two processes must not both announce port 6776."""
    assert re.DEFAULT_COMMAND_ENDPOINT[1] == 6776, "Epic's default moved; revisit"
    for _ in range(5):
        assert _free_port() != 6776


def test_bridge_constructs_without_an_editor():
    bridge = UEFNBridge()
    assert bridge._remote_exec is None, "connecting must stay lazy"


def test_editor_window_is_matched_by_executable():
    """The window lookup decides where a keystroke lands. It must never
    settle for a title match -- "Unreal Editor for Fortnite" is also a
    substring of, say, an editor window open on this repository."""
    if sys.platform != "win32":
        print("skip (not Windows)", end=" ")
        return
    from uefn_mcp import editor_ui

    try:
        hwnd, _title = editor_ui.find_editor_window()
    except editor_ui.EditorWindowError:
        print("skip (no editor running)", end=" ")
        return

    import ctypes
    from ctypes import wintypes

    pid = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    image = editor_ui._process_image(pid.value)
    assert image.endswith(editor_ui.UEFN_EXE), f"matched a non-UEFN window: {image}"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
    print("all checks passed")
