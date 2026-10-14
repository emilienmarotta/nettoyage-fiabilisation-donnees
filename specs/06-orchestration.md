# 06 — Orchestration et tests du code

**Statut : Implemented**

## Objectif

Une commande unique enchaîne tout le pipeline, de façon reproductible et
idempotente, avec des tests automatisés sur le code de nettoyage.

## Orchestration (`pipeline/run.py` + `Makefile`)

Étapes enchaînées dans l'ordre, chacune s'arrêtant en erreur claire si elle
échoue (pas de continuation silencieuse) :
1. `generator/` (si demandé explicitement, pas à chaque run — le fichier
   brut est normalement stable) → `clients_commandes_brut.xlsx`.
2. `pipeline/ingest.py` → chargement `raw_*` + `structure_ecartee`.
3. `pipeline/clean/` (orchestré par `run.py`) → `clean_staging.*` +
   `correction_log` + `quarantine`.
4. `dbt build` (staging → clean + tests) → échoue si un test bloquant
   échoue ou si le seuil de quarantaine est dépassé (garde-fou
   anti-régression, pas une cible de qualité — 35 % clients/produits, 50 %
   commandes, voir [04-dbt.md](04-dbt.md)).
5. `pipeline/report.py` → `docs/rapport_qualite.html` + résumé Markdown.

Cibles `Makefile` : `make up` (docker compose), `make generate`, `make run`
(étapes 2 à 5), `make test` (tests unitaires Python), `make down`.

## Tests unitaires Python (`tests/`)

- Un fichier de test par module de règle (`tests/test_dates.py`,
  `test_nombres.py`, `test_identifiants.py`, `test_texte.py`,
  `test_contacts.py`, `test_doublons.py`) : cas normaux (chaque format
  valide du catalogue) + cas limites (valeurs invalides, vides, ambiguës) +
  vérification que la décision (corriger vs quarantaine) correspond à la
  charte de [00-vision.md](00-vision.md).
- `tests/test_idempotence.py` : exécute le pipeline complet deux fois sur le
  même fichier source (via `run.py` ou directement les étapes) et vérifie
  que l'état final de `clean_*`/`correction_log`/`quarantine` est
  strictement identique (mêmes lignes, pas de doublons supplémentaires).

## Critères de réussite

- [x] `make run` enchaîne ingestion → nettoyage → dbt build → rapport sans
  intervention manuelle.
- [x] `pytest` couvre chaque règle de nettoyage avec au moins un cas normal
  et un cas limite.
- [x] Le test d'idempotence passe : deux exécutions successives sur le même
  fichier donnent un résultat strictement identique.
