"""Injection des défauts du catalogue dans le jeu de données parfait.

Chaque injection est tracée dans la vérité terrain (voir
specs/01-generator.md) : onglet, ligne (index logique dans la table, avant
insertion des lignes de structure par `excel_writer.py`), colonne, valeur
avant, valeur après, catégorie de défaut, et si le défaut est censé être
corrigé (`corrigeable=True`) ou mis en quarantaine (`corrigeable=False`).

Les comptes de base ci-dessous sont calibrés pour un taux d'injection de
0.15 (15 % des lignes touchées) et mis à l'échelle linéairement par
`taux_defauts`.
"""

import copy
import random
import unicodedata
from datetime import date, timedelta

MOIS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

EXCEL_EPOCH = date(1899, 12, 30)

# (catégorie, nombre de lignes à un taux de référence de 0.15)
CLIENTS_COUNTS_REF = {
    "doublon_exact": 15,
    "doublon_quasi_evident": 15,
    "doublon_quasi_incertain": 15,
    "code_postal_4_chiffres": 25,
    "siret_scientifique": 20,
    "siret_illisible": 15,
    "email_invalide": 20,
    "telephone_format": 25,
    "champ_obligatoire_vide": 15,
    "champ_vide_normalise": 20,
}

PRODUITS_COUNTS_REF = {
    "code_produit_casse": 25,
    "categorie_casse": 25,
    "champ_vide_normalise": 15,
    "valeur_numerique_invalide": 10,
    "nombre_espace_virgule": 10,
    "nombre_point_simple": 10,
    "nombre_point_virgule_euro": 10,
    "nombre_pourcentage": 8,
}

COMMANDES_COUNTS_REF = {
    "date_format_iso": 30,
    "date_format_texte_fr": 30,
    "date_serie_excel": 30,
    "date_invalide": 20,
    "date_aberrante": 20,
    "nombre_espace_virgule": 25,
    "nombre_point_simple": 25,
    "nombre_point_virgule_euro": 25,
    "nombre_pourcentage": 15,
    "valeur_numerique_invalide": 15,
    "champ_obligatoire_vide": 20,
    "quantite_ou_prix_invalide": 25,
    "reference_inexistante": 20,
    "livraison_avant_commande": 20,
}

REF_TAUX = 0.15


def _scaled_counts(counts_ref: dict, taux_defauts: float, n_rows: int) -> dict:
    facteur = taux_defauts / REF_TAUX
    scaled = {}
    for categorie, n_ref in counts_ref.items():
        n = max(1, round(n_ref * facteur))
        scaled[categorie] = min(n, n_rows)
    return scaled


def _sans_accent(texte: str) -> str:
    normalise = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in normalise if not unicodedata.combining(c))


def _format_nombre(valeur: float, style: str) -> str:
    entier, decimales = f"{valeur:.2f}".split(".")
    if style == "espace_virgule":
        entier_espace = f"{int(entier):,}".replace(",", " ")
        return f"{entier_espace},{decimales}"
    if style == "point_simple":
        return f"{valeur:.1f}"
    if style == "point_virgule_euro":
        entier_point = f"{int(entier):,}".replace(",", ".")
        return f"{entier_point},{decimales} €"
    if style == "pourcentage":
        return f"{decimales},{entier[-1]}%"
    raise ValueError(f"style de nombre inconnu : {style}")


def _format_date(d: date, style: str, rng: random.Random) -> str:
    if style == "iso":
        return d.isoformat()
    if style == "texte_fr":
        return f"{d.day} {MOIS_FR[d.month - 1]} {d.year}"
    if style == "serie_excel":
        return str((d - EXCEL_EPOCH).days)
    if style == "invalide":
        return rng.choice(["32/13/2025", "jamais", "--/--/----", "n.c."])
    if style == "aberrante":
        futur = d.replace(year=d.year + rng.randint(5, 15))
        return futur.strftime("%d/%m/%Y")
    raise ValueError(f"style de date inconnu : {style}")


def _champ_vide_variant(rng: random.Random) -> str:
    return rng.choice(["", "N/A", "-", "null", "   "])


class VeriteTerrain:
    def __init__(self):
        self.lignes: list[dict] = []

    def ajouter(
        self,
        onglet: str,
        ligne_originale,
        colonne,
        valeur_avant,
        valeur_apres,
        categorie_defaut: str,
        corrigeable,
    ) -> None:
        self.lignes.append(
            {
                "onglet": onglet,
                "ligne_originale": ligne_originale,
                "colonne": colonne,
                "valeur_avant": valeur_avant,
                "valeur_apres": valeur_apres,
                "categorie_defaut": categorie_defaut,
                "corrigeable": corrigeable,
            }
        )


def _injecter_doublons_clients(
    clients: list[dict], rng: random.Random, counts: dict, verite: VeriteTerrain
) -> list[dict]:
    n = len(clients)
    doublons_ajoutes = []
    next_id = max(c["client_id"] for c in clients) + 1

    for ligne_idx in rng.sample(range(n), counts["doublon_exact"]):
        original = clients[ligne_idx]
        clone = copy.deepcopy(original)
        clone["client_id"] = next_id
        clone["code_client"] = f"CLI-{next_id:04d}"
        doublons_ajoutes.append(clone)
        verite.ajouter(
            "Clients", n + len(doublons_ajoutes), "nom_entreprise",
            original["nom_entreprise"], clone["nom_entreprise"],
            "doublon_exact", True,
        )
        next_id += 1

    candidats_restants = list(range(n))
    for ligne_idx in rng.sample(candidats_restants, counts["doublon_quasi_evident"]):
        original = clients[ligne_idx]
        clone = copy.deepcopy(original)
        clone["client_id"] = next_id
        clone["code_client"] = f"CLI-{next_id:04d}"
        variante = rng.choice(["casse", "espaces", "accents", "ordre_mots"])
        nom = original["nom_entreprise"]
        if variante == "casse":
            nom_variant = nom.upper()
        elif variante == "espaces":
            nom_variant = f"  {nom}  ".replace(" ", "  ", 1)
        elif variante == "accents":
            nom_variant = _sans_accent(nom)
        else:
            mots = nom.split(" ")
            nom_variant = " ".join(reversed(mots)) if len(mots) > 1 else nom
        clone["nom_entreprise"] = nom_variant
        doublons_ajoutes.append(clone)
        verite.ajouter(
            "Clients", n + len(doublons_ajoutes), "nom_entreprise",
            nom, nom_variant, "doublon_quasi_evident", True,
        )
        next_id += 1

    for ligne_idx in rng.sample(candidats_restants, counts["doublon_quasi_incertain"]):
        original = clients[ligne_idx]
        clone = copy.deepcopy(original)
        clone["client_id"] = next_id
        clone["code_client"] = f"CLI-{next_id:04d}"
        autres_villes = sorted({c["ville"] for c in clients} - {original["ville"]})
        clone["ville"] = rng.choice(autres_villes or [original["ville"]])
        clone["code_postal"] = f"{rng.randint(10000, 95999)}"
        doublons_ajoutes.append(clone)
        verite.ajouter(
            "Clients", n + len(doublons_ajoutes), "ville",
            original["ville"], clone["ville"], "doublon_quasi_incertain", False,
        )
        next_id += 1

    return clients + doublons_ajoutes


def _injecter_defauts_clients(
    clients: list[dict], rng: random.Random, taux_defauts: float, verite: VeriteTerrain
) -> list[dict]:
    clients = [dict(c) for c in clients]
    n = len(clients)
    counts = _scaled_counts(CLIENTS_COUNTS_REF, taux_defauts, n)

    clients = _injecter_doublons_clients(clients, rng, counts, verite)

    for idx in rng.sample(range(n), counts["code_postal_4_chiffres"]):
        avant = clients[idx]["code_postal"]
        apres = avant.lstrip("0") or avant[-4:]
        clients[idx]["code_postal"] = apres
        verite.ajouter("Clients", idx + 1, "code_postal", avant, apres,
                        "code_postal_4_chiffres", True)

    for idx in rng.sample(range(n), counts["siret_scientifique"]):
        avant = clients[idx]["siret"]
        apres = f"{float(avant):.5E}"
        clients[idx]["siret"] = apres
        verite.ajouter("Clients", idx + 1, "siret", avant, apres,
                        "siret_scientifique", True)

    for idx in rng.sample(range(n), counts["siret_illisible"]):
        avant = clients[idx]["siret"]
        apres = f"{float(avant):.1E}"
        clients[idx]["siret"] = apres
        verite.ajouter("Clients", idx + 1, "siret", avant, apres,
                        "siret_illisible", False)

    for idx in rng.sample(range(n), counts["email_invalide"]):
        avant = clients[idx]["email"]
        apres = avant.replace("@", "_")
        clients[idx]["email"] = apres
        verite.ajouter("Clients", idx + 1, "email", avant, apres,
                        "email_invalide", False)

    for idx in rng.sample(range(n), counts["telephone_format"]):
        avant = clients[idx]["telephone"]
        chiffres = avant.replace(" ", "")
        variante = rng.choice(["points", "sans_espace", "international", "espace_insecable"])
        if variante == "points":
            apres = ".".join(chiffres[i:i + 2] for i in range(0, len(chiffres), 2))
        elif variante == "sans_espace":
            apres = chiffres
        elif variante == "international":
            apres = "+33 " + " ".join(
                [chiffres[1:3]] + [chiffres[i:i + 2] for i in range(3, len(chiffres), 2)]
            )
        else:
            apres = avant.replace(" ", " ")
        clients[idx]["telephone"] = apres
        verite.ajouter("Clients", idx + 1, "telephone", avant, apres,
                        "telephone_format", True)

    for idx in rng.sample(range(n), counts["champ_obligatoire_vide"]):
        avant = clients[idx]["nom_entreprise"]
        apres = _champ_vide_variant(rng)
        clients[idx]["nom_entreprise"] = apres
        verite.ajouter("Clients", idx + 1, "nom_entreprise", avant, apres,
                        "champ_obligatoire_vide", False)

    for idx in rng.sample(range(n), counts["champ_vide_normalise"]):
        avant = clients[idx]["adresse"]
        apres = _champ_vide_variant(rng)
        clients[idx]["adresse"] = apres
        verite.ajouter("Clients", idx + 1, "adresse", avant, apres,
                        "champ_vide_normalise", True)

    return clients


def _injecter_defauts_produits(
    produits: list[dict], rng: random.Random, taux_defauts: float, verite: VeriteTerrain
) -> list[dict]:
    produits = [dict(p) for p in produits]
    n = len(produits)
    counts = _scaled_counts(PRODUITS_COUNTS_REF, taux_defauts, n)

    for idx in rng.sample(range(n), counts["code_produit_casse"]):
        avant = produits[idx]["code_produit"]
        apres = rng.choice([avant.lower(), avant.replace("ART", "Art")])
        produits[idx]["code_produit"] = apres
        verite.ajouter("Produits", idx + 1, "code_produit", avant, apres,
                        "code_produit_casse", True)

    for idx in rng.sample(range(n), counts["categorie_casse"]):
        avant = produits[idx]["categorie"]
        variante = rng.choice(["majuscule", "capitalize_accent", "sans_accent_maj"])
        if variante == "majuscule":
            apres = avant.upper()
        elif variante == "capitalize_accent":
            apres = avant.capitalize()
        else:
            apres = _sans_accent(avant).upper()
        produits[idx]["categorie"] = apres
        verite.ajouter("Produits", idx + 1, "categorie", avant, apres,
                        "categorie_casse", True)

    for idx in rng.sample(range(n), counts["champ_vide_normalise"]):
        avant = produits[idx]["fournisseur"]
        apres = _champ_vide_variant(rng)
        produits[idx]["fournisseur"] = apres
        verite.ajouter("Produits", idx + 1, "fournisseur", avant, apres,
                        "champ_vide_normalise", True)

    for idx in rng.sample(range(n), counts["valeur_numerique_invalide"]):
        avant = produits[idx]["prix_unitaire"]
        apres = rng.choice(["gratuit", "ND", "prix sur devis"])
        produits[idx]["prix_unitaire"] = apres
        verite.ajouter("Produits", idx + 1, "prix_unitaire", avant, apres,
                        "valeur_numerique_invalide", False)

    for style, cle in [
        ("espace_virgule", "nombre_espace_virgule"),
        ("point_simple", "nombre_point_simple"),
        ("point_virgule_euro", "nombre_point_virgule_euro"),
    ]:
        for idx in rng.sample(range(n), counts[cle]):
            avant = produits[idx]["prix_unitaire"]
            if isinstance(avant, str):
                continue
            apres = _format_nombre(avant, style)
            produits[idx]["prix_unitaire"] = apres
            verite.ajouter("Produits", idx + 1, "prix_unitaire", avant, apres,
                            cle, True)

    for idx in rng.sample(range(n), counts["nombre_pourcentage"]):
        avant = produits[idx]["prix_unitaire"]
        if not isinstance(avant, (int, float)):
            continue
        apres = _format_nombre(avant, "pourcentage")
        produits[idx]["prix_unitaire"] = apres
        verite.ajouter("Produits", idx + 1, "prix_unitaire", avant, apres,
                        "nombre_pourcentage", False)

    return produits


def _injecter_defauts_commandes(
    commandes: list[dict],
    rng: random.Random,
    taux_defauts: float,
    verite: VeriteTerrain,
    id_client_max: int,
    id_produit_max: int,
) -> list[dict]:
    commandes = [dict(c) for c in commandes]
    n = len(commandes)
    counts = _scaled_counts(COMMANDES_COUNTS_REF, taux_defauts, n)

    for style, cle in [
        ("iso", "date_format_iso"),
        ("texte_fr", "date_format_texte_fr"),
        ("serie_excel", "date_serie_excel"),
        ("invalide", "date_invalide"),
        ("aberrante", "date_aberrante"),
    ]:
        for idx in rng.sample(range(n), counts[cle]):
            colonne = rng.choice(["date_commande", "date_livraison"])
            avant = commandes[idx][colonne]
            if not isinstance(avant, date):
                continue
            apres = _format_date(avant, style, rng)
            commandes[idx][colonne] = apres
            corrigeable = style not in ("invalide", "aberrante")
            verite.ajouter("Commandes", idx + 1, colonne, avant, apres,
                            cle, corrigeable)

    for style, cle in [
        ("espace_virgule", "nombre_espace_virgule"),
        ("point_simple", "nombre_point_simple"),
        ("point_virgule_euro", "nombre_point_virgule_euro"),
    ]:
        for idx in rng.sample(range(n), counts[cle]):
            avant = commandes[idx]["prix_unitaire_commande"]
            if isinstance(avant, str):
                continue
            apres = _format_nombre(avant, style)
            commandes[idx]["prix_unitaire_commande"] = apres
            verite.ajouter("Commandes", idx + 1, "prix_unitaire_commande",
                            avant, apres, cle, True)

    for idx in rng.sample(range(n), counts["nombre_pourcentage"]):
        avant = commandes[idx]["prix_unitaire_commande"]
        if not isinstance(avant, (int, float)):
            continue
        apres = _format_nombre(avant, "pourcentage")
        commandes[idx]["prix_unitaire_commande"] = apres
        verite.ajouter("Commandes", idx + 1, "prix_unitaire_commande",
                        avant, apres, "nombre_pourcentage", False)

    for idx in rng.sample(range(n), counts["valeur_numerique_invalide"]):
        avant = commandes[idx]["prix_unitaire_commande"]
        apres = rng.choice(["cinquante euros", "ND", "voir devis"])
        commandes[idx]["prix_unitaire_commande"] = apres
        verite.ajouter("Commandes", idx + 1, "prix_unitaire_commande",
                        avant, apres, "valeur_numerique_invalide", False)

    for idx in rng.sample(range(n), counts["champ_obligatoire_vide"]):
        colonne = rng.choice(["client_id", "produit_id", "quantite"])
        avant = commandes[idx][colonne]
        apres = _champ_vide_variant(rng)
        commandes[idx][colonne] = apres
        verite.ajouter("Commandes", idx + 1, colonne, avant, apres,
                        "champ_obligatoire_vide", False)

    for idx in rng.sample(range(n), counts["quantite_ou_prix_invalide"]):
        colonne = rng.choice(["quantite", "prix_unitaire_commande"])
        avant = commandes[idx][colonne]
        apres = rng.choice([0, -rng.randint(1, 20)])
        commandes[idx][colonne] = apres
        verite.ajouter("Commandes", idx + 1, colonne, avant, apres,
                        "quantite_ou_prix_invalide", False)

    for idx in rng.sample(range(n), counts["reference_inexistante"]):
        colonne = rng.choice(["client_id", "produit_id"])
        avant = commandes[idx][colonne]
        apres = (id_client_max if colonne == "client_id" else id_produit_max) + rng.randint(500, 999)
        commandes[idx][colonne] = apres
        verite.ajouter("Commandes", idx + 1, colonne, avant, apres,
                        "reference_inexistante", False)

    for idx in rng.sample(range(n), counts["livraison_avant_commande"]):
        avant = commandes[idx]["date_livraison"]
        date_commande = commandes[idx]["date_commande"]
        if not isinstance(avant, date) or not isinstance(date_commande, date):
            continue
        apres = date_commande - timedelta(days=rng.randint(1, 10))
        commandes[idx]["date_livraison"] = apres
        verite.ajouter("Commandes", idx + 1, "date_livraison", avant, apres,
                        "livraison_avant_commande", False)

    return commandes


def injecter_defauts(dataset: dict, seed: int, taux_defauts: float) -> tuple[dict, list[dict]]:
    """Retourne (dataset_desordonne, lignes_verite_terrain)."""
    rng = random.Random(seed + 1)
    verite = VeriteTerrain()

    clients = _injecter_defauts_clients(dataset["clients"], rng, taux_defauts, verite)
    produits = _injecter_defauts_produits(dataset["produits"], rng, taux_defauts, verite)
    commandes = _injecter_defauts_commandes(
        dataset["commandes"], rng, taux_defauts, verite,
        id_client_max=max(c["client_id"] for c in dataset["clients"]),
        id_produit_max=max(p["produit_id"] for p in dataset["produits"]),
    )

    dataset_desordonne = {"clients": clients, "produits": produits, "commandes": commandes}
    return dataset_desordonne, verite.lignes
