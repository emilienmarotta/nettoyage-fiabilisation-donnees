# 03 — Nettoyage Python, journal des corrections, quarantaine

**Statut : Approved**

## Objectif

Implémenter en Python la charte de règles de [00-vision.md](00-vision.md),
lue depuis les tables `raw_*`, pour produire :
- des lignes propres, prêtes à être chargées pour dbt ;
- un **journal des corrections** complet ;
- une **table de quarantaine** complète, avec motif.

## Organisation du code (`pipeline/clean/`)

Un module par famille de règle, chacun testé unitairement
(`tests/test_clean_*.py`) :
- `dates.py` : parsing multi-format (JJ/MM/AAAA, AAAA-MM-JJ, texte FR,
  numéro de série Excel) → date ISO ou `None` + motif si invalide/aberrante.
- `nombres.py` : parsing multi-format (séparateurs milliers/décimale,
  symboles `€`/`%`) → `Decimal` ou `None` + motif.
- `identifiants.py` : code postal (recomplétion zéro), SIRET (notation
  scientifique → entier), code produit (casse).
- `texte.py` : normalisation champs vides (`N/A`, `-`, `null`, espaces) →
  `NULL`, normalisation catégories via table de correspondance.
- `contacts.py` : validation email (motif si invalide, jamais corrigé),
  normalisation téléphone.
- `doublons.py` : détection doublons exacts et quasi-doublons (normalisation
  + similarité de chaînes + comparaison ville/code postal), avec la règle de
  seuil de fusion automatique (0,92) de [00-vision.md](00-vision.md).

Chaque fonction de règle est **pure** : entrée = valeur brute (+ contexte
minimal si besoin, ex. ville pour les quasi-doublons), sortie =
`(valeur_corrigee, correction_appliquee: bool, motif_si_rejet: str | None)`.
Pas d'accès direct à la base dans ces modules — testable sans Postgres.

## Journal des corrections (`correction_log`)

Colonnes : `id`, `source_fichier`, `source_onglet`, `ligne_origine`,
`table_cible` (clients/produits/commandes), `colonne`, `valeur_avant`,
`valeur_apres`, `regle_appliquee` (nom de la fonction/règle), `corrige_le`.

Une ligne par correction individuelle (une ligne source avec 3 colonnes
corrigées = 3 lignes dans `correction_log`).

## Table de quarantaine (`quarantine`)

Colonnes : `id`, `source_fichier`, `source_onglet`, `ligne_origine`,
`table_cible`, `donnees_brutes` (JSON de la ligne complète), `motif_rejet`
(un des motifs normalisés listés dans [00-vision.md](00-vision.md), ex.
`date_invalide`, `email_invalide`, `reference_inexistante`...), `detecte_le`.

Une ligne de quarantaine par ligne source rejetée (pas par colonne) :
si plusieurs colonnes d'une même ligne sont invalides, `motif_rejet` liste
tous les motifs séparés par `;`.

## Ordre de traitement

1. Normalisation colonne par colonne (dates, nombres, identifiants, texte,
   contacts) → correction ou motif de rejet par colonne.
2. Une ligne avec au moins un motif de rejet sur une colonne obligatoire
   part en quarantaine (la ligne entière, pas seulement la colonne).
3. Détection des doublons/quasi-doublons sur les lignes restantes
   (clients uniquement — les produits et commandes n'ont pas de notion de
   quasi-doublon dans ce projet).
4. Vérification des références (commande → client/produit existant dans les
   données déjà validées) : rupture → quarantaine motif
   `reference_inexistante`.
5. Écriture des lignes survivantes dans des tables intermédiaires
   `clean_staging.clients`, `.produits`, `.commandes` (schéma dédié, lu
   ensuite par dbt comme source) + écriture complète de `correction_log` et
   `quarantine`.

## Idempotence

Même logique que l'ingestion : le nettoyage est rejoué entièrement à chaque
exécution à partir de `raw_*` (pas d'état intermédiaire accumulé),
`correction_log`/`quarantine`/tables de staging nettoyées puis
régénérées pour le fichier source traité.

## Critères de réussite

- [ ] Une fonction testée par règle du catalogue, cas normaux et cas limites
  (tests unitaires `tests/test_clean_*.py`).
- [ ] 100 % des lignes `raw_*` finissent soit en staging propre, soit en
  quarantaine (réconciliation vérifiée).
- [ ] `correction_log` permet de retrouver, pour n'importe quelle correction,
  la valeur brute d'origine et la règle appliquée.
- [ ] Rejouer le nettoyage sur le même `raw_*` donne un résultat identique
  (test d'idempotence).
