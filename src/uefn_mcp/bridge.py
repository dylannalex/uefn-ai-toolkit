"""Bridge to a running UEFN / Unreal Editor instance via the Python Editor Script
Plugin's remote execution protocol (UDP discovery + TCP command channel).

This talks to whatever editor is listening on the default multicast group
(239.0.0.1:6766) with "Remote Execution" enabled in the Python plugin settings,
which is the default. The editor must be running with the target project open
and Python enabled for that project.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from typing import Any

from . import remote_execution as re

RESULT_START = "@@UEFN_MCP_RESULT_START@@"
RESULT_END = "@@UEFN_MCP_RESULT_END@@"

# How long to wait for the editor to answer one command. Epic's client sets no
# receive timeout at all, so when the editor dies mid-call (a GPU crash leaves
# the process alive writing a dump, holding the socket open) recv() blocks for
# as long as that process lingers - measured at eleven minutes, in silence,
# during a 36-actor build. Longest legitimate call measured is 4.5 s, except a
# Verse compile, during which the editor stops answering entirely; raise this
# if a compile on this machine outlasts it.
COMMAND_TIMEOUT = float(os.environ.get("UEFN_MCP_COMMAND_TIMEOUT", "120"))


class UEFNConnectionError(RuntimeError):
    pass


class UEFNScriptError(RuntimeError):
    pass


def _free_port() -> int:
    """Reserve a currently-free localhost TCP port for this process's use.

    Epic's client defaults every process to the same command port (6776) and
    sets SO_REUSEADDR, which on Windows lets a second process take over a port
    the first is already listening on. Two Claude Code sessions therefore both
    announce 6776 to the editor, the editor's callback lands on whichever
    process the OS picks, and the loser reconnects and steals it back - the
    connection ping-pongs until both die. Giving each process its own port
    removes the contention instead of arbitrating it.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class UEFNBridge:
    """Thread-safe wrapper around a single remote execution command connection."""

    def __init__(
        self,
        discovery_timeout: float = 5.0,
        command_timeout: float = COMMAND_TIMEOUT,
    ) -> None:
        self._lock = threading.RLock()
        self._remote_exec: re.RemoteExecution | None = None
        self._discovery_timeout = discovery_timeout
        self._command_timeout = command_timeout

    def connect(self) -> dict:
        """(Re)establish a command connection to the first discovered editor node."""
        with self._lock:
            self._teardown()
            config = re.RemoteExecutionConfig()
            config.command_endpoint = ("127.0.0.1", _free_port())
            self._remote_exec = re.RemoteExecution(config)
            self._remote_exec.start()
            deadline = time.time() + self._discovery_timeout
            node = None
            while time.time() < deadline:
                nodes = self._remote_exec.remote_nodes
                if nodes:
                    node = nodes[0]
                    break
                time.sleep(0.2)
            if not node:
                self._teardown()
                raise UEFNConnectionError(
                    "No running Unreal/UEFN editor was discovered on the local "
                    "network. Make sure the editor is open with a project loaded "
                    "and that Python is enabled for that project "
                    "(Edit > Project Settings > Python)."
                )
            try:
                self._remote_exec.open_command_connection(node["node_id"])
            except RuntimeError as exc:
                self._teardown()
                raise UEFNConnectionError(
                    f"Found the editor ({node.get('project_name') or node['node_id']}) "
                    f"but it never connected back: {exc}\n"
                    "The editor accepted the discovery ping and then failed to open "
                    "the command channel. Usual causes, in order: the editor is busy "
                    "or mid-dialog and cannot service the request; Python remote "
                    "execution was enabled in the .uefnproject or DefaultEngine.ini "
                    "but UEFN has not been restarted since; or a firewall is blocking "
                    "the loopback callback. Do not kill the editor - retrying once it "
                    "is idle is usually enough."
                ) from exc
            # Bound the receive here rather than in remote_execution.py, which
            # stays a drop-in copy of Epic's client.
            conn = getattr(self._remote_exec, "_command_connection", None)
            sock = getattr(conn, "_command_channel_socket", None)
            if sock is not None:
                sock.settimeout(self._command_timeout)
            return node

    def disconnect(self) -> None:
        with self._lock:
            self._teardown()

    def _teardown(self) -> None:
        if self._remote_exec:
            try:
                self._remote_exec.stop()
            except Exception:
                pass
            self._remote_exec = None

    def _ensure_connected(self) -> None:
        if not (self._remote_exec and self._remote_exec.has_command_connection()):
            self.connect()

    def exec_raw(
        self,
        code: str,
        exec_mode: str = re.MODE_EXEC_FILE,
        unattended: bool = True,
    ) -> dict:
        """Run `code` in the editor and return the raw command_result dict."""
        with self._lock:
            self._ensure_connected()
            started = time.monotonic()
            try:
                return self._remote_exec.run_command(
                    code, unattended=unattended, exec_mode=exec_mode
                )
            except TimeoutError as exc:
                # The editor took the command and never answered. Do NOT retry:
                # the command may well have run, and re-running a create or a
                # transform duplicates work. Fail now and let the caller resume
                # from its own log - the batch scripts are idempotent by label.
                self._teardown()
                raise UEFNConnectionError(
                    f"UEFN accepted the command but sent no result within "
                    f"{time.monotonic() - started:.0f}s. It is compiling Verse, "
                    "blocked on a modal dialog, or dead (a GPU crash leaves the "
                    "process alive holding the socket).\n"
                    "The command was NOT retried, because it may already have "
                    "taken effect. Check the editor, then resume from the last "
                    "step your own log recorded as finished."
                ) from exc
            except (OSError, RuntimeError) as first:
                # The connection went stale (e.g. the editor was restarted).
                # has_command_connection() only checks the object exists, never
                # that the socket is alive, so this is where staleness surfaces.
                self.connect()
                try:
                    return self._remote_exec.run_command(
                        code, unattended=unattended, exec_mode=exec_mode
                    )
                except (OSError, RuntimeError) as second:
                    self._teardown()
                    raise UEFNConnectionError(
                        f"Lost the connection to UEFN and could not re-establish it.\n"
                        f"  first attempt:  {first}\n"
                        f"  after reconnect: {second}\n"
                        "The editor is discoverable but not executing commands. Check "
                        "that UEFN is still open with the project loaded and is not "
                        "blocked on a modal dialog. Killing the uefn-mcp process does "
                        "not help - each session gets its own command port, so a "
                        "second session is not the cause."
                    ) from second

    def exec_json(self, code: str, **params: Any) -> Any:
        """Run `code` in the editor and return a JSON-decoded result.

        `code` must assign a JSON-serializable value to a variable named
        `result`. Any `params` are made available inside `code` as a dict
        named `_params` (round-tripped through JSON, so only JSON-safe
        values are supported).
        """
        params_json = json.dumps(params)
        wrapped = (
            "import json as _mcp_json\n"
            f"_params = _mcp_json.loads({params_json!r})\n"
            f"{code}\n"
            f"print({RESULT_START!r} + _mcp_json.dumps(result) + {RESULT_END!r})\n"
        )
        data = self.exec_raw(wrapped, exec_mode=re.MODE_EXEC_FILE)
        output_text = extract_output_text(data)
        if not data.get("success", False):
            raise UEFNScriptError(f"{data.get('result')}\n{output_text}".strip())
        start = output_text.find(RESULT_START)
        end = output_text.find(RESULT_END)
        if start == -1 or end == -1:
            raise UEFNScriptError(
                f"Command ran but produced no result marker. Output:\n{output_text}"
            )
        json_str = output_text[start + len(RESULT_START) : end]
        return json.loads(json_str)


def extract_output_text(data: dict) -> str:
    return "".join(entry.get("output", "") for entry in (data.get("output") or []))


_bridge: UEFNBridge | None = None


def get_bridge() -> UEFNBridge:
    global _bridge
    if _bridge is None:
        _bridge = UEFNBridge()
    return _bridge
