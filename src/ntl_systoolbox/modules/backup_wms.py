import pymysql
import csv
import os
import time
from datetime import datetime
from typing import Dict, Any
from ..utils.output import format_result

class BackupWMSModule:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backup_dir = "outputs/backups"
        os.makedirs(self.backup_dir, exist_ok=True)

    def run_dump(self):
        db_conf = self.config.get('database', {})
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.backup_dir}/wms_backup_{timestamp}.sql"
        
        try:
            conn = pymysql.connect(
                host=db_conf.get('host', 'localhost'),
                user=db_conf.get('user', 'root'),
                password=db_conf.get('password', ''),
                database=db_conf.get('name', 'wms')
            )
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
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
        # AMBIGU: Choix minimal pour l'export CSV (table stock par défaut)
        db_conf = self.config.get('database', {})
        filename = f"{self.backup_dir}/stock_export_{datetime.now().strftime('%Y%m%d')}.csv"
        try:
            conn = pymysql.connect(
                host=db_conf.get('host', 'localhost'),
                user=db_conf.get('user', 'root'),
                password=db_conf.get('password', ''),
                database=db_conf.get('name', 'wms')
            )
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM stock LIMIT 1000") # Exemple
                rows = cursor.fetchall()
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([i[0] for i in cursor.description])
                    writer.writerows(rows)
            conn.close()
            return {"status": "OK", "file": filename}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def run(self):
        print("\n--- Sauvegarde WMS ---")
        res_sql = self.run_dump()
        res_csv = self.run_csv_export()
        format_result("backup_wms", {"sql": res_sql, "csv": res_csv})
        return 0
