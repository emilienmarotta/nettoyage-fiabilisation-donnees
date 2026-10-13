# 00 — Vision, principes, charte de règles, seuils qualité

**Statut : Approved**

## Contexte et objectif

> Projet de démonstration pour le profil Malt d'Emilien Marotta (offre
> « pipelines de données fiables »). Données 100 % fictives.

Scénario : une PME fictive de commerce de gros (même univers que les projets
portfolio [rapport-commercial-auto](https://github.com/emilienmarotta/rapport-commercial-auto)
et [tableau-de-bord-pilotage](https://github.com/emilienmarotta/tableau-de-bord-pilotage) —
mêmes types de clients, produits, régions) tient depuis des années ses
clients, produits et commandes dans des fichiers Excel remplis à la main.
Résultat : doublons, dates dans trois formats différents, montants écrits de
dix façons, champs vides, lignes de total au milieu des données.

Solution : un pipeline qui lit ces fichiers, corrige ce qui peut l'être de
façon sûre, met de côté ce qui ne peut pas l'être (avec la raison), charge le
tout dans une base propre, et vérifie automatiquement la qualité à chaque
exécution.

Le projet doit démontrer :
- un avant/après très parlant pour un non-technicien ;
- des règles de nettoyage explicites, traçables et rejouables, sans perte
  silencieuse de donnée ;
- des contrôles qualité automatiques (tests dbt) qui bloquent le pipeline si
  les données sont mauvaises ;
- un rapport qualité lisible par un dirigeant.

**Outils imposés :** Python (pandas, openpyxl), SQL (PostgreSQL), dbt.

## Lien avec les projets 1 et 2

Dépôt **autonome** : pas de Postgres partagé, pas de dépendance d'infra
envers `rapport-commercial-auto` ou `tableau-de-bord-pilotage`. Cohérence
maintenue uniquement au niveau du **scénario métier** (même PME fictive, même
univers produit/client/région). `docker compose up` doit suffire à faire
tourner ce dépôt seul.

## Principes directeurs

1. **Ne jamais perdre une donnée en silence.** Chaque ligne d'entrée finit
   soit dans les tables propres, soit dans la table de quarantaine avec un
   motif de rejet, soit dans le journal des lignes de structure écartées
   (total, en-tête répété, ligne vide). Réconciliation : lignes lues = lignes
   propres + quarantaine + structure écartées, affichée dans le rapport.
2. **Tracer chaque correction.** Le journal des corrections (`correction_log`)
   indique : fichier source, onglet, ligne d'origine, colonne, valeur avant,
   valeur après, règle appliquée.
3. **Corriger seulement ce qui est sans ambiguïté.** Une règle documentée
   s'applique toujours de la même façon ; en cas de doute, quarantaine plutôt
   que correction « intelligente » non explicable à un client.
4. **Idempotence.** Rejouer le pipeline sur le même fichier donne exactement
   le même résultat, sans doublons.
5. **Raw d'abord.** Les données brutes sont chargées telles quelles (tout en
   texte) avant toute transformation, pour pouvoir rejouer et auditer.

## Architecture

```
Fichier Excel désordonné (3 onglets)
        ↓
Python : lecture + chargement brut (tout en texte) → Postgres schéma raw
        ↓
Python : nettoyage des cas complexes (formats, normalisation, quasi-doublons)
        + journal des corrections + quarantaine
        ↓
dbt : modèles staging → clean + tests de qualité (bloquants)
        ↓
Tables propres + rapport qualité (HTML + section Markdown) + avant/après
```

Répartition des rôles :
- **Python** : tout ce qui est pénible en SQL (parsing de formats mixtes,
  dates série Excel, normalisation de texte, rapprochement de
  quasi-doublons). Produit des données déjà propres **ou explicitement
  rejetées** — jamais de données ambiguës silencieusement passées en clean.
- **SQL / dbt** : règles de cohérence référentielle, dédoublonnage final sur
  les données déjà normalisées, contrôles qualité sous forme de tests
  bloquants.

## Charte de règles (par catégorie de défaut)

Pour chaque défaut du catalogue : la décision (corriger, mettre en
quarantaine, ou signaler seulement) et la règle exacte. Appliquée dans
[03-cleaning.md](03-cleaning.md) (Python) et [04-dbt.md](04-dbt.md) (dbt).

| Catégorie | Défaut | Décision |
|---|---|---|
| Doublons | Doublon exact (toutes colonnes identiques) | Dédoublonner : garder la première occurrence lue, tracer dans `correction_log` |
| Doublons | Quasi-doublon (casse, espaces, accents, ordre des mots — ex. « SARL Dupont » / « Dupont SARL ») | Normaliser (minuscule, sans accent, espaces compressés) puis comparer ; fusion automatique seulement si similarité ≥ 0,92 (ratio de similarité de chaînes) **et** même ville/code postal ; sinon **signalé en quarantaine** comme quasi-doublon incertain, jamais fusionné à l'aveugle |
| Dates | Formats connus : `JJ/MM/AAAA`, `AAAA-MM-JJ`, `12 mars 2025` (texte FR), numéro de série Excel | Parser et convertir en date ISO stockée en base ; règle et format source tracés dans `correction_log` |
| Dates | Ambiguïté jour/mois (ex. `03/04/2025`) | **Jamais deviné** : convention française fixe `JJ/MM/AAAA` appliquée uniformément et documentée ici, pas de détection cas par cas |
| Dates | Texte invalide, date non parsable | Quarantaine, motif `date_invalide` |
| Dates | Date de livraison future aberrante (> date du jour + 2 ans) ou antérieure à 2015 | Quarantaine, motif `date_aberrante` |
| Nombres | Formats connus : `1 234,50`, `1234.5`, `1.234,50 €`, `12,5%` | Parser (retirer séparateurs de milliers, symboles `€`/`%`, normaliser séparateur décimal) → décimal ; tracé dans `correction_log` |
| Nombres | Texte non numérique dans colonne numérique | Quarantaine, motif `valeur_numerique_invalide` |
| Champs vides | `""`, `N/A`, `-`, `null`, espaces seuls | Normalisé en `NULL` ; si la colonne est obligatoire pour la ligne (ex. `client_id` d'une commande), quarantaine motif `champ_obligatoire_vide` |
| Identifiants | Code postal à 4 chiffres (zéro initial perdu) | Recomplété avec un zéro initial (CP français = 5 chiffres), tracé dans `correction_log` |
| Identifiants | SIRET en notation scientifique | Reconverti en entier 14 chiffres si reconstituable sans perte ; sinon quarantaine motif `siret_illisible` |
| Identifiants | Code produit en casse mixte | Normalisé en majuscules, tracé dans `correction_log` |
| Catégories | Variantes de casse/orthographe (`Outillage` / `outillage` / `Outilage` / `OUTILLAGE`) | Normalisées via une table de correspondance explicite et documentée (mapping figé, pas de rapprochement flou automatique) |
| Contacts | Email sans `@` ou format invalide | **Jamais corrigé** : quarantaine motif `email_invalide` |
| Contacts | Téléphone multi-formats, espaces/caractères invisibles | Normalisé au format `0X XX XX XX XX`, caractères invisibles supprimés, tracé dans `correction_log` |
| Cohérence | Quantité négative ou nulle, prix à 0 | Quarantaine, motif `quantite_ou_prix_invalide` |
| Cohérence | Commande rattachée à un client ou produit inexistant | Quarantaine, motif `reference_inexistante` (contrôlé en Python à la jointure et re-vérifié par un test `relationships` dbt) |
| Cohérence | Date de livraison avant la date de commande | Quarantaine, motif `livraison_avant_commande` |
| Structure | Ligne de total, en-tête répété, ligne vide, cellule fusionnée, colonne inutile | Écartée à l'ingestion, **journalisée** (fichier, onglet, numéro de ligne, raison), jamais supprimée silencieusement ; comptée à part dans la réconciliation du rapport |

## Seuils de qualité bloquants

- Si **plus de 5 %** des lignes lues (hors lignes de structure) finissent en
  quarantaine après nettoyage → le pipeline s'arrête en erreur (vérifié en
  fin d'étape Python et par un test dbt personnalisé sur le volume de
  `clean_*` vs `raw_*`).
- Tout test dbt générique critique (`unique`, `not_null` sur clé primaire,
  `relationships` commande→client et commande→produit) doit passer à 100 % :
  aucune exception tolérée sur les tables `clean_*`.
- Tout test dbt personnalisé (email valide, code postal 5 chiffres, quantité
  strictement positive, livraison ≥ commande, aucune date future) doit passer
  à 100 % sur `clean_*` — les lignes qui violeraient ces règles sont censées
  avoir déjà été mises en quarantaine par Python ; un échec dbt sur `clean_*`
  signale donc un bug du nettoyage, pas une donnée sale tolérée.

## Décisions

- **Rapport qualité : HTML autonome** (plus visuel pour la capture), avec un
  résumé en Markdown intégré au README. Choix retenu par défaut pour aller
  vite, cf. [05-report.md](05-report.md).
- **Taux de correction cible : ≥ 95 %** des défauts injectés correctement
  corrigés ou mis en quarantaine à bon escient, mesuré contre la vérité
  terrain (cf. [01-generator.md](01-generator.md)).

## Honnêteté du portfolio

- Mentionner explicitement « projet démo, données fictives » dans le README
  et sur le profil Malt. Préciser que les défauts sont injectés
  volontairement par un script : c'est ce qui rend la mesure du taux de
  correction crédible (comparaison à une vérité terrain connue).
- Aucun bénéfice chiffré présenté comme un résultat mesuré réel : toujours
  formulé comme hypothèse de scénario.

## Critères de réussite globaux

- [ ] Le générateur produit un classeur Excel désordonné avec tous les types
  de défauts du catalogue.
- [ ] Aucune ligne n'est perdue : lignes en entrée = lignes propres +
  quarantaine + lignes de structure écartées (réconciliation affichée dans le
  rapport).
- [ ] Le journal des corrections et la table de quarantaine sont complets et
  lisibles.
- [ ] `dbt test` passe sur les données propres et échoue volontairement si on
  réinjecte un défaut critique (démontré en M4).
- [ ] Le nettoyage retrouve au moins 95 % des défauts corrigeables par
  rapport à la vérité terrain.
- [ ] Le pipeline est idempotent.
- [ ] README, avant/après, rapport qualité et 3 lignes de présentation sont
  prêts pour le profil Malt.
