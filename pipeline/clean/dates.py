"""Parsing des dates multi-format (voir specs/03-cleaning.md et la charte
de specs/00-vision.md). Fonctions pures : valeur brute en entrée, date ISO
(ou None) + indicateur de correction + motif de rejet en sortie.

Convention française fixe pour les dates ambiguës `JJ/MM/AAAA` : jamais de
détection cas par cas (principe 3 de 00-vision.md).
"""

import re
from datetime import date, datetime, timedelta

MOIS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

EXCEL_EPOCH = date(1899, 12, 30)
DATE_MIN_RAISONNABLE = date(2015, 1, 1)

_RE_JJMMAAAA = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
_RE_TEXTE_FR = re.compile(r"(\d{1,2}) (\w+) (\d{4})", re.UNICODE)


def _sans_accent(texte: str) -> str:
    import unicodedata
    normalise = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in normalise if not unicodedata.combining(c))


def parser_date(valeur: str | None) -> tuple[str | None, bool, str | None]:
    """Retourne (date_iso, corrige, motif_si_rejet)."""
    texte = (valeur or "").strip()
    if texte == "":
        return None, False, None

    try:
        d = date.fromisoformat(texte)
        return d.isoformat(), False, None
    except ValueError:
        pass

    # Cellule Excel de type date lue par openpyxl comme datetime (ingestion
    # la restitue en texte via .isoformat(), donc avec un suffixe horaire
    # "T00:00:00") : pas une anomalie de donnée, juste un artefact de lecture.
    try:
        d = datetime.fromisoformat(texte).date()
        return d.isoformat(), False, None
    except ValueError:
        pass

    m = _RE_JJMMAAAA.fullmatch(texte)
    if m:
        jour, mois, annee = (int(g) for g in m.groups())
        try:
            d = date(annee, mois, jour)
        except ValueError:
            return None, False, "date_invalide"
        return d.isoformat(), True, None

    m = _RE_TEXTE_FR.fullmatch(texte)
    if m:
        jour_s, mois_nom, annee_s = m.groups()
        cible = _sans_accent(mois_nom).lower()
        mois_normalises = [_sans_accent(nom).lower() for nom in MOIS_FR]
        if cible in mois_normalises:
            mois = mois_normalises.index(cible) + 1
            try:
                d = date(int(annee_s), mois, int(jour_s))
            except ValueError:
                return None, False, "date_invalide"
            return d.isoformat(), True, None
        return None, False, "date_invalide"

    if texte.isdigit():
        try:
            d = EXCEL_EPOCH + timedelta(days=int(texte))
        except OverflowError:
            return None, False, "date_invalide"
        return d.isoformat(), True, None

    return None, False, "date_invalide"


def est_date_aberrante(date_iso: str, aujourdhui: date | None = None) -> bool:
    """Date de livraison/commande future aberrante (> aujourd'hui + 2 ans)
    ou antérieure à 2015 (charte de 00-vision.md)."""
    aujourdhui = aujourdhui or date.today()
    d = date.fromisoformat(date_iso)
    date_max_raisonnable = aujourdhui.replace(year=aujourdhui.year + 2)
    return d < DATE_MIN_RAISONNABLE or d > date_max_raisonnable
