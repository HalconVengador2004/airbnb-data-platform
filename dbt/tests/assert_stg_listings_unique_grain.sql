-- Fails if the staging grain (_city, scrape_id, id) is not unique.

select
    _city,
    scrape_id,
    id,
    count(*) as row_count
from {{ ref('stg_listings') }}
group by _city, scrape_id, id
having count(*) > 1
