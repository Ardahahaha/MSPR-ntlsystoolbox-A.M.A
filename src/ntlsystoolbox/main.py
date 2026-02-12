from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict

from ntlsystoolbox.core.config import load_config
from ntlsystoolbox.core.result import ModuleResult
from ntlsystoolbox.core.reporting import save_json_report, print_result

from ntlsystoolbox.modules.diagnostic import DiagnosticModule
from ntlsystoolbox.modules.backup_wms import BackupWMSModule
from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule


def _emit(result: ModuleResult, pause: bool) -> None:
    if result.ended_at is None:
        result.finish()
    json_path = save_json_report(result)
    print_result(result, json_path=json_path)
    if pause:
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
            summary="Le module n'a pas retourné de ModuleResult.",
            details={"returned_type": type(res).__name__},
        ).finish()
    except Exception as e:
        return ModuleResult(
            module=module_name,
            status="ERROR",
            summary=str(e),
            details={"exception": repr(e)},
        ).finish()


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
            cidr = input(f"CIDR [{default_cidr}] : ").strip() or default_cidr
            _emit(audit.run_action("scan_range", cidr=cidr), pause=True)
            continue

        if a == "2":
            product = input("Produit [ubuntu] : ").strip() or "ubuntu"
            _emit(audit.run_action("list_versions_eol", product=product), pause=True)
            continue

        if a == "3":
            csv_path = input(f"Chemin CSV [{default_csv}] : ").strip() or default_csv
            do_scan = input("Faire aussi un scan réseau ? (y/n) [n] : ").strip().lower().startswith("y")
            cidr = None
            if do_scan:
                cidr = input(f"CIDR [{default_cidr}] : ").strip() or default_cidr

            _emit(audit.run_action("csv_to_report", csv_path=csv_path, do_scan=do_scan, cidr=cidr), pause=True)
            continue

        print("\nChoix invalide.\n")


def interactive_main() -> int:
    config: Dict[str, Any] = load_config()

    while True:
        _print_menu()
        choice = input("ntl-cli > ").strip()

        if choice == "0":
            return 0

        if choice == "1":
            print("\nLancement du Diagnostic...\n")
            _emit(_safe_run("diagnostic", DiagnosticModule(config)), pause=True)
            continue

        if choice == "2":
            print("\nLancement de la Sauvegarde WMS...\n")
            _emit(_safe_run("backup_wms", BackupWMSModule(config)), pause=True)
            continue

        if choice == "3":
            _audit_submenu(config)
            continue

        print("\nChoix invalide. Tape 0, 1, 2 ou 3.\n")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ntl-systoolbox")
    p.add_argument("--config", help="Chemin du fichier config.yml (sinon NTL_CONFIG ou config.yml)")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("menu", help="Force le mode menu interactif")

    diag = sub.add_parser("diagnostic", help="Lancer le diagnostic (non-interactif)")
    diag.add_argument("--dc01")
    diag.add_argument("--dc02")
    diag.add_argument("--wms-db")
    diag.add_argument("--wms-app")
    diag.add_argument("--db-user")
    diag.add_argument("--db-pass")
    diag.add_argument("--db-name")
    diag.add_argument("--db-port", type=int)

    backup = sub.add_parser("backup", help="Lancer la sauvegarde WMS (non-interactif)")
    backup.add_argument("--host")
    backup.add_argument("--port", type=int)
    backup.add_argument("--user")
    backup.add_argument("--pass", dest="password")
    backup.add_argument("--db")
    backup.add_argument("--table")

    audit = sub.add_parser("audit", help="Audit obsolescence (non-interactif)")
    audit_sub = audit.add_subparsers(dest="audit_cmd")

    a_scan = audit_sub.add_parser("scan", help="Scan plage réseau")
    a_scan.add_argument("--cidr", required=True)

    a_list = audit_sub.add_parser("list", help="Lister versions + EOL d’un produit")
    a_list.add_argument("--product", required=True)

    a_report = audit_sub.add_parser("report", help="CSV -> EOL + rapport HTML")
    a_report.add_argument("--csv", required=True)
    a_report.add_argument("--scan", action="store_true")
    a_report.add_argument("--cidr")

    return p


def cli_main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd in (None, "menu"):
        return interactive_main()

    os.environ["NTL_NON_INTERACTIVE"] = "1"

    if args.config:
        os.environ["NTL_CONFIG"] = args.config

    config: Dict[str, Any] = load_config()

    if args.cmd == "diagnostic":
        if args.dc01:
            os.environ["NTL_DC01_IP"] = args.dc01
        if args.dc02:
            os.environ["NTL_DC02_IP"] = args.dc02
        if args.wms_db:
            os.environ["NTL_WMSDB_IP"] = args.wms_db
        if args.wms_app:
            os.environ["NTL_WMSAPP_IP"] = args.wms_app

        if args.db_user:
            os.environ["NTL_DB_USER"] = args.db_user
        if args.db_pass:
            os.environ["NTL_DB_PASS"] = args.db_pass
        if args.db_name:
            os.environ["NTL_DB_NAME"] = args.db_name
        if args.db_port:
            os.environ["NTL_DB_PORT"] = str(args.db_port)

        result = _safe_run("diagnostic", DiagnosticModule(config))
        _emit(result, pause=False)
        return result.exit_code

    if args.cmd == "backup":
        if args.host:
            os.environ["NTL_DB_HOST"] = args.host
        if args.port:
            os.environ["NTL_DB_PORT"] = str(args.port)
        if args.user:
            os.environ["NTL_DB_USER"] = args.user
        if args.password is not None:
            os.environ["NTL_DB_PASS"] = args.password
        if args.db:
            os.environ["NTL_DB_NAME"] = args.db
        if args.table:
            os.environ["NTL_DB_TABLE"] = args.table

        result = _safe_run("backup_wms", BackupWMSModule(config))
        _emit(result, pause=False)
        return result.exit_code

    if args.cmd == "audit":
        audit_mod = AuditObsolescenceModule(config)

        if args.audit_cmd == "scan":
            result = audit_mod.run_action("scan_range", cidr=args.cidr)
            _emit(result, pause=False)
            return result.exit_code

        if args.audit_cmd == "list":
            result = audit_mod.run_action("list_versions_eol", product=args.product)
            _emit(result, pause=False)
            return result.exit_code

        if args.audit_cmd == "report":
            do_scan = bool(args.scan)
            cidr = args.cidr
            if do_scan and not cidr:
                cidr = (config.get("audit", {}) or {}).get("scan_cidr", "")
            result = audit_mod.run_action("csv_to_report", csv_path=args.csv, do_scan=do_scan, cidr=cidr)
            _emit(result, pause=False)
            return result.exit_code

        result = ModuleResult(
            module="obsolescence",
            status="ERROR",
            summary="Sous-commande audit manquante",
            details={},
        ).finish()
        _emit(result, pause=False)
        return result.exit_code

    return 0


def main() -> int:
    if len(sys.argv) == 1:
        return interactive_main()
    return cli_main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
