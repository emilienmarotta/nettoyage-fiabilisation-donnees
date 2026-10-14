"""Enchaîne ingestion -> nettoyage -> dbt build -> rapport qualité.

Chaque étape s'arrête en erreur claire si elle échoue (réconciliation KO,
`dbt build` non nul) : pas de continuation silencieuse sur un pipeline
cassé.
"""
import argparse
import subprocess
from pathlib import Path

from pipeline.clean.run import nettoyer
from pipeline.db import get_connection
from pipeline.ingest import ingerer
from pipeline.report import ecrire_html, ecrire_markdown, generer_rapport

DBT_PROJECT_DIR = Path(__file__).resolve().parent.parent / "dbt_project"


def _etape_ingestion(fichier: Path) -> dict:
    conn = get_connection()
    try:
        resume = ingerer(fichier, conn)
    finally:
        conn.close()

    print("Ingestion terminée :")
    for onglet, compte in resume.items():
        ok = compte["lignes_chargees"] + compte["lignes_structure"] == compte["lignes_lues"]
        print(f"  {onglet:10s} (réconciliation : {'OK' if ok else 'KO'})")
        if not ok:
            raise SystemExit(f"Réconciliation KO à l'ingestion pour {onglet} — pipeline arrêté.")
    return resume


def _etape_nettoyage(source_fichier: str) -> dict:
    conn = get_connection()
    try:
        resume = nettoyer(conn, source_fichier)
    finally:
        conn.close()

    print("Nettoyage terminé :")
    for table, compte in resume.items():
        ok = compte["propres"] + compte["quarantaine"] + compte["fusionnes"] == compte["lues"]
        print(f"  {table:10s} (réconciliation : {'OK' if ok else 'KO'})")
        if not ok:
            raise SystemExit(f"Réconciliation KO au nettoyage pour {table} — pipeline arrêté.")
    return resume


def _etape_dbt(dbt_project_dir: Path) -> None:
    print("dbt build...")
    resultat = subprocess.run(["dbt", "build"], cwd=dbt_project_dir)
    if resultat.returncode != 0:
        raise SystemExit(
            f"dbt build a échoué (code {resultat.returncode}) — pipeline arrêté, "
            "voir la sortie ci-dessus."
        )
    print("dbt build terminé (OK).")


def _etape_rapport(
    source_fichier: str,
    verite_terrain: Path,
    dbt_results: Path,
    sortie_html: Path,
    sortie_md: Path,
) -> dict:
    conn = get_connection()
    try:
        contexte = generer_rapport(conn, source_fichier, verite_terrain, dbt_results)
    finally:
        conn.close()

    ecrire_html(contexte, sortie_html)
    ecrire_markdown(contexte, sortie_md)
    print(f"Rapport généré : {sortie_html} / {sortie_md}")
    return contexte


def executer(
    fichier: Path,
    verite_terrain: Path,
    dbt_results: Path,
    sortie_html: Path,
    sortie_md: Path,
    dbt_project_dir: Path = DBT_PROJECT_DIR,
) -> dict:
    resume_ingestion = _etape_ingestion(fichier)
    resume_nettoyage = _etape_nettoyage(fichier.name)
    _etape_dbt(dbt_project_dir)
    contexte_rapport = _etape_rapport(fichier.name, verite_terrain, dbt_results, sortie_html, sortie_md)
    return {
        "ingestion": resume_ingestion,
        "nettoyage": resume_nettoyage,
        "rapport": contexte_rapport,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enchaîne ingestion -> nettoyage -> dbt build -> rapport qualité."
    )
    parser.add_argument("--fichier", type=Path, default=Path("data/clients_commandes_brut.xlsx"))
    parser.add_argument("--verite-terrain", type=Path, default=Path("data/verite_terrain.csv"))
    parser.add_argument("--dbt-results", type=Path, default=Path("dbt_project/target/run_results.json"))
    parser.add_argument("--sortie-html", type=Path, default=Path("docs/rapport_qualite.html"))
    parser.add_argument("--sortie-md", type=Path, default=Path("docs/rapport_qualite.md"))
    args = parser.parse_args()

    executer(args.fichier, args.verite_terrain, args.dbt_results, args.sortie_html, args.sortie_md)


if __name__ == "__main__":
    main()
