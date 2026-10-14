"""Détection de doublons/quasi-doublons de clients (voir specs/03-cleaning.md
et la charte de specs/00-vision.md). Seuls les clients ont une notion de
quasi-doublon dans ce projet.
"""

import unicodedata
from difflib import SequenceMatcher

SEUIL_FUSION = 0.92


def _sans_accent(texte: str) -> str:
    normalise = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in normalise if not unicodedata.combining(c))


def normaliser_nom(nom: str) -> str:
    texte = _sans_accent(nom).lower()
    return " ".join(texte.split())


def _cle_similarite(nom: str) -> str:
    """Les mots sont triés : un simple changement d'ordre des mots (« SARL
    Dupont » / « Dupont SARL ») ne doit pas faire chuter la similarité."""
    return " ".join(sorted(normaliser_nom(nom).split(" ")))


def similarite(nom1: str, nom2: str) -> float:
    return SequenceMatcher(None, _cle_similarite(nom1), _cle_similarite(nom2)).ratio()


def est_doublon_fusionnable(
    nom1: str, ville1: str, code_postal1: str,
    nom2: str, ville2: str, code_postal2: str,
    seuil: float = SEUIL_FUSION,
) -> bool:
    """Fusion automatique seulement si similarité de nom >= seuil **et**
    même ville/code postal ; sinon quasi-doublon incertain, jamais fusionné
    à l'aveugle."""
    return (
        similarite(nom1, nom2) >= seuil
        and ville1 == ville2
        and code_postal1 == code_postal2
    )
