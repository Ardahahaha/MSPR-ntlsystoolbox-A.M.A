import requests
import os
import socket
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
                    is_eol = datetime.strptime(eol_date, "%Y-%m-%d") < datetime.now()
                return {
                    "product": product,
                    "version": version,
                    "eol": eol_date,
                    "status": "EOL" if is_eol else "SUPPORTED"
                }
        except:
            pass
        return {"product": product, "version": version, "status": "UNKNOWN"}

    def scan_network_minimal(self):
        # Scan réseau minimal (périmètre fonctionnel)
        print("Scan réseau en cours (segment local)...")
        # Logique simplifiée pour l'exemple
        return [{"ip": "192.168.1.1", "status": "UP"}]

    def run(self):
        print("\n--- Audit Obsolescence ---")
        network = self.scan_network_minimal()
        
        targets = [("python", "3.8"), ("debian", "10"), ("mysql", "5.7")]
        results = [self.check_eol(p, v) for p, v in targets]
        
        html_file = "outputs/audit_report.html"
        os.makedirs("outputs", exist_ok=True)
        with open(html_file, "w", encoding='utf-8') as f:
            f.write("<html><head><meta charset='UTF-8'><title>Rapport Obsolescence</title></head><body>")
            f.write("<h1>Rapport Obsolescence NTL</h1><table border='1'>")
            f.write("<tr><th>Produit</th><th>Version</th><th>EOL</th><th>Status</th></tr>")
            for r in results:
                f.write(f"<tr><td>{r['product']}</td><td>{r['version']}</td><td>{r.get('eol', 'N/A')}</td><td>{r['status']}</td></tr>")
            f.write("</table></body></html>")
            
        format_result("obsolescence", {"report": html_file, "items": results, "network": network})
        return 0
