-- Renommage/typage final + dédoublonnage exact final (filet de sécurité en
-- plus de celui déjà fait en Python, voir specs/03-cleaning.md et
-- specs/04-dbt.md). Aucune logique métier ici.

with source as (
    select * from {{ source('clean_staging', 'clients') }}
),

dedupliquee as (
    select
        *,
        row_number() over (
            partition by client_id order by source_fichier, ligne_origine
        ) as rn
    from source
)

select
    client_id,
    code_client,
    nom_entreprise,
    contact_nom,
    email,
    telephone,
    adresse,
    code_postal,
    ville,
    region,
    siret,
    segment,
    date_creation::date as date_creation,
    source_fichier,
    ligne_origine
from dedupliquee
where rn = 1
