# Manuel d'Utilisation - NTL-SysToolbox

Ce guide est destiné aux équipes DSI pour l'exploitation de la boîte à outils NTL-SysToolbox.

## 1. Exécution Rapide

L'outil se lance via le script racine `cli.py` :

```bash
python cli.py
```

Un menu interactif s'affiche. Utilisez les flèches du clavier pour naviguer et la touche Entrée pour valider.

## 2. Procédures par Module

### Module 1 : Diagnostic
- **Usage** : Utilisé lors d'incidents de connectivité ou pour un check-up hebdomadaire.
- **Vérifications** : Résolution DNS, accessibilité AD (LDAP/SMB), état de la base MySQL WMS.
- **Artefacts** : Un rapport JSON est généré à chaque exécution dans `outputs/reports/diagnostic_YYYYMMDD_HHMMSS.json`.

### Module 2 : Sauvegarde WMS
- **Usage** : Sauvegarde ponctuelle avant maintenance ou export de données métier.
- **Sauvegarde SQL** : Génère un dump logique (structure + données) sans outils externes.
- **Export CSV** : Permet d'extraire une table spécifique (ex: `stocks`, `users`) pour analyse.
- **Emplacement** : Les fichiers sont stockés dans `outputs/backups/`.

### Module 3 : Audit d'Obsolescence
- **Usage** : Inventaire des serveurs et vérification des dates de fin de vie (EOL).
- **Scan Réseau** : Scanne une plage (ex: `192.168.10.0/24`) pour détecter les OS (heuristique ports).
- **Import CSV** : Vous pouvez fournir votre propre inventaire au format `IP,OS,Version`.
- **Rapports** : Génère un rapport HTML visuel dans `outputs/reports/audit_YYYYMMDD_HHMMSS.html`.

## 3. Gestion des Secrets

Ne modifiez pas le code pour changer les mots de passe. Utilisez un fichier `.env` à la racine :

```ini
NTL_MYSQL_PASSWORD=votre_mot_de_passe
NTL_AD_PASSWORD=votre_mot_de_passe
```

## 4. Interprétation des Résultats

L'outil retourne des codes standardisés :
- **SUCCESS (0)** : Tout est nominal.
- **WARNING (1)** : Problème mineur (ex: latence élevée, EOL proche < 6 mois).
- **CRITICAL (2)** : Problème majeur (ex: service injoignable, EOL dépassée).
- **ERROR (3)** : Le script n'a pas pu s'exécuter correctement.
