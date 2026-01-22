import requests
import os
from datetime import datetime
from ..utils.output import format_result

class AuditObsolescenceModule:
    def __init__(self, config):
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
        
        html_file = "reports/audit_report.html"
        os.makedirs("reports", exist_ok=True)
        with open(html_file, "w", encoding='utf-8') as f:
            f.write("<html><head><meta charset='UTF-8'><title>Rapport Obsolescence</title></head><body>")
            f.write("<h1>Rapport Obsolescence NTL</h1><table border='1'>")
            f.write("<tr><th>Produit</th><th>Version</th><th>EOL</th><th>Status</th></tr>")
            for r in results:
                f.write(f"<tr><td>{r['product']}</td><td>{r['version']}</td><td>{r.get('eol', 'N/A')}</td><td>{r['status']}</td></tr>")
            f.write("</table></body></html>")
            
        print(f"Rapport HTML généré : {html_file}")
        format_result("obsolescence", {"report": html_file, "items": results})
        return 0
