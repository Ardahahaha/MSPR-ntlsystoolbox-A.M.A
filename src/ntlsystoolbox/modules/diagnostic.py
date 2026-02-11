import socket
import psutil
import pymysql
import time
from typing import Dict, Any
from ntlsystoolbox.core.result import ModuleResult
from ..utils.output import format_result

class DiagnosticModule:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def check_dns(self, hostname: str) -> bool:
        try:
            socket.gethostbyname(hostname)
            return True
        except socket.error:
            return False

    def check_tcp_port(self, host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            return s.connect_ex((host, port)) == 0

    def get_system_metrics(self) -> Dict[str, Any]:
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "ram_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }

    def check_mysql(self) -> Dict[str, Any]:
        db_conf = self.config.get('database', {})
        try:
            conn = pymysql.connect(
                host=db_conf.get('host', 'localhost'),
                user=db_conf.get('user', 'root'),
                password=db_conf.get('password', ''),
                database=db_conf.get('name', 'mysql'),
                connect_timeout=3
            )
            conn.close()
            return {"status": "OK", "message": "Connexion réussie"}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def run(self):
        print("\n--- Diagnostic Système ---")
        
        # Collecte des données
        dns_ok = self.check_dns("ad.local")
        ldap_ok = self.check_tcp_port("127.0.0.1", 389)
        metrics = self.get_system_metrics()
        db_res = self.check_mysql()
        
        results = {
            "timestamp": time.time(),
            "dns_ad": dns_ok,
            "port_ldap_389": ldap_ok,
            "metrics": metrics,
            "database": db_res
        }

        # Affichage console (legacy)
        format_result("diagnostic", results)

        # Détermination du statut global
        # Si un élément critique (DNS, LDAP ou DB) échoue, on passe en WARNING ou ERROR
        success = dns_ok and ldap_ok and db_res["status"] == "OK"
        status = "SUCCESS" if success else "WARNING"

        # Retour avec ModuleResult
        return ModuleResult(
            module="diagnostic",
            status=status,
            summary="Diagnostic système terminé" if success else "Diagnostic terminé avec des alertes",
            details={
                "dns_check": "OK" if dns_ok else "FAILED",
                "ldap_port": "OPEN" if ldap_ok else "CLOSED",
                "db_status": db_res["status"],
                "metrics": metrics
            },
            artifacts={},
        ).finish()
