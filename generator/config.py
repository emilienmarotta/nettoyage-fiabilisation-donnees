"""Constantes du générateur (voir specs/01-generator.md).

Univers métier partagé avec les projets portfolio `rapport-commercial-auto`
et `tableau-de-bord-pilotage` : mêmes régions, mêmes catégories de produits,
mêmes segments de client.
"""

from datetime import date

SEED = 42

N_CLIENTS = 300
N_PRODUITS = 150
N_COMMANDES = 3000

START_DATE_CREATION_CLIENT = date(2015, 1, 1)
START_DATE_COMMANDE = date(2025, 1, 1)
END_DATE_COMMANDE = date(2026, 9, 30)

REGIONS = [
    "Île-de-France",
    "Auvergne-Rhône-Alpes",
    "Nouvelle-Aquitaine",
    "Occitanie",
    "Hauts-de-France",
    "Grand Est",
]

SEGMENTS = ["grand_compte", "pme", "detaillant"]
SEGMENT_WEIGHTS = [15, 55, 30]

CATEGORIES = [
    "emballage",
    "hygiene",
    "boissons",
    "alimentaire",
    "papier",
    "protection",
    "entretien",
    "textile",
]

# Quelques noms de produits réalistes par catégorie, dans le même style que
# le catalogue de rapport-commercial-auto (distributeur de gros).
PRODUCT_NAMES_BY_CATEGORY = {
    "emballage": [
        "Carton d'emballage 40x30", "Rouleau de film étirable",
        "Lot de cartons d'emballage 60x40", "Rouleau de ruban adhésif emballage",
        "Lot de housses plastique palette", "Lot de palettes bois EUR",
    ],
    "hygiene": [
        "Carton de gants nitrile", "Lot de gants de protection latex",
        "Carton de masques jetables", "Lot de charlottes jetables",
        "Carton de gel hydroalcoolique", "Lot de serviettes en papier",
    ],
    "boissons": [
        "Palette de bouteilles d'eau 50cl", "Palette de packs d'eau gazeuse",
        "Palette de briques de jus de fruit", "Carton de bouteilles de soda 1L",
        "Palette de packs de bière 33cl", "Carton de briques de lait UHT",
    ],
    "alimentaire": [
        "Carton de boîtes de conserve légumes", "Palette de sacs de farine 25kg",
        "Carton de boîtes de café moulu", "Carton de bouteilles d'huile 1L",
        "Lot de caisses plastique gerbables", "Carton de paquets de pâtes 500g",
    ],
    "papier": [
        "Rouleau de papier essuyage industriel", "Lot de ramettes papier A4",
        "Carton de rouleaux de papier toilette", "Lot de sacs kraft",
        "Carton de boîtes à pizza", "Lot de nappes en papier",
    ],
    "protection": [
        "Lot de gants de protection cuir", "Carton de lunettes de protection",
        "Lot de casques de chantier", "Carton de chasubles haute visibilité",
        "Lot de bouchons d'oreille", "Carton de combinaisons jetables",
    ],
    "entretien": [
        "Carton de bidons de détergent 5L", "Lot de serpillières microfibre",
        "Carton de sacs poubelle 100L", "Lot de balais-brosses",
        "Carton de bidons d'eau de javel", "Lot de chiffons microfibre",
    ],
    "textile": [
        "Lot de tee-shirts coton 180g", "Carton de torchons coton",
        "Lot de gilets de travail", "Carton de blouses de travail",
        "Lot de serviettes éponge", "Carton de housses de protection textile",
    ],
}

FOURNISSEURS = [
    "Dupont Industrie", "Groupe Lefèvre", "Michel Distribution",
    "Bernard & Fils", "Petit Logistique", "Garnier Négoce",
    "Lambert Approvisionnement", "Roussel Gros",
]

UNITES = ["pièce", "lot", "carton", "palette", "boîte"]

STATUTS_COMMANDE = ["Livrée", "En cours", "Annulée"]
STATUT_WEIGHTS = [75, 15, 10]

# Taux global d'injection de défauts (fraction des lignes "touchées" par au
# moins un défaut). Ajustable via variable d'environnement / CLI.
TAUX_DEFAUTS_DEFAUT = 0.15
