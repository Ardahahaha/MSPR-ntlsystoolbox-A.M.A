# src/ntlsystoolbox/main.py
from __future__ import annotations

import sys
from typing import Any, Dict

from ntlsystoolbox.modules.diagnostic import DiagnosticModule
from ntlsystoolbox.modules.backup_wms import BackupWMSModule
from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule

from ntlsystoolbox.core.result import ModuleResult
from ntlsystoolbox.core.reporting import save_json_report, print_result


def _safe_run(module_name: str, module_obj: Any) -> ModuleResult:
    """
    Exécute un module sans faire crash le CLI.
    Attend un retour ModuleResult. Sinon, renvoie UNKNOWN.
    """
    try:
        res = module_obj.run()
        if isinstance(res, ModuleResult):
            if res.ended_at is None:
                res.finish()
            return res
        # Si un module n'a pas encore été refactor => pas de crash
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
    json_path = save_json_report(result)  # JSON standardisé (status + exit_code)
    print_result(result, json_path=json_path)
    input("\nAppuyez sur Entrée pour revenir au menu...")


def _print_menu() -> None:
    print("\nMENU PRINCIPAL :")
    print(" ────────────────────────────────────────────────────────────────")
    print(" ┌── [1] INFRASTRUCTURE")
    print(" │   ⚡  Diagnostic complet (Ping, CPU, RAM)\n")
    print(" ┌── [2] SAUVEGARDE WMS")
    print(" │   💾  Export SQL & CSV\n")
    print(" ┌── [3] AUDIT OBSOLESCENCE")
    print(" │   ☣   Vérification EOL + Rapport HTML")
    print(" ────────────────────────────────────────────────────────────────")
    print(" [0] ✕ Quitter\n")


def main() -> int:
    # Config: si tu as déjà un loader, mets-le ici.
    # Pour l’instant, on laisse vide (les modules peuvent demander via prompt).
    config: Dict[str, Any] = {}

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
            print("\nLancement de l'Audit d'obsolescence...\n")
            _run_and_report("obsolescence", AuditObsolescenceModule(config))
            continue

        print("\nChoix invalide. Tape 0, 1, 2 ou 3.\n")


if __name__ == "__main__":
    sys.exit(main())
