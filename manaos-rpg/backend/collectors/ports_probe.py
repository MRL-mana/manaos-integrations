from __future__ import annotations

import socket
from contextlib import closing


def is_port_open(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(timeout)
            return sock.connect_ex((host, port)) == 0
    except Exception:
        return False
