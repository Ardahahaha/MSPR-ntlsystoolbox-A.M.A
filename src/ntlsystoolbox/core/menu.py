import sys
from ..modules.diagnostic import DiagnosticModule
from ..modules.backup_wms import BackupWMSModule
from ..modules.audit_obsolescence import AuditObsolescenceModule
from ..utils.exit_codes import SUCCESS, WARNING, CRITICAL
from ..ui.menu import Color, clear_screen, print_logo, print_menu

def run_menu(config):
    while True:
        try:
            clear_screen()
            print_logo()
            print_menu()
            
            # Input stylisé
            choice = input(f"{Color.BOLD}{Color.CYAN}ntl-cli > {Color.END}").strip()

            if choice == "1":
                print(f"\n{Color.CYAN}Lancement du Diagnostic...{Color.END}")
                DiagnosticModule(config).run()
                input(f"\n{Color.YELLOW}Appuyez sur Entrée pour revenir au menu...{Color.END}")
            elif choice == "2":
                print(f"\n{Color.PURPLE}Lancement de la Sauvegarde WMS...{Color.END}")
                BackupWMSModule(config).run()
                input(f"\n{Color.YELLOW}Appuyez sur Entrée pour revenir au menu...{Color.END}")
            elif choice == "3":
                print(f"\n{Color.YELLOW}Lancement de l'Audit d'obsolescence...{Color.END}")
                AuditObsolescenceModule(config).run()
                input(f"\n{Color.YELLOW}Appuyez sur Entrée pour revenir au menu...{Color.END}")
            elif choice == "0":
                print(f"\n{Color.GREEN}Au revoir.{Color.END}")
                sys.exit(SUCCESS)
            else:
                print(f"\n{Color.RED}[!] Choix '{choice}' invalide. Veuillez saisir 1, 2, 3 ou 0.{Color.END}")
                # Le user demande: choix invalide -> message clair + ExitCode WARNING
                # Dans un menu interactif, on affiche le message et on attend.
                input(f"\n{Color.YELLOW}Appuyez sur Entrée pour réessayer...{Color.END}")
        
        except KeyboardInterrupt:
            print(f"\n\n{Color.RED}Interruption par l'utilisateur (Ctrl+C).{Color.END}")
            sys.exit(CRITICAL)
        except Exception as e:
            print(f"\n{Color.RED}[CRITICAL] Une erreur inattendue est survenue : {e}{Color.END}")
            sys.exit(CRITICAL)
