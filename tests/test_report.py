from pipeline.report import (
    CHAMPS_OBLIGATOIRES,
    VALIDATEURS,
    _cle_doublon,
    _completude,
    _non_vide,
    _unicite,
    _validite,
    _valeurs_equivalentes,
)


def test_non_vide_variantes_vides():
    assert _non_vide(None) is False
    assert _non_vide("") is False
    assert _non_vide("N/A") is False
    assert _non_vide("  ") is False


def test_non_vide_valeur_presente():
    assert _non_vide("Dupont SARL") is True


def test_non_vide_type_non_str():
    # Colonnes entières (client_id/produit_id de clean_staging.commandes) :
    # jamais vides par construction (NOT NULL), pas de .strip() à tenter.
    assert _non_vide(42) is True


def test_completude_champ_obligatoire_manquant():
    rows = [{"nom_entreprise": "Dupont"}, {"nom_entreprise": ""}]
    assert _completude(rows, CHAMPS_OBLIGATOIRES["clients"]) == 0.5


def test_completude_aucune_ligne():
    assert _completude([], CHAMPS_OBLIGATOIRES["clients"]) == 1.0


def test_validite_email_et_code_postal():
    rows = [
        {"email": "a@b.fr", "telephone": "01 02 03 04 05", "code_postal": "75001",
         "siret": "12345678901234", "date_creation": "2020-01-01"},
        {"email": "invalide", "telephone": "01 02 03 04 05", "code_postal": "75001",
         "siret": "12345678901234", "date_creation": "2020-01-01"},
    ]
    taux = _validite(rows, VALIDATEURS["clients"])
    # 1 champ invalide (email) sur 10 vérifiés (2 lignes x 5 champs).
    assert taux == 0.9


def test_cle_doublon_normalise_casse_accents_espaces():
    row1 = {"nom_entreprise": "  DUPONT sarl  ", "ville": "Paris", "code_postal": "75001"}
    row2 = {"nom_entreprise": "Dupont SARL", "ville": "paris", "code_postal": "75001"}
    assert _cle_doublon(row1) == _cle_doublon(row2)


def test_unicite_clients_detecte_doublon():
    rows = [
        {"nom_entreprise": "Dupont", "ville": "Paris", "code_postal": "75001"},
        {"nom_entreprise": "dupont", "ville": "Paris", "code_postal": "75001"},
    ]
    assert _unicite(rows, "clients") == 0.5


def test_unicite_clients_aucun_doublon():
    rows = [
        {"nom_entreprise": "Dupont", "ville": "Paris", "code_postal": "75001"},
        {"nom_entreprise": "Martin", "ville": "Lyon", "code_postal": "69001"},
    ]
    assert _unicite(rows, "clients") == 1.0


def test_valeurs_equivalentes_nombre_precision_differente():
    # Même montant, précision d'affichage différente (vérité terrain générée
    # depuis un float Python vs valeur réellement saisie) : pas une erreur.
    assert _valeurs_equivalentes("287.70", "287.7") is True


def test_valeurs_equivalentes_texte_identique():
    assert _valeurs_equivalentes("ART-0022", "ART-0022") is True


def test_valeurs_equivalentes_texte_different():
    assert _valeurs_equivalentes("ART-0099", "ART-0022") is False


def test_valeurs_equivalentes_attendu_vide_toujours_ok():
    assert _valeurs_equivalentes("peu importe", "") is True
    assert _valeurs_equivalentes(None, None) is True
