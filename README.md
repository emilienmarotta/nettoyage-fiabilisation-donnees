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
make run        # ingestion → nettoyage → dbt build → rapport qualité (à venir)
```

Le générateur (`make generate`) produit, de façon déterministe (graine
fixe) :
- `data/parfait/{clients,produits,commandes}.csv` : le jeu de données
  cohérent sans défaut ;
- `data/clients_commandes_brut.xlsx` : le classeur désordonné (3 onglets,
  tous les défauts du catalogue) ;
- `data/verite_terrain.csv` : chaque défaut injecté, avec la valeur
  d'origine et s'il est censé être corrigé ou mis en quarantaine.

Détails complets à venir au fil des milestones (voir
[specs/07-deliverables.md](specs/07-deliverables.md)).
