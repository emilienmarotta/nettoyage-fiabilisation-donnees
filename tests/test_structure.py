"""Vérifie les règles de détection des lignes de structure de
specs/02-ingestion.md (pures, sans base de données)."""

from pipeline.structure import est_entete_repete, est_ligne_total, est_ligne_vide

LABELS = ["ID Client", "Nom Entreprise", "Ville"]


def test_ligne_vide_detectee():
    assert est_ligne_vide([None, "", "  "])


def test_ligne_non_vide_non_detectee():
    assert not est_ligne_vide([None, "x", ""])


def test_ligne_total_detectee_quelle_que_soit_la_colonne():
    assert est_ligne_total(["", "Sous-total", ""])
    assert est_ligne_total(["TOTAL", "", ""])


def test_ligne_total_insensible_casse_et_espaces():
    assert est_ligne_total([" total ", "", ""])


def test_ligne_normale_pas_un_total():
    assert not est_ligne_total(["1", "Leblanc", "Paris"])


def test_entete_repete_detectee():
    assert est_entete_repete(["id client", " NOM ENTREPRISE", "ville"], LABELS)


def test_entete_repete_mauvaise_longueur():
    assert not est_entete_repete(["ID Client", "Nom Entreprise"], LABELS)


def test_ligne_de_donnees_pas_un_entete():
    assert not est_entete_repete(["1", "Leblanc", "Paris"], LABELS)
