"""Reflection Feed outbox replay utility."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional

import requests

DEFAULT_OUTBOX = Path(os.getenv("MACHI_FEED_OUTBOX", "/var/lib/machi/feed_outbox.jsonl"))
DEFAULT_BASE_URL = os.getenv("MACHI_FEED_BASE_URL", "http://127.0.0.1:5057")
DEFAULT_TOKEN = os.getenv("MACHI_FEED_TOKEN")


class OutboxReplayer:
    """Replay persisted Reflection Feed payloads."""

    def __init__(
        self,
        outbox_path: Path,
        base_url: str,
        token: Optional[str],
        *,
        timeout: float = 5.0,
        dry_run: bool = False,
    ) -> None:
        self.outbox_path = outbox_path
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.dry_run = dry_run
        self.session = requests.Session()
        self._headers = {"Content-Type": "application/json"}
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def replay(self, *, limit: Optional[int] = None, verbose: bool = True) -> Dict[str, int]:
        """Replay the outbox file and return counts for {sent, failed}."""

        if not self.outbox_path.exists():
            if verbose:
                print(f"[replay] Outbox not found: {self.outbox_path}")
            return {"sent": 0, "failed": 0, "skipped": 0}

        sent = 0
        failed = 0
        skipped = 0
        remaining: list[str] = []
        processed = 0

        for record_line in self._iter_lines(limit=limit):
            processed += 1
            try:
                record = json.loads(record_line)
            except json.JSONDecodeError:
                failed += 1
                continue

            topic = record.get("topic")
            payload = record.get("payload")
            if not topic or payload is None:
                skipped += 1
                continue

            if self.dry_run:
                sent += 1
                continue

            endpoint = f"{self.base_url}/ingest/{topic}"
            success = self._post(endpoint, payload)
            if success:
                sent += 1
            else:
                failed += 1
                remaining.append(record_line)

        if not self.dry_run:
            self._rewrite_outbox(remaining)

        if verbose:
            print(
                f"[replay] processed={processed} sent={sent} failed={failed} remaining={len(remaining)}"
            )

        return {"sent": sent, "failed": failed, "skipped": skipped}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _iter_lines(self, *, limit: Optional[int]) -> Iterator[str]:
        with self.outbox_path.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if limit is not None and index >= limit:
                    break
                line = line.strip()
                if not line:
                    continue
                yield line

    def _post(self, endpoint: str, payload: Dict[str, object]) -> bool:
        try:
            response = self.session.post(
                endpoint,
                headers=self._headers,
                json=payload,
                timeout=self.timeout,
            )
            if response.status_code < 400:
                return True
            print(
                f"[replay] HTTP {response.status_code} for {endpoint}: {response.text}",
                file=sys.stderr,
            )
            return False
        except Exception as exc:  # pragma: no cover - network failure
            print(f"[replay] Exception posting to {endpoint}: {exc}", file=sys.stderr)
            return False

    def _rewrite_outbox(self, remaining: Iterable[str]) -> None:
        tmp_path = self.outbox_path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            for line in remaining:
                handle.write(line + "\n")
        tmp_path.replace(self.outbox_path)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay Reflection Feed outbox payloads")
    parser.add_argument("--outbox", help="Path to outbox JSONL file", default=str(DEFAULT_OUTBOX))
    parser.add_argument("--base-url", help="Reflection Feed base URL", default=DEFAULT_BASE_URL)
    parser.add_argument("--token", help="Bearer token", default=DEFAULT_TOKEN)
    parser.add_argument("--limit", type=int, default=None, help="Maximum entries to replay")
    parser.add_argument("--timeout", type=float, default=5.0, help="HTTP timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Do not send requests; count entries")
    parser.add_argument("--quiet", action="store_true", help="Suppress summary output")
    return parser.parse_args(argv)  # type: ignore


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)

    replayer = OutboxReplayer(
        Path(args.outbox),
        args.base_url,
        args.token,
        timeout=args.timeout,
        dry_run=args.dry_run,
    )
    summary = replayer.replay(limit=args.limit, verbose=not args.quiet)

    if not args.quiet:
        print(json.dumps(summary, ensure_ascii=False))

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
