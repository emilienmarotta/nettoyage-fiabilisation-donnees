"""Vérifie les critères de réussite de specs/01-generator.md :
déterminisme et couverture du catalogue de défauts par la vérité terrain.
"""

import csv
from collections import Counter

import pytest

from generator.main import run

SEED = 42
TAUX_DEFAUTS = 0.15

CATEGORIES_ATTENDUES = {
    "doublon_exact", "doublon_quasi_evident", "doublon_quasi_incertain",
    "code_postal_4_chiffres", "siret_scientifique", "siret_illisible",
    "email_invalide", "telephone_format", "champ_obligatoire_vide",
    "champ_vide_normalise", "code_produit_casse", "categorie_casse",
    "valeur_numerique_invalide", "nombre_espace_virgule", "nombre_point_simple",
    "nombre_point_virgule_euro", "nombre_pourcentage", "date_format_iso",
    "date_format_texte_fr", "date_serie_excel", "date_invalide",
    "date_aberrante", "quantite_ou_prix_invalide", "reference_inexistante",
    "livraison_avant_commande",
}


def _lire_verite_terrain(data_dir) -> list[dict]:
    with (data_dir / "verite_terrain.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def deux_executions(tmp_path_factory):
    dir1 = tmp_path_factory.mktemp("run1")
    dir2 = tmp_path_factory.mktemp("run2")
    run(SEED, TAUX_DEFAUTS, dir1)
    run(SEED, TAUX_DEFAUTS, dir2)
    return dir1, dir2


def test_idempotence_verite_terrain(deux_executions):
    dir1, dir2 = deux_executions
    assert (dir1 / "verite_terrain.csv").read_text() == (dir2 / "verite_terrain.csv").read_text()


def test_idempotence_donnees_parfaites(deux_executions):
    dir1, dir2 = deux_executions
    for table in ["clients", "produits", "commandes"]:
        chemin = f"parfait/{table}.csv"
        assert (dir1 / chemin).read_text() == (dir2 / chemin).read_text()


def test_couverture_catalogue_defauts(deux_executions):
    dir1, _ = deux_executions
    lignes = _lire_verite_terrain(dir1)
    categories_presentes = {l["categorie_defaut"] for l in lignes}
    manquantes = CATEGORIES_ATTENDUES - categories_presentes
    assert not manquantes, f"catégories absentes de la vérité terrain : {manquantes}"


def test_volume_minimum_par_categorie(deux_executions):
    dir1, _ = deux_executions
    lignes = _lire_verite_terrain(dir1)
    compte = Counter(l["categorie_defaut"] for l in lignes)
    trop_rares = {cat: n for cat, n in compte.items() if cat in CATEGORIES_ATTENDUES and n < 10}
    assert not trop_rares, f"catégories avec moins de 10 occurrences : {trop_rares}"
