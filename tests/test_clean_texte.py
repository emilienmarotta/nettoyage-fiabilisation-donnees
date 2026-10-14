from pipeline.clean.texte import normaliser_categorie, normaliser_champ_vide

CATEGORIES = ["emballage", "hygiene", "boissons", "alimentaire"]


def test_champ_deja_rempli_inchange():
    assert normaliser_champ_vide("Paris") == ("Paris", False)


def test_variantes_vides_normalisees_en_none():
    assert normaliser_champ_vide("") == (None, False)
    assert normaliser_champ_vide("N/A") == (None, True)
    assert normaliser_champ_vide("-") == (None, True)
    assert normaliser_champ_vide("null") == (None, True)
    assert normaliser_champ_vide("   ") == (None, True)


def test_categorie_deja_normalisee():
    assert normaliser_categorie("hygiene", CATEGORIES) == ("hygiene", False, None)


def test_categorie_majuscule():
    assert normaliser_categorie("HYGIENE", CATEGORIES) == ("hygiene", True, None)


def test_categorie_capitalize_avec_accent():
    assert normaliser_categorie("Hygiène", CATEGORIES) == ("hygiene", True, None)


def test_categorie_inconnue():
    assert normaliser_categorie("outillage", CATEGORIES) == (None, False, "categorie_invalide")
