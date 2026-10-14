"""Validation email et normalisation téléphone (voir specs/03-cleaning.md
et la charte de specs/00-vision.md)."""

import re

_RE_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_RE_TELEPHONE_FR = re.compile(r"0\d{9}")


def valider_email(valeur: str | None) -> tuple[str | None, bool, str | None]:
    """Jamais corrigé : un email invalide part toujours en quarantaine."""
    texte = (valeur or "").strip()
    if _RE_EMAIL.fullmatch(texte):
        return texte, False, None
    return None, False, "email_invalide"


def normaliser_telephone(valeur: str | None) -> tuple[str | None, bool, str | None]:
    """Normalise au format `0X XX XX XX XX`, caractères invisibles et
    séparateurs supprimés, préfixe international `+33`/`0033` reconverti."""
    texte = (valeur or "").strip()
    sans_separateurs = (
        texte.replace(" ", "").replace("\xa0", "").replace(".", "")
    )

    if sans_separateurs.startswith("+33"):
        chiffres = "0" + sans_separateurs[3:]
    elif sans_separateurs.startswith("0033"):
        chiffres = "0" + sans_separateurs[4:]
    else:
        chiffres = sans_separateurs

    if not _RE_TELEPHONE_FR.fullmatch(chiffres):
        return None, False, "telephone_invalide"

    groupes = [chiffres[0:2]] + [chiffres[i:i + 2] for i in range(2, 10, 2)]
    apres = " ".join(groupes)
    return apres, apres != texte, None
