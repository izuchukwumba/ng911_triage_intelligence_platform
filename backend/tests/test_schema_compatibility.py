"""Schema compatibility (design v1.2, sections 4.3 and 4.4).

Every published sample, from every schema version, must still be accepted by
the current models and by the committed JSON Schemas. Minor versions may only
add: a document written before a field existed must stay valid and keep its
meaning, which is checked by removing every field added since 2.0.0.
"""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from ntip.schema.base import SCHEMA_VERSION
from ntip.schema.export import CONTRACTS, SCHEMA_DIR
from ntip.schema.samples import EXAMPLES_DIR, stale_files

EXAMPLES = sorted(EXAMPLES_DIR.glob("*.json"))

# Fields added after 2.0.0, by contract, with the version that added them.
# A dotted path with "*" reaches into every item of a list. Keep this up to
# date when a minor version adds a field: it is the evidence for "additive".
ADDED_AFTER_2_0: dict[str, list[tuple[str, str]]] = {
    "source-event": [("tenant_id", "2.5.0"), ("supplied_locations", "2.6.0")],
    "incident": [
        ("inference", "2.2.0"),
        ("locations.*.supplied_by", "2.6.0"),
        ("inference.fusion_policy", "2.7.0"),
        ("inference.suggestions", "2.7.0"),
    ],
    "assessment": [],
    "human-review": [],
    "audit-event": [],
    # ReplayRun itself was added in 2.1.0.
    "replay-run": [("tenant_id", "2.5.0")],
}


def _contract(path: Path) -> str:
    return path.name.split(".", 1)[0]


def _schema(name: str) -> Draft202012Validator:
    document = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text("utf-8"))
    return Draft202012Validator(document)


def _remove(document: Any, path: list[str]) -> None:
    head, *rest = path
    if head == "*":
        for item in document:
            _remove(item, rest)
    elif not rest:
        document.pop(head, None)
    elif head in document:
        _remove(document[head], rest)


def test_this_versions_samples_are_published() -> None:
    assert stale_files() == [], "run `python -m ntip.schema.samples` and commit the result"
    published = {_contract(p) for p in EXAMPLES if p.name.endswith(f".{SCHEMA_VERSION}.json")}
    assert published == set(CONTRACTS)


def test_the_registry_covers_every_contract() -> None:
    assert set(ADDED_AFTER_2_0) == set(CONTRACTS)


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_every_published_sample_is_still_accepted(path: Path) -> None:
    document = json.loads(path.read_text("utf-8"))
    name = _contract(path)
    CONTRACTS[name].model_validate(document)
    errors = [e.message for e in _schema(name).iter_errors(document)]
    assert errors == []


@pytest.mark.parametrize("name", sorted(CONTRACTS))
def test_documents_without_later_fields_stay_valid_and_keep_their_meaning(name: str) -> None:
    current = json.loads((EXAMPLES_DIR / f"{name}.{SCHEMA_VERSION}.json").read_text("utf-8"))
    older = copy.deepcopy(current)
    for path, _ in ADDED_AFTER_2_0[name]:
        _remove(older, path.split("."))

    assert [e.message for e in _schema(name).iter_errors(older)] == []
    reread = CONTRACTS[name].model_validate(older).model_dump(mode="json")
    # Everything the older document said is read back unchanged: apart from
    # the newer fields (filled in with their defaults), the documents agree.
    for path, _ in ADDED_AFTER_2_0[name]:
        _remove(reread, path.split("."))
    assert reread == older
