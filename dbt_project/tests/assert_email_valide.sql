-- Aucune ligne clean_clients avec un email ne respectant pas un format
-- minimal (voir specs/04-dbt.md). Ce test doit toujours passer : Python a
-- déjà quarantiné les emails invalides (motif email_invalide). Un échec ici
-- signale un bug du nettoyage, pas une tolérance de donnée sale.

select client_id, email
from {{ ref('clean_clients') }}
where email is not null
  and email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'
