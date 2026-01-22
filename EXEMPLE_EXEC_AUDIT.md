# Exemple d'Exécution : Audit d'Obsolescence

Ce document trace une exécution de référence du module d'audit pour validation.

## 1. Commande Lancée
```bash
python cli.py
# Sélection de "3. Module Audit d'Obsolescence"
# Sélection de "Scan Réseau & Audit"
# Saisie de la plage : 192.168.10.0/24
```

## 2. Trace Console (Extrait)
```text
[INFO] Démarrage du scan réseau sur 192.168.10.0/24...
[INFO] 192.168.10.1 : Port 80 ouvert -> OS probable: Linux/Generic
[INFO] 192.168.10.21 : Ports 135, 445 ouverts -> OS probable: Windows
[INFO] 192.168.10.22 : Port 22 ouvert -> OS probable: Linux (Ubuntu/Debian)

[INFO] Vérification des dates EOL via endoflife.date...
[SUCCESS] Audit terminé.
```

## 3. Résultats et Artefacts

### Rapport JSON
**Emplacement** : `outputs/reports/audit_20260122_103005.json`
**Extrait** :
```json
{
  "metadata": {
    "module": "audit_obsolescence",
    "timestamp": "2026-01-22T10:30:05",
    "status": "WARNING",
    "exit_code": 1
  },
  "data": {
    "hosts": [
      {
        "ip": "192.168.10.21",
        "os": "windows",
        "version": "10",
        "eol": "2025-10-14",
        "status": "EOL_EXPIRED"
      },
      {
        "ip": "192.168.10.22",
        "os": "ubuntu",
        "version": "22.04",
        "eol": "2027-04-01",
        "status": "SUPPORTED"
      }
    ]
  }
}
```

### Rapport HTML
**Emplacement** : `outputs/reports/audit_20260122_103005.html`
**Description** : Un tableau trié par statut (Rouge pour EOL dépassée, Orange pour EOL proche, Vert pour Supporté).

## 4. Code de Retour
L'outil a retourné `1` (WARNING) car au moins un équipement (`192.168.10.21`) a dépassé sa date de fin de vie.
