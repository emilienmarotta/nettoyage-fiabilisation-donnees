"""Contrat de colonnes du classeur `clients_commandes_brut.xlsx`.

Partagé entre `generator/excel_writer.py` (qui écrit ces colonnes/libellés)
et `pipeline/ingest.py` (qui les relit) — un seul endroit pour faire
évoluer le schéma métier. Voir specs/01-generator.md et
specs/02-ingestion.md.
"""

TABLES = {
    "Clients": {
        "raw_table": "raw_clients",
        "columns": [
            "client_id", "code_client", "nom_entreprise", "contact_nom",
            "email", "telephone", "adresse", "code_postal", "ville",
            "region", "siret", "segment", "date_creation",
        ],
        "labels": {
            "client_id": "ID Client", "code_client": "Code Client",
            "nom_entreprise": "Nom Entreprise", "contact_nom": "Contact",
            "email": "Email", "telephone": "Téléphone", "adresse": "Adresse",
            "code_postal": "Code Postal", "ville": "Ville", "region": "Région",
            "siret": "SIRET", "segment": "Segment", "date_creation": "Date Création",
        },
    },
    "Produits": {
        "raw_table": "raw_produits",
        "columns": [
            "produit_id", "code_produit", "nom_produit", "categorie",
            "prix_unitaire", "unite", "fournisseur",
        ],
        "labels": {
            "produit_id": "ID Produit", "code_produit": "Code Produit",
            "nom_produit": "Désignation", "categorie": "Catégorie",
            "prix_unitaire": "Prix Unitaire", "unite": "Unité",
            "fournisseur": "Fournisseur",
        },
    },
    "Commandes": {
        "raw_table": "raw_commandes",
        "columns": [
            "commande_id", "client_id", "produit_id", "quantite",
            "prix_unitaire_commande", "date_commande", "date_livraison",
            "statut",
        ],
        "labels": {
            "commande_id": "ID Commande", "client_id": "ID Client",
            "produit_id": "ID Produit", "quantite": "Quantité",
            "prix_unitaire_commande": "Prix Unitaire", "date_commande": "Date Commande",
            "date_livraison": "Date Livraison", "statut": "Statut",
        },
    },
}

COLONNE_INUTILE_LABEL = "Commentaire interne"
