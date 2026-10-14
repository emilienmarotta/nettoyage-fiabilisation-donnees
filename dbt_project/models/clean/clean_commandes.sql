-- Enrichissement simple (jointure + flag dérivé), pas de recalcul de règles
-- déjà appliquées en Python.

with commandes as (
    select * from {{ ref('stg_commandes') }}
),

clients as (
    select client_id from {{ ref('stg_clients') }}
),

produits as (
    select produit_id from {{ ref('stg_produits') }}
)

select
    c.commande_id,
    c.client_id,
    c.produit_id,
    c.quantite,
    c.prix_unitaire_commande,
    c.quantite * c.prix_unitaire_commande as montant_total,
    c.date_commande,
    c.date_livraison,
    c.statut,
    (cl.client_id is not null and p.produit_id is not null) as commande_valide
from commandes c
left join clients cl on cl.client_id = c.client_id
left join produits p on p.produit_id = c.produit_id
