# NTL-SysToolbox

Outil industriel 100% Python pour le diagnostic réseau, la sauvegarde WMS et l'audit d'obsolescence. Conçu pour les environnements critiques (Siège, Entrepôt) sans dépendances binaires externes (`nmap`, `mysqldump`, etc.).

## Installation

```bash
# Installation des dépendances
pip install -r requirements.txt

# Ou via environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux
# venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Utilisation

L'outil propose un menu interactif complet :

```bash
python cli.py
```

## Configuration

La configuration est gérée par priorité décroissante :
1. Variables d'environnement (préfixe `NTL_`, ex: `NTL_MYSQL_PASSWORD`)
2. Fichier `.env`
3. Fichier `ntl_systoolbox/config/config.yml`
4. Valeurs par défaut

## Modules

1. **Diagnostic** : Vérification de la santé AD, DNS, MySQL et serveurs (Siège/Entrepôt).
2. **Sauvegarde WMS** : Dump logique SQL et export CSV natif Python (sans `mysqldump`).
3. **Audit d'Obsolescence** : Scan réseau minimal et vérification EOL via API `endoflife.date`.

## Sorties (Outputs)

L'outil génère trois types de sorties :
- **Console** : Affichage coloré (via `rich`) et interactif (via `questionary`).
- **Rapports JSON** : Horodatés dans `outputs/reports/`.
- **Artefacts** : Dumps SQL et exports CSV dans `outputs/backups/`.

## Codes de Retour (Exit Codes)

- `0` : SUCCESS
- `1` : WARNING
- `2` : CRITICAL
- `3` : ERROR
- `4` : UNKNOWN
