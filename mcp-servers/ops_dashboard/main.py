from __future__ import annotations

import argparse
import hashlib
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .events import (
    EVENT_ADB_DEVICE_OFFLINE,
    EVENT_ADB_SERVER_RESTART,
    EVENT_RECONNECT_ATTEMPT,
    EVENT_RECONNECT_GIVEUP,
    EVENT_RECONNECT_OK,
    EVENT_SCRCPY_EXIT,
    EVENT_SCRCPY_FROZEN,
    EVENT_SCRCPY_READY,
    EVENT_SCRCPY_START,
    EventLogger,
)
from .state import Signal, WatchState, transition


@dataclass(slots=True)
class WatchConfig:
    device_id: str
    log_path: Path
    max_attempts: int = 6
    tick_sec: float = 2.0
    dry_run: bool = False
    adb_cmd: str = "adb"
    scrcpy_cmd: str = "scrcpy"
    ready_timeout_sec: float = 8.0
    fps_min: int = 10
    low_fps_consecutive: int = 3
    freeze_sec: float = 12.0
    probe_interval_sec: float = 3.0
    probe_timeout_sec: float = 4.0
    trigger_dir: Path | None = None
    initial_state: WatchState | None = None


class ScrcpyWatch:
    def __init__(self, config: WatchConfig) -> None:
        self.config = config
        self.logger = EventLogger(log_path=config.log_path)
        self.state = config.initial_state or WatchState.DISCONNECTED
        self.attempt = 0
        self.session_id: str | None = None
        self.scrcpy_proc: subprocess.Popen[str] | None = None
        self.backoff_table = [2, 5, 10, 20, 40, 60]
        self.last_probe_ts: float = 0.0
        self.last_frame_ts: float = 0.0
        self.last_frame_sig: str | None = None
        self.low_fps_streak = 0

    def _manual_retry_flag_path(self) -> Path:
        trigger_dir = self.config.trigger_dir or (self.config.log_path.parent / "triggers")
        return trigger_dir / f"manual_retry_{self.config.device_id}.flag"

    def consume_manual_retry_trigger(self) -> bool:
        flag_path = self._manual_retry_flag_path()
        if not flag_path.exists():
            return False
        try:
            flag_path.unlink()
        except OSError:
            pass

        if self.state == WatchState.GIVEUP:
            self.set_state(Signal.MANUAL_RETRY)
            self.emit(
                "WARN",
                EVENT_RECONNECT_ATTEMPT,
                "manual retry requested from dashboard",
                "MANUAL_RETRY",
            )
            return True

        self.emit(
            "INFO",
            EVENT_RECONNECT_ATTEMPT,
            "manual retry requested but state is not GIVEUP",
            "MANUAL_RETRY_IGNORED",
            extra={"current_state": self.state.value},
        )
        return False

    def emit(self, level: str, event: str, message: str, reason: str, extra: dict | None = None) -> None:
        self.logger.emit(
            level=level,
            event=event,
            message=message,
            device_id=self.config.device_id,
            session_id=self.session_id,
            attempt=self.attempt if self.attempt else None,
            state=self.state.value,
            reason=reason,
            extra=extra,
        )

    def set_state(self, signal: Signal, *, attempts_exceeded: bool = False) -> None:
        result = transition(self.state, signal, attempts_exceeded=attempts_exceeded)
        self.state = result.current

    def check_adb_visible(self) -> bool:
        if self.config.dry_run:
            return True

        try:
            completed = subprocess.run(
                [self.config.adb_cmd, "devices"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            return False

        if completed.returncode != 0:
            return False

        for line in completed.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices"):
                continue
            parts = line.split()
            serial = parts[0] if parts else ""
            status = parts[1] if len(parts) > 1 else ""
            if serial == self.config.device_id and status == "device":
                return True

        return False

    def stop_scrcpy(self) -> None:
        process = self.scrcpy_proc
        if process is None:
            return
        if process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=3)
            except subprocess.SubprocessError:
                process.kill()
        self.scrcpy_proc = None

    def _scrcpy_alive(self) -> bool:
        process = self.scrcpy_proc
        return process is not None and process.poll() is None

    def start_scrcpy(self) -> bool:
        self.stop_scrcpy()
        self.session_id = f"scrcpy-{uuid.uuid4().hex[:4]}"
        self.emit("INFO", EVENT_SCRCPY_START, "scrcpy start", "CONNECT")

        if self.config.dry_run:
            return True

        try:
            self.scrcpy_proc = subprocess.Popen(
                [self.config.scrcpy_cmd, "-s", self.config.device_id],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            self.scrcpy_proc = None
            return False

        deadline = time.time() + self.config.ready_timeout_sec
        while time.time() < deadline:
            if self._scrcpy_alive():
                now = time.time()
                self.last_frame_ts = now
                self.last_probe_ts = now
                self.last_frame_sig = None
                self.low_fps_streak = 0
                return True
            time.sleep(0.2)

        self.stop_scrcpy()
        return False

    def restart_adb_server(self) -> bool:
        if self.config.dry_run:
            self.emit("INFO", EVENT_ADB_SERVER_RESTART, "adb server restart (dry-run)", "ADB_RECOVERY")
            return True

        try:
            kill_result = subprocess.run(
                [self.config.adb_cmd, "kill-server"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            start_result = subprocess.run(
                [self.config.adb_cmd, "start-server"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            self.emit("WARN", EVENT_ADB_SERVER_RESTART, "adb server restart failed", "ADB_RECOVERY")
            return False

        ok = kill_result.returncode == 0 and start_result.returncode == 0
        level = "INFO" if ok else "WARN"
        message = "adb server restarted" if ok else "adb server restart failed"
        self.emit(level, EVENT_ADB_SERVER_RESTART, message, "ADB_RECOVERY")
        return ok

    def probe_stream_health(self) -> tuple[bool, str, dict | None]:
        now = time.time()

        if self.config.dry_run:
            self.last_frame_ts = now
            return False, "OK", {"dry_run": True}

        if now - self.last_probe_ts < self.config.probe_interval_sec:
            return False, "SKIP", None

        self.last_probe_ts = now

        try:
            started = time.time()
            completed = subprocess.run(
                [self.config.adb_cmd, "-s", self.config.device_id, "exec-out", "screencap", "-p"],
                capture_output=True,
                timeout=self.config.probe_timeout_sec,
                check=False,
            )
            elapsed = max(0.001, time.time() - started)
        except (FileNotFoundError, subprocess.SubprocessError):
            completed = None
            elapsed = self.config.probe_timeout_sec

        estimated_fps = round(1.0 / elapsed, 2)

        frame_changed = False
        if completed and completed.returncode == 0 and completed.stdout:
            frame_sig = hashlib.sha1(completed.stdout).hexdigest()
            frame_changed = self.last_frame_sig != frame_sig
            if frame_changed or self.last_frame_sig is None:
                self.last_frame_ts = now
            self.last_frame_sig = frame_sig
        else:
            frame_sig = self.last_frame_sig

        if estimated_fps < self.config.fps_min:
            self.low_fps_streak += 1
        else:
            self.low_fps_streak = 0

        if self.low_fps_streak >= self.config.low_fps_consecutive:
            return True, "FPS_LOW", {
                "estimated_fps": estimated_fps,
                "fps_min": self.config.fps_min,
                "low_fps_streak": self.low_fps_streak,
            }

        if self.last_frame_ts > 0 and (now - self.last_frame_ts) >= self.config.freeze_sec:
            return True, "FRAME_STALE", {
                "freeze_sec": self.config.freeze_sec,
                "frame_age_sec": round(now - self.last_frame_ts, 2),
                "estimated_fps": estimated_fps,
                "frame_changed": frame_changed,
                "frame_sig": frame_sig,
            }

        return False, "OK", {
            "estimated_fps": estimated_fps,
            "frame_changed": frame_changed,
            "low_fps_streak": self.low_fps_streak,
        }

    def run_recovery(self) -> bool:
        self.attempt += 1
        self.emit(
            "WARN",
            EVENT_RECONNECT_ATTEMPT,
            f"scrcpy reconnect attempt #{self.attempt}",
            "RECOVERY",
        )

        ok = self.start_scrcpy()
        if ok:
            self.emit("INFO", EVENT_RECONNECT_OK, "scrcpy reconnect ok", "RECOVERY")
            self.attempt = 0
            return True

        self.restart_adb_server()
        ok_after_adb = self.start_scrcpy()
        if ok_after_adb:
            self.emit("INFO", EVENT_RECONNECT_OK, "scrcpy reconnect ok after adb restart", "RECOVERY")
            self.attempt = 0
            return True

        return False

    def cooldown_sleep(self) -> None:
        index = min(max(self.attempt - 1, 0), len(self.backoff_table) - 1)
        sleep_sec = self.backoff_table[index]
        time.sleep(min(sleep_sec, 2) if self.config.dry_run else sleep_sec)

    def tick(self) -> None:
        self.consume_manual_retry_trigger()

        if self.state == WatchState.DISCONNECTED:
            if self.check_adb_visible():
                self.set_state(Signal.ADB_VISIBLE)

        if self.state in {WatchState.ADB_OK, WatchState.CONNECTING, WatchState.STREAMING, WatchState.DEGRADED}:
            if not self.check_adb_visible():
                self.emit("ERROR", EVENT_ADB_DEVICE_OFFLINE, "adb device offline", "ADB_OFFLINE")
                self.stop_scrcpy()
                self.set_state(Signal.ADB_OFFLINE)
                return

        if self.state == WatchState.ADB_OK:
            self.set_state(Signal.START_CONNECT)

        if self.state == WatchState.CONNECTING:
            if self.start_scrcpy():
                self.set_state(Signal.READY)
                self.emit("INFO", EVENT_SCRCPY_READY, "scrcpy ready", "READY")

        if self.state == WatchState.STREAMING:
            frozen, reason, details = self.probe_stream_health()
            if frozen:
                self.emit("WARN", EVENT_SCRCPY_FROZEN, "stream seems frozen", reason, extra=details)
                self.set_state(Signal.FROZEN)

        if self.state == WatchState.STREAMING and not self._scrcpy_alive() and not self.config.dry_run:
            self.emit("ERROR", EVENT_SCRCPY_EXIT, "scrcpy exited unexpectedly", "PROCESS_EXIT")
            self.set_state(Signal.FROZEN)

        if self.state == WatchState.DEGRADED:
            self.set_state(Signal.START_CONNECT)

        if self.state == WatchState.RECOVERING:
            if not self.check_adb_visible():
                self.emit("ERROR", EVENT_ADB_DEVICE_OFFLINE, "adb device offline", "ADB_OFFLINE")
                self.set_state(Signal.ADB_OFFLINE)
                return

            ok = self.run_recovery()
            if ok:
                self.set_state(Signal.RECOVER_OK)
            else:
                exceeded = self.attempt >= self.config.max_attempts
                self.set_state(Signal.RECOVER_FAIL, attempts_exceeded=exceeded)
                if exceeded:
                    self.emit("ERROR", EVENT_RECONNECT_GIVEUP, "reconnect giveup", "MAX_ATTEMPTS")
                else:
                    self.cooldown_sleep()

    def loop(self, max_ticks: int | None = None) -> None:
        ticks = 0
        while True:
            self.tick()
            ticks += 1
            if max_ticks is not None and ticks >= max_ticks:
                break
            time.sleep(self.config.tick_sec)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="scrcpy-watch minimal runner")
    parser.add_argument("--device-id", default="pixel7")
    parser.add_argument("--log-path", default="../logs/recovery.jsonl")
    parser.add_argument("--tick-sec", type=float, default=2.0)
    parser.add_argument("--max-attempts", type=int, default=6)
    parser.add_argument("--max-ticks", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--adb-cmd", default="adb")
    parser.add_argument("--scrcpy-cmd", default="scrcpy")
    parser.add_argument("--ready-timeout-sec", type=float, default=8.0)
    parser.add_argument("--fps-min", type=int, default=10)
    parser.add_argument("--low-fps-consecutive", type=int, default=3)
    parser.add_argument("--freeze-sec", type=float, default=12.0)
    parser.add_argument("--probe-interval-sec", type=float, default=3.0)
    parser.add_argument("--probe-timeout-sec", type=float, default=4.0)
    parser.add_argument("--trigger-dir", default="../logs/triggers")
    parser.add_argument(
        "--initial-state",
        choices=[state.value for state in WatchState],
        default=None,
        help="debug/testing only",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = WatchConfig(
        device_id=args.device_id,
        log_path=Path(args.log_path).resolve(),
        max_attempts=args.max_attempts,
        tick_sec=args.tick_sec,
        dry_run=args.dry_run,
        adb_cmd=args.adb_cmd,
        scrcpy_cmd=args.scrcpy_cmd,
        ready_timeout_sec=args.ready_timeout_sec,
        fps_min=args.fps_min,
        low_fps_consecutive=args.low_fps_consecutive,
        freeze_sec=args.freeze_sec,
        probe_interval_sec=args.probe_interval_sec,
        probe_timeout_sec=args.probe_timeout_sec,
        trigger_dir=Path(args.trigger_dir).resolve(),
        initial_state=WatchState(args.initial_state) if args.initial_state else None,
    )
    watch = ScrcpyWatch(config)
    watch.loop(max_ticks=args.max_ticks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
