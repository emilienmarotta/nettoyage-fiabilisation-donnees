-- Garde-fou anti-régression sur le volume de quarantaine (voir
-- "Seuils de qualité bloquants" dans specs/00-vision.md) : pas un objectif
-- de qualité absolu, le catalogue de défauts de M1 injecte volontairement
-- beaucoup de défauts non corrigeables. Objectif : attraper une vraie
-- régression de nettoyage (ex. le bug de parsing de date corrigé en M3, qui
-- avait fait exploser la quarantaine de commandes à ~99 %), pas faire
-- échouer le pipeline sur le volume de défauts normal de ce jeu de données
-- (clients/produits ~20-25 %, commandes ~35 % avec la cascade référentielle).
--
-- Une ligne retournée par table_cible dont le taux dépasse son seuil fait
-- échouer ce test (dbt test singulier : toute ligne renvoyée = échec).

with quarantine_par_table as (
    select table_cible, count(*) as n_quarantaine
    from {{ source('clean_staging', 'quarantine') }}
    group by table_cible
),

propres as (
    select 'clients' as table_cible, count(*) as n_propres from {{ ref('stg_clients') }}
    union all
    select 'produits', count(*) from {{ ref('stg_produits') }}
    union all
    select 'commandes', count(*) from {{ ref('stg_commandes') }}
),

taux as (
    select
        p.table_cible,
        coalesce(q.n_quarantaine, 0) as n_quarantaine,
        p.n_propres,
        coalesce(q.n_quarantaine, 0)::numeric
            / nullif(p.n_propres + coalesce(q.n_quarantaine, 0), 0) as taux_quarantaine
    from propres p
    left join quarantine_par_table q on q.table_cible = p.table_cible
)

select *
from taux
where (table_cible in ('clients', 'produits') and taux_quarantaine > 0.35)
   or (table_cible = 'commandes' and taux_quarantaine > 0.50)
