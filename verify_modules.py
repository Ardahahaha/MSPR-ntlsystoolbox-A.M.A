
import sys
import os
import json
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from ntlsystoolbox.modules.diagnostic import DiagnosticModule
from ntlsystoolbox.modules.backup_wms import BackupWMSModule
from ntlsystoolbox.modules.audit_obsolescence import AuditObsolescenceModule

def test_diagnostic():
    print("\n--- Test Diagnostic ---")
    config = {"database": {"host": "127.0.0.1", "user": "root", "password": "", "name": "test_db"}}
    diag = DiagnosticModule(config)
    diag.run()
    # Check if JSON is created
    json_dir = "outputs/json"
    files = os.listdir(json_dir)
    diag_files = [f for f in files if f.startswith("diagnostic_")]
    if diag_files:
        print(f"SUCCESS: JSON diagnostic créé : {diag_files[-1]}")
    else:
        print("FAIL: Aucun JSON diagnostic créé")

def test_backup():
    print("\n--- Test Backup (Expected Fail on DB) ---")
    config = {"database": {"host": "invalid_host", "user": "root", "password": "", "name": "wms"}}
    backup = BackupWMSModule(config)
    backup.run()
    # Check if JSON is created
    json_dir = "outputs/json"
    files = os.listdir(json_dir)
    backup_files = [f for f in files if f.startswith("backup_wms_")]
    if backup_files:
        print(f"SUCCESS: JSON backup créé : {backup_files[-1]}")
    else:
        print("FAIL: Aucun JSON backup créé")

def test_audit():
    print("\n--- Test Audit ---")
    config = {}
    audit = AuditObsolescenceModule(config)
    audit.run()
    # Check artifacts
    if os.path.exists("outputs/audit_report.html"):
        print("SUCCESS: Rapport HTML audit créé")
    json_dir = "outputs/json"
    files = os.listdir(json_dir)
    audit_files = [f for f in files if f.startswith("obsolescence_")]
    if audit_files:
        print(f"SUCCESS: JSON audit créé : {audit_files[-1]}")

if __name__ == "__main__":
    os.makedirs("outputs/json", exist_ok=True)
    test_diagnostic()
    test_backup()
    test_audit()
