"""Validate EIDO instances against the pinned NENA schema.

The schema is NENA's OpenAPI 3.0 document plus its NIEM component files;
cross-file references are resolved through a registry built from the pinned,
verified documents only, so validation can never reach out to other URLs.
"""

from dataclasses import dataclass
from typing import Any

from jsonschema import Draft7Validator
from referencing import Registry
from referencing.jsonschema import DRAFT7

from ntip.interop.eido.fetch import load_documents
from ntip.interop.eido.profile import PROFILE, EidoProfile

_BASE = "https://pinned-eido.invalid/"


@dataclass(frozen=True)
class SchemaProblem:
    pointer: str
    message: str


_VALIDATORS: dict[str, Draft7Validator] = {}


def _validator(profile: EidoProfile = PROFILE) -> Draft7Validator:
    if profile.profile_id in _VALIDATORS:
        return _VALIDATORS[profile.profile_id]
    registry: Registry[Any] = Registry()
    for path, document in load_documents(profile).items():
        registry = registry.with_resource(_BASE + path, DRAFT7.create_resource(document))
    root = {"$ref": f"{_BASE}{profile.root_schema}#/components/schemas/{profile.root_type}"}
    validator = _VALIDATORS[profile.profile_id] = Draft7Validator(root, registry=registry)
    return validator


def validate(instance: Any, profile: EidoProfile = PROFILE) -> list[SchemaProblem]:
    """Every schema violation, most specific first; empty means valid."""
    errors = sorted(_validator(profile).iter_errors(instance), key=lambda e: e.json_path)
    return [SchemaProblem(pointer=e.json_path, message=e.message[:300]) for e in errors]
