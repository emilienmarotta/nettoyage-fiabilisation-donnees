from pipeline.clean.identifiants import (
    normaliser_code_postal,
    normaliser_code_produit,
    normaliser_siret,
)


def test_code_postal_5_chiffres_inchange():
    assert normaliser_code_postal("64716") == ("64716", False, None)


def test_code_postal_4_chiffres_recomplete():
    assert normaliser_code_postal("4716") == ("04716", True, None)


def test_code_postal_invalide():
    assert normaliser_code_postal("abcde") == (None, False, "code_postal_invalide")


def test_siret_deja_valide():
    assert normaliser_siret("86379402000835") == ("86379402000835", False, None)


def test_siret_scientifique_reconstituable():
    # 6 chiffres significatifs (.5E) : reconstituable, documenté comme tel.
    valeur, corrige, motif = normaliser_siret("1.04332E+13")
    assert corrige is True and motif is None
    assert valeur == "10433200000000" and len(valeur) == 14


def test_siret_illisible_notation_trop_pauvre():
    # 2 chiffres significatifs (.1E) : pas assez d'information, quarantaine.
    assert normaliser_siret("1.0E+13") == (None, False, "siret_illisible")


def test_siret_scientifique_zero_de_tete_recompose():
    # SIRET d'origine commençant par 0, perdu par la conversion Excel en
    # nombre (exposant E+12 au lieu de E+13) : à recompléter à gauche.
    valeur, corrige, motif = normaliser_siret("7.68104E+12")
    assert corrige is True and motif is None
    assert valeur == "07681040000000" and len(valeur) == 14


def test_code_produit_casse_normalisee():
    assert normaliser_code_produit("art-0042") == ("ART-0042", True, None)


def test_code_produit_deja_normalise():
    assert normaliser_code_produit("ART-0042") == ("ART-0042", False, None)
