from pathlib import Path

from airbnb_pipeline.datasets import DatasetSpec
from airbnb_pipeline.validation.listings import (
    ValidationError,
    ValidationReport,
    validate_listings,
)

VALIDATORS = {
    "listings": validate_listings,
}


def validate_dataset(path: Path, spec: DatasetSpec) -> ValidationReport:
    return VALIDATORS[spec.name](path, spec)


__all__ = [
    "ValidationError",
    "ValidationReport",
    "validate_dataset",
    "validate_listings",
]
