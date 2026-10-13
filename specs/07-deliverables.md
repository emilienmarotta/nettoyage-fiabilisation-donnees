# 07 — Livrables pour le profil Malt

**Statut : Approved**

## Objectif

Finaliser les livrables de présentation du projet, en s'appuyant sur ce qui
a déjà été produit par les milestones précédents (rapport, avant/après,
résultats dbt) — pas de nouveau calcul, uniquement de la mise en forme et de
la capture.

## Livrables

1. **Capture avant/après** sur l'extrait de 8-10 lignes du rapport qualité
   ([05-report.md](05-report.md)) — exportée en image dans `docs/`.
2. **Capture du rapport qualité** (chiffres clés : réconciliation, taux de
   qualité avant/après, taux de correction vs vérité terrain) et du résultat
   `dbt test` (`dbt build` en sortie console ou `docs/dbt_build.png`).
3. **3 lignes de présentation** (problème / solution / bénéfice, formulé
   comme hypothèse de scénario, jamais un résultat mesuré réel — cf.
   [00-vision.md](00-vision.md)), intégrées au README et réutilisables
   telles quelles sur le profil Malt.
4. **README final** : suit la convention déjà utilisée sur les projets 1 et
   2 (titre + bandeau « démo, données fictives » + section « Le problème » /
   « La solution » + bénéfice hypothétique encadré), complétée par :
   - instructions `docker compose up` + `make run` reproductibles de bout en
     bout ;
   - lien vers chaque spec ;
   - résumé Markdown du rapport qualité (chiffres clés) ;
   - mention explicite de la charte de règles et du principe « jamais de
     perte silencieuse ».

## Critères de réussite

- [ ] Les captures sont présentes dans `docs/` et référencées dans le
  README.
- [ ] Les 3 lignes de présentation sont écrites et formulées en hypothèse de
  scénario (pas de chiffre présenté comme un résultat mesuré réel).
- [ ] Le README permet à quelqu'un qui découvre le projet de comprendre en
  moins d'une minute le problème, la solution et comment le faire tourner.
- [ ] `docker compose up` + `make run` reproduisent le fichier brut, le
  pipeline et le rapport sans étape manuelle non documentée.
