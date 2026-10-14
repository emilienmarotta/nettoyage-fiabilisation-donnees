from pipeline.clean.doublons import est_doublon_fusionnable, similarite


def test_similarite_casse():
    assert similarite("LEBLANC SARL", "Leblanc Sarl") == 1.0


def test_similarite_accents():
    assert similarite("Laurent et Fils", "Laurent et Fils") == 1.0
    assert similarite("Société Générale", "Societe Generale") == 1.0


def test_similarite_ordre_des_mots():
    assert similarite("SARL Dupont", "Dupont SARL") == 1.0


def test_similarite_noms_differents_basse():
    assert similarite("Leblanc", "Dupont Industries") < 0.5


def test_fusion_meme_ville_et_cp():
    assert est_doublon_fusionnable(
        "Leblanc SARL", "Paris", "75001",
        "SARL Leblanc", "Paris", "75001",
    )


def test_pas_de_fusion_si_ville_differente():
    # Même nom, ville différente : quasi-doublon incertain, jamais fusionné.
    assert not est_doublon_fusionnable(
        "Leblanc SARL", "Paris", "75001",
        "Leblanc SARL", "Lyon", "69001",
    )
