import socket
import psutil
import pymysql
import time
from typing import Dict, Any
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
        results = {
            "timestamp": time.time(),
            "dns_ad": self.check_dns("ad.local"),
            "port_ldap_389": self.check_tcp_port("127.0.0.1", 389),
            "metrics": self.get_system_metrics(),
            "database": self.check_mysql()
        }
        format_result("diagnostic", results)
        return 0
