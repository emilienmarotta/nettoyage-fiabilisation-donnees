select
    produit_id,
    code_produit,
    nom_produit,
    categorie,
    prix_unitaire,
    unite,
    fournisseur
from {{ ref('stg_produits') }}
