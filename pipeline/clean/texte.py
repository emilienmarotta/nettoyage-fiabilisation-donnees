"""Normalisation de texte générique : champs vides et catégories (voir
specs/03-cleaning.md et la charte de specs/00-vision.md)."""

import unicodedata

VARIANTES_VIDES = {"", "n/a", "na", "-", "null"}


def _sans_accent(texte: str) -> str:
    normalise = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in normalise if not unicodedata.combining(c))


def normaliser_champ_vide(valeur: str | None) -> tuple[str | None, bool]:
    """Retourne (valeur_normalisee, corrige). `None` si le champ est
    considéré vide après normalisation (``""``, ``N/A``, ``-``, ``null``,
    espaces seuls)."""
    if valeur is None:
        return None, False
    simplifie = valeur.strip().lower()
    if simplifie in VARIANTES_VIDES:
        return None, valeur != ""
    return valeur, False


def normaliser_categorie(
    valeur: str | None, categories_valides: list[str]
) -> tuple[str | None, bool, str | None]:
    """Table de correspondance explicite (mapping figé, pas de
    rapprochement flou) : compare la valeur normalisée (minuscule, sans
    accent) à la liste fixe des catégories valides."""
    texte = (valeur or "").strip()
    cible = _sans_accent(texte).lower()
    for categorie in categories_valides:
        if _sans_accent(categorie).lower() == cible:
            return categorie, categorie != texte, None
    return None, False, "categorie_invalide"
