-- Fails when any non-null source date, boolean, integer, or numeric value does
-- not match the format expected by the staging model.

{% set checks = [] %}

{% set date_columns = [
    'last_scraped',
    'calendar_last_scraped',
    'first_review',
    'last_review',
    'host_since',
    'price_quote_checkin_date',
    'price_quote_checkout_date',
] %}
{% for column in date_columns %}
{% do checks.append((column, "btrim(" ~ column ~ ") !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' or not pg_input_is_valid(btrim(" ~ column ~ "), 'date')")) %}
{% endfor %}

{% set boolean_columns = [
    'host_is_superhost',
    'host_has_profile_pic',
    'host_identity_verified',
    'has_availability',
    'instant_bookable',
] %}
{% for column in boolean_columns %}
{% do checks.append((column, "btrim(" ~ column ~ ") not in ('t', 'f')")) %}
{% endfor %}

{% set integer_columns = [
    'host_listings_count',
    'host_total_listings_count',
    'hosts_time_as_user_years',
    'hosts_time_as_user_months',
    'hosts_time_as_host_years',
    'hosts_time_as_host_months',
    'accommodates',
    'bedrooms',
    'beds',
    'minimum_nights',
    'maximum_nights',
    'minimum_minimum_nights',
    'maximum_minimum_nights',
    'minimum_maximum_nights',
    'maximum_maximum_nights',
    'availability_30',
    'availability_60',
    'availability_90',
    'availability_365',
    'availability_eoy',
    'number_of_reviews',
    'number_of_reviews_ltm',
    'number_of_reviews_l30d',
    'number_of_reviews_ly',
    'estimated_occupancy_l365d',
    'calculated_host_listings_count',
    'calculated_host_listings_count_entire_homes',
    'calculated_host_listings_count_private_rooms',
    'calculated_host_listings_count_shared_rooms',
] %}
{% for column in integer_columns %}
{% do checks.append((column, "btrim(" ~ column ~ ") !~ '^-?[0-9]+$'")) %}
{% endfor %}

{% set numeric_columns = [
    'latitude',
    'longitude',
    'bathrooms',
    'minimum_nights_avg_ntm',
    'maximum_nights_avg_ntm',
    'estimated_revenue_l365d',
    'review_scores_rating',
    'review_scores_accuracy',
    'review_scores_cleanliness',
    'review_scores_checkin',
    'review_scores_communication',
    'review_scores_location',
    'review_scores_value',
    'reviews_per_month',
    'host_response_rate',
    'host_acceptance_rate',
    'price_quote_total_price',
    'price_quote_price_per_night',
] %}
{% for column in numeric_columns %}
{% do checks.append((column, "btrim(" ~ column ~ ") !~ '^-?[0-9]+(\\.[0-9]+)?$'")) %}
{% endfor %}

{% for column, predicate in checks %}
select
    '{{ column }}' as column_name,
    _city,
    scrape_id,
    id,
    {{ column }} as raw_value
from {{ source('raw', 'listings') }}
where {{ column }} is not null
  and btrim({{ column }}) <> ''
  and ({{ predicate }})
{% if not loop.last %}
union all
{% endif %}
{% endfor %}
