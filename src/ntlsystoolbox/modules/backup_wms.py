from __future__ import annotations

import csv
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from getpass import getpass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pymysql

from ntlsystoolbox.core.result import ModuleResult, status_from_two_flags


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(key)
    return val if val not in (None, "") else default


def _prompt(msg: str, default: Optional[str] = None) -> str:
    if os.getenv("NTL_NON_INTERACTIVE", "0") == "1":
        return default or ""
    suffix = f" [{default}]" if default else ""
    v = input(f"{msg}{suffix} : ").strip()
    return v if v else (default or "")


@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    db: str
    csv_table: Optional[str] = None


class BackupWMSModule:
    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}

    def _load_db_config(self) -> DBConfig:
        db_cfg = self.config.get("database", {}) if isinstance(self.config, dict) else {}

        default_host = _env("NTL_DB_HOST", db_cfg.get("host", "192.168.10.21"))
        default_port = _env("NTL_DB_PORT", str(db_cfg.get("port", 3306)))
        default_user = _env("NTL_DB_USER", db_cfg.get("user", "root"))
        default_db = _env("NTL_DB_NAME", db_cfg.get("name", "wms"))
        default_table = _env("NTL_DB_TABLE", db_cfg.get("table", "")) or None

        print("\n--- Configuration Sauvegarde WMS ---\n")
        host = _prompt("Host MySQL (ex: 192.168.10.21)", default_host)
        port_str = _prompt("Port MySQL", default_port)
        try:
            port = int(port_str)
        except ValueError:
            port = 3306

        user = _prompt("Utilisateur", default_user)

        pwd = _env("NTL_DB_PASS", db_cfg.get("password", ""))
        if not pwd and os.getenv("NTL_NON_INTERACTIVE", "0") != "1":
            pwd = getpass("Mot de passe (input masqué, vide si aucun) : ")
        if pwd is None:
            pwd = ""

        db = _prompt("Nom de la base", default_db)

        table = _prompt("Table à exporter en CSV (optionnel)", default_table or "")
        csv_table = table.strip() or None

        return DBConfig(host=host, port=port, user=user, password=pwd, db=db, csv_table=csv_table)

    def _connect(self, dbc: DBConfig):
        return pymysql.connect(
            host=dbc.host,
            port=dbc.port,
            user=dbc.user,
            password=dbc.password,
            database=dbc.db,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.Cursor,
            autocommit=True,
        )

    def _fetch_tables(self, conn) -> List[str]:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            rows = cur.fetchall()
        return [r[0] for r in rows]

    def _dump_sql(self, conn, dbc: DBConfig, out_dir: str) -> Tuple[bool, str, Optional[str]]:
        try:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = str(Path(out_dir) / f"wms_backup_{dbc.db}_{ts}.sql")

            tables = self._fetch_tables(conn)
            if not tables:
                return False, "Aucune table trouvée dans la base.", None

            with open(out_path, "w", encoding="utf-8") as f:
                f.write("-- NTL SysToolbox SQL Backup\n")
                f.write(f"-- Database: {dbc.db}\n")
                f.write(f"-- Generated: {datetime.now().isoformat(timespec='seconds')}\n\n")
                f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

                for table in tables:
                    with conn.cursor() as cur:
                        cur.execute(f"SHOW CREATE TABLE `{table}`")
                        row = cur.fetchone()
                        create_stmt = row[1] if row and len(row) > 1 else None

                    if not create_stmt:
                        continue

                    f.write(f"-- Table: `{table}`\n")
                    f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                    f.write(create_stmt + ";\n\n")

                    with conn.cursor() as cur:
                        cur.execute(f"SELECT * FROM `{table}`")
                        cols = [d[0] for d in cur.description] if cur.description else []
                        if not cols:
                            f.write("\n")
                            continue
                        col_list = ", ".join(f"`{c}`" for c in cols)

                        while True:
                            rows = cur.fetchmany(500)
                            if not rows:
                                break

                            f.write(f"INSERT INTO `{table}` ({col_list}) VALUES\n")
                            values_lines = []
                            for r in rows:
                                vals = []
                                for v in r:
                                    if isinstance(v, (bytes, bytearray)):
                                        vals.append("0x" + bytes(v).hex())
                                    else:
                                        vals.append(conn.escape(v))
                                values_lines.append("(" + ", ".join(vals) + ")")
                            f.write(",\n".join(values_lines) + ";\n\n")

                f.write("SET FOREIGN_KEY_CHECKS=1;\n")

            return True, "Dump SQL généré.", out_path
        except Exception as e:
            return False, f"{e}", None

    def _export_csv(self, conn, dbc: DBConfig, out_dir: str) -> Tuple[bool, str, Optional[str]]:
        try:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            table = dbc.csv_table
            tables = self._fetch_tables(conn)

            if not tables:
                return False, "Aucune table trouvée dans la base.", None

            if not table:
                table = tables[0]

            if table not in tables:
                return False, f"Table '{table}' introuvable. Tables dispo: {', '.join(tables[:10])}", None

            out_path = str(Path(out_dir) / f"wms_export_{table}_{ts}.csv")

            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM `{table}`")
                cols = [d[0] for d in cur.description] if cur.description else []

                with open(out_path, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    if cols:
                        w.writerow(cols)

                    while True:
                        rows = cur.fetchmany(1000)
                        if not rows:
                            break
                        w.writerows(rows)

            return True, f"Export CSV généré (table={table}).", out_path
        except Exception as e:
            return False, f"{e}", None

    def run(self) -> ModuleResult:
        started = datetime.now().isoformat(timespec="seconds")
        dbc = self._load_db_config()

        print("\nExécution des sauvegardes...")

        try:
            conn = self._connect(dbc)
        except Exception as e:
            msg = f"Connexion MySQL impossible: {e}"
            return ModuleResult(
                module="backup_wms",
                status="ERROR",
                summary="Sauvegarde WMS impossible (connexion DB KO)",
                details={
                    "host": dbc.host,
                    "port": dbc.port,
                    "db": dbc.db,
                    "sql": f"FAIL ({msg})",
                    "csv": f"FAIL ({msg})",
                },
                artifacts={},
                started_at=started,
            ).finish()

        sql_ok = False
        csv_ok = False
        sql_msg = ""
        csv_msg = ""
        sql_path = None
        csv_path = None

        try:
            sql_ok, sql_msg, sql_path = self._dump_sql(conn, dbc, out_dir="reports/backup/sql")
            print(f"SQL: {'OK' if sql_ok else 'ERROR'} ({sql_msg})")

            csv_ok, csv_msg, csv_path = self._export_csv(conn, dbc, out_dir="reports/backup/csv")
            print(f"CSV: {'OK' if csv_ok else 'ERROR'} ({csv_msg})")
        finally:
            try:
                conn.close()
            except Exception:
                pass

        status = status_from_two_flags(sql_ok, csv_ok)

        artifacts: Dict[str, str] = {}
        if sql_ok and sql_path:
            artifacts["sql_backup_path"] = sql_path
            artifacts["sql_backup_sha256"] = _sha256_file(sql_path)
        if csv_ok and csv_path:
            artifacts["csv_export_path"] = csv_path
            artifacts["csv_export_sha256"] = _sha256_file(csv_path)

        return ModuleResult(
            module="backup_wms",
            status=status,
            summary="Sauvegarde WMS SQL/CSV",
            details={
                "host": dbc.host,
                "port": dbc.port,
                "db": dbc.db,
                "sql": "OK" if sql_ok else f"FAIL ({sql_msg})",
                "csv": "OK" if csv_ok else f"FAIL ({csv_msg})",
                "csv_table": dbc.csv_table or "(auto)",
            },
            artifacts=artifacts,
            started_at=started,
        ).finish()
