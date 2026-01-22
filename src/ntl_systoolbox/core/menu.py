import questionary
from ..modules.diagnostic import DiagnosticModule
from ..modules.backup_wms import BackupWMSModule
from ..modules.audit_obsolescence import AuditObsolescenceModule

def run_menu(config):
    while True:
        choice = questionary.select(
            "NTL-SysToolbox - Menu Principal",
            choices=[
                "1. Diagnostic Système",
                "2. Sauvegarde WMS",
                "3. Audit Obsolescence",
                "Quitter"
            ]
        ).ask()

        if choice == "1. Diagnostic Système":
            DiagnosticModule(config).run()
        elif choice == "2. Sauvegarde WMS":
            BackupWMSModule(config).run()
        elif choice == "3. Audit Obsolescence":
            AuditObsolescenceModule(config).run()
        elif choice == "Quitter" or choice is None:
            print("Au revoir.")
            break
