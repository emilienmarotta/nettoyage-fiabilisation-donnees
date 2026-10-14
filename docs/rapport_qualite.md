# Rapport qualité — résumé

> Projet démo, données 100 % fictives. Défauts injectés volontairement par le générateur (voir [specs/00-vision.md](../specs/00-vision.md)). Rapport complet : [rapport_qualite.html](rapport_qualite.html).

## Réconciliation des volumes

| Table | Lues | Structure écartée | Propres | Quarantaine | Fusionnés | OK |
|---|---:|---:|---:|---:|---:|---|
| clients | 354 | 9 | 243 | 79 | 23 | ✅ |
| produits | 159 | 9 | 133 | 17 | 0 | ✅ |
| commandes | 3009 | 9 | 1939 | 1061 | 0 | ✅ |

## Comparaison à la vérité terrain

Taux de correction mesuré : **98.1%** (cible ≥ 95%) — ✅ atteint.

## Tests dbt

19/19 tests dbt passés.
