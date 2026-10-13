# CLAUDE.md

Contexte et conventions de ce projet, pour que les prochaines sessions
Claude Code reprennent sans réexpliquer. La session change à chaque
milestone : ce fichier + [ROADMAP.md](ROADMAP.md) + la spec du milestone en
cours doivent suffire à redémarrer.

## Projet

Projet portfolio fictif (profil Malt, data engineer) : pipeline de
nettoyage et de fiabilisation de données pour une PME fictive de commerce de
gros (clients/produits/commandes saisis à la main dans Excel, pleins de
défauts). Données 100 % fictives. Vision complète :
[specs/00-vision.md](specs/00-vision.md).

## Méthode : specs-driven

Chaque fonctionnalité a une spec dans [specs/](specs/), **écrite et validée
avant d'être codée**. Ne pas coder en dehors d'une spec existante ; si le
besoin évolue en cours d'implémentation, mettre à jour la spec en premier,
puis le code. Statuts : `Draft` → `Approved` → `Implemented` (champ en haut
de chaque fichier spec, et dans [specs/README.md](specs/README.md)). En fin
de milestone, repasser le statut de la/des spec(s) correspondantes à
`Implemented` et cocher la case du milestone dans [ROADMAP.md](ROADMAP.md).

## Roadmap

Milestones dans [ROADMAP.md](ROADMAP.md), un par grande brique (cadrage,
générateur, ingestion, nettoyage Python, dbt, rapport, orchestration,
livrables).

## Contrainte de design critique

Répartition stricte des responsabilités (voir
[specs/00-vision.md](specs/00-vision.md)) :

- **Python (`generator/`, `pipeline/`)** : génération des données fictives,
  ingestion brute, et tout le nettoyage "pénible en SQL" (parsing de
  formats mixtes, dates série Excel, normalisation de texte, rapprochement
  de quasi-doublons). Produit des données déjà propres **ou explicitement
  rejetées en quarantaine** — jamais de données ambiguës passées en silence.
- **dbt** : règles de cohérence référentielle, dédoublonnage exact final
  (filet de sécurité), et **tous les tests de qualité bloquants**. dbt ne
  corrige rien : si une colonne a besoin d'une règle de nettoyage, c'est une
  règle Python manquante, pas une requête dbt à écrire.
- **Jamais de perte silencieuse de donnée** : chaque ligne lue finit dans
  les tables propres, dans `quarantine`, ou dans `structure_ecartee` — avec
  une raison. La réconciliation (lues = propres + quarantaine + structure)
  est vérifiée et affichée dans le rapport qualité à chaque exécution.

## Conventions de nommage dbt

- Sources : `clean_staging.*` (écrit par Python, lu par dbt comme source,
  jamais écrit par dbt).
- Modèles : `stg_*` (staging, vues, renommage/typage/dédoublonnage exact
  final uniquement) → `clean_*` (tables finales, destinées aux tests et à la
  consultation).
- Chaque modèle et chaque test personnalisé documenté, avec des descriptions
  qui reprennent mot pour mot la charte de règles de
  [specs/00-vision.md](specs/00-vision.md).

## Stack

Docker Compose (PostgreSQL), Python (venv à la racine du projet : `.venv/`),
dbt-postgres, SQL. Pas d'hébergement : tout tourne en local.

## Workflow Git

- Jamais de commit ni de push direct sur `main`.
- Une branche par milestone : `milestone/m{N}-{slug}` (ex.
  `milestone/m1-generateur`).
- À la fin d'un milestone : commit, push de la branche, ouverture d'une PR
  vers `main` avec `gh pr create` (description courte + plan de test).
- Quand l'utilisateur confirme que la PR a été mergée (sur GitHub) :
  `git checkout main && git pull && git branch -d <branche>`. La branche
  distante est supprimée automatiquement au merge (`delete_branch_on_merge`
  activé sur le repo) ; sinon, la supprimer explicitement
  (`git push origin --delete <branche>`).
- Ne jamais supposer une validation implicite : attendre que l'utilisateur
  confirme explicitement le merge avant de nettoyer les branches.
- Dépôt GitHub public (`emilienmarotta/nettoyage-fiabilisation-donnees`),
  aucun secret commité (`.env` ignoré, seul `.env.example` versionné).

## Honnêteté du contenu

Rappeler partout où c'est pertinent (README, rapport qualité, code) que les
données sont fictives, que les défauts sont injectés volontairement par le
générateur (ce qui permet de mesurer un vrai taux de correction), et que
tout bénéfice annoncé est une hypothèse de scénario, jamais un résultat
mesuré réel (cf. spec 00).

## Relation avec les projets 1 et 2

Même univers métier (même PME fictive de commerce de gros — voir
[rapport-commercial-auto](https://github.com/emilienmarotta/rapport-commercial-auto)
et [tableau-de-bord-pilotage](https://github.com/emilienmarotta/tableau-de-bord-pilotage)),
mais dépôt **techniquement autonome** : pas de Postgres partagé, pas de
dépendance d'infra entre les dépôts (raison détaillée dans
[specs/00-vision.md](specs/00-vision.md)).
