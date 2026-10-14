"""Détection des lignes de structure à écarter (voir specs/02-ingestion.md).

Règles explicites et documentées, pas de détection « magique ». Chaque
fonction travaille sur les valeurs déjà lues (texte, non normalisées) des
colonnes métier attendues d'une ligne.
"""

MOTS_TOTAL = {"total", "sous-total", "sous total"}


def _normalise(valeur) -> str:
    if valeur is None:
        return ""
    return str(valeur).strip().lower()


def est_ligne_vide(valeurs: list) -> bool:
    """Toutes les cellules sont vides/espaces seuls."""
    return all(_normalise(v) == "" for v in valeurs)


def est_ligne_total(valeurs: list) -> bool:
    """Une cellule contient `Total` / `Sous-total` (à la casse et aux
    espaces près), typiquement en première position d'une ligne de total
    de tableau Excel."""
    return any(_normalise(v) in MOTS_TOTAL for v in valeurs)


def est_entete_repete(valeurs: list, labels_attendus: list[str]) -> bool:
    """La ligne correspond exactement aux libellés d'en-tête attendus,
    après normalisation casse/espaces."""
    if len(valeurs) != len(labels_attendus):
        return False
    return [_normalise(v) for v in valeurs] == [_normalise(lbl) for lbl in labels_attendus]


def est_banniere(valeurs: list) -> bool:
    """Ligne de bannière sur cellule fusionnée (ex. « --- Export mensuel -
    Service commercial --- ») : seule la première colonne porte une valeur
    (le reste de la ligne fusionnée est lu vide par openpyxl), et cette
    valeur commence par le marqueur explicite `---`."""
    if not valeurs or _normalise(valeurs[0]) == "":
        return False
    return _normalise(valeurs[0]).startswith("---")
