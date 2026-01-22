import sys
import os
from .core.menu import run_menu

def main():
    config = {
        "database": {
            "host": os.getenv("DB_HOST", "localhost"),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "name": "wms"
        }
    }
    
    try:
        run_menu(config)
    except KeyboardInterrupt:
        print("\nInterruption utilisateur.")
        sys.exit(0)
    except Exception as e:
        print(f"\nErreur fatale : {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
