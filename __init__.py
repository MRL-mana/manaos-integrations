"""ManaOS外部システム統合モジュール"""

try:
    from importlib.metadata import version as _version

    __version__ = _version("manaos-integrations")
except Exception:
    __version__ = "2.6.0"
