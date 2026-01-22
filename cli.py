import sys
import os

# Ajout du chemin src pour exécution directe sans installation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from ntlsystoolbox.main import main

if __name__ == "__main__":
    main()
