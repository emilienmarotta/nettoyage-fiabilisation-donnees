-- Renommage/typage final + dédoublonnage exact final (filet de sécurité).
-- Aucune logique métier ici.

with source as (
    select * from {{ source('clean_staging', 'commandes') }}
),

dedupliquee as (
    select
        *,
        row_number() over (
            partition by commande_id order by source_fichier, ligne_origine
        ) as rn
    from source
)

select
    commande_id,
    client_id,
    produit_id,
    quantite::numeric as quantite,
    prix_unitaire_commande::numeric as prix_unitaire_commande,
    date_commande::date as date_commande,
    date_livraison::date as date_livraison,
    statut,
    source_fichier,
    ligne_origine
from dedupliquee
where rn = 1
