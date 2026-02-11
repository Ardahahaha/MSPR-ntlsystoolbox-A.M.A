# src/ntlsystoolbox/modules/audit_obsolescence.py
from __future__ import annotations

import csv
import ipaddress
import json
import os
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from ntlsystoolbox.core.result import ModuleResult


# ----------------------------
# Helpers
# ----------------------------
def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(key)
    return v if v not in (None, "") else default


def _prompt(msg: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default else ""
    v = input(f"{msg}{suffix} : ").strip()
    return v if v else (default or "")


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def _parse_date(d: Any) -> Optional[date]:
    """
    endoflife.date peut renvoyer:
    - une date "YYYY-MM-DD"
    - true/false/null selon produits
    """
    if d is None:
        return None
    if isinstance(d, bool):
        return None
    if isinstance(d, str):
        try:
            return datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            return None
    return None


def _tcp_ports(host: str, ports: List[int], timeout_s: float = 0.5) -> List[int]:
    open_ports: List[int] = []
    for p in ports:
        try:
            with socket.create_connection((host, p), timeout=timeout_s):
                open_ports.append(p)
        except Exception:
            pass
    return open_ports


def _guess_os_from_ports(open_ports: List[int]) -> str:
    # Heuristique simple (demande: "essayer de déterminer l’OS")
    if any(p in open_ports for p in (3389, 445, 139)):
        return "windows"
    if any(p in open_ports for p in (53, 389)):
        return "windows-server (dc/dns probable)"
    if 22 in open_ports:
        return "linux"
    return "unknown"


def _status_from_eol(today: date, eol: Any, soon_days: int) -> Tuple[str, Optional[str]]:
    """
    Retourne: (status, eol_date_str)
    status ∈ {"OK", "SOON", "EOL", "UNKNOWN"}
    """
    if eol is None:
        return "UNKNOWN", None
    if isinstance(eol, bool):
        # True => EOL dépassé (selon certains produits), False => pas EOL (ou inconnu)
        return ("EOL" if eol else "OK"), None
    if isinstance(eol, str):
        d = _parse_date(eol)
        if not d:
            return "UNKNOWN", eol
        if d < today:
            return "EOL", d.isoformat()
        if (d - today).days <= soon_days:
            return "SOON", d.isoformat()
        return "OK", d.isoformat()
    return "UNKNOWN", None


# ----------------------------
# EOL Provider (endoflife.date)
# ----------------------------
@dataclass
class EOLMeta:
    source: str
    fetched_at_iso: str
    api_mode: str  # "v1" or "v0"


class EOLProvider:
    """
    Récupère les cycles + EOL via endoflife.date.
    - tente v1: https://endoflife.date/api/v1/products/{product}/
    - fallback v0: https://endoflife.date/api/{product}.json
    Cache local: reports/audit/eol_cache.json
    """

    def __init__(self, cache_path: str = "reports/audit/eol_cache.json", ttl_hours: int = 24):
        self.cache_path = cache_path
        self.ttl_hours = ttl_hours
        self._cache: Dict[str, Any] = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_cache(self) -> None:
        try:
            _ensure_dir(str(Path(self.cache_path).parent))
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _cache_valid(self, fetched_at_iso: str) -> bool:
        try:
            fetched = datetime.fromisoformat(fetched_at_iso)
            return (datetime.now() - fetched).total_seconds() <= self.ttl_hours * 3600
        except Exception:
            return False

    def fetch_product(self, product: str) -> Tuple[List[Dict[str, Any]], EOLMeta]:
        product = product.strip().lower()

        # Cache
        cached = self._cache.get(product)
        if cached and isinstance(cached, dict):
            if self._cache_valid(cached.get("fetched_at_iso", "")):
                return cached.get("data", []), EOLMeta(
                    source=cached.get("source", "endoflife.date"),
                    fetched_at_iso=cached.get("fetched_at_iso", ""),
                    api_mode=cached.get("api_mode", "cache"),
                )

        fetched_at_iso = datetime.now().isoformat(timespec="seconds")

        # Try v1
        v1_url = f"https://endoflife.date/api/v1/products/{product}/"
        try:
            r = requests.get(v1_url, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    meta = EOLMeta(source="endoflife.date", fetched_at_iso=fetched_at_iso, api_mode="v1")
                    self._cache[product] = {"data": data, "fetched_at_iso": fetched_at_iso, "source": meta.source, "api_mode": meta.api_mode}
                    self._save_cache()
                    return data, meta
        except Exception:
            pass

        # Fallback v0
        v0_url = f"https://endoflife.date/api/{product}.json"
        r = requests.get(v0_url, timeout=8)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            data = []

        meta = EOLMeta(source="endoflife.date", fetched_at_iso=fetched_at_iso, api_mode="v0")
        self._cache[product] = {"data": data, "fetched_at_iso": fetched_at_iso, "source": meta.source, "api_mode": meta.api_mode}
        self._save_cache()
        return data, meta


# ----------------------------
# Module
# ----------------------------
class AuditObsolescenceModule:
    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.provider = EOLProvider()

    def _menu(self) -> str:
        print("\n--- Audit Obsolescence ---")
        print(" [1] Scanner une plage réseau (inventaire + OS probable)")
        print(" [2] Lister versions + EOL d’un produit/OS (ex: ubuntu, debian, windows, mysql, python)")
        print(" [3] Import CSV (composants + versions) + Générer rapport HTML")
        print(" [0] Retour\n")
        return input("Choix > ").strip()

    def _scan_range(self, cidr: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        ports = [22, 53, 80, 443, 389, 445, 3389, 3306]
        timeout_s = float(_env("NTL_SCAN_TIMEOUT", "0.4") or "0.4")
        workers = int(_env("NTL_SCAN_WORKERS", "120") or "120")

        net = ipaddress.ip_network(cidr, strict=False)
        ips = [str(ip) for ip in net.hosts()]

        results: List[Dict[str, Any]] = []

        def worker(ip: str) -> Optional[Dict[str, Any]]:
            open_ports = _tcp_ports(ip, ports, timeout_s=timeout_s)
            if not open_ports:
                return None
            os_guess = _guess_os_from_ports(open_ports)
            return {"ip": ip, "open_ports": sorted(open_ports), "os_guess": os_guess}

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(worker, ip) for ip in ips]
            for f in as_completed(futs):
                item = f.result()
                if item:
                    results.append(item)

        results.sort(key=lambda x: tuple(int(p) for p in x["ip"].split(".")))

        stats = {
            "cidr": cidr,
            "found_hosts": len(results),
            "ports_checked": ports,
            "timeout_s": timeout_s,
            "workers": workers,
        }
        return results, stats

    def _list_versions_eol(self, product: str) -> Tuple[List[Dict[str, Any]], EOLMeta]:
        data, meta = self.provider.fetch_product(product)
        rows: List[Dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "cycle": item.get("cycle") or item.get("release") or item.get("version"),
                    "latest": item.get("latest"),
                    "eol": item.get("eol"),
                    "support": item.get("support"),
                    "extendedSupport": item.get("extendedSupport"),
                    "link": item.get("link"),
                    "releaseDate": item.get("releaseDate") or item.get("released"),
                }
            )
        rows = [r for r in rows if r.get("cycle")]
        return rows, meta

    def _read_components_csv(self, path: str) -> List[Dict[str, str]]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"CSV introuvable: {path}")

        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            sample = f.read(2048)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=";,")
            except Exception:
                dialect = csv.excel
            reader = csv.DictReader(f, dialect=dialect)

            items: List[Dict[str, str]] = []
            for row in reader:
                product = (row.get("product") or row.get("os") or row.get("OS") or row.get("Produit") or row.get("produit") or "").strip().lower()
                version = (row.get("version") or row.get("cycle") or row.get("Version") or row.get("version_os") or "").strip()
                name = (row.get("name") or row.get("hostname") or row.get("machine") or row.get("composant") or row.get("Composant") or "").strip()

                if not product or not version:
                    continue
                items.append({"name": name or "(n/a)", "product": product, "version": version})
        return items

    def _match_cycle(self, rows: List[Dict[str, Any]], version: str) -> Optional[Dict[str, Any]]:
        v = version.strip()
        for r in rows:
            c = str(r.get("cycle", "")).strip()
            if not c:
                continue
            if v == c or v.startswith(c + ".") or v.startswith(c + " "):
                return r
        return None

    def _generate_html_report(
        self,
        inventory: Optional[List[Dict[str, Any]]],
        components: List[Dict[str, Any]],
        out_path: str,
        meta_by_product: Dict[str, EOLMeta],
        soon_days: int,
    ) -> Dict[str, Any]:
        counts = {"OK": 0, "SOON": 0, "EOL": 0, "UNKNOWN": 0}
        for c in components:
            counts[c["support_status"]] += 1

        _ensure_dir(str(Path(out_path).parent))

        def esc(s: Any) -> str:
            return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("<!doctype html><html><head><meta charset='utf-8'>")
            f.write("<title>NTL SysToolbox - Audit d'obsolescence</title>")
            f.write("<style>body{font-family:Arial,Helvetica,sans-serif;margin:24px} table{border-collapse:collapse;width:100%} td,th{border:1px solid #ddd;padding:8px} th{background:#f3f3f3} .ok{background:#e9ffe9} .soon{background:#fff7d6} .eol{background:#ffe2e2} .unk{background:#f0f0f0}</style>")
            f.write("</head><body>")
            f.write(f"<h1>Audit d'obsolescence</h1>")
            f.write(f"<p>Généré le <b>{esc(datetime.now().isoformat(timespec='seconds'))}</b> | Seuil 'bientôt' = {soon_days} jours</p>")

            f.write("<h2>Sources EOL (référence + date de validité)</h2><ul>")
            for prod, m in meta_by_product.items():
                f.write(f"<li>{esc(prod)} — source: {esc(m.source)} — fetch: {esc(m.fetched_at_iso)} — mode: {esc(m.api_mode)}</li>")
            f.write("</ul>")

            f.write("<h2>Résumé</h2><ul>")
            f.write(f"<li>OK: {counts['OK']}</li>")
            f.write(f"<li>Bientôt EOL: {counts['SOON']}</li>")
            f.write(f"<li>EOL: {counts['EOL']}</li>")
            f.write(f"<li>Inconnu: {counts['UNKNOWN']}</li>")
            f.write("</ul>")

            if inventory is not None:
                f.write("<h2>Inventaire réseau (scan)</h2>")
                f.write("<table><thead><tr><th>IP</th><th>Ports ouverts</th><th>OS probable</th></tr></thead><tbody>")
                for h in inventory:
                    f.write("<tr>")
                    f.write(f"<td>{esc(h['ip'])}</td>")
                    f.write(f"<td>{esc(','.join(str(p) for p in h['open_ports']))}</td>")
                    f.write(f"<td>{esc(h['os_guess'])}</td>")
                    f.write("</tr>")
                f.write("</tbody></table>")

            f.write("<h2>Composants (CSV) + statut support</h2>")
            f.write("<table><thead><tr><th>Composant</th><th>Produit/OS</th><th>Version</th><th>EOL</th><th>Statut</th></tr></thead><tbody>")
            for c in components:
                st = c["support_status"]
                css = "ok" if st == "OK" else ("soon" if st == "SOON" else ("eol" if st == "EOL" else "unk"))
                f.write(f"<tr class='{css}'>")
                f.write(f"<td>{esc(c['name'])}</td>")
                f.write(f"<td>{esc(c['product'])}</td>")
                f.write(f"<td>{esc(c['version'])}</td>")
                f.write(f"<td>{esc(c.get('eol_date') or '')}</td>")
                f.write(f"<td><b>{esc(st)}</b></td>")
                f.write("</tr>")
            f.write("</tbody></table>")

            f.write("</body></html>")

        return {"counts": counts, "report_path": out_path}

    # ✅ NOUVEAU : version non-interactive pilotée par main.py
    def run_action(self, action: str, **kwargs) -> ModuleResult:
        started = datetime.now().isoformat(timespec="seconds")
        soon_days = int(_env("NTL_EOL_SOON_DAYS", str(kwargs.get("soon_days", 180))) or "180")

        # 1) Scan
        if action == "scan_range":
            cidr = (kwargs.get("cidr") or "").strip()
            if not cidr:
                return ModuleResult(
                    module="obsolescence",
                    status="ERROR",
                    summary="CIDR manquant pour scan_range",
                    details={"action": action},
                    started_at=started,
                ).finish()

            inventory, stats = self._scan_range(cidr)

            status = "SUCCESS" if inventory else "WARNING"
            summary = f"Scan terminé: {len(inventory)} hôte(s) trouvé(s)" if inventory else "Scan terminé: aucun hôte détecté"

            out_inv = f"reports/audit/inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            _ensure_dir("reports/audit")
            with open(out_inv, "w", encoding="utf-8") as f:
                json.dump({"stats": stats, "inventory": inventory}, f, indent=2, ensure_ascii=False)

            return ModuleResult(
                module="obsolescence",
                status=status,
                summary=summary,
                details={"action": "scan_range", "stats": stats, "inventory": inventory},
                artifacts={"inventory_json": out_inv},
                started_at=started,
            ).finish()

        # 2) Listing versions + EOL
        if action == "list_versions_eol":
            product = (kwargs.get("product") or "").strip().lower()
            if not product:
                return ModuleResult(
                    module="obsolescence",
                    status="ERROR",
                    summary="Produit manquant pour list_versions_eol",
                    details={"action": action},
                    started_at=started,
                ).finish()

            rows, meta = self._list_versions_eol(product)

            today = datetime.now().date()
            enriched: List[Dict[str, Any]] = []
            for r in rows:
                st, eol_date = _status_from_eol(today, r.get("eol"), soon_days)
                enriched.append({**r, "support_status": st, "eol_date": eol_date})

            if not enriched:
                status = "WARNING"
                summary = f"Aucune donnée EOL pour '{product}'"
            else:
                any_bad = any(x["support_status"] in ("SOON", "EOL") for x in enriched)
                status = "WARNING" if any_bad else "SUCCESS"
                summary = f"Versions/EOL récupérées pour '{product}' (mode {meta.api_mode})"

            return ModuleResult(
                module="obsolescence",
                status=status,
                summary=summary,
                details={"action": "list_versions_eol", "product": product, "meta": meta.__dict__, "rows": enriched},
                artifacts={},
                started_at=started,
            ).finish()

        # 3) CSV -> EOL + rapport HTML (option scan)
        if action == "csv_to_report":
            csv_path = (kwargs.get("csv_path") or "").strip()
            if not csv_path:
                return ModuleResult(
                    module="obsolescence",
                    status="ERROR",
                    summary="CSV manquant pour csv_to_report",
                    details={"action": action},
                    started_at=started,
                ).finish()

            do_scan = bool(kwargs.get("do_scan", False))
            cidr = (kwargs.get("cidr") or "").strip() if do_scan else ""

            if do_scan and not cidr:
                return ModuleResult(
                    module="obsolescence",
                    status="ERROR",
                    summary="CIDR manquant (do_scan=True) pour csv_to_report",
                    details={"action": action},
                    started_at=started,
                ).finish()

            inventory = None
            inv_stats = None
            if do_scan:
                inventory, inv_stats = self._scan_range(cidr)

            components_raw = self._read_components_csv(csv_path)

            by_product: Dict[str, List[Dict[str, str]]] = {}
            for c in components_raw:
                by_product.setdefault(c["product"], []).append(c)

            today = datetime.now().date()
            meta_by_product: Dict[str, EOLMeta] = {}
            resolved: List[Dict[str, Any]] = []

            for product, comps in by_product.items():
                rows, meta = self._list_versions_eol(product)
                meta_by_product[product] = meta

                for c in comps:
                    match = self._match_cycle(rows, c["version"])
                    if match:
                        st, eol_date = _status_from_eol(today, match.get("eol"), soon_days)
                    else:
                        st, eol_date = "UNKNOWN", None
                    resolved.append(
                        {"name": c["name"], "product": product, "version": c["version"], "eol_date": eol_date, "support_status": st}
                    )

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_html = f"reports/audit/audit_report_{ts}.html"
            report_info = self._generate_html_report(
                inventory=inventory,
                components=resolved,
                out_path=out_html,
                meta_by_product=meta_by_product,
                soon_days=soon_days,
            )

            any_eol = any(r["support_status"] == "EOL" for r in resolved)
            any_soon = any(r["support_status"] == "SOON" for r in resolved)
            any_unknown = any(r["support_status"] == "UNKNOWN" for r in resolved)

            if any_eol or any_soon or any_unknown:
                status = "WARNING"
                summary = "Audit terminé: composants EOL/SOON/UNKNOWN détectés"
            else:
                status = "SUCCESS"
                summary = "Audit terminé: aucun composant EOL/SOON"

            return ModuleResult(
                module="obsolescence",
                status=status,
                summary=summary,
                details={
                    "action": "csv_to_eol_and_report",
                    "csv_path": csv_path,
                    "scan": {"enabled": do_scan, "stats": inv_stats, "inventory_count": (len(inventory) if inventory else 0)},
                    "meta_by_product": {k: v.__dict__ for k, v in meta_by_product.items()},
                    "components": resolved,
                    "report": report_info,
                    "soon_days": soon_days,
                },
                artifacts={"audit_report_html": out_html},
                started_at=started,
            ).finish()

        return ModuleResult(
            module="obsolescence",
            status="ERROR",
            summary=f"Action inconnue: {action}",
            details={"action": action},
            started_at=started,
        ).finish()

    # ✅ run() reste interactif, mais délègue à run_action()
    def run(self) -> ModuleResult:
        choice = self._menu()

        if choice == "1":
            cidr = _prompt("Plage réseau (CIDR)", _env("NTL_SCAN_CIDR", "192.168.10.0/24"))
            return self.run_action("scan_range", cidr=cidr)

        if choice == "2":
            product = _prompt("Produit/OS (ex: ubuntu, debian, windows, mysql, python)", "ubuntu")
            return self.run_action("list_versions_eol", product=product)

        if choice == "3":
            csv_path = _prompt("Chemin CSV composants", _env("NTL_COMPONENTS_CSV", "inputs/components.csv"))
            do_scan = _prompt("Faire aussi un scan réseau ? (y/n)", "n").lower().startswith("y")
            cidr = None
            if do_scan:
                cidr = _prompt("Plage réseau (CIDR)", _env("NTL_SCAN_CIDR", "192.168.10.0/24"))
            return self.run_action("csv_to_report", csv_path=csv_path, do_scan=do_scan, cidr=cidr)

        return ModuleResult(
            module="obsolescence",
            status="SUCCESS",
            summary="Retour menu principal",
            details={"action": "exit"},
            artifacts={},
        ).finish()
