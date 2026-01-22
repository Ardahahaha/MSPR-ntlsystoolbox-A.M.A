# SPECIFICATION TECHNIQUE - NTL-SysToolbox

## 1. Informations Générales
- **Nom de l'outil** : NTL-SysToolbox
- **Objectif** : Industrialiser les vérifications d’exploitation, sécuriser les sauvegardes WMS et auditer l'obsolescence du parc.
- **Utilisateur cible** : DSI de NordTransit Logistics (NTL).

## 2. Contraintes Techniques (Strictes)
- **Langage** : 100% Python (Interdiction de : scripts bash, binaires externes, nmap, mysqldump, appels `subprocess`).
- **Compatibilité** : Windows et Linux (Exécutable/Scriptable sur les deux OS).
- **Interface** : Menu CLI interactif demandant les arguments nécessaires.
- **Configuration** : Fichier simple, surchargeable par variables d'environnement.
- **Sécurité** : Gestion des secrets (à détailler dans la doc technique).

## 3. Modules Fonctionnels

### 3.1 Module Diagnostic
- **Services AD / DNS** : Vérifier l’état sur les contrôleurs de domaine (DC01: 192.168.10.10, DC02: 192.168.10.11).
- **Base de données MySQL** : Tester le bon fonctionnement (WMS-DB: 192.168.10.21).
- **Santé Serveur (Windows Server)** : Version OS, uptime, CPU, RAM, Disques.
- **Santé Serveur (Ubuntu)** : Version OS, uptime, CPU, RAM, Disques (WMS-APP, WMS-DB, IPBX-VM).

### 3.2 Module Sauvegarde WMS
- **Export SQL** : Sauvegarde logique complète de la base MySQL au format SQL.
- **Export CSV** : Export d'une table spécifique au format CSV.
- **Contraintes** : Garantir l’existence, l’intégrité et la traçabilité des exports.

### 3.3 Module Audit d’Obsolescence
- **Scan Réseau** : Lister les composants sur une plage donnée (ex: 192.168.x.0/24).
- **Détection OS** : Tentative d'identification de l'OS des composants détectés.
- **Base de connaissance EOL** : Pour un OS, lister versions et dates de fin de vie (End Of Life).
- **Audit via CSV** : Analyser une liste (Composant, Version OS) et retourner les dates EOL.
- **Rapport** : Synthèse des composants non supportés ou en fin de vie imminente.

## 4. Exigences de Sortie
- **Format Humain** : Affichage console lisible et structuré.
- **Format Machine** : Fichiers JSON horodatés.
- **Codes de retour** : Exit codes standardisés (0: OK, >0: Erreur/Alerte) exploitables par outil de supervision (ex: Zabbix).

## 5. Livrables
- **Code Source** : Dépôt Git (historique propre, branches isolées, tags de version).
- **Documentation Technique & Fonctionnelle** : Justification des choix, architecture, gestion des secrets.
- **Manuel d'Installation & Utilisation** : Guide court pour déploiement autonome.
- **Exécution de référence** : Rapport d'audit d'obsolescence généré par l'outil.

## 6. Annexes (Données Métier)

### Plan d'adressage (Extraits)
- **Siège (Lille)** : 192.168.10.0/24 (AD/DNS, WMS, Téléphonie).
- **WH1 (Lens)** : 192.168.20.0/24.
- **WH2 (Valenciennes)** : 192.168.30.0/24.
- **WH3 (Arras)** : 192.168.40.0/24.
- **Cross-dock** : 192.168.50.0/24.

### Machines Virtuelles Critiques
- **DC01/DC02** : 192.168.10.10/11 (Windows Server).
- **WMS-DB** : 192.168.10.21 (Ubuntu 20.04 - MySQL).
- **WMS-APP** : 192.168.10.22 (Ubuntu 20.04).
- **IPBX-VM** : 192.168.10.40 (CentOS).
