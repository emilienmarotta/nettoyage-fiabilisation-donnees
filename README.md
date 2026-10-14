# Nettoyage et fiabilisation de données

> Projet de démonstration (portfolio Malt — profil data engineer).
> **Données 100 % fictives.**

## Le problème

Une PME fictive de commerce de gros tient depuis des années ses clients, ses
produits et ses commandes dans des fichiers Excel remplis à la main par
plusieurs personnes : doublons, dates dans trois formats différents,
montants écrits de dix façons, champs vides, lignes de total au milieu des
données. Impossible de s'appuyer dessus pour décider ou pour alimenter un
tableau de bord.

## La solution

Un pipeline (Python → PostgreSQL → dbt) qui lit ces fichiers, corrige ce qui
peut l'être de façon sûre et traçable, met de côté ce qui ne peut pas l'être
(avec la raison), charge le tout dans une base propre, et vérifie
automatiquement la qualité à chaque exécution — avec un rapport avant/après
lisible par un dirigeant.

> **Bénéfice (hypothèse de scénario, pas une mesure réelle)** : remplacer des
> heures de nettoyage manuel Excel par une exécution automatisée, rejouable
> et vérifiée, avant chaque mise à jour d'un tableau de bord.

Ce projet est en cours de construction, milestone par milestone (méthode
specs-driven). Voir [ROADMAP.md](ROADMAP.md) pour l'avancement et
[specs/](specs/) pour le détail de chaque brique.

## Faire tourner le projet

```bash
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

docker compose up -d
make generate   # génère data/clients_commandes_brut.xlsx + vérité terrain
make ingest     # charge le classeur tel quel dans le schéma raw Postgres
make clean      # nettoie raw.* vers clean_staging.* (corrections + quarantaine)
make run        # + dbt build + rapport qualité (à venir)
```

Le générateur (`make generate`) produit, de façon déterministe (graine
fixe) :
- `data/parfait/{clients,produits,commandes}.csv` : le jeu de données
  cohérent sans défaut ;
- `data/clients_commandes_brut.xlsx` : le classeur désordonné (3 onglets,
  tous les défauts du catalogue) ;
- `data/verite_terrain.csv` : chaque défaut injecté, avec la valeur
  d'origine et s'il est censé être corrigé ou mis en quarantaine.

L'ingestion (`make ingest`) lit ce classeur onglet par onglet, charge
chaque ligne telle quelle (tout en texte, sans conversion de type) dans
`raw.raw_clients` / `raw.raw_produits` / `raw.raw_commandes`, et écarte
proprement les lignes de structure (total, en-tête répété, ligne vide,
bannière, colonne inutile) dans `raw.structure_ecartee` avec la raison —
rejouable sans dupliquer (idempotent par fichier source). Détail :
[specs/02-ingestion.md](specs/02-ingestion.md).

Le nettoyage (`make clean`) relit `raw.*`, applique la charte de règles
(parsing de dates/nombres/identifiants multi-formats, normalisation de
texte et de contacts, rapprochement de quasi-doublons clients) et écrit
chaque ligne soit dans `clean_staging.{clients,produits,commandes}`, soit
dans `clean_staging.quarantine` avec un motif — jamais les deux, jamais
perdue en silence. Chaque correction appliquée est tracée dans
`clean_staging.correction_log` (valeur avant/après, règle appliquée).
Rejouable sans dupliquer. Détail :
[specs/03-cleaning.md](specs/03-cleaning.md).

Détails complets à venir au fil des milestones (voir
[specs/07-deliverables.md](specs/07-deliverables.md)).
