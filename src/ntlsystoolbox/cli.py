from __future__ import annotations

import argparse
import os
import sys
import textwrap
from typing import Any, Dict, Optional


# -----------------------------
# UI (sans dépendance externe)
# -----------------------------
def _supports_color() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    return sys.stdout.isatty()


_COLOR = _supports_color()


def _c(s: str, code: str) -> str:
    if not _COLOR:
        return s
    return f"\033[{code}m{s}\033[0m"


def _bold(s: str) -> str:
    return _c(s, "1")


def _dim(s: str) -> str:
    return _c(s, "2")


def _green(s: str) -> str:
    return _c(s, "32")


def _yellow(s: str) -> str:
    return _c(s, "33")


def _red(s: str) -> str:
    return _c(s, "31")


def _cyan(s: str) -> str:
    return _c(s, "36")


def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _hr() -> None:
    print(_dim("─" * 60))


def _title() -> None:
    logo = r"""
 _   _ _______ _        _____           _______          _ _               
| \ | |__   __| |      / ____|         |__   __|        | | |              
|  \| |  | |  | |_____| (___  _   _ ___   | | ___   ___ | | |__   _____  __
| . ` |  | |  | |______\___ \| | | / __|  | |/ _ \ / _ \| | '_ \ / _ \ \/ /
| |\  |  | |  | |      ____) | |_| \__ \  | | (_) | (_) | | |_) | (_) >  < 
|_| \_|  |_|  |_|     |_____/ \__, |___/  |_|\___/ \___/|_|_.__/ \___/_/\_\
                                __/ |                                       
                               |___/                                        
"""
    print(_cyan(logo.rstrip()))
    print(_bold("NTL SysToolbox") + _dim("  •  CLI administration système & réseau"))
    _hr()


# -----------------------------
# Config loader (YAML)
# -----------------------------
def _load_config(path: Optional[str]) -> Dict[str, Any]:
    try:
        import yaml  # dépendance déjà dans ton projet
    except Exception:
        return {}

    candidates: list[str] = []
    if path:
        candidates.append(path)

    env_path = os.getenv("NTL_CONFIG")
    if env_path:
        candidates.append(env_path)

    candidates += [
        "config/config.yml",
        "config.yml",
        "config.example.yml",
        "config/config.example.yml",
    ]

    for p in candidates:
        if p and os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                return data if isinstance(data, dict) else {}
            except Exception:
                return {}

    return {}


# -----------------------------
# Résultats / reports
# -----------------------------
def _handle_result(
    result: Any,
    *,
    json_only: bool,
    quiet: bool,
    verbose: bool,
) -> int:
    """
    Utilise ntlsystoolbox.main.{save_json_report,print_result} si dispo.
    Sinon fallback simple.
    """
    exit_code = int(getattr(result, "exit_code", 0) or 0)

    try:
        from ntlsystoolbox.main import save_json_report, print_result

        json_path = save_json_report(result)
        print_result(
            result,
            json_path=json_path,
            json_only=json_only,
            quiet=quiet,
            verbose=verbose,
        )
        return int(getattr(result, "exit_code", exit_code) or exit_code)
    except Exception:
        # fallback minimal si main.py n'a pas ces helpers
        if json_only:
            print("")
            return exit_code
        if quiet:
            print(f"{getattr(result, 'module', 'module')} {getattr(result, 'status', 'UNKNOWN')}")
            return exit_code
        print(result)
        return exit_code


# -----------------------------
# Appels Modules
# -----------------------------
def _run_diagnostic(cfg: Dict[str, Any]) -> Any:
    from ntlsystoolbox.modules.diagnostic import DiagnosticModule

    return DiagnosticModule(cfg).run()


def _run_backup(cfg: Dict[str, Any]) -> Any:
    from ntlsystoolbox.modules.backup_wms import BackupWMSModule

    return BackupWMSModule(cfg).run()


def _run_obsolescence_interactive(cfg: Dict[str, Any]) -> Any:
    from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule

    return AuditObsolescenceModule(cfg).run()


def _run_obsolescence_scan(cfg: Dict[str, Any], cidr: str) -> Any:
    from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule

    m = AuditObsolescenceModule(cfg)
    if hasattr(m, "run_action"):
        return m.run_action("scan_range", cidr=cidr)

    # fallback si run_action absent
    from ntlsystoolbox.core.result import ModuleResult

    return ModuleResult(
        module="obsolescence",
        status="ERROR",
        summary="Le module n'expose pas run_action('scan_range', ...).",
        details={"expected": "run_action('scan_range', cidr=...)", "cidr": cidr},
    ).finish()


def _run_obsolescence_list_eol(cfg: Dict[str, Any], product: str) -> Any:
    from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule

    m = AuditObsolescenceModule(cfg)
    if hasattr(m, "run_action"):
        return m.run_action("list_versions_eol", product=product)

    from ntlsystoolbox.core.result import ModuleResult

    return ModuleResult(
        module="obsolescence",
        status="ERROR",
        summary="Le module n'expose pas run_action('list_versions_eol', ...).",
        details={"expected": "run_action('list_versions_eol', product=...)", "product": product},
    ).finish()


def _run_obsolescence_csv_report(cfg: Dict[str, Any], csv_path: str, scan: bool, cidr: str) -> Any:
    from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule

    m = AuditObsolescenceModule(cfg)
    if hasattr(m, "run_action"):
        return m.run_action("csv_to_report", csv_path=csv_path, do_scan=scan, cidr=cidr)

    from ntlsystoolbox.core.result import ModuleResult

    return ModuleResult(
        module="obsolescence",
        status="ERROR",
        summary="Le module n'expose pas run_action('csv_to_report', ...).",
        details={"expected": "run_action('csv_to_report', csv_path=..., do_scan=..., cidr=...)", "csv": csv_path},
    ).finish()


# -----------------------------
# Menu interactif (joli + loop)
# -----------------------------
def _pause(msg: str = "Appuie sur Entrée pour continuer...") -> None:
    try:
        input(_dim(msg))
    except KeyboardInterrupt:
        print()
        return


def _menu(cfg: Dict[str, Any]) -> int:
    while True:
        _clear()
        _title()

        print(_bold("Menu principal"))
        print(_dim("Choisis une action :"))
        print()
        print(f"{_bold('1')}  Diagnostic (AD/DNS/MySQL + système)")
        print(f"{_bold('2')}  Backup WMS")
        print(f"{_bold('3')}  Audit obsolescence (menu)")
        print(_dim("—"))
        print(f"{_bold('4')}  Audit obsolescence (scan CIDR direct)")
        print(f"{_bold('5')}  Audit obsolescence (liste EOL produit)")
        print(f"{_bold('6')}  Audit obsolescence (CSV -> rapport)")
        print()
        print(f"{_bold('q')}  Quitter")
        _hr()

        try:
            choice = input("Votre choix > ").strip().lower()
        except KeyboardInterrupt:
            print()
            return 130

        if choice in ("q", "quit", "exit"):
            return 0

        try:
            if choice == "1":
                print(_cyan("\n[•] Lancement Diagnostic…"))
                res = _run_diagnostic(cfg)
                return _handle_result(res, json_only=False, quiet=False, verbose=True)

            if choice == "2":
                print(_cyan("\n[•] Lancement Backup WMS…"))
                res = _run_backup(cfg)
                return _handle_result(res, json_only=False, quiet=False, verbose=True)

            if choice == "3":
                print(_cyan("\n[•] Audit obsolescence (menu)…"))
                res = _run_obsolescence_interactive(cfg)
                return _handle_result(res, json_only=False, quiet=False, verbose=True)

            if choice == "4":
                cidr = input("CIDR (ex: 192.168.10.0/24) > ").strip()
                if not cidr:
                    print(_yellow("CIDR vide."))
                    _pause()
                    continue
                res = _run_obsolescence_scan(cfg, cidr)
                return _handle_result(res, json_only=False, quiet=False, verbose=True)

            if choice == "5":
                product = input("Produit (ex: ubuntu, debian, mysql, python) > ").strip()
                if not product:
                    print(_yellow("Produit vide."))
                    _pause()
                    continue
                res = _run_obsolescence_list_eol(cfg, product)
                return _handle_result(res, json_only=False, quiet=False, verbose=True)

            if choice == "6":
                csv_path = input("Chemin CSV > ").strip()
                if not csv_path:
                    print(_yellow("CSV vide."))
                    _pause()
                    continue
                do_scan = input("Scan réseau aussi ? (y/N) > ").strip().lower() == "y"
                cidr = ""
                if do_scan:
                    cidr = input("CIDR (ex: 192.168.10.0/24) > ").strip()
                    if not cidr:
                        print(_yellow("CIDR obligatoire si scan activé."))
                        _pause()
                        continue
                res = _run_obsolescence_csv_report(cfg, csv_path, do_scan, cidr)
                return _handle_result(res, json_only=False, quiet=False, verbose=T_
cat > src/ntlsystoolbox/cli.py <<'PY'
import os
import sys

def menu_principal():
    os.system('clear')
    print("========================================")
    print("       NTL SysToolbox - MENU           ")
    print("========================================")
    print("1. Diagnostic (AD/DNS/MySQL)")
    print("2. Backup WMS")
    print("3. Audit Obsolescence")
    print("q. Quitter")
    print("========================================")
    
    choix = input("Votre choix > ")
    
    if choix == "1":
        print("\n[!] Lancement du Diagnostic...")
        # C'est ici qu'on appellera tes vrais scripts plus tard
    elif choix == "2":
        print("\n[!] Lancement du Backup...")
    elif choix == "3":
        print("\n[!] Lancement de l'Audit...")
    elif choix.lower() == "q":
        sys.exit()
    else:
        input("Choix invalide. Appuyez sur Entrée...")
        menu_principal()

def main():
    # Si on lance juste 'ntl-systoolbox', on affiche le menu
    if len(sys.argv) == 1:
        menu_principal()
    else:
        # Ici on pourra ajouter la gestion des arguments plus tard
        print("Mode argument détecté (non-interactif)")

if __name__ == "__main__":
    main()
PY
