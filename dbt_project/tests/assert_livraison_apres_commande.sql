-- Aucune date_livraison < date_commande dans clean_commandes (voir
-- specs/04-dbt.md). Doit toujours passer : Python quarantine ce cas (motif
-- livraison_avant_commande).

select commande_id, date_commande, date_livraison
from {{ ref('clean_commandes') }}
where date_livraison is not null
  and date_livraison < date_commande
