# 02 — Ingestion brute

**Statut : Implemented**

## Objectif

Lire le classeur `clients_commandes_brut.xlsx` et charger chaque onglet tel
quel (tout en texte, sans conversion automatique de type) dans le schéma
`raw` de Postgres, en détectant et écartant proprement les lignes de
structure (total, en-tête répété, ligne vide) — journalisées, jamais
supprimées en silence (principe 1 de [00-vision.md](00-vision.md)).

## Tables raw

`raw.raw_clients`, `raw.raw_produits`, `raw.raw_commandes` : toutes les
colonnes métier en `text` (aucune colonne typée nombre/date), plus colonnes
techniques communes :
- `source_fichier` (nom du classeur)
- `source_onglet`
- `ligne_origine` (numéro de ligne Excel d'origine, pour traçabilité)
- `charge_le` (timestamp d'ingestion)

Clé technique : `(source_fichier, source_onglet, ligne_origine)` — permet de
rejouer l'ingestion de façon idempotente (voir ci-dessous).

## Table des lignes de structure écartées

`raw.structure_ecartee` : `source_fichier`, `source_onglet`, `ligne_origine`,
`contenu_brut` (JSON ou texte de la ligne complète), `raison`
(`ligne_total` / `en_tete_repete` / `ligne_vide` / `banniere` /
`colonne_inutile`).

## Détection des lignes de structure

- **Ligne de total** : heuristique explicite et documentée (ex. une cellule
  contient `Total`, `TOTAL`, `Sous-total`, ou la ligne a beaucoup moins de
  valeurs renseignées que les colonnes attendues avec un total numérique en
  fin de ligne). Règle écrite en commentaire de code, pas de détection
  « magique ».
- **En-tête répété** : ligne dont les valeurs correspondent exactement (ou
  après normalisation casse/espaces) aux noms de colonnes attendus, à une
  position ≠ ligne 1.
- **Ligne vide** : toutes les cellules vides/espaces.
- **Bannière (cellule fusionnée)** : seule la première colonne porte une
  valeur (le reste de la cellule fusionnée est lu vide par openpyxl) et
  cette valeur commence par le marqueur explicite `---`.
- **Colonne inutile** : colonne présente dans le fichier mais absente du
  schéma attendu — ignorée et journalisée une fois par onglet (pas par
  ligne).

## Idempotence de l'ingestion

- Avant de charger, `TRUNCATE` (ou `DELETE WHERE source_fichier = ...`) des
  tables `raw_*` et `structure_ecartee` pour ce fichier source, puis
  rechargement complet. Rejouer l'ingestion sur le même fichier donne un
  état `raw` strictement identique.

## Critères de réussite

- [ ] Toutes les colonnes des tables `raw_*` sont de type texte.
- [ ] Chaque ligne du classeur source finit soit dans une table `raw_*`,
  soit dans `structure_ecartee`, jamais perdue.
- [ ] Rejouer l'ingestion sur le même fichier ne crée aucun doublon et donne
  un état identique (test d'idempotence).
- [ ] Le compte de lignes lues par onglet = lignes chargées en `raw_*` +
  lignes dans `structure_ecartee` pour cet onglet (vérifié par une requête
  de réconciliation, reprise dans le rapport qualité).
