# Dossier Technique - NTL-SysToolbox

## 1. Introduction
NTL-SysToolbox est une suite logicielle développée en Python pour répondre aux besoins de diagnostic et de maintenance des infrastructures SI (Siège et Entrepôts). L'accent est mis sur la portabilité (Windows/Linux) et l'absence totale de dépendances binaires externes.

## 2. Architecture Logicielle
L'outil suit une architecture modulaire :

- **Core** : Gestion du menu interactif (`questionary`) et du routage.
- **Modules** :
    - `diagnostic` : Santé AD, DNS, MySQL.
    - `backup_wms` : Sauvegarde logique DB.
    - `audit_obsolescence` : Scan réseau et EOL.
- **Utils** : Gestion de la configuration, des sorties (Rich/JSON) et des codes de retour.

## 3. Choix Techniques et Compromis

### 100% Python
- **Pourquoi** : Facilité de déploiement sur des serveurs restreints où l'installation d'outils comme `nmap` ou `mysql-client` est impossible ou non souhaitée.
- **Compromis** : Le scan réseau est moins performant qu'un outil en C (comme nmap) mais suffisant pour un inventaire minimal sur des sous-réseaux de classe C.

### Sauvegarde Logique Native
- **Implémentation** : Utilisation de `pymysql` pour reconstruire les schémas via `SHOW CREATE TABLE` et extraire les données.
- **Limites** : Pour des bases de données de plusieurs To, un outil natif (mysqldump) serait préférable. Pour le WMS actuel, la solution Python offre la flexibilité nécessaire sans binaire externe.

### Heuristique d'OS
- **Méthode** : Détection via l'ouverture de ports caractéristiques (80/443 pour Web, 135/445 pour Windows/SMB, 22 pour Linux/SSH).
- **Fiabilité** : Approche "best effort". En cas d'ambiguïté, le module privilégie la sécurité en signalant le composant comme "Inconnu/À vérifier".

## 4. Sécurité
- Les secrets ne sont jamais stockés en dur.
- Support natif des variables d'environnement pour une intégration sécurisée dans des pipelines CI/CD ou des ordonnanceurs.
- Validation des entrées utilisateur pour prévenir les injections.

## 5. Maintenance
Le code est structuré de manière à faciliter l'ajout de nouveaux modules. Chaque module est indépendant et communique via des objets de réponse standardisés.
