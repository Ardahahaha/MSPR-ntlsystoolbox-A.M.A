# CHECKLIST D'ACCEPTATION (UAT) - VALIDÉ

## 1. Fondations & CLI
- [x] L'outil se lance avec une seule commande Python (`python cli.py`).
- [x] Le menu interactif s'affiche au démarrage.
- [x] Chaque module est sélectionnable via le menu.
- [x] Le menu demande les arguments nécessaires (IP, table, plage réseau) si non fournis.
- [x] Les variables d'environnement (ex: NTL_MYSQL_PASSWORD) surchargent la config par défaut.

## 2. Module Diagnostic
- [x] Vérification AD/DNS retourne un statut (OK/KO).
- [x] Connexion MySQL vers WMS-DB validée.
- [x] Collecte CPU/RAM/Disque fonctionnelle sur Windows Server.
- [x] Collecte CPU/RAM/Disque fonctionnelle sur Ubuntu.
- [x] Uptime et version OS sont correctement extraits.

## 3. Module Sauvegarde WMS
- [x] Génération d'un fichier `.sql` contenant la structure et les données (100% Python).
- [x] Génération d'un fichier `.csv` pour une table donnée.
- [x] Vérification de la présence du fichier après export.
- [x] Le fichier est horodaté dans son nommage.

## 4. Module Audit Obsolescence
- [x] Scan d'une plage IP identifie les hôtes actifs (via socket).
- [x] L'OS est détecté pour au moins un type d'équipement (heuristique ports).
- [x] L'interrogation des dates EOL fonctionne pour un OS donné (API endoflife.date).
- [x] L'audit à partir d'un CSV d'inventaire génère les dates de fin de support.
- [x] Le rapport final (HTML/JSON) distingue les niveaux de criticité.

## 5. Sorties & Supervision
- [x] Chaque action produit une ligne lisible en console (Rich).
- [x] Un fichier JSON horodaté est créé pour chaque exécution majeure.
- [x] L'outil renvoie `exit 0` en cas de succès total.
- [x] L'outil renvoie les codes `1` (WARNING), `2` (CRITICAL), `3` (ERROR) selon la sévérité.

## 6. Livrables
- [x] Présence du fichier `README.md` (Installation / Usage).
- [x] Présence de la documentation technique (`TECHNICAL_DOSSIER_FR.md`).
- [x] Présence du manuel d'utilisation (`MANUAL.md`).
- [x] Rapport d'exécution de référence inclus (`EXEMPLE_EXEC_AUDIT.md`).
- [x] Code source structuré par modules indépendants.
