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
cp dbt_project/profiles.yml.example dbt_project/profiles.yml

docker compose up -d
make generate   # génère data/clients_commandes_brut.xlsx + vérité terrain
make ingest     # charge le classeur tel quel dans le schéma raw Postgres
make clean      # nettoie raw.* vers clean_staging.* (corrections + quarantaine)
make dbt        # dbt build : modèles stg_*/clean_* + tests de qualité bloquants
make report     # docs/rapport_qualite.html + docs/rapport_qualite.md
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

dbt (`make dbt`) lit `clean_staging.*` comme source (jamais `raw.*`
directement), construit des vues `stg_clients/produits/commandes`
(renommage, typage, dédoublonnage exact final en filet de sécurité) puis des
tables `clean_clients/produits/commandes` (enrichissement simple côté
commandes : `montant_total`, flag `commande_valide`), et fait tourner tous
les tests de qualité bloquants : contraintes génériques (clé primaire,
valeurs autorisées, intégrité référentielle) et 6 tests personnalisés
(format email, code postal, quantité positive, cohérence des dates,
garde-fou anti-régression sur le taux de quarantaine). dbt ne corrige
jamais rien : une anomalie détectée ici signale une règle de nettoyage
Python manquante, pas une requête SQL à écrire. Détail :
[specs/04-dbt.md](specs/04-dbt.md).

**Démonstration volontaire d'échec** : pour vérifier que les tests
détectent vraiment une régression (et pas seulement qu'ils passent sur des
données déjà propres), une ligne invalide a été insérée directement dans
`clean_staging.clients` en contournant Python (email sans `@`) — `dbt build`
échoue alors immédiatement sur `assert_email_valide`, la ligne a ensuite été
retirée et `dbt build` revérifié au vert. Détail dans la description de la
PR du milestone M4.

Le rapport qualité (`make report`) relit Postgres (`raw.*`,
`clean_staging.*`, `correction_log`, `quarantine`) ainsi que le fichier
vérité terrain et les résultats dbt, et génère `docs/rapport_qualite.html`
— un fichier HTML autonome (CSS inline, aucune dépendance réseau), lisible
sans contexte technique : réconciliation des volumes, répartition des
défauts par type, taux de qualité avant/après sur 4 dimensions
(complétude/unicité/validité/cohérence), comparaison au cas par cas avec la
vérité terrain (taux de correction mesuré, pas estimé), résultat des tests
dbt, et un extrait avant/après de 8 à 10 lignes par table avec les cellules
corrigées surlignées. Un résumé Markdown (`docs/rapport_qualite.md`) est
généré en parallèle. Réutilise directement les mêmes fonctions de
validation que le nettoyage (`pipeline/clean/*`), pour que le rapport
mesure exactement ce que le pipeline applique. Détail :
[specs/05-report.md](specs/05-report.md).

Détails complets à venir au fil des milestones (voir
[specs/07-deliverables.md](specs/07-deliverables.md)).
