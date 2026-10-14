from decimal import Decimal

from pipeline.clean.nombres import parser_nombre


def test_espace_milliers_virgule_decimale():
    assert parser_nombre("1 234,50") == (Decimal("1234.50"), True, None)


def test_point_decimal_simple():
    assert parser_nombre("1234.56") == (Decimal("1234.56"), False, None)


def test_point_milliers_virgule_decimale_euro():
    assert parser_nombre("1.234,50 €") == (Decimal("1234.50"), True, None)


def test_virgule_decimale_sans_milliers():
    assert parser_nombre("45,67") == (Decimal("45.67"), True, None)


def test_entier_simple():
    assert parser_nombre("5") == (Decimal("5"), False, None)


def test_pourcentage_toujours_invalide():
    # Un % n'est jamais une notation fiable de prix/quantité : quarantaine
    # systématique, jamais une division silencieuse par 100.
    assert parser_nombre("50,2%") == (None, False, "valeur_numerique_invalide")


def test_texte_non_numerique_invalide():
    assert parser_nombre("gratuit") == (None, False, "valeur_numerique_invalide")


def test_champ_vide():
    assert parser_nombre("") == (None, False, None)


def test_nombre_negatif():
    assert parser_nombre("-5") == (Decimal("-5"), False, None)
