from __future__ import annotations

import os
import platform
import socket
import subprocess
from dataclasses import dataclass
from datetime import datetime, date
from typing import Any, Dict, Optional, Tuple, List

import psutil
import pymysql

from ntlsystoolbox.core.result import ModuleResult


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(key)
    return v if v not in (None, "") else default


def _prompt(msg: str, default: Optional[str] = None) -> str:
    # Mode non-interactif : ne demande rien
    if os.getenv("NTL_NON_INTERACTIVE", "0") == "1":
        return default or ""
    suffix = f" [{default}]" if default else ""
    v = input(f"{msg}{suffix} : ").strip()
    return v if v else (default or "")


def _ping(host: str, timeout_s: int = 2) -> bool:
    try:
        if platform.system().lower().startswith("win"):
            cmd = ["ping", "-n", "1", "-w", str(timeout_s * 1000), host]
        else:
            cmd = ["ping", "-c", "1", "-W", str(timeout_s), host]
        r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return r.returncode == 0
    except Exception:
        return False


def _tcp_check(host: str, port: int, timeout_s: float = 2.0) -> Tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True, "OK"
    except Exception as e:
        return False, str(e)


def _read_linux_pretty_os() -> Optional[str]:
    try:
        path = "/etc/os-release"
        if not os.path.exists(path):
            return None
        data = {}
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                data[k] = v.strip().strip('"')
        return data.get("PRETTY_NAME") or data.get("NAME")
    except Exception:
        return None


def _local_system_snapshot() -> Dict[str, Any]:
    hostname = socket.gethostname()
    os_name = platform.system()
    os_release = platform.release()
    os_version = platform.version()
    pretty = _read_linux_pretty_os()

    boot_ts = psutil.boot_time()
    uptime_s = int(datetime.now().timestamp() - boot_ts)

    cpu_percent = psutil.cpu_percent(interval=0.5)
    vm = psutil.virtual_memory()

    disks: List[Dict[str, Any]] = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append(
                {
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": float(usage.percent),
                }
            )
        except Exception:
            continue

    if os_name.lower().startswith("win"):
        root = os.environ.get("SystemDrive", "C:") + "\\"
    else:
        root = "/"
    try:
        root_usage = psutil.disk_usage(root)
        disk_percent = float(root_usage.percent)
    except Exception:
        disk_percent = None

    return {
        "hostname": hostname,
        "os": {
            "system": os_name,
            "release": os_release,
            "version": os_version,
            "pretty_name": pretty,
        },
        "uptime_seconds": uptime_s,
        "cpu_percent": float(cpu_percent),
        "ram_percent": float(vm.percent),
        "ram_total_gb": round(vm.total / (1024**3), 2),
        "disk_system_percent": disk_percent,
        "disks": disks,
    }


@dataclass
class InfraTargets:
    dc01: str
    dc02: str
    wms_db: str
    wms_app: str


class DiagnosticModule:
    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}

    def _load_targets(self) -> InfraTargets:
        infra = self.config.get("infrastructure", {}) if isinstance(self.config, dict) else {}

        dc01_default = _env("NTL_DC01_IP", infra.get("dc01_ip", "192.168.10.10"))
        dc02_default = _env("NTL_DC02_IP", infra.get("dc02_ip", "192.168.10.11"))
        wmsdb_default = _env("NTL_WMSDB_IP", infra.get("wms_db_ip", "192.168.10.21"))
        wmsapp_default = _env("NTL_WMSAPP_IP", infra.get("wms_app_ip", "192.168.10.22"))

        print("\n--- Diagnostic Système ---\n")
        dc01 = _prompt("IP DC01 (AD/DNS)", dc01_default)
        dc02 = _prompt("IP DC02 (AD/DNS)", dc02_default)
        wms_db = _prompt("IP WMS-DB (MySQL)", wmsdb_default)
        wms_app = _prompt("IP WMS-APP (optionnel)", wmsapp_default)

        return InfraTargets(dc01=dc01, dc02=dc02, wms_db=wms_db, wms_app=wms_app)

    def _mysql_check(self, host: str) -> Tuple[bool, str, Optional[str]]:
        db_cfg = self.config.get("database", {}) if isinstance(self.config, dict) else {}

        port = int(_env("NTL_DB_PORT", str(db_cfg.get("port", 3306))) or "3306")
        user = _env("NTL_DB_USER", db_cfg.get("user", "root")) or "root"
        password = _env("NTL_DB_PASS", db_cfg.get("password", "")) or ""
        dbname = _env("NTL_DB_NAME", db_cfg.get("name", "")) or ""

        user = _prompt("MySQL user", user)
        password = _prompt("MySQL password (vide si aucun)", password)
        dbname = _prompt("MySQL database (optionnel)", dbname)

        try:
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=dbname if dbname else None,
                connect_timeout=3,
                read_timeout=3,
                write_timeout=3,
                charset="utf8mb4",
                autocommit=True,
            )
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
                cur.execute("SELECT VERSION()")
                v = cur.fetchone()
                version = v[0] if v else None
            conn.close()
            return True, "OK", version
        except Exception as e:
            return False, str(e), None

    def run(self) -> ModuleResult:
        started = datetime.now().isoformat(timespec="seconds")
        targets = self._load_targets()

        local = _local_system_snapshot()

        ping_dc01 = _ping(targets.dc01)
        ping_dc02 = _ping(targets.dc02)
        ping_wmsdb = _ping(targets.wms_db)
        ping_wmsapp = _ping(targets.wms_app) if targets.wms_app else False

        dc01_dns_ok, dc01_dns_msg = _tcp_check(targets.dc01, 53)
        dc02_dns_ok, dc02_dns_msg = _tcp_check(targets.dc02, 53)

        dc01_krb_ok, dc01_krb_msg = _tcp_check(targets.dc01, 88)
        dc02_krb_ok, dc02_krb_msg = _tcp_check(targets.dc02, 88)

        dc01_ldap_ok, dc01_ldap_msg = _tcp_check(targets.dc01, 389)
        dc02_ldap_ok, dc02_ldap_msg = _tcp_check(targets.dc02, 389)

        dc01_ad_dns_ok = dc01_dns_ok and dc01_krb_ok and dc01_ldap_ok
        dc02_ad_dns_ok = dc02_dns_ok and dc02_krb_ok and dc02_ldap_ok
        ad_dns_ok = dc01_ad_dns_ok or dc02_ad_dns_ok

        print("\nTest MySQL (WMS-DB)...")
        mysql_ok, mysql_msg, mysql_version = self._mysql_check(targets.wms_db)

        thresholds = self.config.get("thresholds", {}) if isinstance(self.config, dict) else {}
        cpu_warn_th = float(_env("NTL_CPU_WARN", str(thresholds.get("cpu_warn", 90))) or "90")
        ram_warn_th = float(_env("NTL_RAM_WARN", str(thresholds.get("ram_warn", 90))) or "90")
        disk_warn_th = float(_env("NTL_DISK_WARN", str(thresholds.get("disk_warn", 90))) or "90")

        cpu_warn = local["cpu_percent"] >= cpu_warn_th
        ram_warn = local["ram_percent"] >= ram_warn_th
        disk_warn = (local["disk_system_percent"] is not None) and (local["disk_system_percent"] >= disk_warn_th)

        status = "SUCCESS"
        if not ad_dns_ok or not mysql_ok:
            status = "ERROR"
        else:
            if dc01_ad_dns_ok != dc02_ad_dns_ok:
                status = "WARNING"
            if cpu_warn or ram_warn or disk_warn:
                status = "WARNING"

        summary = "AD/DNS OK, MySQL OK" if (ad_dns_ok and mysql_ok) else "Problème AD/DNS ou MySQL"

        details: Dict[str, Any] = {
            "targets": {
                "dc01": targets.dc01,
                "dc02": targets.dc02,
                "wms_db": targets.wms_db,
                "wms_app": targets.wms_app,
            },
            "ping": {
                "dc01": ping_dc01,
                "dc02": ping_dc02,
                "wms_db": ping_wmsdb,
                "wms_app": ping_wmsapp,
            },
            "ad_dns": {
                "dc01": {
                    "dns_tcp_53": {"ok": dc01_dns_ok, "msg": dc01_dns_msg},
                    "kerberos_88": {"ok": dc01_krb_ok, "msg": dc01_krb_msg},
                    "ldap_389": {"ok": dc01_ldap_ok, "msg": dc01_ldap_msg},
                    "overall_ok": dc01_ad_dns_ok,
                },
                "dc02": {
                    "dns_tcp_53": {"ok": dc02_dns_ok, "msg": dc02_dns_msg},
                    "kerberos_88": {"ok": dc02_krb_ok, "msg": dc02_krb_msg},
                    "ldap_389": {"ok": dc02_ldap_ok, "msg": dc02_ldap_msg},
                    "overall_ok": dc02_ad_dns_ok,
                },
                "overall_ok": ad_dns_ok,
            },
            "mysql": {
                "ok": mysql_ok,
                "msg": mysql_msg,
                "version": mysql_version,
            },
            "local": local,
            "thresholds": {
                "cpu_warn": cpu_warn_th,
                "ram_warn": ram_warn_th,
                "disk_warn": disk_warn_th,
            },
        }

        return ModuleResult(
            module="diagnostic",
            status=status,
            summary=summary,
            details=details,
            artifacts={},
            started_at=started,
        ).finish()
