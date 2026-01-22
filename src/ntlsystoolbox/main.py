import sys
import os
from .core.menu import run_menu
from .utils.config import load_config
from .utils.exit_codes import CRITICAL

def main():
    # Définition du dossier de base
    base_dir = os.getcwd()
    config_path = os.path.join(base_dir, "config", "config.yml")
    
    # Chargement de la configuration
    config = load_config(config_path)
    
    # Si la config est vide, on initialise les clés minimales
    if not config:
        config = {
            "database": {
                "host": "localhost",
                "user": "root",
                "password": "",
                "name": "wms"
            }
        }
    
    try:
        run_menu(config)
    except KeyboardInterrupt:
        print("\n[CRITICAL] Interruption utilisateur (Ctrl+C).")
        sys.exit(CRITICAL)
    except Exception as e:
        print(f"\n[CRITICAL] Erreur fatale : {e}")
        sys.exit(CRITICAL)

if __name__ == "__main__":
    main()
