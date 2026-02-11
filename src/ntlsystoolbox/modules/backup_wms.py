import pymysql
import csv
import os
from datetime import datetime
from typing import Dict, Any

from ntlsystoolbox.core.result import ModuleResult, status_from_two_flags
from ..utils.output import format_result

class BackupWMSModule:
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('database', {})
        self.backup_dir = "reports/backups"
        os.makedirs(self.backup_dir, exist_ok=True)

    def _ensure_config(self):
        """Demande les paramètres si absents de la config."""
        if not self.config.get('host'):
            self.config['host'] = input("Host MySQL [localhost] : ") or "localhost"
        if not self.config.get('user'):
            self.config['user'] = input("Utilisateur MySQL [root] : ") or "root"
        if 'password' not in self.config:
            self.config['password'] = input("Mot de passe MySQL : ")
        if not self.config.get('name'):
            self.config['name'] = input("Nom de la base [wms] : ") or "wms"

    def run_dump(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.backup_dir}/wms_backup_{timestamp}.sql"
        
        try:
            conn = pymysql.connect(
                host=self.config.get('host'),
                user=self.config.get('user'),
                password=self.config.get('password'),
                database=self.config.get('name')
            )
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                if not tables:
                    return {"status": "WARNING", "message": "Aucune table trouvée."}
                
                with open(filename, 'w', encoding='utf-8') as f:
                    for (table_name,) in tables:
                        f.write(f"\n-- Table: {table_name}\n")
                        cursor.execute(f"SHOW CREATE TABLE {table_name}")
                        create_stmt = cursor.fetchone()[1]
                        f.write(f"{create_stmt};\n")
            conn.close()
            return {"status": "OK", "file": filename}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def run_csv_export(self):
        filename = f"{self.backup_dir}/stock_export_{datetime.now().strftime('%Y%m%d')}.csv"
        try:
            conn = pymysql.connect(
                host=self.config.get('host'),
                user=self.config.get('user'),
                password=self.config.get('password'),
                database=self.config.get('name')
            )
            with conn.cursor() as cursor:
                try:
                    cursor.execute("SELECT * FROM stock LIMIT 1000")
                    rows = cursor.fetchall()
                    with open(filename, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow([i[0] for i in cursor.description])
                        writer.writerows(rows)
                    conn.close()
                    return {"status": "OK", "file": filename}
                except Exception:
                    conn.close()
                    return {"status": "SKIP", "message": "Table 'stock' non trouvée."}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def run(self):
        print("\n--- Configuration Sauvegarde WMS ---")
        self._ensure_config()
        
        print("\nExécution des sauvegardes...")
        
        # Initialisation des flags et données
        sql_ok, csv_ok = False, False
        sql_msg, csv_msg = "", ""
        sql_path, csv_path = None, None

        # Exécution SQL
        res_sql = self.run_dump()
        if res_sql['status'] == "OK":
            sql_ok = True
            sql_path = res_sql.get('file')
        else:
            sql_msg = res_sql.get('message', "Erreur inconnue")

        # Exécution CSV
        res_csv = self.run_csv_export()
        if res_csv['status'] == "OK":
            csv_ok = True
            csv_path = res_csv.get('file')
        else:
            csv_msg = res_csv.get('message', "Erreur ou table absente")

        # Affichage console pour debug immédiat
        print(f"SQL: {res_sql['status']} ({sql_path if sql_ok else sql_msg})")
        print(f"CSV: {res_csv['status']} ({csv_path if csv_ok else csv_msg})")

        # Construction du résultat structuré
        status = status_from_two_flags(sql_ok, csv_ok)

        result = ModuleResult(
            module="backup_wms",
            status=status,
            summary="Sauvegarde WMS SQL/CSV",
            details={
                "sql": "OK" if sql_ok else f"FAIL ({sql_msg})",
                "csv": "OK" if csv_ok else f"FAIL ({csv_msg})",
            },
            artifacts={
                **({"sql_backup": sql_path} if sql_ok and sql_path else {}),
                **({"csv_export": csv_path} if csv_ok and csv_path else {}),
            },
        ).finish()

        return result
