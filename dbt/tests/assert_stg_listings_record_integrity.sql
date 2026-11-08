-- Fails if staging and raw do not contain exactly the same records.
-- A FULL OUTER JOIN reports both missing rows and additional rows.

with raw_rows as (
    select _city, scrape_id, id
    from {{ source('raw', 'listings') }}
),

stg_rows as (
    select _city, scrape_id, id
    from {{ ref('stg_listings') }}
)

select
    coalesce(r._city, s._city) as _city,
    coalesce(r.scrape_id, s.scrape_id) as scrape_id,
    coalesce(r.id, s.id) as id,
    case
        when s.id is null then 'missing_in_staging'
        when r.id is null then 'additional_in_staging'
    end as issue
from raw_rows r
full outer join stg_rows s
    on r._city = s._city
   and r.scrape_id = s.scrape_id
   and r.id = s.id
where r.id is null or s.id is null
