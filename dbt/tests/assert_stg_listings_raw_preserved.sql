-- Fails if any selected raw source value was altered by staging.

select
    r._city,
    r.scrape_id,
    r.id
from {{ source('raw', 'listings') }} r
inner join {{ ref('stg_listings') }} s
    on r._city = s._city
   and r.scrape_id = s.scrape_id
   and r.id = s.id
where r.price is distinct from s.price_raw
   or r.bathrooms_text is distinct from s.bathrooms_text
   or r.amenities is distinct from s.amenities_raw
   or r.license is distinct from s.license_raw
