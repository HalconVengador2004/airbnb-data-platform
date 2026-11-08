-- Fails when bathroom parsing loses shared/private information, assigns a
-- wrong count, or mishandles half-baths and "No bathroom".

select *
from {{ ref('stg_listings') }}
where bathrooms_parse_status = 'invalid'
   or (bathrooms_parse_status = 'ok' and bathrooms_count is null)
   or (
        bathrooms_parse_status = 'null'
        and (bathrooms_count is not null or bathroom_type is not null or is_half_bath is not null)
   )
   or (bathroom_type = 'shared' and lower(bathrooms_text) not like '%shared%')
   or (bathroom_type = 'private' and lower(bathrooms_text) not like '%private%')
   or (
        bathroom_type = 'not_specified'
        and (lower(bathrooms_text) like '%shared%' or lower(bathrooms_text) like '%private%')
   )
   or (is_half_bath and bathrooms_count <> 0.5)
   or (
        is_half_bath
        and lower(btrim(bathrooms_text)) not in ('half-bath', 'shared half-bath', 'private half-bath')
   )
   or (
        not is_half_bath
        and lower(btrim(bathrooms_text)) in ('half-bath', 'shared half-bath', 'private half-bath')
   )
   or (
        lower(btrim(bathrooms_text)) = 'no bathroom'
        and (bathroom_type <> 'none' or bathrooms_count <> 0)
   )
   or (bathroom_type = 'none' and lower(btrim(bathrooms_text)) <> 'no bathroom')
   or (bathroom_type = 'unknown' and bathrooms_parse_status <> 'invalid')
   or (
        bathrooms_parse_status = 'ok'
        and not is_half_bath
        and lower(btrim(bathrooms_text)) <> 'no bathroom'
        and bathrooms_count <> split_part(btrim(bathrooms_text), ' ', 1)::numeric
   )
