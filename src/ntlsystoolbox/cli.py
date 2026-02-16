from __future__ import annotations
import os
import sys
from typing import Any, Dict, Optional

import click
import yaml

# Imports internes
from ntlsystoolbox.core.result import ModuleResult
from ntlsystoolbox.main import save_json_report, print_result


def _load_config(path: Optional[str]) -> Dict[str, Any]:
    """Charge la configuration YAML."""
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


def _handle_result(result, ctx_params):
    """Gère la sauvegarde JSON et l'affichage du résultat final."""
    json_path = save_json_report(result)
    print_result(
        result,
        json_path=json_path,
        json_only=ctx_params.get('json_only'),
        quiet=ctx_params.get('quiet'),
        verbose=ctx_params.get('verbose')
    )
    return int(result.exit_code or 0)


@click.group(invoke_without_command=True)
@click.option("--config", default=None, help="Chemin vers le fichier de config YAML.")
@click.option("--json-only", is_flag=True, help="Affiche uniquement le chemin du rapport JSON.")
@click.option("--quiet", is_flag=True, help="Sortie console minimale.")
@click.option("--verbose", is_flag=True, help="Sortie console détaillée.")
@click.option("--non-interactive", is_flag=True, help="Désactive les prompts utilisateur.")
@click.pass_context
def main(ctx, config, json_only, quiet, verbose, non_interactive):
    """NTL SysToolbox - Outil CLI de maintenance et diagnostic (MSPR)."""
    if non_interactive:
        os.environ["NTL_NON_INTERACTIVE"] = "1"

    ctx.ensure_object(dict)
    ctx.obj['cfg'] = _load_config(config)
    ctx.obj['params'] = {
        'json_only': json_only,
        'quiet': quiet,
        'verbose': verbose
    }

    # SI AUCUNE COMMANDE N'EST TAPÉE : ON AFFICHE LE MENU
    if ctx.invoked_subcommand is None:
        click.clear()
        click.secho("=== NTL SysToolbox - Menu Principal ===", fg="cyan", bold=True)
        click.echo("1) Lancer le Diagnostic (AD/DNS/MySQL)")
        click.echo("2) Lancer le Backup WMS")
        click.echo("3) Lancer l'Audit Obsolescence (Interactif)")
        click.echo("q) Quitter")
        
        choix = click.prompt("\nVotre choix", type=str, default="q")
        
        if choix == "1":
            ctx.invoke(diagnostic)
        elif choix == "2":
            ctx.invoke(backup_wms)
        elif choix == "3":
            # On invoque le sous-groupe, puis la commande interactive
            ctx.invoke(audit_interactive)
        elif choix.lower() == "q":
            click.echo("Au revoir !")
            ctx.exit()
        else:
            click.secho("Choix invalide.", fg="red")


@main.command()
@click.option('--ip', help='IP du contrôleur de domaine (AD).')
@click.pass_context
def diagnostic(ctx, ip):
    """Lance les diagnostics (AD, DNS, MySQL, Système)."""
    cfg = ctx.obj['cfg']
    if ip:
        cfg['dc_ip'] = ip
    elif os.environ.get("NTL_NON_INTERACTIVE") != "1":
        # On demande l'IP si elle n'est pas fournie et qu'on est en interactif
        cfg['dc_ip'] = click.prompt("IP du contrôleur de domaine", default="127.0.0.1")

    try:
        from ntlsystoolbox.modules.diagnostic import DiagnosticModule
        result = DiagnosticModule(cfg).run()
    except Exception as e:
        result = ModuleResult(module="diagnostic", status="ERROR", summary=f"Crash: {e}").finish()

    sys.exit(_handle_result(result, ctx.obj['params']))


@main.command()
@click.pass_context
def backup_wms(ctx):
    """Exécute la sauvegarde de la base de données WMS."""
    try:
        from ntlsystoolbox.modules.backup_wms import BackupWMSModule
        result = BackupWMSModule(ctx.obj['cfg']).run()
    except Exception as e:
        result = ModuleResult(module="backup-wms", status="ERROR", summary=f"Crash: {e}").finish()

    sys.exit(_handle_result(result, ctx.obj['params']))


@main.group()
def audit_obsolescence():
    """Module d'audit de fin de vie (EOL) et scan réseau."""
    pass


@audit_obsolescence.command(name="interactive")
@click.pass_context
def audit_interactive(ctx):
    """Lance l'audit obsolescence en mode menu interactif."""
    try:
        from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule
        result = AuditObsolescenceModule(ctx.obj['cfg']).run()
    except Exception as e:
        result = ModuleResult(module="obsolescence", status="ERROR", summary=f"Crash: {e}").finish()

    sys.exit(_handle_result(result, ctx.obj['params']))


@audit_obsolescence.command(name="scan-range")
@click.option('--cidr', required=True, help="Plage réseau à scanner (ex: 192.168.1.0/24).")
@click.pass_context
def audit_scan(ctx, cidr):
    """Scan une plage IP spécifique sans intervention manuelle."""
    try:
        from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule
        m = AuditObsolescenceModule(ctx.obj['cfg'])
        
        if hasattr(m, "run_action"):
            result = m.run_action("scan_range", cidr=cidr)
        elif hasattr(m, "scan_range"):
            result = m.scan_range(cidr=cidr)
        else:
            result = ModuleResult(
                module="obsolescence",
                status="ERROR",
                summary="Action scan-range non trouvée dans le module."
            ).finish()
    except Exception as e:
        result = ModuleResult(module="obsolescence", status="ERROR", summary=f"Crash: {e}").finish()

    sys.exit(_handle_result(result, ctx.obj['params']))


if __name__ == "__main__":
    main()
