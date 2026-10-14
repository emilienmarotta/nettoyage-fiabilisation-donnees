# 05 — Rapport qualité et avant/après

**Statut : Implemented**

## Objectif

Générer automatiquement, à chaque exécution du pipeline, un rapport qualité
lisible par un dirigeant (`docs/rapport_qualite.html`, autonome, avec un
résumé Markdown copié dans le README — décision prise en
[00-vision.md](00-vision.md)).

## Contenu du rapport

1. **Réconciliation des volumes** : lignes lues (par onglet) = lignes
   propres (`clean_*`) + lignes en quarantaine + lignes de structure
   écartées. Affiché comme une égalité vérifiée, pas juste des compteurs.
2. **Répartition par type de défaut** : nombre de corrections/rejets par
   catégorie du catalogue ([00-vision.md](00-vision.md)), avec motif pour la
   quarantaine.
3. **Taux de qualité avant/après**, sur les 4 dimensions suivantes, calculées
   sur les données brutes vs les données propres :
   - **Complétude** : % de champs obligatoires non vides.
   - **Unicité** : % de lignes sans doublon exact/quasi-doublon détecté.
   - **Validité** : % de valeurs conformes au format attendu (dates, emails,
     nombres, codes postaux).
   - **Cohérence** : % de lignes sans violation référentielle ou logique
     (client/produit existant, livraison ≥ commande, quantité/prix > 0).
4. **Comparaison avec la vérité terrain** (`data/verite_terrain.csv` du
   générateur, [01-generator.md](01-generator.md)) : pour chaque défaut
   injecté marqué `corrigeable`, vérifier que la valeur en `clean_*`
   correspond à la valeur parfaite d'origine ; pour chaque défaut marqué
   ambigu, vérifier qu'il est bien en quarantaine. Taux de correction global
   et par catégorie, comparé au seuil cible de 95 %.
5. **Résultat des tests dbt** (`dbt build` — parsé depuis
   `target/run_results.json`) : nombre de tests passés/échoués par modèle.
6. **Avant/après visuel** : extrait de 8 à 10 lignes présenté côte à côte
   (valeur brute / valeur propre), avec surlignage des cellules corrigées —
   le livrable le plus visuel du projet, pensé pour une capture d'écran.

## Implémentation (`pipeline/report.py`)

- Lit directement Postgres (`raw_*`, `clean_staging.*`/`clean_*`,
  `correction_log`, `quarantine`) + le fichier vérité terrain + le JSON de
  résultats dbt.
- Génère le HTML avec un template simple (Jinja2), CSS inline (autonome,
  pas de dépendance externe au chargement).
- Écrit aussi un résumé Markdown (chiffres clés + lien vers le HTML) réutilisé
  tel quel dans le README en M7.

## Critères de réussite

- [x] Le rapport s'ouvre comme fichier HTML autonome (aucune dépendance
  réseau), lisible sans contexte technique.
- [x] La réconciliation des volumes est exacte à chaque exécution (0 ligne
  perdue).
- [x] Le taux de correction mesuré contre la vérité terrain est affiché et
  comparé explicitement au seuil de 95 % (98,1 % mesuré).
- [x] L'avant/après sur 8-10 lignes se comprend en moins de 10 secondes par
  quelqu'un qui ne connaît pas la data (vérifié visuellement par l'auteur
  avant capture).
