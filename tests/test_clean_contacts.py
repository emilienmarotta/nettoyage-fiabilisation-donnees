from pipeline.clean.contacts import normaliser_telephone, valider_email


def test_email_valide():
    assert valider_email("jean.dupont@exemple.fr") == ("jean.dupont@exemple.fr", False, None)


def test_email_invalide_jamais_corrige():
    assert valider_email("jean.dupont_exemple.fr") == (None, False, "email_invalide")


def test_telephone_deja_normalise():
    assert normaliser_telephone("06 12 34 56 78") == ("06 12 34 56 78", False, None)


def test_telephone_points():
    assert normaliser_telephone("06.12.34.56.78") == ("06 12 34 56 78", True, None)


def test_telephone_sans_espace():
    assert normaliser_telephone("0612345678") == ("06 12 34 56 78", True, None)


def test_telephone_international():
    assert normaliser_telephone("+33 61 23 45 67 8") == ("06 12 34 56 78", True, None)


def test_telephone_invalide():
    assert normaliser_telephone("123") == (None, False, "telephone_invalide")
