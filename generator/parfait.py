"""Génère le jeu de données parfait (sans défaut), voir specs/01-generator.md.

Cohérence référentielle garantie dès la génération : tous les FK existent,
toutes les dates sont cohérentes, tous les champs obligatoires sont remplis.
"""

import random
from datetime import date, timedelta

from faker import Faker

from generator import config


def _random_date(rng: random.Random, start: date, end: date) -> date:
    delta_days = (end - start).days
    return start + timedelta(days=rng.randint(0, delta_days))


def _siret(fake: Faker) -> str:
    return fake.siret().replace(" ", "")


def _telephone(rng: random.Random) -> str:
    premier = rng.choice(["01", "02", "03", "04", "05", "06", "07", "09"])
    reste = [f"{rng.randint(0, 99):02d}" for _ in range(4)]
    return " ".join([premier] + reste)


def build_clients(fake: Faker, rng: random.Random) -> list[dict]:
    clients = []
    for i in range(1, config.N_CLIENTS + 1):
        region = rng.choice(config.REGIONS)
        segment = rng.choices(config.SEGMENTS, weights=config.SEGMENT_WEIGHTS)[0]
        nom_entreprise = fake.company()
        clients.append(
            {
                "client_id": i,
                "code_client": f"CLI-{i:04d}",
                "nom_entreprise": nom_entreprise,
                "contact_nom": fake.name(),
                "email": fake.company_email(),
                "telephone": _telephone(rng),
                "adresse": fake.street_address(),
                "code_postal": fake.postcode(),
                "ville": fake.city(),
                "region": region,
                "siret": _siret(fake),
                "segment": segment,
                "date_creation": _random_date(
                    rng, config.START_DATE_CREATION_CLIENT, config.START_DATE_COMMANDE
                ),
            }
        )
    return clients


def build_produits(rng: random.Random) -> list[dict]:
    produits = []
    for i in range(1, config.N_PRODUITS + 1):
        categorie = rng.choice(config.CATEGORIES)
        nom_produit = rng.choice(config.PRODUCT_NAMES_BY_CATEGORY[categorie])
        prix_unitaire = round(rng.uniform(2.0, 450.0), 2)
        produits.append(
            {
                "produit_id": i,
                "code_produit": f"ART-{i:04d}",
                "nom_produit": nom_produit,
                "categorie": categorie,
                "prix_unitaire": prix_unitaire,
                "unite": rng.choice(config.UNITES),
                "fournisseur": rng.choice(config.FOURNISSEURS),
            }
        )
    return produits


def build_commandes(rng: random.Random, clients: list[dict], produits: list[dict]) -> list[dict]:
    commandes = []
    client_ids = [c["client_id"] for c in clients]
    produits_by_id = {p["produit_id"]: p for p in produits}
    produit_ids = list(produits_by_id.keys())

    for i in range(1, config.N_COMMANDES + 1):
        client_id = rng.choice(client_ids)
        produit_id = rng.choice(produit_ids)
        prix_catalogue = produits_by_id[produit_id]["prix_unitaire"]
        remise = rng.choice([0, 0, 0, 0.05, 0.1, 0.15])
        prix_unitaire_commande = round(prix_catalogue * (1 - remise), 2)
        date_commande = _random_date(rng, config.START_DATE_COMMANDE, config.END_DATE_COMMANDE)
        delai_livraison = rng.randint(1, 15)
        date_livraison = date_commande + timedelta(days=delai_livraison)
        statut = rng.choices(config.STATUTS_COMMANDE, weights=config.STATUT_WEIGHTS)[0]

        commandes.append(
            {
                "commande_id": i,
                "client_id": client_id,
                "produit_id": produit_id,
                "quantite": rng.randint(1, 200),
                "prix_unitaire_commande": prix_unitaire_commande,
                "date_commande": date_commande,
                "date_livraison": date_livraison,
                "statut": statut,
            }
        )
    return commandes


def build_dataset(seed: int = config.SEED) -> dict[str, list[dict]]:
    fake = Faker("fr_FR")
    fake.seed_instance(seed)
    rng = random.Random(seed)

    clients = build_clients(fake, rng)
    produits = build_produits(rng)
    commandes = build_commandes(rng, clients, produits)

    return {"clients": clients, "produits": produits, "commandes": commandes}
