cat > src/ntlsystoolbox/cli.py <<'PY'
import os
import sys

def menu_principal():
    os.system('clear')
    print("========================================")
    print("       NTL SysToolbox - MENU           ")
    print("========================================")
    print("1. Diagnostic (AD/DNS/MySQL)")
    print("2. Backup WMS")
    print("3. Audit Obsolescence")
    print("q. Quitter")
    print("========================================")
    
    choix = input("Votre choix > ")
    
    if choix == "1":
        print("\n[!] Lancement du Diagnostic...")
        # C'est ici qu'on appellera tes vrais scripts plus tard
    elif choix == "2":
        print("\n[!] Lancement du Backup...")
    elif choix == "3":
        print("\n[!] Lancement de l'Audit...")
    elif choix.lower() == "q":
        sys.exit()
    else:
        input("Choix invalide. Appuyez sur Entrée...")
        menu_principal()

def main():
    # Si on lance juste 'ntl-systoolbox', on affiche le menu
    if len(sys.argv) == 1:
        menu_principal()
    else:
        # Ici on pourra ajouter la gestion des arguments plus tard
        print("Mode argument détecté (non-interactif)")

if __name__ == "__main__":
    main()
PY
