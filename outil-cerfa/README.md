# Outil CERFA - MML

Application qui génère automatiquement les CERFA à partir des factures Sellsy.

À chaque lancement, l'outil récupère les factures d'une période, et pour chacune :

- crée un **CERFA 1301-SD** (attestation TVA) avec l'identité du client,
- crée un **CERFA 15497-04** (fiche d'intervention) pour **chaque produit dont le nom contient "groupe extérieur"**,

puis range les PDF dans le dossier de sortie, classés par mois (`CERFA/AAAA-MM/`).

Les cases à cocher sont laissées **vides** (à cocher à la main ensuite). Les PDF restent **modifiables**.

## Ce que l'outil remplit

CERFA 15497-04

- Bloc opérateur, n° d'attestation et signataire : valeurs fixes (MML), définies en haut de `cerfa_fill.py`.
- Détenteur : le client de la facture.
- Date du contrôle : la date de la facture.
- Référence matériel : le nom du produit "groupe extérieur".

CERFA 1301-SD

- Nom, prénom, adresse, code postal, commune du client.
- Adresse des travaux : identique à l'adresse client par défaut.
- "Fait à" et date : commune du client et date de la facture.

## Contenu du dossier

| Fichier | Rôle |
|---|---|
| `app.py` | L'application (fenêtre avec un bouton "Générer") |
| `core.py` | La logique : récupère les factures et génère les CERFA |
| `sellsy_client.py` | Connexion à Sellsy (API v1) |
| `cerfa_fill.py` | Remplissage des deux PDF |
| `modeles/` | Les deux CERFA vierges (gabarits avec champs) |
| `config.example.json` | Modèle de configuration à recopier en `config.json` |
| `requirements.txt` | Les dépendances Python |

## Installation (une seule fois)

1. Installer Python 3 (python.org).
2. Installer les dépendances :

   ```
   pip install -r requirements.txt
   ```

3. Copier `config.example.json` en `config.json` et y coller les 4 codes Sellsy
   (Réglages > API/OAuth2 dans Sellsy : Consumer token/secret + Utilisateur token/secret).
4. Dans `config.json`, régler `dossier_sortie` sur le dossier voulu.
   Astuce : pour avoir le cloud gratuitement, pointer vers un dossier situé
   dans le dossier Google Drive de l'ordinateur, il se synchronise tout seul.

## Utilisation

Double-cliquer sur l'application (ou `python app.py`), choisir la période
(par défaut : la veille), cliquer "Générer les CERFA". Les PDF apparaissent
dans le dossier de sortie.

## Installation sur Windows (le plus simple)

Le dossier contient des fichiers `.bat` à double-cliquer, dans l'ordre :

1. Installer Python 3 depuis python.org (cocher "Add Python to PATH" à l'installation).
2. Copier `config.example.json` en `config.json` et y coller les 4 codes Sellsy.
3. Double-clic sur **Installer-Windows.bat** (une seule fois) : installe les composants.
4. Double-clic sur **Lancer-CERFA.bat** : ouvre la fenêtre. On choisit la période,
   on clique "Go", les CERFA se créent dans le dossier `CERFA`.

C'est tout. L'outil fonctionne dès cette étape.

### Version .exe autonome (Python plus nécessaire)

Pour livrer un seul fichier `.exe` que le client lance sans rien installer :
double-clic sur **Construire-exe-Windows.bat**. Le résultat est `dist/CERFA-MML.exe`.
Placer `config.json` à côté de ce `.exe`, et c'est un vrai double-clic autonome.

Cette compilation se fait sur une machine Windows (un binaire Windows ne se
fabrique que sur Windows).

## Mac

Même principe, en ligne de commande :

```
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --windowed --name "CERFA-MML" --add-data "modeles:modeles" app.py
```

Résultat dans `dist/CERFA-MML.app`, avec `config.json` à côté.

## État : testé en réel

La connexion Sellsy a été testée avec les vrais tokens :

- authentification OK ;
- récupération des factures avec filtre par date de création (fiable, côté client) ;
- détection des produits "groupe extérieur" sur le nom du produit
  (un cache dont la description mentionne le groupe extérieur n'est pas capté) ;
- extraction du client, particulier comme société (SIRET inclus si présent) ;
- génération des deux CERFA validée sur des factures réelles.

Restes optionnels :

- Signature de l'opérateur : si tu veux qu'elle soit apposée automatiquement,
  fournir une image PNG de la signature, elle sera ajoutée sur le 15497.
- Choix de la date de filtrage : actuellement la date de création de la facture
  dans Sellsy. Modifiable dans `sellsy_client.lister_factures` si tu préfères la
  date du document.

## Automatiser chaque matin (optionnel)

Pour un lancement quotidien sans clic, planifier `python core_run.py` (ou l'exécutable)
via le Planificateur de tâches Windows ou un cron Mac. Le mode automatique se
branche sur `core.generer` avec la date de la veille.

## Version EN LIGNE (rien à installer chez le client)

Fichier `web_app.py` : une page web avec deux dates et un bouton "Go". Au clic,
elle prépare les CERFA de la période et les renvoie dans un fichier ZIP à
télécharger. Le client range ensuite les PDF où il veut. Aucune installation
sur son ordinateur.

Test en local : `python web_app.py` puis ouvrir http://localhost:8000

### Mettre en ligne (le plus simple, gratuit)

Sur Render.com (offre gratuite), sans serveur à gérer :

1. Déposer ce dossier dans un dépôt GitHub (ou l'importer dans Render).
2. Render détecte `render.yaml` et crée le service automatiquement.
3. Dans Render, renseigner les 4 variables d'environnement Sellsy :
   SELLSY_CONSUMER_TOKEN, SELLSY_CONSUMER_SECRET, SELLSY_USER_TOKEN, SELLSY_USER_SECRET.
   Les tokens restent donc dans le serveur, pas dans le code.
4. Render fournit une adresse type `https://cerfa-mml.onrender.com` à donner au client.

Les tokens sont lus depuis ces variables d'environnement (voir `charger_config`),
aucun `config.json` n'est nécessaire en ligne.

### À prévoir avant d'ouvrir au client

La page génère des CERFA depuis les données Sellsy. Il faut la protéger par un
mot de passe simple pour que l'adresse ne soit pas utilisable par n'importe qui.
Petit ajout à faire avant la mise en service.
