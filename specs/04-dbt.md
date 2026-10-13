# 04 — Modèles et contrôles dbt

**Statut : Approved**

## Objectif

À partir des tables de staging produites par Python (`clean_staging.*`,
voir [03-cleaning.md](03-cleaning.md)), construire les modèles dbt finaux et
les tests de qualité **bloquants** décrits dans [00-vision.md](00-vision.md).

## Source dbt

`sources.yml` déclare `clean_staging.clients`, `.produits`, `.commandes`
(écrites par Python) comme sources dbt — dbt ne fait que lire, jamais
écrire dans ce schéma.

## Modèles

### Staging (`models/staging/`, vues)
- `stg_clients`, `stg_produits`, `stg_commandes` : renommage/typage final,
  **dédoublonnage exact final** (filet de sécurité en plus de celui fait en
  Python — `qualify row_number() over (...) = 1` sur la clé naturelle), rien
  d'autre. Pas de logique métier ici.

### Clean (`models/clean/`, tables)
- `clean_clients`, `clean_produits`, `clean_commandes` : jointures et
  enrichissements simples uniquement si nécessaires (ex. flag
  `commande_valide` dérivé). Pas de recalcul de règles déjà appliquées en
  Python — si une colonne nécessite une règle de nettoyage, c'est qu'il
  manque une règle côté Python, pas une requête dbt ad hoc.

## Tests génériques (schema YAML)

- `unique` + `not_null` sur chaque clé primaire (`client_id`, `produit_id`,
  `commande_id`) dans `clean_*`.
- `relationships` : `clean_commandes.client_id` → `clean_clients.client_id`,
  `clean_commandes.produit_id` → `clean_produits.produit_id`.
- `accepted_values` sur `categorie` (liste fixe de [01-generator.md](01-generator.md)),
  `segment`, `statut`.

## Tests personnalisés (`dbt_project/tests/`, SQL singuliers)

- `assert_email_valide.sql` : aucune ligne `clean_clients` avec un email ne
  respectant pas un format minimal (regex `^[^@\s]+@[^@\s]+\.[^@\s]+$`).
- `assert_code_postal_5_chiffres.sql` : aucun code postal ≠ 5 chiffres.
- `assert_quantite_strictement_positive.sql` : aucune `quantite` ≤ 0 dans
  `clean_commandes`.
- `assert_livraison_apres_commande.sql` : aucune `date_livraison <
  date_commande`.
- `assert_aucune_date_future.sql` : aucune date (commande/livraison) dans le
  futur par rapport à `current_date`.
- `assert_taux_quarantaine_sous_seuil.sql` : échoue si `count(quarantine) /
  (count(clean_*) + count(quarantine))` dépasse le seuil de 5 % défini dans
  [00-vision.md](00-vision.md) (lit la table `quarantine` écrite par
  Python).

Ces tests sont censés **toujours passer** sur `clean_*` (Python a déjà
éliminé les lignes invalides) — un échec signale un bug du nettoyage, pas une
tolérance de données sales.

## Démonstration volontaire d'échec

Documentée dans le README/rapport : réinjecter manuellement une ligne
invalide directement dans `clean_staging` (contournant Python) et montrer
que `dbt test` **échoue** — preuve que les tests sont réellement bloquants et
pas décoratifs.

## Critères de réussite

- [ ] `dbt build` passe à 100 % sur les données nettoyées par le pipeline
  normal.
- [ ] `dbt test` échoue si on réinjecte un défaut critique directement en
  base (démontré et documenté).
- [ ] Aucune logique de nettoyage dupliquée entre Python et dbt : dbt lit des
  données déjà propres, il ne les corrige pas.
