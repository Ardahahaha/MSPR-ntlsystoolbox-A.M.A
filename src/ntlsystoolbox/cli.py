cat > src/ntlsystoolbox/cli.py <<'PY'
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
import textwrap
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


# ============================================================
#  UI (ANSI) – 0 dépendance, style "premium"
# ============================================================
def _isatty() -> bool:
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def _env_true(name: str) -> bool:
    v = os.getenv(name, "").strip().lower()
    return v in ("1", "true", "yes", "y", "on")


@dataclass
class UI:
    color: bool = True
    use_256: bool = True

    def __post_init__(self) -> None:
        if os.getenv("NO_COLOR"):
            self.color = False
        if not _isatty():
            self.color = False
        term = os.getenv("TERM", "")
        if "256color" not in term and "xterm" not in term:
            self.use_256 = False

    def clear(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def _wrap(self, s: str, code: str) -> str:
        if not self.color:
            return s
        return f"\033[{code}m{s}\033[0m"

    def bold(self, s: str) -> str:
        return self._wrap(s, "1")

    def dim(self, s: str) -> str:
        return self._wrap(s, "2")

    def red(self, s: str) -> str:
        return self._wrap(s, "31")

    def green(self, s: str) -> str:
        return self._wrap(s, "32")

    def yellow(self, s: str) -> str:
        return self._wrap(s, "33")

    def cyan(self, s: str) -> str:
        return self._wrap(s, "36")

    def gray(self, s: str) -> str:
        return self._wrap(s, "90")

    def c256(self, s: str, color_256: int) -> str:
        if not self.color or not self.use_256:
            return s
        return f"\033[38;5;{color_256}m{s}\033[0m"

    def hr(self) -> None:
        print(self.dim("─" * 74))

    def badge(self, label: str, tone: str = "info") -> str:
        # tones: info/success/warn/error/neutral
        if not self.color:
            return f"[{label}]"
        if tone == "success":
            return self.c256(f" {label} ", 48)
        if tone == "warn":
            return self.c256(f" {label} ", 214)
        if tone == "error":
            return self.c256(f" {label} ", 196)
        if tone == "neutral":
            return self.c256(f" {label} ", 245)
        return self.c256(f" {label} ", 39)

    def title_block(self, version: str, cfg_hint: str, non_interactive: bool) -> None:
        # Gradient-ish title (256 colors)
        lines = [
            "███╗   ██╗████████╗██╗          ███████╗██╗   ██╗███████╗████████╗ ██████╗  ██████╗ ██╗     ██████╗  ██████╗ ██╗  ██╗",
            "████╗  ██║╚══██╔══╝██║          ██╔════╝╚██╗ ██╔╝██╔════╝╚══██╔══╝██╔═══██╗██╔═══██╗██║     ██╔══██╗██╔═══██╗╚██╗██╔╝",
            "██╔██╗ ██║   ██║   ██║          ███████╗ ╚████╔╝ ███████╗   ██║   ██║   ██║██║   ██║██║     ██████╔╝██║   ██║ ╚███╔╝ ",
            "██║╚██╗██║   ██║   ██║          ╚════██║  ╚██╔╝  ╚════██║   ██║   ██║   ██║██║   ██║██║     ██╔══██╗██║   ██║ ██╔██╗ ",
            "██║ ╚████║   ██║   ███████╗      ███████║   ██║   ███████║   ██║   ╚██████╔╝╚██████╔╝███████╗██████╔╝╚██████╔╝██╔╝ ██╗",
            "╚═╝  ╚═══╝   ╚═╝   ╚══════╝      ╚══════╝   ╚═╝   ╚══════╝   ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝",
        ]

        if self.color and self.use_256:
            palette = [39, 45, 51, 87, 123, 159]
            for i, ln in enumerate(lines):
                c = palette[i % len(palette)]
                print(self.c256(ln, c))
        else:
            print("\n".join(lines))

        self.hr()
        ni = self.badge("NON-INTERACTIVE", "warn") if non_interactive else self.badge("INTERACTIVE", "success")
        print(
            f"{self.bold('NTL SysToolbox')} {self.dim('•')} v{version}  {ni}  "
            f"{self.badge('JSON reports', 'neutral')} {self.dim('→')} {cfg_hint}"
        )
        self.hr()


_UI = UI()


# ============================================================
#  Defaults (MSPR / NTL)
# ============================================================
DEFAULTS: Dict[str, Any] = {
    "infrastructure": {
        "dc01_ip": "192.168.10.10",
        "dc02_ip": "192.168.10.11",
        "wms_db_ip": "192.168.10.21",
        "wms_app_ip": "192.168.10.22",
        "supervision_ip": "192.168.10.50",
        "ipbx_ip": "192.168.10.40",
    },
    "networks": {
        "siege": "192.168.10.0/24",
        "wh1": "192.168.20.0/24",
        "wh2": "192.168.30.0/24",
        "wh3": "192.168.40.0/24",
        "cdk": "192.168.50.0/24",
    },
    "database": {
        "host": "192.168.10.21",
        "port": 3306,
        "user": "root",
        "password": "",
        "name": "wms",
        "table": "",
    },
    "thresholds": {"cpu_warn": 90, "ram_warn": 90, "disk_warn": 90},
}


# ============================================================
#  Config loader
# ============================================================
def _load_config(path: Optional[str]) -> Tuple[Dict[str, Any], str]:
    try:
        import yaml  # type: ignore
    except Exception:
        return {}, "(pyyaml manquant)"

    candidates: list[str] = []
    if path:
        candidates.append(path)

    env_path = os.getenv("NTL_CONFIG")
    if env_path:
        candidates.append(env_path)

    candidates += [
        "config/config.yml",
        "config.yml",
        "config/config.yaml",
        "config.yaml",
        "config.example.yml",
        "config/config.example.yml",
    ]

    for p in candidates:
        if p and os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                return (data if isinstance(data, dict) else {}), p
            except Exception:
                return {}, p

    return {}, "(aucun fichier config trouvé)"


def _deep_get(cfg: Dict[str, Any], path: str, default: Any = "") -> Any:
    cur: Any = cfg
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _merge_defaults(cfg: Dict[str, Any]) -> Dict[str, Any]:
    # merge simple (DEFAULTS -> cfg override)
    out = json.loads(json.dumps(DEFAULTS))
    for k, v in cfg.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    return out


# ============================================================
#  Reports helpers (fallback + main.py if present)
# ============================================================
def _handle_result(result: Any, *, json_only: bool, quiet: bool, verbose: bool) -> int:
    exit_code = int(getattr(result, "exit_code", 0) or 0)

    # Prefer your project's helpers if they exist
    try:
        from ntlsystoolbox.main import save_json_report, print_result  # type: ignore

        json_path = save_json_report(result)
        print_result(result, json_path=json_path, json_only=json_only, quiet=quiet, verbose=verbose)
        return int(getattr(result, "exit_code", exit_code) or exit_code)
    except Exception:
        # fallback: print minimal and still return code
        if json_only:
            print("")
            return exit_code
        if quiet:
            print(f"{getattr(result, 'module', 'module')} {getattr(result, 'status', 'UNKNOWN')}")
            return exit_code

        print(_UI.bold("Résultat :"))
        print(result)
        return exit_code


def _list_reports(limit: int = 10) -> list[Path]:
    p = Path("reports/json")
    if not p.exists():
        return []
    files = sorted(p.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    return files[:limit]


# ============================================================
#  Prompts (jolis + defaults)
# ============================================================
def _ask(prompt: str, default: str = "", *, secret: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    try:
        if secret:
            # no getpass (SSH + compat), simple fallback
            v = input(f"{prompt}{suffix} : ").strip()
        else:
            v = input(f"{prompt}{suffix} : ").strip()
    except KeyboardInterrupt:
        print()
        return default
    return v if v else default


def _ask_choice(title: str, choices: Dict[str, str], *, default_key: str = "") -> str:
    # choices: key -> label
    print(_UI.bold(title))
    for k, label in choices.items():
        mark = _UI.c256("▶", 39) if k == default_key else " "
        print(f"  {mark} {_UI.bold(k)}  {label}")
    _UI.hr()
    v = _ask("Choix", default_key).lower()
    return v


def _valid_cidr(s: str) -> bool:
    return bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}\/\d{1,2}$", s.strip()))


# ============================================================
#  Module calls
# ============================================================
def _run_diagnostic(cfg: Dict[str, Any]) -> Any:
    from ntlsystoolbox.modules.diagnostic import DiagnosticModule  # type: ignore
    return DiagnosticModule(cfg).run()


def _run_backup(cfg: Dict[str, Any]) -> Any:
    from ntlsystoolbox.modules.backup_wms import BackupWMSModule  # type: ignore
    return BackupWMSModule(cfg).run()


def _run_obso(cfg: Dict[str, Any]) -> Any:
    from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule  # type: ignore
    return AuditObsolescenceModule(cfg).run()


def _run_obso_action(cfg: Dict[str, Any], action: str, **kwargs: Any) -> Any:
    from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule  # type: ignore
    m = AuditObsolescenceModule(cfg)

    if hasattr(m, "run_action"):
        return m.run_action(action, **kwargs)

    from ntlsystoolbox.core.result import ModuleResult  # type: ignore
    return ModuleResult(
        module="obsolescence",
        status="ERROR",
        summary="run_action() manquant dans le module (action non disponible sans menu).",
        details={"expected": "AuditObsolescenceModule.run_action(action, **kwargs)", "action": action, "kwargs": kwargs},
    ).finish()


# ============================================================
#  Menu (style “de fou”)
# ============================================================
def _about_screen(cfg_path: str, cfg: Dict[str, Any]) -> None:
    _UI.clear()
    _UI.title_block(version=_get_version(), cfg_hint=cfg_path, non_interactive=_env_true("NTL_NON_INTERACTIVE"))
    print(_UI.bold("À propos / Infos runtime"))
    print()

    info = {
        "OS": f"{platform.system()} {platform.release()}",
        "Python": sys.version.split()[0],
        "Repo": str(Path.cwd()),
        "Config": cfg_path,
        "Reports": str(Path("reports/json").resolve()),
        "NTL_NON_INTERACTIVE": os.getenv("NTL_NON_INTERACTIVE", "(unset)"),
    }

    for k, v in info.items():
        print(f"  {_UI.c256(k + ':', 245)} {v}")

    _UI.hr()
    print(_UI.bold("Rappels MSPR (sorties attendues)"))
    print(_UI.dim("• sorties lisibles + JSON horodaté + codes retour supervisables"))
    print(_UI.dim("• menu CLI interactif + collecte des arguments nécessaires"))
    _UI.hr()
    _pause()


def _pause(msg: str = "Appuie sur Entrée pour continuer…") -> None:
    try:
        input(_UI.dim(msg))
    except KeyboardInterrupt:
        print()
        return


def _show_reports() -> None:
    _UI.clear()
    _UI.title_block(version=_get_version(), cfg_hint=str(Path("reports/json").resolve()), non_interactive=_env_true("NTL_NON_INTERACTIVE"))
    print(_UI.bold("Derniers rapports JSON"))
    print()
    files = _list_reports(12)
    if not files:
        print(_UI.yellow("Aucun rapport trouvé (reports/json/*.json). Lance un module d’abord."))
        _pause()
        return

    for i, f in enumerate(files, 1):
        ts = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"  {_UI.bold(str(i).rjust(2))}  {_UI.c256(ts, 245)}  {_UI.cyan(f.name)}")

    _UI.hr()
    idx = _ask("Ouvrir un fichier (numéro) ou Entrée pour retour", "").strip()
    if not idx:
        return
    try:
        n = int(idx)
        target = files[n - 1]
    except Exception:
        print(_UI.yellow("Numéro invalide."))
        _pause()
        return

    print()
    print(_UI.bold(f"Contenu (aperçu) : {target.name}"))
    _UI.hr()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        print(json.dumps(data, indent=2, ensure_ascii=False)[:4000])
        if len(json.dumps(data, ensure_ascii=False)) > 4000:
            print(_UI.dim("\n(aperçu tronqué)"))
    except Exception as e:
        print(_UI.red(f"Impossible de lire JSON: {e}"))
    _pause()


def _config_wizard(cfg_path: str) -> None:
    _UI.clear()
    _UI.title_block(version=_get_version(), cfg_hint=cfg_path, non_interactive=_env_true("NTL_NON_INTERACTIVE"))
    print(_UI.bold("Config Wizard (rapide)"))
    print(_UI.dim("Génère/écrase un fichier config YAML minimal pour éviter les prompts."))
    _UI.hr()

    target = "config/config.yml"
    overwrite = _ask("Écraser si existe ? (y/N)", "n").lower() == "y"

    p = Path(target)
    if p.exists() and not overwrite:
        print(_UI.yellow(f"{target} existe déjà. Rien fait."))
        _pause()
        return

    p.parent.mkdir(parents=True, exist_ok=True)

    # prompt minimal, avec defaults NTL
    dc01 = _ask("DC01 IP (AD/DNS)", DEFAULTS["infrastructure"]["dc01_ip"])
    dc02 = _ask("DC02 IP (AD/DNS)", DEFAULTS["infrastructure"]["dc02_ip"])
    wms_db = _ask("WMS-DB IP (MySQL)", DEFAULTS["infrastructure"]["wms_db_ip"])
    wms_app = _ask("WMS-APP IP", DEFAULTS["infrastructure"]["wms_app_ip"])
    mysql_user = _ask("MySQL user", DEFAULTS["database"]["user"])
    mysql_pass = _ask("MySQL password (vide si aucun)", DEFAULTS["database"]["password"])
    mysql_db = _ask("MySQL database", DEFAULTS["database"]["name"])
    cidr = _ask("CIDR scan par défaut (audit)", DEFAULTS["networks"]["siege"])
    if cidr and not _valid_cidr(cidr):
        print(_UI.yellow("CIDR invalide, je mets le défaut siège."))
        cidr = DEFAULTS["networks"]["siege"]

    cfg = {
        "infrastructure": {
            "dc01_ip": dc01,
            "dc02_ip": dc02,
            "wms_db_ip": wms_db,
            "wms_app_ip": wms_app,
        },
        "database": {
            "host": wms_db,
            "port": 3306,
            "user": mysql_user,
            "password": mysql_pass,
            "name": mysql_db,
        },
        "networks": {"default_scan": cidr},
        "thresholds": DEFAULTS["thresholds"],
    }

    try:
        import yaml  # type: ignore

        p.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
        print(_UI.green(f"OK → {target} écrit."))
    except Exception as e:
        print(_UI.red(f"Échec écriture config: {e}"))

    _pause()


def _doctor(cfg_path: str, cfg: Dict[str, Any]) -> None:
    _UI.clear()
    _UI.title_block(version=_get_version(), cfg_hint=cfg_path, non_interactive=_env_true("NTL_NON_INTERACTIVE"))
    print(_UI.bold("Doctor (sanity check)"))
    _UI.hr()

    checks = []

    # config
    checks.append(("Config chargée", "OK" if cfg else "VIDE", "warn" if not cfg else "success"))

    # modules import
    def _check_import(name: str) -> Tuple[str, str, str]:
        try:
            __import__(name)
            return name, "OK", "success"
        except Exception as e:
            return name, f"KO ({e.__class__.__name__})", "error"

    for mod in (
        "ntlsystoolbox.modules.diagnostic",
        "ntlsystoolbox.modules.backup_wms",
        "ntlsystoolbox.modules.audit_obsolescence",
    ):
        checks.append(_check_import(mod))

    # reports dir
    rp = Path("reports/json")
    checks.append(("reports/json", "OK" if rp.exists() else "ABSENT", "warn" if not rp.exists() else "success"))

    for name, status, tone in checks:
        print(f"  {_UI.badge(status, tone)}  {_UI.bold(name)}")

    _UI.hr()
    print(_UI.dim("Si un import est KO: packaging/paths ou fichier manquant dans src/ntlsystoolbox/."))
    _pause()


def _menu(cfg_path: str, cfg_raw: Dict[str, Any]) -> int:
    cfg = _merge_defaults(cfg_raw)
    non_interactive = _env_true("NTL_NON_INTERACTIVE")

    while True:
        _UI.clear()
        _UI.title_block(version=_get_version(), cfg_hint=cfg_path, non_interactive=non_interactive)

        # mini status
        dc01 = _deep_get(cfg, "infrastructure.dc01_ip", DEFAULTS["infrastructure"]["dc01_ip"])
        dc02 = _deep_get(cfg, "infrastructure.dc02_ip", DEFAULTS["infrastructure"]["dc02_ip"])
        wms_db = _deep_get(cfg, "infrastructure.wms_db_ip", DEFAULTS["infrastructure"]["wms_db_ip"])
        wms_app = _deep_get(cfg, "infrastructure.wms_app_ip", DEFAULTS["infrastructure"]["wms_app_ip"])
        default_scan = _deep_get(cfg, "networks.default_scan", DEFAULTS["networks"]["siege"])

        print(_UI.bold("Targets (résumé)"))
        print(
            f"  {_UI.badge('AD/DNS', 'neutral')} DC01={_UI.cyan(dc01)}  DC02={_UI.cyan(dc02)}"
            f"    {_UI.badge('WMS', 'neutral')} DB={_UI.cyan(wms_db)}  APP={_UI.cyan(wms_app)}"
        )
        print(f"  {_UI.badge('SCAN', 'neutral')} default CIDR={_UI.cyan(default_scan)}")
        _UI.hr()

        print(_UI.bold("Modules"))
        print(f"  {_UI.bold('1')}  { _UI.c256('Diagnostic', 87) }        {_UI.dim('AD/DNS + MySQL + état serveur')}")
        print(f"  {_UI.bold('2')}  { _UI.c256('Backup WMS', 87) }       {_UI.dim('dump SQL + export CSV table')}")
        print(f"  {_UI.bold('3')}  { _UI.c256('Audit Obsolescence', 87) } {_UI.dim('menu interactif complet')}")
        _UI.hr()

        print(_UI.bold("Quick actions"))
        print(f"  {_UI.bold('4')}  Scan réseau (CIDR)      {_UI.dim('audit-obsolescence scan-range')}")
        print(f"  {_UI.bold('5')}  Lister EOL (produit)    {_UI.dim('audit-obsolescence list-eol')}")
        print(f"  {_UI.bold('6')}  CSV → Rapport           {_UI.dim('audit-obsolescence csv-report')}")
        _UI.hr()

        print(_UI.bold("Tools"))
        print(f"  {_UI.bold('7')}  Reports JSON            {_UI.dim('voir les derniers rapports générés')}")
        print(f"  {_UI.bold('8')}  Config Wizard           {_UI.dim('générer config/config.yml')}")
        print(f"  {_UI.bold('9')}  Doctor                 {_UI.dim('check imports + config + reports')}")
        print(f"  {_UI.bold('a')}  About                  {_UI.dim('infos runtime + exigences MSPR')}")
        print()
        print(f"  {_UI.bold('q')}  Quitter")
        _UI.hr()

        choice = _ask("Votre choix", "").strip().lower()

        try:
            if choice in ("q", "quit", "exit"):
                return 0

            if choice == "1":
                print(_UI.cyan("\n[•] Lancement Diagnostic…"))
                res = _run_diagnostic(cfg)
                code = _handle_result(res, json_only=False, quiet=False, verbose=True)
                _pause()
                return code

            if choice == "2":
                print(_UI.cyan("\n[•] Lancement Backup WMS…"))
                res = _run_backup(cfg)
                code = _handle_result(res, json_only=False, quiet=False, verbose=True)
                _pause()
                return code

            if choice == "3":
                print(_UI.cyan("\n[•] Audit Obsolescence (menu)…"))
                res = _run_obso(cfg)
                code = _handle_result(res, json_only=False, quiet=False, verbose=True)
                _pause()
                return code

            if choice == "4":
                cidr = _ask("CIDR (ex: 192.168.10.0/24)", default_scan)
                if not _valid_cidr(cidr):
                    print(_UI.yellow("CIDR invalide."))
                    _pause()
                    continue
                print(_UI.cyan(f"\n[•] Scan réseau {cidr}…"))
                res = _run_obso_action(cfg, "scan_range", cidr=cidr)
                code = _handle_result(res, json_only=False, quiet=False, verbose=True)
                _pause()
                return code

            if choice == "5":
                product = _ask("Produit (ex: ubuntu, debian, mysql, windows)", "ubuntu")
                print(_UI.cyan(f"\n[•] Liste EOL pour {product}…"))
                res = _run_obso_action(cfg, "list_versions_eol", product=product)
                code = _handle_result(res, json_only=False, quiet=False, verbose=True)
                _pause()
                return code

            if choice == "6":
                csv_path = _ask("Chemin CSV (ex: inputs/components.csv)", "inputs/components.csv")
                do_scan = _ask("Scan réseau aussi ? (y/N)", "n").lower() == "y"
                cidr = ""
                if do_scan:
                    cidr = _ask("CIDR", default_scan)
                    if not _valid_cidr(cidr):
                        print(_UI.yellow("CIDR invalide."))
                        _pause()
                        continue
                print(_UI.cyan("\n[•] Génération rapport…"))
                res = _run_obso_action(cfg, "csv_to_report", csv_path=csv_path, do_scan=do_scan, cidr=cidr)
                code = _handle_result(res, json_only=False, quiet=False, verbose=True)
                _pause()
                return code

            if choice == "7":
                _show_reports()
                continue

            if choice == "8":
                _config_wizard(cfg_path)
                # reload config after wizard
                cfg_raw2, cfg_path2 = _load_config(None)
                cfg = _merge_defaults(cfg_raw2)
                cfg_path = cfg_path2
                continue

            if choice == "9":
                _doctor(cfg_path, cfg_raw)
                continue

            if choice == "a":
                _about_screen(cfg_path, cfg_raw)
                continue

            print(_UI.yellow("Choix invalide."))
            _pause()
        except KeyboardInterrupt:
            print(_UI.yellow("\nInterrompu."))
            _pause()
        except Exception as e:
            print(_UI.red(f"\nErreur: {e}"))
            _pause()


# ============================================================
#  Argparse (non-interactif)
# ============================================================
def _get_version() -> str:
    try:
        from ntlsystoolbox import __version__  # type: ignore
        return str(__version__)
    except Exception:
        return "1.0.0"


def _build_parser() -> argparse.ArgumentParser:
    epilog = textwrap.dedent(
        """
        Exemples:
          ntl-systoolbox
          ntl-systoolbox diagnostic --config config/config.yml
          ntl-systoolbox backup-wms --non-interactive --config config/config.yml
          ntl-systoolbox audit-obsolescence scan-range --cidr 192.168.10.0/24
        """
    ).strip()

    p = argparse.ArgumentParser(
        prog="ntl-systoolbox",
        description="NTL SysToolbox – Diagnostic, Backup WMS, Audit Obsolescence.",
        epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    p.add_argument("--config", default=None, help="Chemin config YAML (optionnel)")
    p.add_argument("--json-only", action="store_true", help="Affiche uniquement le chemin du JSON")
    p.add_argument("--quiet", action="store_true", help="Sortie compacte")
    p.add_argument("--verbose", action="store_true", help="Détails")
    p.add_argument("--non-interactive", action="store_true", help="Désactive les prompts (NTL_NON_INTERACTIVE=1)")
    p.add_argument("--menu", action="store_true", help="Force le menu interactif")
    p.add_argument("--version", action="store_true", help="Affiche la version")

    sub = p.add_subparsers(dest="cmd", required=False)

    sub.add_parser("diagnostic", help="Diagnostic AD/DNS + MySQL + état serveur")
    sub.add_parser("backup-wms", help="Backup WMS (SQL/CSV)")

    obs = sub.add_parser("audit-obsolescence", help="Audit d'obsolescence")
    obs_sub = obs.add_subparsers(dest="action", required=False)

    obs_sub.add_parser("interactive", help="Menu interactif du module")
    scan = obs_sub.add_parser("scan-range", help="Scan CIDR (non-interactif)")
    scan.add_argument("--cidr", required=True)

    le = obs_sub.add_parser("list-eol", help="Lister EOL d'un produit")
    le.add_argument("--product", required=True)

    cr = obs_sub.add_parser("csv-report", help="CSV composants -> rapport (option scan)")
    cr.add_argument("--csv", required=True)
    cr.add_argument("--scan", action="store_true")
    cr.add_argument("--cidr", default="")

    return p


def main(argv: Optional[list[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = _build_parser()
    ns = parser.parse_args(argv)

    if ns.version:
        print(_get_version())
        return 0

    if ns.non_interactive:
        os.environ["NTL_NON_INTERACTIVE"] = "1"

    cfg_raw, cfg_path = _load_config(ns.config)
    cfg = _merge_defaults(cfg_raw)

    # menu si demandé ou si aucune commande
    if ns.menu or not ns.cmd:
        return _menu(cfg_path, cfg_raw)

    try:
        if ns.cmd == "diagnostic":
            res = _run_diagnostic(cfg)
            return _handle_result(res, json_only=ns.json_only, quiet=ns.quiet, verbose=ns.verbose)

        if ns.cmd == "backup-wms":
            res = _run_backup(cfg)
            return _handle_result(res, json_only=ns.json_only, quiet=ns.quiet, verbose=ns.verbose)

        if ns.cmd == "audit-obsolescence":
            action = ns.action or "interactive
