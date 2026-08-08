"""Bridge to a running UEFN / Unreal Editor instance via the Python Editor Script
Plugin's remote execution protocol (UDP discovery + TCP command channel).

This talks to whatever editor is listening on the default multicast group
(239.0.0.1:6766) with "Remote Execution" enabled in the Python plugin settings,
which is the default. The editor must be running with the target project open
and Python enabled for that project.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any

from . import remote_execution as re

RESULT_START = "@@UEFN_MCP_RESULT_START@@"
RESULT_END = "@@UEFN_MCP_RESULT_END@@"


class UEFNConnectionError(RuntimeError):
    pass


class UEFNScriptError(RuntimeError):
    pass


class UEFNBridge:
    """Thread-safe wrapper around a single remote execution command connection."""

    def __init__(self, discovery_timeout: float = 5.0) -> None:
        self._lock = threading.RLock()
        self._remote_exec: re.RemoteExecution | None = None
        self._discovery_timeout = discovery_timeout

    def connect(self) -> dict:
        """(Re)establish a command connection to the first discovered editor node."""
        with self._lock:
            self._teardown()
            self._remote_exec = re.RemoteExecution()
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
            self._remote_exec.open_command_connection(node["node_id"])
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
            try:
                return self._remote_exec.run_command(
                    code, unattended=unattended, exec_mode=exec_mode
                )
            except (OSError, RuntimeError):
                # Stale/closed connection (e.g. editor was restarted) - reconnect once.
                self.connect()
                return self._remote_exec.run_command(
                    code, unattended=unattended, exec_mode=exec_mode
                )

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
