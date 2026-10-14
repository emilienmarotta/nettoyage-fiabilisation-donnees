"""Nettoyage Python : lit `raw.*`, applique la charte de règles (voir
specs/03-cleaning.md et specs/00-vision.md), écrit les lignes propres dans
`clean_staging.*`, trace chaque correction dans `correction_log` et chaque
rejet dans `quarantine`. Rejoué entièrement à chaque exécution (pas d'état
accumulé) pour rester idempotent.
"""

import argparse
import json
from datetime import date

from generator.config import CATEGORIES
from pipeline.clean import contacts, dates, doublons, identifiants, nombres, texte
from pipeline.db import get_connection

DDL = """
CREATE SCHEMA IF NOT EXISTS clean_staging;

CREATE TABLE IF NOT EXISTS clean_staging.clients (
    source_fichier text NOT NULL,
    ligne_origine integer NOT NULL,
    client_id integer NOT NULL,
    code_client text, nom_entreprise text, contact_nom text, email text,
    telephone text, adresse text, code_postal text, ville text,
    region text, siret text, segment text, date_creation text,
    PRIMARY KEY (source_fichier, client_id)
);

CREATE TABLE IF NOT EXISTS clean_staging.produits (
    source_fichier text NOT NULL,
    ligne_origine integer NOT NULL,
    produit_id integer NOT NULL,
    code_produit text, nom_produit text, categorie text,
    prix_unitaire text, unite text, fournisseur text,
    PRIMARY KEY (source_fichier, produit_id)
);

CREATE TABLE IF NOT EXISTS clean_staging.commandes (
    source_fichier text NOT NULL,
    ligne_origine integer NOT NULL,
    commande_id integer NOT NULL,
    client_id integer NOT NULL, produit_id integer NOT NULL,
    quantite text, prix_unitaire_commande text,
    date_commande text, date_livraison text, statut text,
    PRIMARY KEY (source_fichier, commande_id)
);

CREATE TABLE IF NOT EXISTS clean_staging.correction_log (
    id serial PRIMARY KEY,
    source_fichier text NOT NULL, source_onglet text NOT NULL,
    ligne_origine integer NOT NULL, table_cible text NOT NULL,
    colonne text NOT NULL, valeur_avant text, valeur_apres text,
    regle_appliquee text NOT NULL,
    corrige_le timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS clean_staging.quarantine (
    id serial PRIMARY KEY,
    source_fichier text NOT NULL, source_onglet text NOT NULL,
    ligne_origine integer NOT NULL, table_cible text NOT NULL,
    donnees_brutes jsonb NOT NULL, motif_rejet text NOT NULL,
    detecte_le timestamptz NOT NULL DEFAULT now()
);
"""


def _motifs_uniques(motifs: list[str]) -> str:
    return ";".join(dict.fromkeys(motifs))


def _lire_raw(conn, raw_table: str, colonnes: list[str], source_fichier: str) -> list[dict]:
    with conn.cursor() as cur:
        noms = ", ".join(["source_fichier", "source_onglet", "ligne_origine"] + colonnes)
        cur.execute(
            f"SELECT {noms} FROM raw.{raw_table} WHERE source_fichier = %s "
            f"ORDER BY ligne_origine",
            (source_fichier,),
        )
        colonnes_resultat = ["source_fichier", "source_onglet", "ligne_origine"] + colonnes
        return [dict(zip(colonnes_resultat, ligne)) for ligne in cur.fetchall()]


def _nettoyer_clients(
    rows: list[dict],
) -> tuple[list[dict], list[dict], list[dict], dict[int, int]]:
    clean: list[dict] = []
    corrections: list[dict] = []
    quarantines: list[dict] = []

    def corr(row, colonne, avant, apres, regle):
        corrections.append({
            "source_fichier": row["source_fichier"], "source_onglet": row["source_onglet"],
            "ligne_origine": row["ligne_origine"], "table_cible": "clients",
            "colonne": colonne, "valeur_avant": avant, "valeur_apres": apres,
            "regle_appliquee": regle,
        })

    for row in rows:
        motifs: list[str] = []
        valeurs = dict(row)

        nom, _ = texte.normaliser_champ_vide(row["nom_entreprise"])
        if nom is None:
            motifs.append("champ_obligatoire_vide")
        valeurs["nom_entreprise"] = nom

        email, _, motif = contacts.valider_email(row["email"])
        if motif:
            motifs.append(motif)
        valeurs["email"] = email

        tel, changed, motif = contacts.normaliser_telephone(row["telephone"])
        if motif:
            motifs.append(motif)
        else:
            if changed:
                corr(row, "telephone", row["telephone"], tel, "telephone_format")
            valeurs["telephone"] = tel

        adresse, changed = texte.normaliser_champ_vide(row["adresse"])
        if changed:
            corr(row, "adresse", row["adresse"], adresse, "champ_vide_normalise")
        valeurs["adresse"] = adresse

        cp, changed, motif = identifiants.normaliser_code_postal(row["code_postal"])
        if motif:
            motifs.append(motif)
        else:
            if changed:
                corr(row, "code_postal", row["code_postal"], cp, "code_postal_4_chiffres")
            valeurs["code_postal"] = cp

        siret, changed, motif = identifiants.normaliser_siret(row["siret"])
        if motif:
            motifs.append(motif)
        else:
            if changed:
                corr(row, "siret", row["siret"], siret, "siret_scientifique")
            valeurs["siret"] = siret

        valeurs["client_id"] = int(row["client_id"])

        if motifs:
            quarantines.append({
                "source_fichier": row["source_fichier"], "source_onglet": row["source_onglet"],
                "ligne_origine": row["ligne_origine"], "table_cible": "clients",
                "donnees_brutes": row, "motif_rejet": _motifs_uniques(motifs),
            })
            continue
        clean.append(valeurs)

    colonnes_signature = [
        "nom_entreprise", "contact_nom", "email", "telephone", "adresse",
        "code_postal", "ville", "region", "siret", "segment", "date_creation",
    ]
    canonique: list[dict] = []
    mapping_fusion: dict[int, int] = {}
    for row in clean:
        signature = tuple(row.get(c) for c in colonnes_signature)
        doublon_exact = next(
            (c for c in canonique if tuple(c.get(k) for k in colonnes_signature) == signature),
            None,
        )
        if doublon_exact is not None:
            corr(row, "doublon", row["nom_entreprise"],
                 f"fusionné avec client_id={doublon_exact['client_id']}", "doublon_exact")
            mapping_fusion[row["client_id"]] = doublon_exact["client_id"]
            continue

        fusion_cible = next(
            (c for c in canonique if doublons.est_doublon_fusionnable(
                row["nom_entreprise"], row["ville"], row["code_postal"],
                c["nom_entreprise"], c["ville"], c["code_postal"],
            )),
            None,
        )
        if fusion_cible is not None:
            corr(row, "doublon", row["nom_entreprise"],
                 f"fusionné avec client_id={fusion_cible['client_id']}", "doublon_quasi_evident")
            mapping_fusion[row["client_id"]] = fusion_cible["client_id"]
            continue

        nom_identique = next(
            (c for c in canonique
             if doublons.normaliser_nom(c["nom_entreprise"]) == doublons.normaliser_nom(row["nom_entreprise"])),
            None,
        )
        if nom_identique is not None:
            quarantines.append({
                "source_fichier": row["source_fichier"], "source_onglet": row["source_onglet"],
                "ligne_origine": row["ligne_origine"], "table_cible": "clients",
                "donnees_brutes": row, "motif_rejet": "doublon_quasi_incertain",
            })
            continue

        canonique.append(row)

    return canonique, corrections, quarantines, mapping_fusion


def _nettoyer_produits(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    clean: list[dict] = []
    corrections: list[dict] = []
    quarantines: list[dict] = []

    def corr(row, colonne, avant, apres, regle):
        corrections.append({
            "source_fichier": row["source_fichier"], "source_onglet": row["source_onglet"],
            "ligne_origine": row["ligne_origine"], "table_cible": "produits",
            "colonne": colonne, "valeur_avant": avant, "valeur_apres": apres,
            "regle_appliquee": regle,
        })

    for row in rows:
        motifs: list[str] = []
        valeurs = dict(row)

        code, changed, _ = identifiants.normaliser_code_produit(row["code_produit"])
        if changed:
            corr(row, "code_produit", row["code_produit"], code, "code_produit_casse")
        valeurs["code_produit"] = code

        categorie, changed, motif = texte.normaliser_categorie(row["categorie"], CATEGORIES)
        if motif:
            motifs.append(motif)
        else:
            if changed:
                corr(row, "categorie", row["categorie"], categorie, "categorie_casse")
            valeurs["categorie"] = categorie

        prix, changed, motif = nombres.parser_nombre(row["prix_unitaire"])
        if motif:
            motifs.append(motif)
        elif prix is None:
            motifs.append("champ_obligatoire_vide")
        elif prix <= 0:
            motifs.append("quantite_ou_prix_invalide")
        else:
            if changed:
                corr(row, "prix_unitaire", row["prix_unitaire"], str(prix), "nombre_reformat")
            valeurs["prix_unitaire"] = str(prix)

        fournisseur, changed = texte.normaliser_champ_vide(row["fournisseur"])
        if changed:
            corr(row, "fournisseur", row["fournisseur"], fournisseur, "champ_vide_normalise")
        valeurs["fournisseur"] = fournisseur

        valeurs["produit_id"] = int(row["produit_id"])

        if motifs:
            quarantines.append({
                "source_fichier": row["source_fichier"], "source_onglet": row["source_onglet"],
                "ligne_origine": row["ligne_origine"], "table_cible": "produits",
                "donnees_brutes": row, "motif_rejet": _motifs_uniques(motifs),
            })
            continue
        clean.append(valeurs)

    return clean, corrections, quarantines


def _nettoyer_commandes(
    rows: list[dict],
    clients_valides: set[int],
    produits_valides: set[int],
    mapping_fusion_clients: dict[int, int] | None = None,
    aujourdhui: date | None = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    mapping_fusion_clients = mapping_fusion_clients or {}
    clean: list[dict] = []
    corrections: list[dict] = []
    quarantines: list[dict] = []

    def corr(row, colonne, avant, apres, regle):
        corrections.append({
            "source_fichier": row["source_fichier"], "source_onglet": row["source_onglet"],
            "ligne_origine": row["ligne_origine"], "table_cible": "commandes",
            "colonne": colonne, "valeur_avant": avant, "valeur_apres": apres,
            "regle_appliquee": regle,
        })

    def _id_obligatoire(valeur_brute):
        texte_id, _ = texte.normaliser_champ_vide(valeur_brute)
        if texte_id is None or not texte_id.lstrip("-").isdigit():
            return None
        return int(texte_id)

    for row in rows:
        motifs: list[str] = []
        valeurs = dict(row)

        client_id = _id_obligatoire(row["client_id"])
        if client_id is not None and client_id in mapping_fusion_clients:
            cible = mapping_fusion_clients[client_id]
            corr(row, "client_id", str(client_id), str(cible), "client_id_remappe_fusion")
            client_id = cible
        if client_id is None:
            motifs.append("champ_obligatoire_vide")
        valeurs["client_id"] = client_id

        produit_id = _id_obligatoire(row["produit_id"])
        if produit_id is None:
            motifs.append("champ_obligatoire_vide")
        valeurs["produit_id"] = produit_id

        qte_texte, _ = texte.normaliser_champ_vide(row["quantite"])
        if qte_texte is None:
            motifs.append("champ_obligatoire_vide")
            qte = None
        else:
            qte, changed, motif = nombres.parser_nombre(qte_texte)
            if motif:
                motifs.append(motif)
            elif qte is None:
                motifs.append("champ_obligatoire_vide")
            elif qte <= 0:
                motifs.append("quantite_ou_prix_invalide")
            elif changed:
                corr(row, "quantite", row["quantite"], str(qte), "nombre_reformat")
        valeurs["quantite"] = str(qte) if qte is not None else None

        prix, changed, motif = nombres.parser_nombre(row["prix_unitaire_commande"])
        if motif:
            motifs.append(motif)
        elif prix is None:
            motifs.append("champ_obligatoire_vide")
        elif prix <= 0:
            motifs.append("quantite_ou_prix_invalide")
        elif changed:
            corr(row, "prix_unitaire_commande", row["prix_unitaire_commande"], str(prix), "nombre_reformat")
        valeurs["prix_unitaire_commande"] = str(prix) if prix is not None else None

        dc_iso, changed, motif = dates.parser_date(row["date_commande"])
        if motif:
            motifs.append(motif)
        elif dc_iso is None:
            motifs.append("champ_obligatoire_vide")
        elif dates.est_date_aberrante(dc_iso, aujourdhui):
            motifs.append("date_aberrante")
        elif changed:
            corr(row, "date_commande", row["date_commande"], dc_iso, "date_reformat")
        valeurs["date_commande"] = dc_iso

        dl_iso, changed, motif = dates.parser_date(row["date_livraison"])
        if motif:
            motifs.append(motif)
        elif dl_iso is not None and dates.est_date_aberrante(dl_iso, aujourdhui):
            motifs.append("date_aberrante")
        elif dl_iso is not None and changed:
            corr(row, "date_livraison", row["date_livraison"], dl_iso, "date_reformat")
        valeurs["date_livraison"] = dl_iso

        if dc_iso is not None and dl_iso is not None and dl_iso < dc_iso:
            motifs.append("livraison_avant_commande")

        if client_id is not None and client_id not in clients_valides:
            motifs.append("reference_inexistante")
        if produit_id is not None and produit_id not in produits_valides:
            motifs.append("reference_inexistante")

        valeurs["commande_id"] = int(row["commande_id"])

        if motifs:
            quarantines.append({
                "source_fichier": row["source_fichier"], "source_onglet": row["source_onglet"],
                "ligne_origine": row["ligne_origine"], "table_cible": "commandes",
                "donnees_brutes": row, "motif_rejet": _motifs_uniques(motifs),
            })
            continue
        clean.append(valeurs)

    return clean, corrections, quarantines


def _ecrire_resultats(
    conn, source_fichier: str,
    clients: list[dict], produits: list[dict], commandes: list[dict],
    corrections: list[dict], quarantines: list[dict],
) -> None:
    with conn.cursor() as cur:
        cur.execute(DDL)

        for table in ("clients", "produits", "commandes"):
            cur.execute(f"DELETE FROM clean_staging.{table} WHERE source_fichier = %s", (source_fichier,))
        cur.execute("DELETE FROM clean_staging.correction_log WHERE source_fichier = %s", (source_fichier,))
        cur.execute("DELETE FROM clean_staging.quarantine WHERE source_fichier = %s", (source_fichier,))

        for row in clients:
            cur.execute(
                "INSERT INTO clean_staging.clients "
                "(source_fichier, ligne_origine, client_id, code_client, nom_entreprise, "
                "contact_nom, email, telephone, adresse, code_postal, ville, region, "
                "siret, segment, date_creation) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    row["source_fichier"], row["ligne_origine"], row["client_id"],
                    row["code_client"], row["nom_entreprise"], row["contact_nom"],
                    row["email"], row["telephone"], row["adresse"], row["code_postal"],
                    row["ville"], row["region"], row["siret"], row["segment"],
                    row["date_creation"],
                ),
            )

        for row in produits:
            cur.execute(
                "INSERT INTO clean_staging.produits "
                "(source_fichier, ligne_origine, produit_id, code_produit, nom_produit, "
                "categorie, prix_unitaire, unite, fournisseur) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    row["source_fichier"], row["ligne_origine"], row["produit_id"],
                    row["code_produit"], row["nom_produit"], row["categorie"],
                    row["prix_unitaire"], row["unite"], row["fournisseur"],
                ),
            )

        for row in commandes:
            cur.execute(
                "INSERT INTO clean_staging.commandes "
                "(source_fichier, ligne_origine, commande_id, client_id, produit_id, "
                "quantite, prix_unitaire_commande, date_commande, date_livraison, statut) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    row["source_fichier"], row["ligne_origine"], row["commande_id"],
                    row["client_id"], row["produit_id"], row["quantite"],
                    row["prix_unitaire_commande"], row["date_commande"],
                    row["date_livraison"], row["statut"],
                ),
            )

        for row in corrections:
            cur.execute(
                "INSERT INTO clean_staging.correction_log "
                "(source_fichier, source_onglet, ligne_origine, table_cible, colonne, "
                "valeur_avant, valeur_apres, regle_appliquee) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    row["source_fichier"], row["source_onglet"], row["ligne_origine"],
                    row["table_cible"], row["colonne"], row["valeur_avant"],
                    row["valeur_apres"], row["regle_appliquee"],
                ),
            )

        for row in quarantines:
            cur.execute(
                "INSERT INTO clean_staging.quarantine "
                "(source_fichier, source_onglet, ligne_origine, table_cible, "
                "donnees_brutes, motif_rejet) VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    row["source_fichier"], row["source_onglet"], row["ligne_origine"],
                    row["table_cible"], json.dumps(row["donnees_brutes"], ensure_ascii=False, default=str),
                    row["motif_rejet"],
                ),
            )

        conn.commit()


def nettoyer(conn, source_fichier: str) -> dict:
    clients_rows = _lire_raw(conn, "raw_clients", [
        "client_id", "code_client", "nom_entreprise", "contact_nom", "email",
        "telephone", "adresse", "code_postal", "ville", "region", "siret",
        "segment", "date_creation",
    ], source_fichier)
    produits_rows = _lire_raw(conn, "raw_produits", [
        "produit_id", "code_produit", "nom_produit", "categorie",
        "prix_unitaire", "unite", "fournisseur",
    ], source_fichier)
    commandes_rows = _lire_raw(conn, "raw_commandes", [
        "commande_id", "client_id", "produit_id", "quantite",
        "prix_unitaire_commande", "date_commande", "date_livraison", "statut",
    ], source_fichier)

    clients, corrections_c, quarantines_c, mapping_fusion_c = _nettoyer_clients(clients_rows)
    produits, corrections_p, quarantines_p = _nettoyer_produits(produits_rows)

    clients_valides = {row["client_id"] for row in clients}
    produits_valides = {row["produit_id"] for row in produits}
    commandes, corrections_o, quarantines_o = _nettoyer_commandes(
        commandes_rows, clients_valides, produits_valides, mapping_fusion_c,
    )

    corrections = corrections_c + corrections_p + corrections_o
    quarantines = quarantines_c + quarantines_p + quarantines_o

    _ecrire_resultats(conn, source_fichier, clients, produits, commandes, corrections, quarantines)

    return {
        "Clients": {
            "lues": len(clients_rows), "propres": len(clients), "quarantaine": len(quarantines_c),
            "fusionnes": len(mapping_fusion_c),
        },
        "Produits": {
            "lues": len(produits_rows), "propres": len(produits), "quarantaine": len(quarantines_p),
            "fusionnes": 0,
        },
        "Commandes": {
            "lues": len(commandes_rows), "propres": len(commandes), "quarantaine": len(quarantines_o),
            "fusionnes": 0,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Nettoyage Python des tables raw vers clean_staging.")
    parser.add_argument("--fichier", default="clients_commandes_brut.xlsx")
    args = parser.parse_args()

    conn = get_connection()
    try:
        resume = nettoyer(conn, args.fichier)
    finally:
        conn.close()

    print("Nettoyage terminé :")
    for table, compte in resume.items():
        reconciliation = (
            compte["propres"] + compte["quarantaine"] + compte["fusionnes"] == compte["lues"]
        )
        print(
            f"  {table:10s} lues={compte['lues']:5d}  "
            f"propres={compte['propres']:5d}  quarantaine={compte['quarantaine']:4d}  "
            f"fusionnes={compte['fusionnes']:3d}  "
            f"(réconciliation : {'OK' if reconciliation else 'KO'})"
        )


if __name__ == "__main__":
    main()
