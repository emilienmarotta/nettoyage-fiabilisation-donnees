# 01 — Générateur du fichier désordonné + vérité terrain

**Statut : Implemented**

## Objectif

Un script Python (Faker, graine fixe) qui :
1. génère un jeu de données **parfait** (cohérent, sans défaut) ;
2. en dérive un classeur Excel **désordonné** (`clients_commandes_brut.xlsx`)
   en injectant les défauts du catalogue à un taux paramétrable ;
3. conserve les données parfaites et un fichier **vérité terrain** décrivant
   chaque défaut injecté (ligne, colonne, valeur originale, valeur altérée,
   catégorie de défaut), pour mesurer ensuite le taux de correction.

Tout ce qui est généré (parfait, brut, vérité terrain) part du **même
univers métier** que les projets 1 et 2 : PME de commerce de gros, mêmes
types de régions/catégories de produits/segments de client.

## Schéma des données parfaites (avant injection de défauts)

### Clients
`client_id` (entier, PK), `code_client` (ex. `CLI-0042`, même format que
`rapport-commercial-auto`), `nom_entreprise`, `contact_nom`, `email`,
`telephone`, `adresse`, `code_postal` (5 chiffres), `ville`, `region`
(liste fixe, identique aux projets 1/2 : Île-de-France,
Auvergne-Rhône-Alpes, Nouvelle-Aquitaine, Occitanie, Hauts-de-France, Grand
Est), `siret` (14 chiffres), `segment` (liste fixe, identique au projet 2 :
`grand_compte` / `pme` / `detaillant`), `date_creation` (date).

### Produits
`produit_id` (entier, PK), `code_produit` (ex. `ART-0042`, même format que
`rapport-commercial-auto`), `nom_produit` (style catalogue gros, ex. « Carton
de gants nitrile », « Rouleau de film étirable » — cohérent avec les
produits déjà utilisés dans les projets 1/2), `categorie` (liste fixe,
identique au projet 2 : emballage, hygiene, boissons, alimentaire, papier,
protection, entretien, textile), `prix_unitaire` (décimal > 0), `unite`
(pièce, lot, carton, palette...), `fournisseur`.

### Commandes
`commande_id` (entier, PK), `client_id` (FK), `produit_id` (FK), `quantite`
(entier > 0), `prix_unitaire_commande` (décimal > 0, peut différer du prix
catalogue — remise), `date_commande` (date), `date_livraison` (date ≥
`date_commande`), `statut` (`Livrée` / `En cours` / `Annulée`).

Volumétrie : ~300 clients, ~150 produits, 2 000 à 5 000 commandes.

## Génération des données parfaites

- Faker en locale `fr_FR`, graine fixe (`Faker.seed(...)` + `random.seed(...)`)
  pour reproductibilité totale.
- Cohérence référentielle garantie dès la génération (tous les FK existent,
  toutes les dates sont cohérentes, tous les champs obligatoires remplis).
- Sauvegardées en Parquet ou CSV dans `data/parfait/` (ignoré par git, sauf
  un petit échantillon versionné dans `docs/` pour preuve).

## Injection des défauts

- Un **taux d'injection paramétrable** par catégorie de défaut (défaut
  global ~15 % des lignes touchées par au moins un défaut, ajustable via
  variable d'environnement ou argument CLI).
- Chaque défaut injecté suit exactement le catalogue de
  [00-vision.md](00-vision.md) (doublons, dates, nombres, champs vides,
  identifiants, catégories, contacts, cohérence, structure).
- Les défauts de **structure** (lignes de total, en-têtes répétés, lignes
  vides, cellules fusionnées, colonnes inutiles) sont injectés au niveau du
  classeur Excel lui-même (openpyxl), pas seulement au niveau des données.
- Chaque injection écrit une ligne dans le fichier **vérité terrain**
  (`data/verite_terrain.csv` ou `.parquet`) :
  `onglet, ligne_originale, colonne, valeur_avant, valeur_apres, categorie_defaut, corrigeable`.
  `corrigeable` indique si le défaut est sans ambiguïté (donc censé être
  corrigé) ou volontairement ambigu (donc censé finir en quarantaine).

## Sortie du classeur Excel

- 3 onglets : **Clients**, **Produits**, **Commandes**.
- Mise en forme volontairement incohérente (types de cellule mixtes,
  colonnes texte/nombre non homogènes) pour forcer une lecture « tout en
  texte » côté ingestion.
- Lignes de total et en-têtes répétés insérés à des positions aléatoires
  mais déterministes (graine fixe).

## Critères de réussite

- [ ] Rejouer le générateur avec la même graine produit un fichier
  strictement identique (test d'idempotence du générateur).
- [ ] Le fichier vérité terrain couvre chaque catégorie du catalogue au moins
  une fois, avec un volume suffisant pour mesurer un taux de correction
  statistiquement lisible (au moins ~20 occurrences par catégorie).
- [ ] Les données parfaites, une fois nettoyées en sens inverse (sans
  défaut), correspondent exactement aux données parfaites d'origine — sert
  de base à la mesure de taux de correction en M5.
