{{ config(materialized='view') }}

-- Staging model for Inside Airbnb listing snapshots.
-- One row per (_city, scrape_id, id). Source values are preserved for fields
-- that require interpretation: price, bathrooms_text, amenities, license.
-- Derived columns never replace the raw text.

select
    -- identifiers and ingestion metadata
    id,
    listing_url,
    scrape_id,

    -- dates (strict ISO plus PostgreSQL calendar validation)
    case
        when last_scraped is null or btrim(last_scraped) = '' then null
        when btrim(last_scraped) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
             and pg_input_is_valid(btrim(last_scraped), 'date')
            then btrim(last_scraped)::date
    end as last_scraped,

    source,
    name,
    description,
    neighborhood_overview,
    picture_url,

    -- host identifiers and profile
    host_id,
    host_url,
    host_profile_id,
    host_profile_url,
    host_name,

    case
        when host_since is null or btrim(host_since) = '' then null
        when btrim(host_since) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
             and pg_input_is_valid(btrim(host_since), 'date')
            then btrim(host_since)::date
    end as host_since,

    case
        when btrim(hosts_time_as_user_years) ~ '^-?[0-9]+$'
            then btrim(hosts_time_as_user_years)::integer
    end as hosts_time_as_user_years,
    case
        when btrim(hosts_time_as_user_months) ~ '^-?[0-9]+$'
            then btrim(hosts_time_as_user_months)::integer
    end as hosts_time_as_user_months,
    case
        when btrim(hosts_time_as_host_years) ~ '^-?[0-9]+$'
            then btrim(hosts_time_as_host_years)::integer
    end as hosts_time_as_host_years,
    case
        when btrim(hosts_time_as_host_months) ~ '^-?[0-9]+$'
            then btrim(hosts_time_as_host_months)::integer
    end as hosts_time_as_host_months,

    host_location,
    host_about,
    host_response_time,

    case
        when btrim(host_response_rate) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(host_response_rate)::numeric(5, 2)
    end as host_response_rate,
    case
        when btrim(host_acceptance_rate) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(host_acceptance_rate)::numeric(5, 2)
    end as host_acceptance_rate,

    case btrim(host_is_superhost)
        when 't' then true
        when 'f' then false
    end as host_is_superhost,

    host_thumbnail_url,
    host_picture_url,
    host_neighbourhood,

    case
        when btrim(host_listings_count) ~ '^-?[0-9]+$'
            then btrim(host_listings_count)::integer
    end as host_listings_count,
    case
        when btrim(host_total_listings_count) ~ '^-?[0-9]+$'
            then btrim(host_total_listings_count)::integer
    end as host_total_listings_count,

    host_verifications,

    case btrim(host_has_profile_pic)
        when 't' then true
        when 'f' then false
    end as host_has_profile_pic,
    case btrim(host_identity_verified)
        when 't' then true
        when 'f' then false
    end as host_identity_verified,

    -- location
    neighbourhood,
    neighbourhood_cleansed,
    neighbourhood_group_cleansed,

    case
        when btrim(latitude) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(latitude)::numeric(9, 6)
    end as latitude,
    case
        when btrim(longitude) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(longitude)::numeric(9, 6)
    end as longitude,

    -- property
    property_type,
    room_type,

    case
        when btrim(accommodates) ~ '^-?[0-9]+$'
            then btrim(accommodates)::integer
    end as accommodates,

    -- bathrooms: raw text is preserved, derived values are added alongside.
    -- `bathrooms` (numeric source column) is all null in the current snapshots.
    case
        when btrim(bathrooms) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(bathrooms)::numeric(4, 1)
    end as bathrooms,
    bathrooms_text,
    case
        when bathrooms_text is null or btrim(bathrooms_text) = '' then null
        when lower(btrim(bathrooms_text)) = 'no bathroom' then 0
        when lower(btrim(bathrooms_text)) in ('half-bath', 'shared half-bath', 'private half-bath') then 0.5
        when btrim(bathrooms_text) ~ '^[0-9]+(\.[0-9]+)? (shared |private )?baths?$'
            then split_part(btrim(bathrooms_text), ' ', 1)::numeric(4, 1)
    end as bathrooms_count,
    case
        when bathrooms_text is null or btrim(bathrooms_text) = '' then null
        when lower(btrim(bathrooms_text)) = 'no bathroom' then 'none'
        when lower(btrim(bathrooms_text)) like '%shared%' then 'shared'
        when lower(btrim(bathrooms_text)) like '%private%' then 'private'
        when lower(btrim(bathrooms_text)) = 'half-bath' then 'not_specified'
        when btrim(bathrooms_text) ~ '^[0-9]+(\.[0-9]+)? baths?$' then 'not_specified'
        else 'unknown'
    end as bathroom_type,
    case
        when bathrooms_text is null or btrim(bathrooms_text) = '' then null
        when lower(btrim(bathrooms_text)) in ('half-bath', 'shared half-bath', 'private half-bath') then true
        else false
    end as is_half_bath,
    case
        when bathrooms_text is null or btrim(bathrooms_text) = '' then 'null'
        when lower(btrim(bathrooms_text)) = 'no bathroom' then 'ok'
        when lower(btrim(bathrooms_text)) in ('half-bath', 'shared half-bath', 'private half-bath') then 'ok'
        when btrim(bathrooms_text) ~ '^[0-9]+(\.[0-9]+)? (shared |private )?baths?$' then 'ok'
        else 'invalid'
    end as bathrooms_parse_status,

    case
        when btrim(bedrooms) ~ '^-?[0-9]+$'
            then btrim(bedrooms)::integer
    end as bedrooms,
    case
        when btrim(beds) ~ '^-?[0-9]+$'
            then btrim(beds)::integer
    end as beds,

    -- amenities: raw JSON text is preserved; derived JSONB is only produced
    -- when the text is a valid JSON array.
    amenities as amenities_raw,
    case
        when amenities is null or btrim(amenities) = '' then '[]'::jsonb
        when pg_input_is_valid(amenities, 'jsonb') then
            case
                when jsonb_typeof(amenities::jsonb) = 'array' then amenities::jsonb
            end
    end as amenities_json,
    case
        when amenities is null or btrim(amenities) = '' then 0
        when pg_input_is_valid(amenities, 'jsonb') then
            case
                when jsonb_typeof(amenities::jsonb) = 'array'
                    then jsonb_array_length(amenities::jsonb)
            end
    end as amenities_count,
    case
        when amenities is null or btrim(amenities) = '' then 'empty'
        when pg_input_is_valid(amenities, 'jsonb') then
            case
                when jsonb_typeof(amenities::jsonb) = 'array' then 'ok'
                else 'invalid'
            end
        else 'invalid'
    end as amenities_parse_status,

    -- price: raw text is preserved; the parsed amount is EUR because the
    -- source price_quote_raw reports "currency": "EUR". No conversion is done.
    price as price_raw,
    case
        when price is null or btrim(price) = '' then null
        when btrim(price) ~ '^\$[0-9]{1,3}(,[0-9]{3})*(\.[0-9]{2})$'
            then replace(replace(btrim(price), '$', ''), ',', '')::numeric(12, 2)
    end as price_eur,
    case
        when price is not null and btrim(price) <> ''
             and btrim(price) ~ '^\$[0-9]{1,3}(,[0-9]{3})*(\.[0-9]{2})$'
            then 'EUR'
    end as price_currency,
    case
        when price is null or btrim(price) = '' then 'null'
        when btrim(price) ~ '^\$[0-9]{1,3}(,[0-9]{3})*(\.[0-9]{2})$' then 'ok'
        else 'invalid'
    end as price_parse_status,

    case
        when price_quote_checkin_date is null or btrim(price_quote_checkin_date) = '' then null
        when btrim(price_quote_checkin_date) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
             and pg_input_is_valid(btrim(price_quote_checkin_date), 'date')
            then btrim(price_quote_checkin_date)::date
    end as price_quote_checkin_date,
    case
        when price_quote_checkout_date is null or btrim(price_quote_checkout_date) = '' then null
        when btrim(price_quote_checkout_date) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
             and pg_input_is_valid(btrim(price_quote_checkout_date), 'date')
            then btrim(price_quote_checkout_date)::date
    end as price_quote_checkout_date,

    case
        when btrim(price_quote_total_price) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(price_quote_total_price)::numeric(12, 2)
    end as price_quote_total_price,
    case
        when btrim(price_quote_price_per_night) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(price_quote_price_per_night)::numeric(12, 4)
    end as price_quote_price_per_night,
    price_quote_raw,

    -- stay rules
    case
        when btrim(minimum_nights) ~ '^-?[0-9]+$'
            then btrim(minimum_nights)::integer
    end as minimum_nights,
    case
        when btrim(maximum_nights) ~ '^-?[0-9]+$'
            then btrim(maximum_nights)::integer
    end as maximum_nights,
    case
        when btrim(minimum_minimum_nights) ~ '^-?[0-9]+$'
            then btrim(minimum_minimum_nights)::integer
    end as minimum_minimum_nights,
    case
        when btrim(maximum_minimum_nights) ~ '^-?[0-9]+$'
            then btrim(maximum_minimum_nights)::integer
    end as maximum_minimum_nights,
    case
        when btrim(minimum_maximum_nights) ~ '^-?[0-9]+$'
            then btrim(minimum_maximum_nights)::integer
    end as minimum_maximum_nights,
    case
        when btrim(maximum_maximum_nights) ~ '^-?[0-9]+$'
            then btrim(maximum_maximum_nights)::integer
    end as maximum_maximum_nights,
    case
        when btrim(minimum_nights_avg_ntm) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(minimum_nights_avg_ntm)::numeric(8, 2)
    end as minimum_nights_avg_ntm,
    case
        when btrim(maximum_nights_avg_ntm) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(maximum_nights_avg_ntm)::numeric(8, 2)
    end as maximum_nights_avg_ntm,

    -- calendar_updated stays TEXT: all current values are null and the source
    -- does not provide reliable date semantics.
    calendar_updated,

    case btrim(has_availability)
        when 't' then true
        when 'f' then false
    end as has_availability,

    case
        when btrim(availability_30) ~ '^-?[0-9]+$'
            then btrim(availability_30)::integer
    end as availability_30,
    case
        when btrim(availability_60) ~ '^-?[0-9]+$'
            then btrim(availability_60)::integer
    end as availability_60,
    case
        when btrim(availability_90) ~ '^-?[0-9]+$'
            then btrim(availability_90)::integer
    end as availability_90,
    case
        when btrim(availability_365) ~ '^-?[0-9]+$'
            then btrim(availability_365)::integer
    end as availability_365,

    case
        when calendar_last_scraped is null or btrim(calendar_last_scraped) = '' then null
        when btrim(calendar_last_scraped) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
             and pg_input_is_valid(btrim(calendar_last_scraped), 'date')
            then btrim(calendar_last_scraped)::date
    end as calendar_last_scraped,

    case
        when btrim(number_of_reviews) ~ '^-?[0-9]+$'
            then btrim(number_of_reviews)::integer
    end as number_of_reviews,
    case
        when btrim(number_of_reviews_ltm) ~ '^-?[0-9]+$'
            then btrim(number_of_reviews_ltm)::integer
    end as number_of_reviews_ltm,
    case
        when btrim(number_of_reviews_l30d) ~ '^-?[0-9]+$'
            then btrim(number_of_reviews_l30d)::integer
    end as number_of_reviews_l30d,
    case
        when btrim(availability_eoy) ~ '^-?[0-9]+$'
            then btrim(availability_eoy)::integer
    end as availability_eoy,
    case
        when btrim(number_of_reviews_ly) ~ '^-?[0-9]+$'
            then btrim(number_of_reviews_ly)::integer
    end as number_of_reviews_ly,
    case
        when btrim(estimated_occupancy_l365d) ~ '^-?[0-9]+$'
            then btrim(estimated_occupancy_l365d)::integer
    end as estimated_occupancy_l365d,
    case
        when btrim(estimated_revenue_l365d) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(estimated_revenue_l365d)::numeric(12, 2)
    end as estimated_revenue_l365d,

    case
        when first_review is null or btrim(first_review) = '' then null
        when btrim(first_review) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
             and pg_input_is_valid(btrim(first_review), 'date')
            then btrim(first_review)::date
    end as first_review,
    case
        when last_review is null or btrim(last_review) = '' then null
        when btrim(last_review) ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
             and pg_input_is_valid(btrim(last_review), 'date')
            then btrim(last_review)::date
    end as last_review,

    case
        when btrim(review_scores_rating) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(review_scores_rating)::numeric(3, 2)
    end as review_scores_rating,
    case
        when btrim(review_scores_accuracy) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(review_scores_accuracy)::numeric(3, 2)
    end as review_scores_accuracy,
    case
        when btrim(review_scores_cleanliness) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(review_scores_cleanliness)::numeric(3, 2)
    end as review_scores_cleanliness,
    case
        when btrim(review_scores_checkin) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(review_scores_checkin)::numeric(3, 2)
    end as review_scores_checkin,
    case
        when btrim(review_scores_communication) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(review_scores_communication)::numeric(3, 2)
    end as review_scores_communication,
    case
        when btrim(review_scores_location) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(review_scores_location)::numeric(3, 2)
    end as review_scores_location,
    case
        when btrim(review_scores_value) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(review_scores_value)::numeric(3, 2)
    end as review_scores_value,

    -- license: descriptive text flags only; no legal-compliance claim.
    license as license_raw,
    case
        when license is null or btrim(license) = '' then false
        else true
    end as license_has_text,
    (
        license is not null
        and btrim(license) <> ''
        and position('exempt' in lower(license)) > 0
    ) as license_mentions_exempt,
    (
        license is not null
        and btrim(license) <> ''
        and position('regional registration number' in lower(license)) > 0
    ) as license_mentions_regional,
    (
        license is not null
        and btrim(license) <> ''
        and position('national registration number' in lower(license)) > 0
    ) as license_mentions_national,
    case
        when license is null or btrim(license) = '' then 'not_provided'
        when position('exempt' in lower(license)) > 0
             and position('registration number' in lower(license)) > 0 then 'mixed'
        when position('exempt' in lower(license)) > 0 then 'exempt_marker'
        when position('registration number' in lower(license)) > 0 then 'registration_marker'
        else 'other'
    end as license_flag,

    case btrim(instant_bookable)
        when 't' then true
        when 'f' then false
    end as instant_bookable,

    case
        when btrim(calculated_host_listings_count) ~ '^-?[0-9]+$'
            then btrim(calculated_host_listings_count)::integer
    end as calculated_host_listings_count,
    case
        when btrim(calculated_host_listings_count_entire_homes) ~ '^-?[0-9]+$'
            then btrim(calculated_host_listings_count_entire_homes)::integer
    end as calculated_host_listings_count_entire_homes,
    case
        when btrim(calculated_host_listings_count_private_rooms) ~ '^-?[0-9]+$'
            then btrim(calculated_host_listings_count_private_rooms)::integer
    end as calculated_host_listings_count_private_rooms,
    case
        when btrim(calculated_host_listings_count_shared_rooms) ~ '^-?[0-9]+$'
            then btrim(calculated_host_listings_count_shared_rooms)::integer
    end as calculated_host_listings_count_shared_rooms,

    case
        when btrim(reviews_per_month) ~ '^-?[0-9]+(\.[0-9]+)?$'
            then btrim(reviews_per_month)::numeric(6, 2)
    end as reviews_per_month,

    -- ingestion metadata
    _city,
    _source_file,
    _file_hash,
    _loaded_at

from {{ source('raw', 'listings') }}
