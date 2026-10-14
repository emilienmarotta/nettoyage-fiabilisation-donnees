# Specs — nettoyage-fiabilisation-donnees

Méthode : chaque fonctionnalité a une spec écrite et validée avant d'être
codée. Une spec ne change pas en cours d'implémentation sans être mise à
jour ici en premier.

Statut possible : `Draft` (à valider) · `Approved` (prête à implémenter) ·
`Implemented` (code conforme livré).

| Spec | Domaine | Statut |
|---|---|---|
| [00-vision.md](00-vision.md) | Vision, principes, charte de règles, seuils qualité | Approved |
| [01-generator.md](01-generator.md) | Générateur du fichier désordonné + vérité terrain | Implemented |
| [02-ingestion.md](02-ingestion.md) | Ingestion brute (raw Postgres) | Implemented |
| [03-cleaning.md](03-cleaning.md) | Nettoyage Python, journal, quarantaine | Implemented |
| [04-dbt.md](04-dbt.md) | Modèles et contrôles dbt | Approved |
| [05-report.md](05-report.md) | Rapport qualité et avant/après | Approved |
| [06-orchestration.md](06-orchestration.md) | Orchestration et tests du code | Approved |
| [07-deliverables.md](07-deliverables.md) | Livrables portfolio Malt | Approved |

Ordre d'implémentation : 00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 (chaque spec
consomme le contrat produit par la précédente).

Correspondance avec les milestones de la [ROADMAP](../ROADMAP.md) :
00 → M0, 01 → M1, 02 → M2, 03 → M3, 04 → M4, 05 → M5, 06 → M6, 07 → M7.
