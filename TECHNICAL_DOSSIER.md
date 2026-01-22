# Dossier Technique : Module Audit d'Obsolescence

Ce document détaille l'implémentation technique du module d'audit d'obsolescence pour NTL-SysToolbox.

## 1. Architecture du Module
Le module est situé dans `src/ntl_systoolbox/modules/audit_obsolescence.py`. Il est conçu pour fonctionner de manière autonome en utilisant uniquement la bibliothèque standard Python pour les opérations réseau et HTTP.

## 2. Découverte Réseau (Scan)
- **Mécanisme** : Utilisation de `socket.create_connection` pour tester l'accessibilité des ports TCP.
- **Ports Scannés** : 22 (SSH), 135/445 (RPC/SMB), 80/443 (HTTP/S).
- **Heuristique d'OS** : 
    - Windows : Détecté via les ports 135 ou 445.
    - Linux : Détecté via le port 22.
    - Web Server : Détecté via 80/443 si les autres sont fermés.

## 3. Analyse d'Obsolescence (EOL)
- **Source de Données** : API publique [endoflife.date](https://endoflife.date).
- **Intégration** : Appels HTTP via `urllib.request`. Les données sont récupérées au format JSON.
- **Logique de Comparaison** :
    - Le module compare la version fournie (via CSV ou saisie manuelle) avec les cycles de vie retournés par l'API.
    - **Seuil d'alerte (Soon EOL)** : 180 jours (configuré en constante).
    - **Statuts** :
        - `EOL` : Date actuelle > Date de fin de vie.
        - `SOON_EOL` : Date actuelle proche de la date de fin de vie (<= 180 jours).
        - `SUPPORTED` : Produit encore sous support actif.
        - `UNKNOWN` : Produit ou version non trouvé dans la base.

## 4. Rapports et Sorties
- **JSON** : Rapport exhaustif incluant les métadonnées de l'audit et les résultats bruts.
- **HTML** : Rapport visuel généré via un template embarqué, utilisant un code couleur sémantique :
    - Rouge : Obsolète (EOL).
    - Orange : Bientôt obsolète.
    - Vert : Supporté.
    - Gris : Inconnu.

## 5. Dépendances Standard
- `socket` : Scan réseau.
- `urllib.request` : Appels API.
- `json` : Parsing des données API et export.
- `csv` : Lecture des inventaires.
- `datetime` : Calcul des échéances.
