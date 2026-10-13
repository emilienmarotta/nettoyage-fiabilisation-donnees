"""Point d'entrée du générateur (voir specs/01-generator.md).

Enchaîne : données parfaites -> injection des défauts -> classeur Excel
désordonné + vérité terrain, tous dérivés de façon déterministe de la
graine fournie (même graine = mêmes fichiers, octet pour octet).
"""

import argparse
import csv
import os
from pathlib import Path

from generator import config
from generator.defauts import injecter_defauts
from generator.excel_writer import ecrire_classeur
from generator.parfait import build_dataset

CHAMPS_VERITE_TERRAIN = [
    "onglet", "ligne_originale", "colonne", "valeur_avant", "valeur_apres",
    "categorie_defaut", "corrigeable",
]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for ligne in path.read_text().splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, valeur = ligne.split("=", 1)
        os.environ.setdefault(cle.strip(), valeur.strip())


def _ecrire_csv(chemin: Path, lignes: list[dict], champs: list[str]) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=champs)
        writer.writeheader()
        for ligne in lignes:
            writer.writerow({champ: ligne.get(champ) for champ in champs})


def run(seed: int, taux_defauts: float, data_dir: Path) -> dict:
    dataset_parfait = build_dataset(seed=seed)

    for table, lignes in dataset_parfait.items():
        champs = list(lignes[0].keys())
        _ecrire_csv(data_dir / "parfait" / f"{table}.csv", lignes, champs)

    dataset_desordonne, verite_lignes = injecter_defauts(dataset_parfait, seed, taux_defauts)

    mapping_global, structure_globale = ecrire_classeur(
        dataset_desordonne, data_dir / "clients_commandes_brut.xlsx", seed,
    )

    for entree in verite_lignes:
        onglet = entree["onglet"]
        entree["ligne_originale"] = mapping_global[onglet][entree["ligne_originale"]]

    for defaut in structure_globale:
        verite_lignes.append({
            "onglet": defaut["onglet"],
            "ligne_originale": defaut["ligne_excel"],
            "colonne": None,
            "valeur_avant": None,
            "valeur_apres": defaut["type"],
            "categorie_defaut": f"structure_{defaut['type']}",
            "corrigeable": "structure",
        })

    _ecrire_csv(data_dir / "verite_terrain.csv", verite_lignes, CHAMPS_VERITE_TERRAIN)

    return {
        "n_clients_parfaits": len(dataset_parfait["clients"]),
        "n_produits_parfaits": len(dataset_parfait["produits"]),
        "n_commandes_parfaits": len(dataset_parfait["commandes"]),
        "n_clients_desordonnes": len(dataset_desordonne["clients"]),
        "n_defauts_verite_terrain": len(verite_lignes),
    }


def main() -> None:
    _load_dotenv(Path(".env"))

    parser = argparse.ArgumentParser(description="Génère le classeur Excel désordonné de démo.")
    parser.add_argument("--seed", type=int, default=int(os.environ.get("GENERATOR_SEED", config.SEED)))
    parser.add_argument(
        "--taux-defauts", type=float,
        default=float(os.environ.get("GENERATOR_TAUX_DEFAUTS", config.TAUX_DEFAUTS_DEFAUT)),
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()

    resume = run(args.seed, args.taux_defauts, args.data_dir)

    print("Génération terminée :")
    for cle, valeur in resume.items():
        print(f"  {cle} : {valeur}")


if __name__ == "__main__":
    main()
