"""Ingestion brute du classeur Excel vers le schéma `raw` de Postgres
(voir specs/02-ingestion.md).

Chaque ligne lue finit soit dans une table `raw_*` (tout en texte), soit
dans `raw.structure_ecartee` avec une raison — jamais perdue en silence.
Idempotent : rejouer sur le même fichier source redonne le même état.
"""

import argparse
import datetime
import json
from pathlib import Path

from openpyxl import load_workbook

from pipeline.db import get_connection
from pipeline.schema import COLONNE_INUTILE_LABEL, TABLES
from pipeline.structure import est_entete_repete, est_ligne_total, est_ligne_vide

DDL = """
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.raw_clients (
    source_fichier text NOT NULL,
    source_onglet text NOT NULL,
    ligne_origine integer NOT NULL,
    charge_le timestamptz NOT NULL DEFAULT now(),
    client_id text, code_client text, nom_entreprise text, contact_nom text,
    email text, telephone text, adresse text, code_postal text, ville text,
    region text, siret text, segment text, date_creation text,
    PRIMARY KEY (source_fichier, source_onglet, ligne_origine)
);

CREATE TABLE IF NOT EXISTS raw.raw_produits (
    source_fichier text NOT NULL,
    source_onglet text NOT NULL,
    ligne_origine integer NOT NULL,
    charge_le timestamptz NOT NULL DEFAULT now(),
    produit_id text, code_produit text, nom_produit text, categorie text,
    prix_unitaire text, unite text, fournisseur text,
    PRIMARY KEY (source_fichier, source_onglet, ligne_origine)
);

CREATE TABLE IF NOT EXISTS raw.raw_commandes (
    source_fichier text NOT NULL,
    source_onglet text NOT NULL,
    ligne_origine integer NOT NULL,
    charge_le timestamptz NOT NULL DEFAULT now(),
    commande_id text, client_id text, produit_id text, quantite text,
    prix_unitaire_commande text, date_commande text, date_livraison text,
    statut text,
    PRIMARY KEY (source_fichier, source_onglet, ligne_origine)
);

CREATE TABLE IF NOT EXISTS raw.structure_ecartee (
    id serial PRIMARY KEY,
    source_fichier text NOT NULL,
    source_onglet text NOT NULL,
    ligne_origine integer,
    contenu_brut jsonb,
    raison text NOT NULL,
    charge_le timestamptz NOT NULL DEFAULT now()
);
"""


def _vers_texte(valeur):
    """Convertit une valeur de cellule openpyxl en texte, sans tenter de la
    « corriger » — on garde sa représentation la plus naturelle."""
    if valeur is None:
        return None
    if isinstance(valeur, (datetime.date, datetime.datetime)):
        return valeur.isoformat()
    if isinstance(valeur, str):
        return valeur
    return str(valeur)


def _lire_feuille(ws, nom_feuille: str) -> tuple[list[dict], list[dict]]:
    """Retourne (lignes_a_charger, lignes_de_structure) pour une feuille."""
    meta = TABLES[nom_feuille]
    colonnes = meta["columns"]
    labels_attendus = [meta["labels"][c] for c in colonnes]

    header = [ws.cell(row=1, column=c + 1).value for c in range(ws.max_column)]
    colonnes_excel = len(colonnes)
    a_colonne_inutile = (
        len(header) > colonnes_excel and header[colonnes_excel] == COLONNE_INUTILE_LABEL
    )

    lignes_a_charger = []
    lignes_structure = []

    for excel_row in range(2, ws.max_row + 1):
        valeurs = [ws.cell(row=excel_row, column=c + 1).value for c in range(colonnes_excel)]
        valeurs_texte = [_vers_texte(v) for v in valeurs]

        if est_ligne_vide(valeurs_texte):
            lignes_structure.append({
                "ligne_origine": excel_row, "raison": "ligne_vide",
                "contenu_brut": valeurs_texte,
            })
            continue
        if est_entete_repete(valeurs_texte, labels_attendus):
            lignes_structure.append({
                "ligne_origine": excel_row, "raison": "en_tete_repete",
                "contenu_brut": valeurs_texte,
            })
            continue
        if est_ligne_total(valeurs_texte):
            lignes_structure.append({
                "ligne_origine": excel_row, "raison": "ligne_total",
                "contenu_brut": valeurs_texte,
            })
            continue

        lignes_a_charger.append({
            "ligne_origine": excel_row,
            "valeurs": dict(zip(colonnes, valeurs_texte)),
        })

    if a_colonne_inutile:
        lignes_structure.append({
            "ligne_origine": None, "raison": "colonne_inutile",
            "contenu_brut": {"colonne": header[colonnes_excel]},
        })

    return lignes_a_charger, lignes_structure


def ingerer(chemin_xlsx: Path, conn) -> dict:
    nom_fichier = chemin_xlsx.name
    wb = load_workbook(chemin_xlsx, data_only=True)

    resume = {}
    with conn.cursor() as cur:
        cur.execute(DDL)

        for nom_feuille, meta in TABLES.items():
            raw_table = meta["raw_table"]
            cur.execute(
                f"DELETE FROM raw.{raw_table} WHERE source_fichier = %s", (nom_fichier,)
            )
            cur.execute(
                "DELETE FROM raw.structure_ecartee "
                "WHERE source_fichier = %s AND source_onglet = %s",
                (nom_fichier, nom_feuille),
            )

            lignes_a_charger, lignes_structure = _lire_feuille(wb[nom_feuille], nom_feuille)

            colonnes = meta["columns"]
            placeholders = ", ".join(["%s"] * (3 + len(colonnes)))
            noms_colonnes = ", ".join(["source_fichier", "source_onglet", "ligne_origine"] + colonnes)
            sql_insert = f"INSERT INTO raw.{raw_table} ({noms_colonnes}) VALUES ({placeholders})"
            for ligne in lignes_a_charger:
                valeurs = [nom_fichier, nom_feuille, ligne["ligne_origine"]]
                valeurs += [ligne["valeurs"][c] for c in colonnes]
                cur.execute(sql_insert, valeurs)

            for ligne in lignes_structure:
                cur.execute(
                    "INSERT INTO raw.structure_ecartee "
                    "(source_fichier, source_onglet, ligne_origine, contenu_brut, raison) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (
                        nom_fichier, nom_feuille, ligne["ligne_origine"],
                        json.dumps(ligne["contenu_brut"], ensure_ascii=False), ligne["raison"],
                    ),
                )

            resume[nom_feuille] = {
                "lignes_lues": len(lignes_a_charger) + len(lignes_structure),
                "lignes_chargees": len(lignes_a_charger),
                "lignes_structure": len(lignes_structure),
            }

        conn.commit()

    return resume


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestion brute du classeur Excel vers Postgres.")
    parser.add_argument("--fichier", type=Path, default=Path("data/clients_commandes_brut.xlsx"))
    args = parser.parse_args()

    conn = get_connection()
    try:
        resume = ingerer(args.fichier, conn)
    finally:
        conn.close()

    print("Ingestion terminée :")
    for onglet, compte in resume.items():
        print(
            f"  {onglet:10s} lues={compte['lignes_lues']:5d}  "
            f"chargées={compte['lignes_chargees']:5d}  "
            f"structure={compte['lignes_structure']:3d}  "
            f"(réconciliation : {'OK' if compte['lignes_chargees'] + compte['lignes_structure'] == compte['lignes_lues'] else 'KO'})"
        )


if __name__ == "__main__":
    main()
