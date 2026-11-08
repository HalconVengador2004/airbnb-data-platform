-- Fails when the descriptive license flags disagree with the raw license text.
-- These flags make no claim about legal compliance.

select *
from {{ ref('stg_listings') }}
where license_has_text is distinct from (
        license_raw is not null and btrim(license_raw) <> ''
    )
   or license_mentions_exempt is distinct from (
        license_raw is not null
        and btrim(license_raw) <> ''
        and position('exempt' in lower(license_raw)) > 0
    )
   or license_mentions_regional is distinct from (
        license_raw is not null
        and btrim(license_raw) <> ''
        and position('regional registration number' in lower(license_raw)) > 0
    )
   or license_mentions_national is distinct from (
        license_raw is not null
        and btrim(license_raw) <> ''
        and position('national registration number' in lower(license_raw)) > 0
    )
   or (license_flag = 'not_provided') is distinct from (
        license_raw is null or btrim(license_raw) = ''
    )
   or (license_flag = 'mixed') is distinct from (
        license_raw is not null
        and btrim(license_raw) <> ''
        and position('exempt' in lower(license_raw)) > 0
        and position('registration number' in lower(license_raw)) > 0
    )
   or (license_flag = 'exempt_marker') is distinct from (
        license_raw is not null
        and btrim(license_raw) <> ''
        and position('exempt' in lower(license_raw)) > 0
        and position('registration number' in lower(license_raw)) = 0
    )
   or (license_flag = 'registration_marker') is distinct from (
        license_raw is not null
        and btrim(license_raw) <> ''
        and position('exempt' in lower(license_raw)) = 0
        and position('registration number' in lower(license_raw)) > 0
    )
   or (license_flag = 'other') is distinct from (
        license_raw is not null
        and btrim(license_raw) <> ''
        and position('exempt' in lower(license_raw)) = 0
        and position('registration number' in lower(license_raw)) = 0
    )
