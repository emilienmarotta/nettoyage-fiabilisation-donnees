-- Renommage/typage final + dédoublonnage exact final (filet de sécurité).
-- Aucune logique métier ici.

with source as (
    select * from {{ source('clean_staging', 'produits') }}
),

dedupliquee as (
    select
        *,
        row_number() over (
            partition by produit_id order by source_fichier, ligne_origine
        ) as rn
    from source
)

select
    produit_id,
    code_produit,
    nom_produit,
    categorie,
    prix_unitaire::numeric as prix_unitaire,
    unite,
    fournisseur,
    source_fichier,
    ligne_origine
from dedupliquee
where rn = 1
