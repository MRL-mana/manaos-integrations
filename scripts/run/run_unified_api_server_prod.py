"""
Production runner for ManaOS Unified API Server.

- Uses Waitress (Windows-friendly WSGI server)
- Respects the existing env config used by unified_api_server.py
"""

import os


def _env_bool(name: str, default: bool = False) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    if v in ("1", "true", "yes", "y", "on"):
        return True
    if v in ("0", "false", "no", "n", "off"):
        return False
    return default


def main():
    from waitress import serve
    from unified_api_server import app

    host = os.getenv("MANAOS_INTEGRATION_HOST", "127.0.0.1")
    port = int(os.getenv("MANAOS_INTEGRATION_PORT", "9502"))

    # Waitress tuning
    threads = int(os.getenv("MANAOS_WAITRESS_THREADS", "8"))
    ident = os.getenv("MANAOS_WAITRESS_IDENT", "manaos-unified-api")
    expose_tracebacks = _env_bool("MANAOS_DEBUG", False)

    print(f"[prod] serving on http://{host}:{port} (threads={threads})")
    serve(
        app,
        host=host,
        port=port,
        threads=threads,
        ident=ident,
        expose_tracebacks=expose_tracebacks,
    )


if __name__ == "__main__":
    main()

