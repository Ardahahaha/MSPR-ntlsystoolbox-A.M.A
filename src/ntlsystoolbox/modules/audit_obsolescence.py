import requests
import os
from datetime import datetime
from typing import Dict, Any
from ntlsystoolbox.core.result import ModuleResult
from ..utils.output import format_result

class AuditObsolescenceModule:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.eol_api = "https://endoflife.date/api"

    def check_eol(self, product: str, version: str):
        try:
            response = requests.get(f"{self.eol_api}/{product}/{version}.json", timeout=5)
            if response.status_code == 200:
                data = response.json()
                eol_date = data.get("eol")
                is_eol = False
                if isinstance(eol_date, str):
                    try:
                        is_eol = datetime.strptime(eol_date, "%Y-%m-%d") < datetime.now()
                    except:
                        pass
                return {
                    "product": product,
                    "version": version,
                    "eol": eol_date,
                    "status": "EOL" if is_eol else "SUPPORTED"
                }
        except:
            pass
        return {"product": product, "version": version, "status": "UNKNOWN"}

    def run(self):
        print("\n--- Audit Obsolescence ---")
        
        # Choix de la cible
        print("Cibles par défaut : python 3.8, debian 10, mysql 5.7")
        custom = input("Voulez-vous tester un produit spécifique ? (laisser vide pour défaut, sinon format 'produit version') : ").strip()
        
        if custom:
            try:
                p, v = custom.split()
                targets = [(p, v)]
            except:
                print("Format invalide, utilisation des cibles par défaut.")
                targets = [("python", "3.8"), ("debian", "10"), ("mysql", "5.7")]
        else:
            targets = [("python", "3.8"), ("debian", "10"), ("mysql", "5.7")]
        
        print(f"Vérification de {len(targets)} cible(s)...")
        results = [self.check_eol(p, v) for p, v in targets]
        
        # Génération du rapport HTML
        html_file = "reports/audit_report.html"
        os.makedirs("reports", exist_ok=True)
        try:
            with open(html_file, "w", encoding='utf-8') as f:
                f.write("<html><head><meta charset='UTF-8'><title>Rapport Obsolescence</title></head><body>")
                f.write("<h1>Rapport Obsolescence NTL</h1><table border='1'>")
                f.write("<tr><th>Produit</th><th>Version</th><th>EOL</th><th>Status</th></tr>")
                for r in results:
                    color = "red" if r['status'] == "EOL" else "black"
                    f.write(f"<tr style='color:{color}'><td>{r['product']}</td><td>{r['version']}</td><td>{r.get('eol', 'N/A')}</td><td>{r['status']}</td></tr>")
                f.write("</table></body></html>")
            report_ok = True
        except Exception as e:
            print(f"Erreur lors de la génération du rapport : {e}")
            report_ok = False
            
        # Affichage console (legacy)
        format_result("obsolescence", {"report": html_file, "items": results})

        # Détermination du statut global : WARNING si un produit est EOL
        any_eol = any(r['status'] == "EOL" for r in results)
        status = "WARNING" if any_eol else "SUCCESS"

        # Retour avec ModuleResult
        return ModuleResult(
            module="obsolescence",
            status=status,
            summary="Audit obsolescence terminé" + (" (Produits obsolètes détectés)" if any_eol else ""),
            details={
                "targets_count": len(targets),
                "eol_count": sum(1 for r in results if r['status'] == "EOL"),
                "items": results
            },
            artifacts={
                "report_html": html_file
            } if report_ok else {},
        ).finish()
