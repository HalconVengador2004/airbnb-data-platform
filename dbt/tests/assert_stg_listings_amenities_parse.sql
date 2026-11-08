-- Fails when amenities are not parsed as a JSON array, when the count is
-- wrong, or when the parse status disagrees with the preserved raw text.

select *
from {{ ref('stg_listings') }}
where amenities_parse_status = 'invalid'
   or (
        amenities_parse_status = 'empty'
        and (amenities_count <> 0 or amenities_json is distinct from '[]'::jsonb)
   )
   or (
        amenities_parse_status = 'ok'
        and (amenities_json is null or jsonb_typeof(amenities_json) <> 'array')
   )
   or (
        amenities_parse_status = 'ok'
        and amenities_count <> jsonb_array_length(amenities_json)
   )
   or (
        amenities_parse_status = 'ok'
        and (amenities_raw is null or btrim(amenities_raw) = '')
   )
   or (
        amenities_raw is not null
        and btrim(amenities_raw) <> ''
        and case
            when pg_input_is_valid(amenities_raw, 'jsonb')
                then jsonb_typeof(amenities_raw::jsonb) = 'array'
            else false
        end
        and amenities_parse_status <> 'ok'
   )
   or (
        amenities_raw is not null
        and btrim(amenities_raw) <> ''
        and not pg_input_is_valid(amenities_raw, 'jsonb')
        and amenities_parse_status <> 'invalid'
   )
   or (
        amenities_raw is not null
        and btrim(amenities_raw) <> ''
        and case
            when pg_input_is_valid(amenities_raw, 'jsonb')
                then jsonb_typeof(amenities_raw::jsonb) <> 'array'
            else false
        end
        and amenities_parse_status <> 'invalid'
   )
