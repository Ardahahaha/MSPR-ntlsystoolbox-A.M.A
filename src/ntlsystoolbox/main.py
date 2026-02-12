# src/ntlsystoolbox/main.py
from __future__ import annotations

import sys
from typing import Any, Dict

from ntlsystoolbox.modules.diagnostic import DiagnosticModule
from ntlsystoolbox.modules.backup_wms import BackupWMSModule
from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule

from ntlsystoolbox.core.config import load_config
from ntlsystoolbox.core.result import ModuleResult
from ntlsystoolbox.core.reporting import save_json_report, print_result


def _run_result(result: ModuleResult) -> None:
    if result.ended_at is None:
        result.finish()
    json_path = save_json_report(result)
    print_result(result, json_path=json_path)
    input("\nAppuyez sur Entrée pour revenir au menu...")


def _safe_run(module_name: str, module_obj: Any) -> ModuleResult:
    try:
        res = module_obj.run()
        if isinstance(res, ModuleResult):
            if res.ended_at is None:
                res.finish()
            return res
        return ModuleResult(
            module=module_name,
            status="UNKNOWN",
            summary="Le module n'a pas retourné de ModuleResult (refactor non appliqué).",
            details={"returned_type": type(res).__name__},
        ).finish()
    except Exception as e:
        return ModuleResult(
            module=module_name,
            status="ERROR",
            summary=str(e),
            details={"exception": repr(e)},
        ).finish()


def _run_and_report(module_name: str, module_obj: Any) -> None:
    result = _safe_run(module_name, module_obj)
    _run_result(result)


def _print_menu() -> None:
    print("\nMENU PRINCIPAL :")
    print(" ────────────────────────────────────────────────────────────────")
    print(" ┌── [1] INFRASTRUCTURE")
    print(" │   ⚡  Diagnostic complet (AD/DNS, MySQL, CPU/RAM/Disk)\n")
    print(" ┌── [2] SAUVEGARDE WMS")
    print(" │   💾  Export SQL & CSV\n")
    print(" ┌── [3] AUDIT OBSOLESCENCE")
    print(" │   ☣   Scan / Versions EOL / CSV->Rapport HTML")
    print(" ────────────────────────────────────────────────────────────────")
    print(" [0] ✕ Quitter\n")


def _audit_submenu(config: Dict[str, Any]) -> None:
    audit_cfg = config.get("audit", {}) if isinstance(config, dict) else {}
    default_cidr = audit_cfg.get("scan_cidr", "192.168.10.0/24")
    default_csv = audit_cfg.get("components_csv", "inputs/components.csv")

    audit = AuditObsolescenceModule(config)

    while True:
        print("\nAUDIT OBSOLESCENCE :")
        print(" [1] Scanner une plage réseau")
        print(" [2] Lister versions + EOL d’un produit/OS")
        print(" [3] Import CSV + Générer rapport HTML")
        print(" [0] Retour\n")

        a = input("audit > ").strip()

        if a == "0":
            return

        if a == "1":
            cidr = input(f"CIDR (ex: 192.168.10.0/24) [{default_cidr}] : ").strip() or default_cidr
            result = audit.run_action("scan_range", cidr=cidr)
            _run_result(result)
            continue

        if a == "2":
            product = input("Produit (ubuntu/debian/windows/mysql/python...) [ubuntu] : ").strip() or "ubuntu"
            result = audit.run_action("list_versions_eol", product=product)
            _run_result(result)
            continue

        if a == "3":
            csv_path = input(f"Chemin CSV [{default_csv}] : ").strip() or default_csv
            do_scan = (input("Faire aussi un scan réseau ? (y/n) [n] : ").strip().lower().startswith("y"))
            cidr = None
            if do_scan:
                cidr = input(f"CIDR [{default_cidr}] : ").strip() or default_cidr

            result = audit.run_action("csv_to_report", csv_path=csv_path, do_scan=do_scan, cidr=cidr)
            _run_result(result)
            continue

        print("\nChoix invalide.\n")


def main() -> int:
    config: Dict[str, Any] = load_config()

    while True:
        _print_menu()
        choice = input("ntl-cli > ").strip()

        if choice == "0":
            return 0

        if choice == "1":
            print("\nLancement du Diagnostic...\n")
            _run_and_report("diagnostic", DiagnosticModule(config))
            continue

        if choice == "2":
            print("\nLancement de la Sauvegarde WMS...\n")
            _run_and_report("backup_wms", BackupWMSModule(config))
            continue

        if choice == "3":
            _audit_submenu(config)
            continue

        print("\nChoix invalide. Tape 0, 1, 2 ou 3.\n")


if __name__ == "__main__":
    sys.exit(main())
