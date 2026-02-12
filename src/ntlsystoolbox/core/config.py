# src/ntlsystoolbox/core/config.py
from __future__ import annotations

import os
from typing import Any, Dict

import yaml


def _deep_set(d: Dict[str, Any], keys: list[str], value: Any) -> None:
    cur = d
    for k in keys[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    cur[keys[-1]] = value


def load_config() -> Dict[str, Any]:
    # 1) fichier config.yml (ou NTL_CONFIG)
    path = os.getenv("NTL_CONFIG", "config.yml")
    cfg: Dict[str, Any] = {}

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

    # 2) overrides via variables d'env
    mapping = {
        "NTL_DC01_IP": ("infrastructure", "dc01_ip"),
        "NTL_DC02_IP": ("infrastructure", "dc02_ip"),
        "NTL_WMSDB_IP": ("infrastructure", "wms_db_ip"),
        "NTL_WMSAPP_IP": ("infrastructure", "wms_app_ip"),
        "NTL_DB_HOST": ("database", "host"),
        "NTL_DB_PORT": ("database", "port"),
        "NTL_DB_USER": ("database", "user"),
        "NTL_DB_PASS": ("database", "password"),
        "NTL_DB_NAME": ("database", "name"),
        "NTL_DB_TABLE": ("database", "table"),
        "NTL_SCAN_CIDR": ("audit", "scan_cidr"),
        "NTL_COMPONENTS_CSV": ("audit", "components_csv"),
        "NTL_EOL_SOON_DAYS": ("audit", "eol_soon_days"),
        "NTL_CPU_WARN": ("thresholds", "cpu_warn"),
        "NTL_RAM_WARN": ("thresholds", "ram_warn"),
        "NTL_DISK_WARN": ("thresholds", "disk_warn"),
    }

    for env_key, keys in mapping.items():
        v = os.getenv(env_key)
        if v in (None, ""):
            continue

        # casts simples
        if keys[-1] in ("port", "eol_soon_days"):
            try:
                v = int(v)
            except Exception:
                pass
        if keys[-1] in ("cpu_warn", "ram_warn", "disk_warn"):
            try:
                v = float(v)
            except Exception:
                pass

        _deep_set(cfg, list(keys), v)

    return cfg
