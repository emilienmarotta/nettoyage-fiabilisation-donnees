from datetime import date

from pipeline.clean.dates import est_date_aberrante, parser_date


def test_iso_deja_valide():
    assert parser_date("2025-03-12") == ("2025-03-12", False, None)


def test_format_jj_mm_aaaa():
    assert parser_date("12/03/2025") == ("2025-03-12", True, None)


def test_convention_francaise_jour_mois_jamais_devinee():
    # 03/04/2025 est toujours jour=3, mois=4 (jamais mois=3, jour=4).
    assert parser_date("03/04/2025") == ("2025-04-03", True, None)


def test_format_texte_fr():
    assert parser_date("12 mars 2025") == ("2025-03-12", True, None)


def test_format_texte_fr_mois_accentue():
    assert parser_date("1 février 2025") == ("2025-02-01", True, None)


def test_format_serie_excel():
    assert parser_date("45000") == ("2023-03-15", True, None)


def test_date_invalide_jour_mois_hors_limites():
    _, corrige, motif = parser_date("32/13/2025")
    assert (corrige, motif) == (False, "date_invalide")


def test_date_invalide_texte_libre():
    assert parser_date("jamais") == (None, False, "date_invalide")


def test_date_invalide_mois_inconnu():
    assert parser_date("12 blurp 2025") == (None, False, "date_invalide")


def test_champ_vide_retourne_none_sans_motif():
    assert parser_date("") == (None, False, None)


def test_date_aberrante_trop_ancienne():
    assert est_date_aberrante("2014-12-31", aujourdhui=date(2026, 1, 1))


def test_date_aberrante_trop_future():
    assert est_date_aberrante("2029-01-01", aujourdhui=date(2026, 1, 1))


def test_date_non_aberrante():
    assert not est_date_aberrante("2025-06-15", aujourdhui=date(2026, 1, 1))
