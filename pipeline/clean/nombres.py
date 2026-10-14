"""Parsing des nombres multi-format (voir specs/03-cleaning.md et la charte
de specs/00-vision.md). Fonction pure : valeur brute en entrée, `Decimal`
(ou None) + indicateur de correction + motif de rejet en sortie.

Un `%` dans une colonne de quantité/prix n'est jamais un format fiable (ce
n'est pas un pourcentage) : toujours quarantaine, jamais une correction
« intelligente » qui diviserait silencieusement une valeur par 100.
"""

from decimal import Decimal, InvalidOperation

ESPACES = (" ", "\xa0", " ")


def parser_nombre(valeur: str | None) -> tuple[Decimal | None, bool, str | None]:
    """Retourne (valeur_decimale, corrige, motif_si_rejet)."""
    texte = (valeur or "").strip()
    if texte == "":
        return None, False, None

    if "%" in texte:
        return None, False, "valeur_numerique_invalide"

    nettoye = texte
    if "€" in nettoye:
        nettoye = nettoye.replace("€", "").strip()

    for espace in ESPACES:
        nettoye = nettoye.replace(espace, "")

    a_virgule = "," in nettoye
    a_point = "." in nettoye

    if a_virgule and a_point:
        # "1.234,50" : point = séparateur de milliers, virgule = décimale.
        nettoye = nettoye.replace(".", "").replace(",", ".")
    elif a_virgule:
        # "1 234,50" (espaces déjà retirées) : virgule = décimale.
        nettoye = nettoye.replace(",", ".")
    # sinon : "1234.50" (point déjà décimal) ou entier simple, rien à faire.

    try:
        resultat = Decimal(nettoye)
    except InvalidOperation:
        return None, False, "valeur_numerique_invalide"

    corrige = texte != str(resultat) and texte != format(resultat, "f")
    return resultat, corrige, None
