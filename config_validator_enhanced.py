#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✅ ManaOS 設定ファイル検証システム（強化版）
スキーマ検証、起動時検証、デフォルト値管理
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from manaos_logger import get_logger

logger = get_logger(__name__)


@dataclass


class ValidationError:
    """検証エラー"""
    field: str
    message: str
    severity: str = "error"  # "error", "warning"


class ConfigSchema:
    """設定スキーマ"""

    def __init__(self):
        self.schemas = {
            "llm_routing_config.yaml": {
                "routing": {
                    "type": "dict",
                    "required": True,
                    "fields": {
                        "reasoning": {
                            "type": "dict",
                            "required": True,
                            "fields": {
                                "primary": {"type": "str", "required": True},
                                "fallback": {"type": "list", "required": False, "default": []}
                            }
                        }
                    }
                }
            },
            "manaos_timeout_config.json": {
                "version": {"type": "str", "required": False},
                "description": {"type": "str", "required": False},
                "timeouts": {
                    "type": "dict",
                    "required": True,
                    "fields": {
                        "health_check": {"type": "float", "required": False, "min": 1.0, "max": 60.0, "default": 2.0},
                        "api_call": {"type": "float", "required": False, "min": 1.0, "max": 300.0, "default": 5.0},
                        "llm_call": {"type": "float", "required": False, "min": 1.0, "max": 600.0, "default": 30.0},
                        "llm_call_heavy": {"type": "float", "required": False, "min": 1.0, "max": 1200.0, "default": 60.0},
                        "workflow_execution": {"type": "float", "required": False, "min": 1.0, "max": 3600.0, "default": 300.0},
                        "script_execution": {"type": "float", "required": False, "min": 1.0, "max": 600.0, "default": 60.0},
                        "command_execution": {"type": "float", "required": False, "min": 1.0, "max": 600.0, "default": 30.0},
                        "database_query": {"type": "float", "required": False, "min": 1.0, "max": 300.0, "default": 10.0},
                        "file_operation": {"type": "float", "required": False, "min": 1.0, "max": 600.0, "default": 30.0},
                        "network_request": {"type": "float", "required": False, "min": 1.0, "max": 300.0, "default": 10.0},
                        "external_service": {"type": "float", "required": False, "min": 1.0, "max": 600.0, "default": 30.0},
                    }
                }
            },
            "auto_optimization_state.json": {
                "history": {"type": "list", "required": False, "default": []},
                "rules": {
                    "type": "list",
                    "required": False,
                    "default": []
                },
                "last_optimization": {"type": ["str", "null"], "required": False, "default": None}
            },
            "oh_my_opencode_config.yaml": {
                "api": {
                    "type": "dict",
                    "required": True,
                    "fields": {
                        "base_url": {"type": "str", "required": True},
                        "api_key": {"type": "str", "required": True},
                        "timeout": {"type": "float", "required": False, "default": 300.0}
                    }
                },
                "execution": {
                    "type": "dict",
                    "required": True,
                    "fields": {
                        "default_mode": {"type": "str", "required": False, "default": "normal"},
                        "max_iterations": {"type": "int", "required": False, "default": 10},
                        "max_execution_time": {"type": "int", "required": False, "default": 3600}
                    }
                },
                "ultra_work": {
                    "type": "dict",
                    "required": False,
                    "fields": {
                        "enabled": {"type": "bool", "required": False, "default": False},
                        "allowed_task_types": {"type": "list", "required": False, "default": []},
                        "require_approval": {"type": "bool", "required": False, "default": True},
                        "cost_limit_per_task": {"type": "float", "required": False, "default": 100.0},
                        "downgrade_enabled": {"type": "bool", "required": False, "default": True},
                        "downgrade_cost_threshold": {"type": "float", "required": False, "default": 0.7},
                        "downgrade_time_threshold": {"type": "float", "required": False, "default": 0.8},
                        "downgrade_iteration_threshold": {"type": "float", "required": False, "default": 0.75}
                    }
                },
                "cost_management": {
                    "type": "dict",
                    "required": False,
                    "fields": {
                        "enabled": {"type": "bool", "required": False, "default": True},
                        "daily_limit": {"type": "float", "required": False, "default": 100.0},
                        "monthly_limit": {"type": "float", "required": False, "default": 2000.0},
                        "warning_threshold": {"type": "float", "required": False, "default": 0.8},
                        "auto_stop": {"type": "bool", "required": False, "default": True}
                    }
                },
                "kill_switch": {
                    "type": "dict",
                    "required": False,
                    "fields": {
                        "enabled": {"type": "bool", "required": False, "default": True},
                        "max_execution_time": {"type": "int", "required": False, "default": 3600},
                        "max_iterations": {"type": "int", "required": False, "default": 20},
                        "detect_infinite_loop": {"type": "bool", "required": False, "default": True},
                        "auto_kill_on_error": {"type": "bool", "required": False, "default": False}
                    }
                },
                "trinity": {
                    "type": "dict",
                    "required": False,
                    "fields": {
                        "enabled": {"type": "bool", "required": False, "default": True},
                        "remi_integration": {"type": "bool", "required": False, "default": True},
                        "luna_integration": {"type": "bool", "required": False, "default": True},
                        "mina_integration": {"type": "bool", "required": False, "default": True}
                    }
                },
                "llm_routing": {
                    "type": "dict",
                    "required": False,
                    "fields": {
                        "enabled": {"type": "bool", "required": False, "default": True},
                        "use_manaos_routing": {"type": "bool", "required": False, "default": True},
                        "fallback_to_local": {"type": "bool", "required": False, "default": True}
                    }
                },
                "logging": {
                    "type": "dict",
                    "required": False,
                    "fields": {
                        "enabled": {"type": "bool", "required": False, "default": True},
                        "level": {"type": "str", "required": False, "default": "INFO"},
                        "save_to_obsidian": {"type": "bool", "required": False, "default": True},
                        "save_to_notion": {"type": "bool", "required": False, "default": False}
                    }
                }
            },
            # ---------- manaos_integration_config.json ----------
            "manaos_integration_config.json": {
                "manaos_services": {"type": "dict", "required": True},
                "integration_services": {"type": "dict", "required": True},
                "health_check_interval": {
                    "type": "int",
                    "required": False,
                    "min": 5,
                    "max": 3600,
                    "default": 60,
                },
                "timeout": {
                    "type": "float",
                    "required": False,
                    "min": 0.5,
                    "max": 120.0,
                    "default": 5.0,
                },
                "retry_attempts": {
                    "type": "int",
                    "required": False,
                    "min": 0,
                    "max": 10,
                    "default": 3,
                },
                "retry_delay": {
                    "type": "float",
                    "required": False,
                    "min": 0.1,
                    "max": 60.0,
                    "default": 1.0,
                },
                "max_workers": {
                    "type": "int",
                    "required": False,
                    "min": 1,
                    "max": 32,
                    "default": 5,
                },
            },
        }

        # ---------- ポート重複検出用ヘルパー ----------
        self._port_range = (1024, 65535)

    # ---- ポート重複検出 ----
    def validate_unique_ports(
        self, config_data: Dict[str, Any]
    ) -> List[ValidationError]:
        """manaos_integration_config.json のポート重複・範囲を検証."""
        errors: List[ValidationError] = []
        seen: Dict[int, str] = {}
        allowed_dupes = {
            frozenset({"manaos_services.ui_operations", "manaos_services.mrl_memory"})
        }
        for section_key in ("manaos_services", "integration_services"):
            section = config_data.get(section_key, {})
            if not isinstance(section, dict):
                continue
            for svc_name, svc_cfg in section.items():
                if not isinstance(svc_cfg, dict):
                    continue
                port = svc_cfg.get("port")
                if port is None:
                    continue
                if not isinstance(port, int):
                    errors.append(
                        ValidationError(
                            field=f"{section_key}.{svc_name}.port",
                            message=f"ポートは整数である必要があります",
                        )
                    )
                    continue
                lo, hi = self._port_range
                if port < lo or port > hi:
                    errors.append(
                        ValidationError(
                            field=f"{section_key}.{svc_name}.port",
                            message=f"ポート {port} は {lo}-{hi} の範囲外です",
                            severity="warning",
                        )
                    )
                if port in seen:
                    pair = frozenset({seen[port], f"{section_key}.{svc_name}"})
                    if pair not in allowed_dupes:
                        errors.append(
                            ValidationError(
                                field=f"{section_key}.{svc_name}.port",
                                message=f"ポート {port} は '{seen[port]}' と重複しています",
                            )
                        )
                seen[port] = f"{section_key}.{svc_name}"
        return errors

    def validate(self, config_path: Path, config_data: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        """
        設定を検証

        Args:
            config_path: 設定ファイルパス
            config_data: 設定データ

        Returns:
            (検証結果, エラーリスト)
        """
        errors = []
        schema_name = config_path.name

        if schema_name not in self.schemas:
            logger.warning(f"スキーマが見つかりません: {schema_name}")
            return True, errors

        schema = self.schemas[schema_name]
        errors.extend(self._validate_dict(config_data, schema, ""))

        # manaos_integration_config.json の場合はポート重複も検証
        if schema_name == "manaos_integration_config.json":
            errors.extend(self.validate_unique_ports(config_data))

        return len(errors) == 0, errors

    def _validate_dict(self, data: Dict[str, Any], schema: Dict[str, Any], prefix: str) -> List[ValidationError]:
        """辞書を検証"""
        errors = []

        for key, field_schema in schema.items():
            field_path = f"{prefix}.{key}" if prefix else key

            if field_schema.get("required", False) and key not in data:
                errors.append(ValidationError(
                    field=field_path,
                    message=f"必須フィールド '{key}' がありません"
                ))
                continue

            if key not in data:
                # デフォルト値を設定
                if "default" in field_schema:
                    data[key] = field_schema["default"]
                continue

            value = data[key]
            field_type = field_schema.get("type")

            # null値のチェック（複数型指定の場合）
            if isinstance(field_type, list) and "null" in field_type and value is None:
                # nullが許可されている場合はスキップ
                continue

            # 型チェック
            if isinstance(field_type, list):
                # 複数の型を許可する場合（例: ["str", "null"]）
                type_valid = False
                for allowed_type in field_type:
                    if allowed_type == "null" and value is None:
                        type_valid = True
                        break
                    elif allowed_type == "str" and isinstance(value, str):
                        type_valid = True
                        break
                    elif allowed_type == "int" and isinstance(value, int):
                        type_valid = True
                        break
                    elif allowed_type == "float" and isinstance(value, (int, float)):
                        type_valid = True
                        break
                if not type_valid:
                    errors.append(ValidationError(
                        field=field_path,
                        message=f"フィールド '{key}' は {', '.join(str(t) for t in field_type)} のいずれかである必要があります"
                    ))
            elif field_type == "str" and not isinstance(value, str):
                errors.append(ValidationError(
                    field=field_path,
                    message=f"フィールド '{key}' は文字列である必要があります"
                ))
            elif field_type == "int" and not isinstance(value, int):
                errors.append(ValidationError(
                    field=field_path,
                    message=f"フィールド '{key}' は整数である必要があります"
                ))
            elif field_type == "float" and not isinstance(value, (int, float)):
                errors.append(ValidationError(
                    field=field_path,
                    message=f"フィールド '{key}' は数値である必要があります"
                ))
            elif field_type == "dict":
                if not isinstance(value, dict):
                    errors.append(ValidationError(
                        field=field_path,
                        message=f"フィールド '{key}' は辞書である必要があります"
                    ))
                elif "fields" in field_schema:
                    errors.extend(self._validate_dict(value, field_schema["fields"], field_path))
            elif field_type == "list" and not isinstance(value, list):
                errors.append(ValidationError(
                    field=field_path,
                    message=f"フィールド '{key}' はリストである必要があります"
                ))

            # 範囲チェック
            if isinstance(value, (int, float)):
                if "min" in field_schema and value < field_schema["min"]:
                    errors.append(ValidationError(
                        field=field_path,
                        message=f"フィールド '{key}' は {field_schema['min']} 以上である必要があります",
                        severity="warning"
                    ))
                if "max" in field_schema and value > field_schema["max"]:
                    errors.append(ValidationError(
                        field=field_path,
                        message=f"フィールド '{key}' は {field_schema['max']} 以下である必要があります",
                        severity="warning"
                    ))

        return errors


class ConfigValidatorEnhanced:
    """設定検証システム（強化版）"""

    def __init__(self):
        self.schema = ConfigSchema()
        self.validated_configs = {}

    def validate_config_file(self, config_path: Path) -> Tuple[bool, List[ValidationError], Dict[str, Any]]:
        """
        設定ファイルを検証

        Args:
            config_path: 設定ファイルパス

        Returns:
            (検証結果, エラーリスト, 検証済み設定データ)
        """
        if not config_path.exists():
            return False, [ValidationError(
                field="file",
                message=f"設定ファイルが見つかりません: {config_path}"
            )], {}

        try:
            # ファイルを読み込み
            if config_path.suffix == ".yaml" or config_path.suffix == ".yml":
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
            elif config_path.suffix == ".json":
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            else:
                return False, [ValidationError(
                    field="file",
                    message=f"サポートされていないファイル形式: {config_path.suffix}"
                )], {}

            # 検証
            is_valid, errors = self.schema.validate(config_path, config_data)

            if is_valid:
                self.validated_configs[str(config_path)] = config_data
                logger.info(f"✅ 設定ファイルを検証しました: {config_path}")

            return is_valid, errors, config_data

        except Exception as e:
            return False, [ValidationError(
                field="file",
                message=f"設定ファイルの読み込みエラー: {str(e)}"
            )], {}

    def validate_all_configs(self, config_dir: Optional[Path] = None) -> Dict[str, Tuple[bool, List[ValidationError]]]:
        """
        すべての設定ファイルを検証

        Args:
            config_dir: 設定ディレクトリ

        Returns:
            検証結果の辞書
        """
        config_dir = config_dir or Path(__file__).parent

        results = {}

        # 設定ファイルを検索
        config_files = list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml")) + list(config_dir.glob("*.json"))

        for config_file in config_files:
            is_valid, errors, config_data = self.validate_config_file(config_file)
            results[str(config_file)] = (is_valid, errors)

        return results

    def get_validated_config(self, config_path: Path) -> Optional[Dict[str, Any]]:
        """検証済み設定を取得"""
        return self.validated_configs.get(str(config_path))


# シングルトンインスタンス
_validator: Optional[ConfigValidatorEnhanced] = None


def get_config_validator() -> ConfigValidatorEnhanced:
    """設定検証システムのシングルトン取得"""
    global _validator
    if _validator is None:
        _validator = ConfigValidatorEnhanced()
    return _validator


# ======================================================================
# .env 必須変数チェック
# ======================================================================

# 起動に最低限必要な環境変数
ENV_REQUIRED: List[str] = [
    "COMFYUI_URL",
    "OLLAMA_URL",
]

# セキュア運用で推奨
ENV_RECOMMENDED: List[str] = [
    "MANAOS_INTEGRATION_API_KEY",
    "GITHUB_TOKEN",
    "MRL_MEMORY_API_KEY",
    "API_KEY",
    "REQUIRE_AUTH",
]


def validate_env(
    required: Optional[List[str]] = None,
    recommended: Optional[List[str]] = None,
) -> Tuple[bool, List[ValidationError]]:
    """環境変数の必須 / 推奨チェック.

    Returns:
        (全必須が設定済みか, エラー + 警告リスト)
    """
    import os as _os

    if required is None:
        required = ENV_REQUIRED
    if recommended is None:
        recommended = ENV_RECOMMENDED
    errors: List[ValidationError] = []

    for var in required:
        if not _os.getenv(var):
            errors.append(
                ValidationError(
                    field=var,
                    message=f"必須環境変数 '{var}' が未設定です",
                    severity="error",
                )
            )

    for var in recommended:
        if not _os.getenv(var):
            errors.append(
                ValidationError(
                    field=var,
                    message=f"推奨環境変数 '{var}' が未設定です",
                    severity="warning",
                )
            )

    has_critical = any(e.severity == "error" for e in errors)
    return not has_critical, errors
