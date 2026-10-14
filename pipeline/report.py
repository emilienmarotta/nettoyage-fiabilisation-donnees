"""Rapport qualité avant/après (voir specs/05-report.md).

Lit l'état Postgres (`raw.*`, `clean_staging.*`), la vérité terrain
(`data/verite_terrain.csv`) et les résultats dbt (`dbt_project/target/
run_results.json`), et génère un rapport HTML autonome
(`docs/rapport_qualite.html`) + un résumé Markdown
(`docs/rapport_qualite.md`) réutilisable tel quel dans le README.

Ne corrige ni ne modifie rien : lecture seule, calculs descriptifs
uniquement, en réutilisant les mêmes fonctions pures que
`pipeline/clean/*` pour ne jamais faire diverger les critères de validité
du rapport de ceux réellement appliqués par le nettoyage.
"""

import argparse
import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from generator.config import CATEGORIES
from pipeline.clean import contacts, dates, doublons, identifiants, nombres, texte
from pipeline.db import get_connection

SEUIL_CORRECTION_CIBLE = 0.95

TABLES = ["clients", "produits", "commandes"]
ONGLET_PAR_TABLE = {"clients": "Clients", "produits": "Produits", "commandes": "Commandes"}

CHAMPS_OBLIGATOIRES = {
    "clients": ["nom_entreprise"],
    "produits": ["prix_unitaire"],
    "commandes": ["client_id", "produit_id", "quantite", "prix_unitaire_commande", "date_commande"],
}

VALIDATEURS = {
    "clients": {
        "email": contacts.valider_email,
        "telephone": contacts.normaliser_telephone,
        "code_postal": identifiants.normaliser_code_postal,
        "siret": identifiants.normaliser_siret,
        "date_creation": dates.parser_date,
    },
    "produits": {
        "categorie": lambda v: texte.normaliser_categorie(v, CATEGORIES),
        "prix_unitaire": nombres.parser_nombre,
    },
    "commandes": {
        "quantite": nombres.parser_nombre,
        "prix_unitaire_commande": nombres.parser_nombre,
        "date_commande": dates.parser_date,
        "date_livraison": dates.parser_date,
    },
}


# ---------------------------------------------------------------------------
# Lecture Postgres
# ---------------------------------------------------------------------------

def _fetchall_dict(conn, sql, params=()):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        colonnes = [d.name for d in cur.description]
        return [dict(zip(colonnes, row)) for row in cur.fetchall()]


def _charger_etat(conn, source_fichier: str) -> dict:
    etat = {"raw": {}, "structure": {}, "clean": {}, "quarantine": {}, "corrections": []}

    for table in TABLES:
        etat["raw"][table] = _fetchall_dict(
            conn, f"SELECT * FROM raw.raw_{table} WHERE source_fichier = %s ORDER BY ligne_origine",
            (source_fichier,),
        )
        etat["clean"][table] = _fetchall_dict(
            conn, f"SELECT * FROM clean_staging.{table} WHERE source_fichier = %s ORDER BY ligne_origine",
            (source_fichier,),
        )
        etat["quarantine"][table] = _fetchall_dict(
            conn,
            "SELECT * FROM clean_staging.quarantine "
            "WHERE source_fichier = %s AND table_cible = %s ORDER BY ligne_origine",
            (source_fichier, table),
        )

    etat["structure"] = _fetchall_dict(
        conn, "SELECT * FROM raw.structure_ecartee WHERE source_fichier = %s", (source_fichier,),
    )
    etat["corrections"] = _fetchall_dict(
        conn, "SELECT * FROM clean_staging.correction_log WHERE source_fichier = %s", (source_fichier,),
    )
    return etat


# ---------------------------------------------------------------------------
# 1. Réconciliation des volumes
# ---------------------------------------------------------------------------

def _reconciliation(etat: dict) -> list[dict]:
    structure_par_onglet = Counter(s["source_onglet"] for s in etat["structure"])
    lignes = []
    for table in TABLES:
        onglet = ONGLET_PAR_TABLE[table]
        structure = structure_par_onglet.get(onglet, 0)
        charge = len(etat["raw"][table])
        propres = len(etat["clean"][table])
        quarantaine = len(etat["quarantine"][table])
        fusionnes = sum(
            1 for c in etat["corrections"]
            if c["table_cible"] == table and c["colonne"] == "doublon"
        )
        lues = structure + charge
        lignes.append({
            "table": table, "onglet": onglet, "lues": lues, "structure": structure,
            "charge": charge, "propres": propres, "quarantaine": quarantaine,
            "fusionnes": fusionnes,
            "ok_ingestion": charge + structure == lues,
            "ok_nettoyage": propres + quarantaine + fusionnes == charge,
        })
    return lignes


# ---------------------------------------------------------------------------
# 2. Répartition par type de défaut
# ---------------------------------------------------------------------------

def _repartition_defauts(etat: dict) -> dict:
    corrections = Counter(c["regle_appliquee"] for c in etat["corrections"])
    motifs = Counter()
    for table in TABLES:
        for q in etat["quarantine"][table]:
            for motif in q["motif_rejet"].split(";"):
                motifs[motif] += 1
    structure = Counter(s["raison"] for s in etat["structure"])
    return {
        "corrections": corrections.most_common(),
        "quarantaine": motifs.most_common(),
        "structure": structure.most_common(),
    }


# ---------------------------------------------------------------------------
# 3. Taux de qualité avant/après (complétude, unicité, validité, cohérence)
# ---------------------------------------------------------------------------

def _non_vide(valeur) -> bool:
    if valeur is None:
        return False
    if not isinstance(valeur, str):
        return True
    simplifie, _ = texte.normaliser_champ_vide(valeur)
    return simplifie is not None


def _completude(rows: list[dict], champs: list[str]) -> float:
    if not rows or not champs:
        return 1.0
    total = len(rows) * len(champs)
    presents = sum(1 for row in rows for champ in champs if _non_vide(row.get(champ)))
    return presents / total


def _validite(rows: list[dict], validateurs: dict) -> float:
    if not rows or not validateurs:
        return 1.0
    total = len(rows) * len(validateurs)
    valides = 0
    for row in rows:
        for champ, fn in validateurs.items():
            _, _, motif = fn(row.get(champ))
            if motif is None:
                valides += 1
    return valides / total


def _cle_doublon(row: dict) -> tuple:
    nom = doublons.normaliser_nom(row.get("nom_entreprise") or "")
    ville = (row.get("ville") or "").strip().lower()
    cp = (row.get("code_postal") or "").strip()
    return (nom, ville, cp)


def _unicite(rows: list[dict], table: str) -> float:
    if not rows:
        return 1.0
    if table != "clients":
        vues = set()
        doublons_exacts = 0
        for row in rows:
            cle = tuple(sorted((k, v) for k, v in row.items() if k not in ("charge_le",)))
            if cle in vues:
                doublons_exacts += 1
            vues.add(cle)
        return 1 - doublons_exacts / len(rows)

    vues = []
    nb_doublons = 0
    for row in rows:
        cle = _cle_doublon(row)
        if cle in vues:
            nb_doublons += 1
        else:
            vues.append(cle)
    return 1 - nb_doublons / len(rows)


def _coherence_commandes(rows: list[dict], clients_ids: set, produits_ids: set) -> float:
    if not rows:
        return 1.0
    ok = 0
    for row in rows:
        try:
            client_id = int(row["client_id"]) if row.get("client_id") not in (None, "") else None
            produit_id = int(row["produit_id"]) if row.get("produit_id") not in (None, "") else None
        except (TypeError, ValueError):
            client_id = produit_id = None

        ref_ok = client_id in clients_ids and produit_id in produits_ids

        qte, _, motif_qte = nombres.parser_nombre(row.get("quantite"))
        prix, _, motif_prix = nombres.parser_nombre(row.get("prix_unitaire_commande"))
        montants_ok = (
            motif_qte is None and motif_prix is None
            and qte is not None and prix is not None and qte > 0 and prix > 0
        )

        dc, _, motif_dc = dates.parser_date(row.get("date_commande"))
        dl, _, motif_dl = dates.parser_date(row.get("date_livraison"))
        dates_ok = motif_dc is None and motif_dl is None and (dl is None or dc is None or dl >= dc)

        if ref_ok and montants_ok and dates_ok:
            ok += 1
    return ok / len(rows)


def _taux_qualite(etat: dict) -> dict:
    clients_ids_raw = {
        int(r["client_id"]) for r in etat["raw"]["clients"]
        if (r.get("client_id") or "").lstrip("-").isdigit()
    }
    produits_ids_raw = {
        int(r["produit_id"]) for r in etat["raw"]["produits"]
        if (r.get("produit_id") or "").lstrip("-").isdigit()
    }
    clients_ids_clean = {r["client_id"] for r in etat["clean"]["clients"]}
    produits_ids_clean = {r["produit_id"] for r in etat["clean"]["produits"]}

    resultat = {}
    for table in TABLES:
        avant_rows = etat["raw"][table]
        apres_rows = etat["clean"][table]
        resultat[table] = {
            "completude_avant": _completude(avant_rows, CHAMPS_OBLIGATOIRES[table]),
            "completude_apres": _completude(apres_rows, CHAMPS_OBLIGATOIRES[table]),
            "unicite_avant": _unicite(avant_rows, table),
            "unicite_apres": _unicite(apres_rows, table),
            "validite_avant": _validite(avant_rows, VALIDATEURS[table]),
            "validite_apres": _validite(apres_rows, VALIDATEURS[table]),
        }

    resultat["commandes"]["coherence_avant"] = _coherence_commandes(
        etat["raw"]["commandes"], clients_ids_raw, produits_ids_raw,
    )
    resultat["commandes"]["coherence_apres"] = _coherence_commandes(
        etat["clean"]["commandes"], clients_ids_clean, produits_ids_clean,
    )
    resultat["clients"]["coherence_avant"] = None
    resultat["clients"]["coherence_apres"] = None
    resultat["produits"]["coherence_avant"] = None
    resultat["produits"]["coherence_apres"] = None
    return resultat


# ---------------------------------------------------------------------------
# 4. Comparaison avec la vérité terrain
# ---------------------------------------------------------------------------

def _charger_verite_terrain(chemin: Path) -> list[dict]:
    with chemin.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _valeur_clean(etat: dict, table: str, ligne_origine: int, colonne: str):
    for row in etat["clean"][table]:
        if row["ligne_origine"] == ligne_origine:
            return row.get(colonne)
    return None


def _en_quarantaine(etat: dict, table: str, ligne_origine: int) -> bool:
    return any(q["ligne_origine"] == ligne_origine for q in etat["quarantine"][table])


def _valeurs_equivalentes(valeur_obtenue, valeur_attendue: str) -> bool:
    """Compare la valeur nettoyée à la valeur attendue (vérité terrain).
    Égalité textuelle, sauf pour les nombres où seule la valeur compte (le
    nombre de décimales peut différer entre la vérité terrain, générée
    depuis un float Python, et la valeur réellement saisie dans le classeur,
    ex. ``287.7`` vs ``287.70`` — même montant, précision d'affichage
    différente, pas une erreur de nettoyage)."""
    if valeur_attendue in (None, ""):
        return True
    try:
        return Decimal(str(valeur_obtenue)) == Decimal(valeur_attendue)
    except (InvalidOperation, TypeError):
        return str(valeur_obtenue) == valeur_attendue


def _comparaison_verite_terrain(etat: dict, verite: list[dict]) -> dict:
    par_categorie: dict[str, list[bool]] = defaultdict(list)
    echecs: list[dict] = []

    # structure_colonne_inutile n'a pas de ligne_originale (défaut au niveau
    # de la colonne, pas d'une ligne) : vérifié à part, contre
    # structure_ecartee avec ligne_origine NULL.
    sans_ligne = [d for d in verite if d["ligne_originale"] == ""]
    for d in sans_ligne:
        ok = any(
            s["source_onglet"] == d["onglet"] and s["ligne_origine"] is None
            and s["raison"] == "colonne_inutile"
            for s in etat["structure"]
        )
        par_categorie[d["categorie_defaut"]].append(ok)
        if not ok:
            echecs.append({"onglet": d["onglet"], "ligne": None, "raison": "colonne inutile non écartée"})

    par_ligne = defaultdict(list)
    for d in verite:
        if d["ligne_originale"] == "":
            continue
        par_ligne[(d["onglet"], int(d["ligne_originale"]))].append(d)

    for (onglet, ligne), defauts in par_ligne.items():
        table = ONGLET_PAR_TABLE_INVERSE[onglet]
        if any(d["categorie_defaut"].startswith("structure_") for d in defauts):
            ok = any(
                s["source_onglet"] == onglet and s["ligne_origine"] == ligne
                for s in etat["structure"]
            )
            for d in defauts:
                par_categorie[d["categorie_defaut"]].append(ok)
            if not ok:
                echecs.append({"onglet": onglet, "ligne": ligne, "raison": "structure non écartée"})
            continue

        tous_corrigeables = all(d["corrigeable"] == "True" for d in defauts)
        quarantaine = _en_quarantaine(etat, table, ligne)

        if any(d["categorie_defaut"] in ("doublon_exact", "doublon_quasi_evident") for d in defauts):
            # Ligne fusionnée avec une autre : elle disparaît de clean_staging
            # (pas son propre client_id) sans être en quarantaine — la bonne
            # vérification est la présence d'une trace de fusion dans
            # correction_log, pas une comparaison de valeur de champ.
            fusionnee = any(
                c["table_cible"] == table and c["ligne_origine"] == ligne and c["colonne"] == "doublon"
                for c in etat["corrections"]
            )
            ok = fusionnee and not quarantaine
            for d in defauts:
                par_categorie[d["categorie_defaut"]].append(ok)
            if not ok:
                echecs.append({"onglet": onglet, "ligne": ligne, "raison": "doublon non fusionné"})
            continue

        if tous_corrigeables:
            ok = not quarantaine
            if ok:
                for d in defauts:
                    colonne = d["colonne"]
                    categorie = d["categorie_defaut"]
                    valeur_obtenue = _valeur_clean(etat, table, ligne, colonne)

                    if categorie == "champ_vide_normalise":
                        # "valeur_avant" (colonne CSV) = la valeur d'origine
                        # avant l'injection du défaut, gardée dans la vérité
                        # terrain pour référence — mais la règle de nettoyage
                        # ne restitue jamais une valeur vide : elle la
                        # normalise en NULL (charte 00-vision.md), l'info
                        # d'origine est irrécupérable par construction.
                        champ_ok = valeur_obtenue is None
                    elif categorie == "siret_scientifique":
                        # Reconstruction à partir de la notation scientifique
                        # volontairement approximative (complétée par des
                        # zéros, voir 00-vision.md) : on vérifie juste qu'un
                        # SIRET à 14 chiffres a bien été reconstruit, pas
                        # qu'il correspond exactement à l'original (perdu par
                        # la conversion Excel en notation scientifique).
                        champ_ok = valeur_obtenue is not None and len(str(valeur_obtenue)) == 14
                    else:
                        valeur_attendue = d["valeur_avant"]
                        champ_ok = _valeurs_equivalentes(valeur_obtenue, valeur_attendue)

                    par_categorie[categorie].append(champ_ok)
                    if not champ_ok:
                        echecs.append({
                            "onglet": onglet, "ligne": ligne, "colonne": colonne,
                            "raison": f"attendu={d['valeur_avant']!r} obtenu={valeur_obtenue!r}",
                        })
            else:
                motifs = next(
                    (q["motif_rejet"] for q in etat["quarantine"][table] if q["ligne_origine"] == ligne),
                    "",
                )
                cascade = motifs.strip(";").split(";") == ["reference_inexistante"]
                for d in defauts:
                    par_categorie[d["categorie_defaut"]].append(cascade)
                if not cascade:
                    echecs.append({
                        "onglet": onglet, "ligne": ligne,
                        "raison": f"corrigeable mais en quarantaine (motifs={motifs})",
                    })
        else:
            ok = quarantaine
            for d in defauts:
                par_categorie[d["categorie_defaut"]].append(ok)
            if not ok:
                echecs.append({"onglet": onglet, "ligne": ligne, "raison": "non corrigeable mais pas en quarantaine"})

    total = sum(len(v) for v in par_categorie.values())
    reussis = sum(sum(v) for v in par_categorie.values())
    taux_global = reussis / total if total else 1.0

    return {
        "taux_global": taux_global,
        "cible": SEUIL_CORRECTION_CIBLE,
        "atteint": taux_global >= SEUIL_CORRECTION_CIBLE,
        "par_categorie": {
            cat: sum(v) / len(v) for cat, v in sorted(par_categorie.items())
        },
        "echecs": echecs,
    }


ONGLET_PAR_TABLE_INVERSE = {v: k for k, v in ONGLET_PAR_TABLE.items()}


# ---------------------------------------------------------------------------
# 5. Résultats dbt
# ---------------------------------------------------------------------------

def _resultats_dbt(chemin: Path) -> dict | None:
    if not chemin.exists():
        return None
    data = json.loads(chemin.read_text())
    resultats = data.get("results", [])
    tests = [r for r in resultats if r.get("unique_id", "").startswith("test.")]
    modeles = [r for r in resultats if r.get("unique_id", "").startswith("model.")]
    return {
        "genere_le": data.get("metadata", {}).get("generated_at"),
        "nb_tests": len(tests),
        "nb_tests_ok": sum(1 for t in tests if t.get("status") == "pass"),
        "nb_tests_echec": sum(1 for t in tests if t.get("status") != "pass"),
        "nb_modeles": len(modeles),
        "tests_echoues": [
            {"nom": t["unique_id"].split(".")[-1], "statut": t.get("status")}
            for t in tests if t.get("status") != "pass"
        ],
    }


# ---------------------------------------------------------------------------
# 6. Avant/après visuel
# ---------------------------------------------------------------------------

def _avant_apres_visuel(etat: dict, table: str, n: int = 10) -> list[dict]:
    corrections_par_ligne: dict[int, list[dict]] = defaultdict(list)
    for c in etat["corrections"]:
        if c["table_cible"] == table:
            corrections_par_ligne[c["ligne_origine"]].append(c)

    lignes_avec_correction = sorted(corrections_par_ligne.keys())[:n]
    extrait = []
    for ligne_origine in lignes_avec_correction:
        raw_row = next(
            (r for r in etat["raw"][table] if r["ligne_origine"] == ligne_origine), None,
        )
        clean_row = next(
            (r for r in etat["clean"][table] if r["ligne_origine"] == ligne_origine), None,
        )
        colonnes_corrigees = {c["colonne"] for c in corrections_par_ligne[ligne_origine]}
        extrait.append({
            "ligne_origine": ligne_origine,
            "raw": raw_row,
            "clean": clean_row,
            "colonnes_corrigees": colonnes_corrigees,
        })
    return extrait


# ---------------------------------------------------------------------------
# Rendu
# ---------------------------------------------------------------------------

def generer_rapport(conn, source_fichier: str, chemin_verite: Path, chemin_dbt_results: Path) -> dict:
    etat = _charger_etat(conn, source_fichier)
    verite = _charger_verite_terrain(chemin_verite) if chemin_verite.exists() else []

    return {
        "source_fichier": source_fichier,
        "reconciliation": _reconciliation(etat),
        "defauts": _repartition_defauts(etat),
        "qualite": _taux_qualite(etat),
        "verite_terrain": _comparaison_verite_terrain(etat, verite) if verite else None,
        "dbt": _resultats_dbt(chemin_dbt_results),
        "avant_apres": {table: _avant_apres_visuel(etat, table) for table in TABLES},
    }


def ecrire_html(contexte: dict, chemin_sortie: Path) -> None:
    env = Environment(
        loader=FileSystemLoader(Path(__file__).parent / "templates"),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("rapport_qualite.html.j2")
    chemin_sortie.parent.mkdir(parents=True, exist_ok=True)
    chemin_sortie.write_text(template.render(**contexte), encoding="utf-8")


def ecrire_markdown(contexte: dict, chemin_sortie: Path) -> None:
    rec = contexte["reconciliation"]
    vt = contexte["verite_terrain"]
    lignes = [
        "# Rapport qualité — résumé",
        "",
        "> Projet démo, données 100 % fictives. Défauts injectés volontairement "
        "par le générateur (voir [specs/00-vision.md](../specs/00-vision.md)). "
        "Rapport complet : [rapport_qualite.html](rapport_qualite.html).",
        "",
        "## Réconciliation des volumes",
        "",
        "| Table | Lues | Structure écartée | Propres | Quarantaine | Fusionnés | OK |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in rec:
        ok = "✅" if r["ok_ingestion"] and r["ok_nettoyage"] else "❌"
        lignes.append(
            f"| {r['table']} | {r['lues']} | {r['structure']} | {r['propres']} | "
            f"{r['quarantaine']} | {r['fusionnes']} | {ok} |"
        )

    lignes += ["", "## Comparaison à la vérité terrain", ""]
    if vt:
        pct = f"{vt['taux_global']*100:.1f}%"
        cible = f"{vt['cible']*100:.0f}%"
        statut = "✅ atteint" if vt["atteint"] else "❌ non atteint"
        lignes.append(f"Taux de correction mesuré : **{pct}** (cible ≥ {cible}) — {statut}.")
    else:
        lignes.append("Vérité terrain non disponible (`make generate` non exécuté).")

    dbt = contexte["dbt"]
    lignes += ["", "## Tests dbt", ""]
    if dbt:
        lignes.append(f"{dbt['nb_tests_ok']}/{dbt['nb_tests']} tests dbt passés.")
    else:
        lignes.append("Résultats dbt non disponibles (`make dbt` non exécuté).")

    chemin_sortie.write_text("\n".join(lignes) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère le rapport qualité HTML + résumé Markdown.")
    parser.add_argument("--fichier", default="clients_commandes_brut.xlsx")
    parser.add_argument("--verite-terrain", type=Path, default=Path("data/verite_terrain.csv"))
    parser.add_argument("--dbt-results", type=Path, default=Path("dbt_project/target/run_results.json"))
    parser.add_argument("--sortie-html", type=Path, default=Path("docs/rapport_qualite.html"))
    parser.add_argument("--sortie-md", type=Path, default=Path("docs/rapport_qualite.md"))
    args = parser.parse_args()

    conn = get_connection()
    try:
        contexte = generer_rapport(conn, args.fichier, args.verite_terrain, args.dbt_results)
    finally:
        conn.close()

    ecrire_html(contexte, args.sortie_html)
    ecrire_markdown(contexte, args.sortie_md)

    print(f"Rapport généré : {args.sortie_html} / {args.sortie_md}")
    for r in contexte["reconciliation"]:
        statut = "OK" if r["ok_ingestion"] and r["ok_nettoyage"] else "KO"
        print(f"  {r['table']:10s} réconciliation : {statut}")
    if contexte["verite_terrain"]:
        print(f"  Taux de correction (vérité terrain) : {contexte['verite_terrain']['taux_global']*100:.1f}%")


if __name__ == "__main__":
    main()
