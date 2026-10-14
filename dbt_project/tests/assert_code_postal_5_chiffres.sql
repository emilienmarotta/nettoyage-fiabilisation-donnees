-- Aucun code postal != 5 chiffres dans clean_clients (voir specs/04-dbt.md).
-- Doit toujours passer : Python recomplète les codes à 4 chiffres et
-- quarantine le reste (motif code_postal_invalide).

select client_id, code_postal
from {{ ref('clean_clients') }}
where code_postal is not null
  and code_postal !~ '^\d{5}$'
