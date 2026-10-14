-- Pas de recalcul de règles déjà appliquées en Python : si une colonne
-- nécessitait une règle de nettoyage, ce serait une règle Python manquante,
-- pas une requête dbt ad hoc (voir specs/04-dbt.md).

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
    date_creation
from {{ ref('stg_clients') }}
