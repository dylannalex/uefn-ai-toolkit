#!/usr/bin/env python3
"""Self-check for the parts of bridge.py that don't need a live editor.

Run: python tests/test_bridge.py
"""

import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uefn_mcp import remote_execution as re  # noqa: E402
from uefn_mcp.bridge import (  # noqa: E402
    UEFNBridge,
    UEFNConnectionError,
    _also_reach_the_editor_directly,
    _free_port,
)


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


def test_every_discovery_message_also_goes_out_by_unicast():
    """A live UEFN answered unicast pings and ignored multicast ones entirely.
    The unicast twin has to cover open_connection too, or discovery finds the
    editor and the handshake then times out one message later."""

    class FakeSocket:
        def __init__(self):
            self.sent = []

        def sendto(self, payload, address):
            self.sent.append((payload, address))

    class FakeRemoteExec:
        def __init__(self):
            self._broadcast_connection = self
            self._broadcast_socket = FakeSocket()
            self.multicast = []
            self._node_id = "node"
            self._config = re.RemoteExecutionConfig()

        def _broadcast_message(self, message):
            self.multicast.append(message.type_)

    fake = FakeRemoteExec()
    _also_reach_the_editor_directly(fake, 6766)
    # the real vendored funnel: if Epic ever stops routing these through
    # _broadcast_message, the unicast twin silently stops covering them
    connection = re._RemoteExecutionBroadcastConnection(re.RemoteExecutionConfig(), "node")
    connection._broadcast_message = fake._broadcast_message
    connection._broadcast_socket = fake._broadcast_socket
    connection._last_ping = None
    connection._broadcast_ping()
    connection.broadcast_open_connection("remote")
    connection.broadcast_close_connection("remote")

    assert fake.multicast == ["ping", "open_connection", "close_connection"], fake.multicast
    assert len(fake._broadcast_socket.sent) == 3, fake._broadcast_socket.sent
    for payload, address in fake._broadcast_socket.sent:
        assert address == ("127.0.0.1", 6766), address
        assert b'"magic": "ue_py"' in payload or b'"magic":"ue_py"' in payload, payload


def test_a_silent_editor_fails_fast_and_is_not_retried():
    """A command the editor never answers must raise, not re-run. Re-running a
    create or a transform duplicates work, and the eleven-minute silence this
    replaced is what made a crashed batch unresumable."""

    class SilentEditor:
        calls = 0

        def has_command_connection(self):
            return True

        def run_command(self, *_a, **_kw):
            SilentEditor.calls += 1
            raise TimeoutError("timed out")

        def stop(self):
            pass

    bridge = UEFNBridge(command_timeout=0.1)
    bridge._remote_exec = SilentEditor()
    try:
        bridge.exec_raw("pass")
    except UEFNConnectionError as exc:
        assert "NOT retried" in str(exc), exc
    else:
        raise AssertionError("a silent editor did not raise")
    assert SilentEditor.calls == 1, f"command was re-run {SilentEditor.calls} times"


def test_the_vendored_socket_is_still_reachable_to_bound():
    """connect() reaches into Epic's client to set the receive timeout it never
    sets itself. If Epic renames either attribute, the bound silently stops
    being applied and the silence comes back."""
    config = re.RemoteExecutionConfig()
    assert "_command_connection" in vars(re.RemoteExecution(config))
    conn = re._RemoteExecutionCommandConnection(config, "node", "remote")
    assert hasattr(conn, "_command_channel_socket")


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
