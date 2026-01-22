# NTL-SysToolbox

Outil industriel 100% Python pour le diagnostic réseau, la sauvegarde WMS et l'audit d'obsolescence. Conçu pour les environnements critiques (Siège, Entrepôt) sans dépendances binaires externes (`nmap`, `mysqldump`, etc.).

## Installation (Windows & Linux) — Tuto simple

1) **Prérequis**
   - Version Python supportée : Python 3.9+
   - Commande pour vérifier : `python --version` (ou `python3 --version`)

2) **Cloner le repo**
   ```bash
   git clone <url-du-repo>
   cd orchids-ntlsystoolbox-spec
   ```

3) **Créer et activer un venv**
   - **Windows (PowerShell) :**
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **Linux/macOS (bash) :**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

4) **Installer le tool**
   - Recommandé : `pip install -e .`
   - Ou : `pip install .`

5) **Lancer le tool**
   - `ntl-systoolbox`
   - et `python -m ntlsystoolbox.cli`

6) **Où trouver les sorties (reports/)**
   Les fichiers sont générés dans le dossier `reports/` :
   - JSON horodaté : `reports/json/diagnostic_YYYYMMDD_HHMMSS.json`
   - Audit HTML : `reports/audit_report.html`
   - Backup SQL : `reports/backups/wms_backup_YYYYMMDD_HHMMSS.sql`

## Dépannage rapide

- **Erreur venv non activé** : Si la commande `ntl-systoolbox` n'est pas reconnue, assurez-vous que `(venv)` est visible dans votre terminal après l'activation.
- **Erreur dépendances** : En cas de module manquant, relancez `pip install -e .` à l'intérieur du venv activé.
- **Erreur permissions écriture dans reports/** : Vérifiez que vous avez les droits d'écriture dans le dossier du projet ou lancez le terminal en tant qu'administrateur.

---

## Configuration
La configuration est gérée par priorité décroissante :
1. Variables d'environnement (préfixe `NTL_`, ex: `NTL_MYSQL_PASSWORD`)
2. Fichier `.env`
3. Fichier `config/config.yml`

## Codes de Retour (Exit Codes)
- `0` : SUCCESS
- `1` : WARNING
- `2` : CRITICAL
- `3` : ERROR
- `4` : UNKNOWN
