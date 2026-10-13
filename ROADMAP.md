# Roadmap

Découpage en milestones, dans l'ordre d'implémentation. Chaque milestone est
livré via une branche dédiée et une pull request (voir [CLAUDE.md](CLAUDE.md)
pour le workflow Git).

- [x] **M0 — Cadrage, squelette et environnement.** `docker-compose.yml`
  (Postgres), `.env.example`, `.gitignore`, specs écrites et approuvées,
  charte de règles, seuils qualité, README initial. Spec :
  [00-vision.md](specs/00-vision.md).
- [x] **M1 — Générateur du fichier désordonné.** Données parfaites (Faker,
  graine fixe), injection des défauts du catalogue, fichier vérité terrain,
  classeur `clients_commandes_brut.xlsx`. Spec :
  [01-generator.md](specs/01-generator.md).
- [ ] **M2 — Ingestion brute.** Lecture du classeur → schéma `raw` Postgres
  (tout en texte), détection et journalisation des lignes de structure.
  Spec : [02-ingestion.md](specs/02-ingestion.md).
- [ ] **M3 — Nettoyage Python.** Modules de règles testés (dates, nombres,
  identifiants, texte, contacts, doublons), journal des corrections, table
  de quarantaine. Spec : [03-cleaning.md](specs/03-cleaning.md).
- [ ] **M4 — Modèles et contrôles dbt.** `stg_*` → `clean_*`, tests
  génériques + personnalisés bloquants, démonstration d'échec volontaire.
  Spec : [04-dbt.md](specs/04-dbt.md).
- [ ] **M5 — Rapport qualité et avant/après.** Réconciliation, taux de
  qualité avant/après, comparaison à la vérité terrain, extrait avant/après.
  Spec : [05-report.md](specs/05-report.md).
- [ ] **M6 — Orchestration et tests du code.** `make run` de bout en bout,
  tests unitaires Python, test d'idempotence. Spec :
  [06-orchestration.md](specs/06-orchestration.md).
- [ ] **M7 — Livrables portfolio Malt.** Captures avant/après et rapport, 3
  lignes de présentation, README final. Spec :
  [07-deliverables.md](specs/07-deliverables.md).

Détail des exigences et critères d'acceptation de chaque milestone :
[specs/](specs/) (voir [specs/README.md](specs/README.md) pour le statut de
chaque spec).
