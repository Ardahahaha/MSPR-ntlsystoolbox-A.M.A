from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ntlsystoolbox.core.result import ModuleResult


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def save_json_report(result: ModuleResult, out_dir: str = "reports/json") -> str:
    """
    Sauvegarde toujours un JSON horodaté (supervision / preuve).
    """
    _ensure_dir(out_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_module = (result.module or "module").replace(" ", "_").lower()
    path = str(Path(out_dir) / f"{safe_module}_{ts}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

    return path


def _p(s: str = "") -> None:
    print(s)


def _kv(k: str, v: Any, indent: int = 0) -> None:
    pad = " " * indent
    _p(f"{pad}- {k}: {v}")


def _print_diagnostic(details: Dict[str, Any]) -> None:
    targets = details.get("targets", {})
    ad = details.get("ad_dns", {})
    mysql = details.get("mysql", {})
    local = details.get("local", {})

    _p("\nDétails clés (Diagnostic) :")
    _kv("DC01", targets.get("dc01"))
    _kv("DC02", targets.get("dc02"))
    _kv("WMS-DB", targets.get("wms_db"))
    _kv("WMS-APP", targets.get("wms_app"))

    _p("\nAD/DNS :")
    _kv("overall_ok", ad.get("overall_ok"))
    for dc in ("dc01", "dc02"):
        dc_obj = ad.get(dc, {})
        _kv(f"{dc}.overall_ok", dc_obj.get("overall_ok"), indent=2)
        _kv(f"{dc}.dns_tcp_53.ok", dc_obj.get("dns_tcp_53", {}).get("ok"), indent=2)
        _kv(f"{dc}.kerberos_88.ok", dc_obj.get("kerberos_88", {}).get("ok"), indent=2)
        _kv(f"{dc}.ldap_389.ok", dc_obj.get("ldap_389", {}).get("ok"), indent=2)

    _p("\nMySQL :")
    _kv("ok", mysql.get("ok"))
    _kv("version", mysql.get("version"))
    if not mysql.get("ok"):
        _kv("error", mysql.get("msg"))

    _p("\nSystème local :")
    _kv("hostname", local.get("hostname"))
    _kv("cpu_percent", local.get("cpu_percent"))
    _kv("ram_percent", local.get("ram_percent"))
    _kv("disk_system_percent", local.get("disk_system_percent"))


def _print_backup(details: Dict[str, Any], artifacts: Dict[str, str]) -> None:
    _p("\nDétails clés (Backup WMS) :")
    _kv("host", details.get("host"))
    _kv("port", details.get("port"))
    _kv("db", details.get("db"))
    _kv("sql", details.get("sql"))
    _kv("csv", details.get("csv"))
    _kv("csv_table", details.get("csv_table"))

    if artifacts:
        _p("\nArtifacts :")
        for k, v in artifacts.items():
            _kv(k, v)


def _print_obsolescence(details: Dict[str, Any], artifacts: Dict[str, str]) -> None:
    action = details.get("action")
    _p("\nDétails clés (Audit obsolescence) :")
    _kv("action", action)

    if action == "scan_range":
        stats = details.get("stats", {})
        inv = details.get("inventory", [])
        _kv("cidr", stats.get("cidr"))
        _kv("found_hosts", stats.get("found_hosts"))
        _kv("ports_checked", stats.get("ports_checked"))
        # Affiche un aperçu
        if inv:
            _p("\nAperçu inventaire (max 10) :")
            for h in inv[:10]:
                _kv("ip", h.get("ip"), indent=2)
                _kv("open_ports", h.get("open_ports"), indent=4)
                _kv("os_guess", h.get("os_guess"), indent=4)

    elif action == "list_versions_eol":
        product = details.get("product")
        rows = details.get("rows", [])
        _kv("product", product)
        _kv("rows_count", len(rows))
        if rows:
            _p("\nAperçu versions (max 12) :")
            for r in rows[:12]:
                _kv("cycle", r.get("cycle"), indent=2)
                _kv("latest", r.get("latest"), indent=4)
                _kv("eol", r.get("eol_date") or r.get("eol"), indent=4)
                _kv("status", r.get("support_status"), indent=4)

    elif action == "csv_to_eol_and_report":
        report = details.get("report", {})
        scan = details.get("scan", {})
        counts = (report.get("counts") or {})
        _kv("csv_path", details.get("csv_path"))
        _kv("scan_enabled", scan.get("enabled"))
        _kv("inventory_count", scan.get("inventory_count"))
        _kv("OK", counts.get("OK"))
        _kv("SOON", counts.get("SOON"))
        _kv("EOL", counts.get("EOL"))
        _kv("UNKNOWN", counts.get("UNKNOWN"))

    if artifacts:
        _p("\nArtifacts :")
        for k, v in artifacts.items():
            _kv(k, v)


def print_result(
    result: ModuleResult,
    json_path: Optional[str] = None,
    *,
    json_only: bool = False,
    quiet: bool = False,
    verbose: bool = False,
) -> None:
    """
    - json_only=True  => affiche uniquement le chemin du JSON (utile pour scripts)
    - quiet=True      => une ligne compacte
    - verbose=True    => affiche des détails clés par module
    """
    if json_only:
        print(json_path or "")
        return

    if quiet:
        print(f"{result.module} {result.status} - {result.summary}" + (f" | {json_path}" if json_path else ""))
        return

    _p("\n==============================")
    _p(f"MODULE   : {result.module}")
    _p(f"STATUT   : {result.status} (exit_code={result.exit_code})")
    _p(f"RÉSUMÉ   : {result.summary}")
    if json_path:
        _p(f"JSON     : {json_path}")
    _p("==============================")

    if verbose:
        try:
            if result.module == "diagnostic":
                _print_diagnostic(result.details or {})
            elif result.module == "backup_wms":
                _print_backup(result.details or {}, result.artifacts or {})
            elif result.module == "obsolescence":
                _print_obsolescence(result.details or {}, result.artifacts or {})
            else:
                _p("\nDétails :")
                _p(json.dumps(result.details or {}, indent=2, ensure_ascii=False))
        except Exception:
            # fallback si un détail casse l'affichage
            _p("\nDétails :")
            _p(json.dumps(result.details or {}, indent=2, ensure_ascii=False))
