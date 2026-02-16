cat > src/ntlsystoolbox/cli.py <<'PY'
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, Optional

import yaml

from ntlsystoolbox.core.result import ModuleResult
from ntlsystoolbox.main import save_json_report, print_result


def _load_config(path: Optional[str]) -> Dict[str, Any]:
    if path is None:
        for p in ("config/config.yml", "config.yml"):
            if os.path.exists(p):
                path = p
                break
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def main(argv: Optional[list[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    p = argparse.ArgumentParser(prog="ntl-systoolbox")
    p.add_argument("--config", default=None, help="Chemin config YAML (optionnel)")
    p.add_argument("--json-only", action="store_true", help="Affiche uniquement le chemin du JSON")
    p.add_argument("--quiet", action="store_true", help="Sortie compacte")
    p.add_argument("--verbose", action="store_true", help="Détails")
    p.add_argument("--non-interactive", action="store_true", help="Désactive les prompts (NTL_NON_INTERACTIVE=1)")

    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("diagnostic")
    sub.add_parser("backup-wms")

    ao = sub.add_parser("audit-obsolescence")
    ao_sub = ao.add_subparsers(dest="action", required=True)
    ao_sub.add_parser("interactive")
    sc = ao_sub.add_parser("scan-range")
    sc.add_argument("--cidr", required=True)

    ns = p.parse_args(argv)

    if ns.non_interactive:
        os.environ["NTL_NON_INTERACTIVE"] = "1"

    cfg = _load_config(ns.config)

    try:
        if ns.cmd == "diagnostic":
            from ntlsystoolbox.modules.diagnostic import DiagnosticModule
            result = DiagnosticModule(cfg).run()

        elif ns.cmd == "backup-wms":
            from ntlsystoolbox.modules.backup_wms import BackupWMSModule
            result = BackupWMSModule(cfg).run()

        elif ns.cmd == "audit-obsolescence":
            from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule
            m = AuditObsolescenceModule(cfg)

            if ns.action == "interactive":
                result = m.run()
            elif ns.action == "scan-range":
                # ton module a déjà un menu, mais on appelle l'action directement si disponible
                if hasattr(m, "run_action"):
                    result = m.run_action("scan_range", cidr=ns.cidr)
                elif hasattr(m, "scan_range"):
                    result = m.scan_range(cidr=ns.cidr)
                else:
                    result = ModuleResult(
                        module="obsolescence",
                        status="ERROR",
                        summary="Action scan-range non disponible dans le module",
                        details={"expected": "run_action('scan_range', cidr=...) ou scan_range(...)"},
                    ).finish()
            else:
                result = ModuleResult(
                    module="obsolescence",
                    status="ERROR",
                    summary=f"Action inconnue: {ns.action}",
                ).finish()
        else:
            result = ModuleResult(module="cli", status="ERROR", summary=f"Commande inconnue: {ns.cmd}").finish()

    except Exception as e:
        result = ModuleResult(module="cli", status="ERROR", summary=f"Crash: {e}").finish()

    json_path = save_json_report(result)
    print_result(result, json_path=json_path, json_only=ns.json_only, quiet=ns.quiet, verbose=ns.verbose)
    return int(result.exit_code or 0)


if __name__ == "__main__":
    raise SystemExit(main())
PY
