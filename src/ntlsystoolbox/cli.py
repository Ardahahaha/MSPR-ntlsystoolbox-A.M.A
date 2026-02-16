from __future__ import annotations
import os
import sys
from typing import Any, Dict, Optional
import click
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

def _handle_result(result, ctx_params):
    json_path = save_json_report(result)
    print_result(result, json_path=json_path, **ctx_params)
    return int(result.exit_code or 0)

@click.group()
@click.option("--config", default=None, help="Config YAML")
@click.option("--json-only", is_flag=True, help="Rapport JSON seul")
@click.option("--quiet", is_flag=True, help="Mode silencieux")
@click.option("--verbose", is_flag=True, help="Mode verbeux")
@click.option("--non-interactive", is_flag=True, help="Pas de prompt")
@click.pass_context
def main(ctx, config, json_only, quiet, verbose, non_interactive):
    """NTL SysToolbox - Outil CLI MSPR"""
    if non_interactive:
        os.environ["NTL_NON_INTERACTIVE"] = "1"
    ctx.ensure_object(dict)
    ctx.obj['cfg'] = _load_config(config)
    ctx.obj['params'] = {'json_only': json_only, 'quiet': quiet, 'verbose': verbose}

@main.command()
@click.option('--ip', help='IP du DC')
@click.pass_context
def diagnostic(ctx, ip):
    """Lancement du diagnostic système et réseau"""
    cfg = ctx.obj['cfg']
    if ip: cfg['dc_ip'] = ip
    from ntlsystoolbox.modules.diagnostic import DiagnosticModule
    result = DiagnosticModule(cfg).run()
    sys.exit(_handle_result(result, ctx.obj['params']))

@main.command()
@click.pass_context
def backup_wms(ctx):
    """Sauvegarde de la base WMS"""
    from ntlsystoolbox.modules.backup_wms import BackupWMSModule
    result = BackupWMSModule(ctx.obj['cfg']).run()
    sys.exit(_handle_result(result, ctx.obj['params']))

@main.group()
def audit_obsolescence():
    """Audit des équipements et scan EOL"""
    pass

@audit_obsolescence.command(name="interactive")
@click.pass_context
def audit_interactive(ctx):
    from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule
    result = AuditObsolescenceModule(ctx.obj['cfg']).run()
    sys.exit(_handle_result(result, ctx.obj['params']))

@audit_obsolescence.command(name="scan-range")
@click.option('--cidr', required=True, help="Range IP (ex: 192.168.1.0/24)")
@click.pass_context
def audit_scan(ctx, cidr):
    from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule
    m = AuditObsolescenceModule(ctx.obj['cfg'])
    result = m.run_action("scan_range", cidr=cidr) if hasattr(m, "run_action") else m.scan_range(cidr=cidr)
    sys.exit(_handle_result(result, ctx.obj['params']))

if __name__ == "__main__":
    main()
