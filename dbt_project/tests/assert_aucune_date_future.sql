-- Aucune date (commande/livraison) dans le futur par rapport à
-- current_date dans clean_commandes (voir specs/04-dbt.md). Note : plus
-- strict que le motif date_aberrante de Python (qui tolère jusqu'à
-- aujourd'hui + 2 ans) ; doit néanmoins toujours passer sur ce jeu de
-- données, les dates générées ne dépassant jamais le 2026-09-30.

select commande_id, date_commande, date_livraison
from {{ ref('clean_commandes') }}
where date_commande > current_date
   or date_livraison > current_date
