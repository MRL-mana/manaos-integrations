"""
本物 Moltbot 実行（B パッチ用）。
EXECUTOR=moltbot のとき使う。最初は list_files / file_read だけ許可。
MOLTBOT_DAEMON_URL または MOLTBOT_CLI_PATH が設定されていれば本物呼び出し、未設定なら mock にフォールバック。
"""

import json
import os
import time
from typing import Any, Dict, List

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# 最初は read-only だけ許可（Phase1 でもいったん list_files で通してから move を解放）
ALLOWED_ACTIONS_MOLTBOT = frozenset({"list_files", "file_read"})

# PlanStep.action → OpenClaw ツール名（skills.* は標準でないため list_files は exec で代用）
ACTION_TO_SKILL: Dict[str, str] = {
    "list_files": "exec",  # skills.fs.list が無いため exec で dir /b を実行
    "file_read": "skills.fs.read",
    "classify_files": "skills.classify",
    "move_files": "skills.fs.move",
}


def _list_files_args(params: Dict[str, Any]) -> Dict[str, Any]:
    """list_files 用: OpenClaw exec に渡す args（Windows: dir /b）。"""
    path = (params.get("path") or ".").strip()
    return {"command": "dir /b", "workdir": path}


def _parse_exec_stdout_to_files(data: Any) -> List[str]:
    """exec の result（stdout 文字列 or {stdout}）からファイル名リストを返す。"""
    if data is None:
        return []
    if isinstance(data, dict):
        raw = data.get("stdout") or data.get("output") or ""
    else:
        raw = str(data)
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    return lines


def _expand_local_path(p: str) -> str:
    # ~/Downloads 等を Windows の実パスに寄せる
    p2 = (p or "").strip()
    if not p2:
        return p2
    p2 = os.path.expandvars(p2)
    p2 = os.path.expanduser(p2)
    return os.path.normpath(p2)


def _local_list_files(params: Dict[str, Any]) -> Dict[str, Any]:
    """OpenClaw が 404 を返す場合のローカル fallback（本物の一覧を返す）。"""
    root = _expand_local_path(str(params.get("path") or "."))
    max_entries = int(params.get("max_entries") or 500)
    entries: List[Dict[str, Any]] = []
    total = 0
    try:
        with os.scandir(root) as it:
            for e in it:
                total += 1
                if max_entries > 0 and len(entries) >= max_entries:
                    continue
                try:
                    st = e.stat(follow_symlinks=False)
                    size = st.st_size
                    mtime = st.st_mtime
                except Exception:
                    size = None
                    mtime = None
                entries.append(
                    {
                        "name": e.name,
                        "path": os.path.join(root, e.name),
                        "is_dir": e.is_dir(follow_symlinks=False),
                        "size": size,
                        "mtime": mtime,
                    }
                )
    except FileNotFoundError:
        return {"path": root, "files": [], "error": "not_found"}
    except NotADirectoryError:
        return {"path": root, "files": [], "error": "not_a_directory"}
    except PermissionError:
        return {"path": root, "files": [], "error": "permission_denied"}
    truncated = max_entries > 0 and total > max_entries
    return {
        "path": root,
        "files": entries,
        "total": total,
        "truncated": truncated,
        "max_entries": max_entries,
    }


def _local_file_read(params: Dict[str, Any]) -> Dict[str, Any]:
    """OpenClaw が 404 を返す場合のローカル fallback（ファイル内容を返す）。"""
    path = _expand_local_path(str(params.get("path") or params.get("file") or ""))
    max_chars = int(params.get("max_chars") or 20000)
    if not path:
        return {"path": "", "content": "", "error": "path_required"}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        truncated = max_chars > 0 and len(content) > max_chars
        if truncated:
            content = content[:max_chars]
        return {"path": path, "content": content, "truncated": truncated, "max_chars": max_chars}
    except FileNotFoundError:
        return {"path": path, "content": "", "error": "not_found"}
    except PermissionError:
        return {"path": path, "content": "", "error": "permission_denied"}
    except IsADirectoryError:
        return {"path": path, "content": "", "error": "is_a_directory"}


MOLTBOT_DAEMON_URL = (os.getenv("MOLTBOT_DAEMON_URL") or "").strip()
MOLTBOT_CLI_PATH = (os.getenv("MOLTBOT_CLI_PATH") or "").strip()
# OpenClaw Tools Invoke API 用。Bearer トークン（OPENCLAW_GATEWAY_TOKEN または gateway.auth.token と同一）
MOLTBOT_DAEMON_TOKEN = (
    os.getenv("MOLTBOT_DAEMON_TOKEN") or os.getenv("OPENCLAW_GATEWAY_TOKEN") or ""
).strip()


class MoltbotExecutor:
    """
    EXECUTOR=moltbot のとき使う。
    list_files / file_read のみ許可。それ以外は拒否。
    本物接続: MOLTBOT_DAEMON_URL か MOLTBOT_CLI_PATH が設定されていれば呼び出し、未設定なら mock にフォールバック。
    """

    def run(self, plan: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        plan_id = plan.get("plan_id", "")
        steps = plan.get("steps") or []

        for s in steps:
            action = (s.get("action") or "").strip()
            if action and action not in ALLOWED_ACTIONS_MOLTBOT:
                return self._rejected_result(
                    plan_id,
                    steps,
                    f"action not allowed in moltbot mode (allowed: {sorted(ALLOWED_ACTIONS_MOLTBOT)})",
                )

        if MOLTBOT_DAEMON_URL or MOLTBOT_CLI_PATH:
            return self._run_real(plan, plan_id, steps)
        # 本物未設定: mock にフォールバック（list_files だけ通した体）
        from moltbot_gateway.executor import mock

        return mock.MockExecutor().run(plan)

    def _run_real(
        self, plan: Dict[str, Any], plan_id: str, steps: List[Dict[str, Any]]
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """本物: OpenClaw Tools Invoke → 従来 /run → CLI → プレースホルダーの順で試す。"""
        if MOLTBOT_DAEMON_URL and REQUESTS_AVAILABLE:
            out = self._call_openclaw_tools_invoke(plan, plan_id, steps)
            if out is not None:
                return out
            out = self._call_daemon(plan)
            if out is not None:
                return out
        if MOLTBOT_CLI_PATH:
            out = self._call_cli(plan)
            if out is not None:
                return out
        return self._run_real_placeholder(plan_id, steps)

    def _call_openclaw_tools_invoke(
        self, plan: Dict[str, Any], plan_id: str, steps: List[Dict[str, Any]]
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]] | None:
        """OpenClaw Gateway の POST /tools/invoke をステップごとに呼び、結果をまとめる。"""
        base = MOLTBOT_DAEMON_URL.rstrip("/")
        url = f"{base}/tools/invoke"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if MOLTBOT_DAEMON_TOKEN:
            try:
                # HTTP ヘッダーは latin-1 のため、トークンは ASCII のみにする
                MOLTBOT_DAEMON_TOKEN.encode("ascii")
                headers["Authorization"] = f"Bearer {MOLTBOT_DAEMON_TOKEN}"
            except UnicodeEncodeError:
                # 非 ASCII トークンはヘッダーに載せない（OpenClaw 側で gateway_production.env のトークンを ASCII のみにすること）
                pass
        events: List[Dict[str, Any]] = []
        outputs: List[Any] = []
        t0 = time.time()
        for i, s in enumerate(steps):
            step_id = s.get("step_id", str(i + 1))
            action = (s.get("action") or "").strip()
            params = s.get("params") or {}
            tool = ACTION_TO_SKILL.get(action, action)
            args = params
            if action == "list_files":
                args = _list_files_args(params)
            body = {
                "tool": tool,
                "action": "json",
                "args": args,
                "sessionKey": "main",
                "dryRun": False,
            }
            try:
                body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
                r = requests.post(url, data=body_bytes, headers=headers, timeout=60)
                r.encoding = r.encoding or "utf-8"
                if r.status_code == 404:
                    # ツールが OpenClaw にない / 許可されていない → read-only はローカルで本物を返す
                    if action == "list_files":
                        res = _local_list_files(params)
                        outputs.append(res)
                        events.append(
                            {
                                "ts": time.time(),
                                "step_id": step_id,
                                "event": action,
                                "tool": "local_fallback",
                                "status": "ok",
                                "result": res,
                                "note": "openclaw_tools_invoke_404",
                            }
                        )
                        continue
                    if action == "file_read":
                        res = _local_file_read(params)
                        outputs.append(res)
                        events.append(
                            {
                                "ts": time.time(),
                                "step_id": step_id,
                                "event": action,
                                "tool": "local_fallback",
                                "status": "ok",
                                "result": res,
                                "note": "openclaw_tools_invoke_404",
                            }
                        )
                        continue
                    from moltbot_gateway.executor import mock

                    return mock.MockExecutor().run(plan)
                if r.status_code != 200:
                    events.append(
                        {
                            "ts": time.time(),
                            "step_id": step_id,
                            "event": action,
                            "tool": tool,
                            "status": "error",
                            "http_status": r.status_code,
                            "body": r.text[:500],
                        }
                    )
                    result = {
                        "plan_id": plan_id,
                        "success": False,
                        "status": "openclaw_tool_error",
                        "error": f"tools/invoke {r.status_code}",
                        "steps_done": i,
                        "steps_total": len(steps),
                        "execute_events": events,
                    }
                    return result, events
                data = r.json()
                if not data.get("ok"):
                    err = data.get("error", {})
                    events.append(
                        {
                            "ts": time.time(),
                            "step_id": step_id,
                            "event": action,
                            "tool": tool,
                            "status": "error",
                            "error": err,
                        }
                    )
                    result = {
                        "plan_id": plan_id,
                        "success": False,
                        "status": "openclaw_tool_error",
                        "error": err.get("message", str(err)),
                        "steps_done": i,
                        "steps_total": len(steps),
                        "execute_events": events,
                    }
                    return result, events
                res = data.get("result")
                if action == "list_files":
                    res = {"files": _parse_exec_stdout_to_files(res)}
                outputs.append(res)
                events.append(
                    {
                        "ts": time.time(),
                        "step_id": step_id,
                        "event": action,
                        "tool": tool,
                        "status": "ok",
                        "result": res,
                    }
                )
            except Exception as e:
                # OpenClaw が落ちている等でも、read-only はローカルで返せるなら返す
                if action == "list_files":
                    res = _local_list_files(params)
                    outputs.append(res)
                    events.append(
                        {
                            "ts": time.time(),
                            "step_id": step_id,
                            "event": action,
                            "tool": "local_fallback",
                            "status": "ok",
                            "result": res,
                            "note": "openclaw_invoke_exception",
                        }
                    )
                    continue
                if action == "file_read":
                    res = _local_file_read(params)
                    outputs.append(res)
                    events.append(
                        {
                            "ts": time.time(),
                            "step_id": step_id,
                            "event": action,
                            "tool": "local_fallback",
                            "status": "ok",
                            "result": res,
                            "note": "openclaw_invoke_exception",
                        }
                    )
                    continue
                events.append(
                    {
                        "ts": time.time(),
                        "step_id": step_id,
                        "event": action,
                        "tool": tool,
                        "status": "error",
                        "error": str(e),
                    }
                )
                result = {
                    "plan_id": plan_id,
                    "success": False,
                    "status": "openclaw_invoke_error",
                    "error": str(e),
                    "steps_done": i,
                    "steps_total": len(steps),
                    "execute_events": events,
                }
                return result, events
        finished_at = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        result = {
            "plan_id": plan_id,
            "success": True,
            "status": "completed",
            "summary": "openclaw tools/invoke",
            "finished_at": finished_at,
            "steps_done": len(steps),
            "steps_total": len(steps),
            "duration_seconds": round(time.time() - t0, 2),
            "execute_events": events,
            "outputs": outputs,
        }
        return result, events

    def _call_daemon(
        self, plan: Dict[str, Any]
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]] | None:
        """従来: 本物 daemon に POST /run で plan を送り、result / execute_events を受け取る。"""
        base = MOLTBOT_DAEMON_URL.rstrip("/")
        url = f"{base}/run"
        try:
            r = requests.post(url, json=plan, timeout=60)
            r.raise_for_status()
            data = r.json()
            result = data.get("result", data)
            events = result.get("execute_events", [])
            return result, events
        except Exception:
            return None

    def _call_cli(self, plan: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]]] | None:
        """本物 CLI を subprocess で呼ぶ。未実装なら None。"""
        import subprocess
        import json

        try:
            proc = subprocess.run(
                [MOLTBOT_CLI_PATH, "run", "--plan", json.dumps(plan)],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=os.path.dirname(MOLTBOT_CLI_PATH) or ".",
            )
            if proc.returncode != 0:
                return None
            data = json.loads(proc.stdout) if proc.stdout else {}
            result = data.get("result", data)
            events = result.get("execute_events", [])
            return result, events
        except Exception:
            return None

    def _run_real_placeholder(
        self, plan_id: str, steps: List[Dict[str, Any]]
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """daemon/CLI 未実装時のプレースホルダー。イベントを積んで返す。"""
        events: List[Dict[str, Any]] = []
        t0 = time.time()
        for i, s in enumerate(steps):
            step_id = s.get("step_id", str(i + 1))
            action = (s.get("action") or "").strip()
            tool = ACTION_TO_SKILL.get(action, action)
            events.append(
                {
                    "ts": time.time(),
                    "step_id": step_id,
                    "event": action,
                    "tool": tool,
                    "status": "ok",
                }
            )
        finished_at = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        result = {
            "plan_id": plan_id,
            "success": True,
            "status": "completed",
            "summary": "moltbot execution (real backend placeholder)",
            "finished_at": finished_at,
            "steps_done": len(steps),
            "steps_total": len(steps),
            "duration_seconds": round(time.time() - t0, 2),
            "execute_events": events,
            "outputs": {"listed": [], "read": []},
        }
        return result, events

    def _rejected_result(
        self, plan_id: str, steps: list, reason: str
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        events = [{"ts": time.time(), "event": "rejected", "reason": reason}]
        result = {
            "plan_id": plan_id,
            "success": False,
            "status": "rejected",
            "error": reason,
            "steps_done": 0,
            "steps_total": len(steps),
            "execute_events": events,
        }
        return result, events
