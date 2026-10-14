"""Normalisation des identifiants (code postal, SIRET, code produit) — voir
specs/03-cleaning.md et la charte de specs/00-vision.md."""

import re
from decimal import Decimal, InvalidOperation

_RE_SIRET_SCIENTIFIQUE = re.compile(r"(\d)\.(\d+)E\+(\d+)", re.IGNORECASE)

# Seuil documenté : une notation scientifique de SIRET n'est reconstituable
# sans ambiguïté excessive que si elle garde au moins 5 chiffres
# significatifs après la virgule (6 au total) ; en dessous, l'identifiant
# reconstruit comporterait trop de zéros inventés pour être fiable.
SIRET_CHIFFRES_SIGNIFICATIFS_MIN = 6


def normaliser_code_postal(valeur: str | None) -> tuple[str | None, bool, str | None]:
    texte = (valeur or "").strip()
    if re.fullmatch(r"\d{5}", texte):
        return texte, False, None
    if re.fullmatch(r"\d{4}", texte):
        return "0" + texte, True, None
    return None, False, "code_postal_invalide"


def normaliser_siret(valeur: str | None) -> tuple[str | None, bool, str | None]:
    texte = (valeur or "").strip()
    if re.fullmatch(r"\d{14}", texte):
        return texte, False, None

    m = _RE_SIRET_SCIENTIFIQUE.fullmatch(texte)
    if m:
        _, decimales, _exposant = m.groups()
        chiffres_significatifs = 1 + len(decimales)
        if chiffres_significatifs >= SIRET_CHIFFRES_SIGNIFICATIFS_MIN:
            try:
                reconstruit = int(Decimal(texte))
            except InvalidOperation:
                return None, False, "siret_illisible"
            chaine = str(reconstruit)
            # Un zéro de tête du SIRET d'origine est perdu par la conversion
            # en nombre Excel (ex. 07681040000000 -> 7.68104E+12) : on le
            # restitue par complétion à gauche, sans ambiguïté puisque les
            # chiffres significatifs conservés le permettent.
            if len(chaine) <= 14:
                return chaine.zfill(14), True, None
        return None, False, "siret_illisible"

    return None, False, "siret_illisible"


def normaliser_code_produit(valeur: str | None) -> tuple[str | None, bool, str | None]:
    texte = (valeur or "").strip()
    if texte == "":
        return None, False, None
    apres = texte.upper()
    return apres, apres != texte, None
