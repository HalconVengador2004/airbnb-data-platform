-- Fails when the price parse status, amount, or currency is inconsistent
-- with the preserved raw price text.

select *
from {{ ref('stg_listings') }}
where price_parse_status = 'invalid'
   or (price_parse_status = 'ok' and (price_eur is null or price_currency is distinct from 'EUR'))
   or (price_parse_status = 'null' and (price_eur is not null or price_currency is not null))
   or (price_parse_status = 'null' and price_raw is not null and btrim(price_raw) <> '')
   or (price_parse_status = 'ok' and (price_raw is null or btrim(price_raw) = ''))
   or price_eur < 0
   or (
        price_parse_status = 'ok'
        and price_eur <> replace(replace(btrim(price_raw), '$', ''), ',', '')::numeric
   )
