-- Aucune quantite <= 0 dans clean_commandes (voir specs/04-dbt.md). Doit
-- toujours passer : Python quarantine les quantités invalides (motif
-- quantite_ou_prix_invalide).

select commande_id, quantite
from {{ ref('clean_commandes') }}
where quantite <= 0
