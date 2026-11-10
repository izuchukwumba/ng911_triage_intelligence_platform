import json

from ntip.schema.export import CONTRACTS, DIALECT, rendered, stale_files


def test_committed_schemas_match_the_models() -> None:
    stale = stale_files()
    assert stale == [], (
        f"JSON Schema files are out of date: {[p.name for p in stale]}. "
        "Run `python -m ntip.schema.export` and commit the result."
    )


def test_every_contract_declares_the_2020_12_dialect() -> None:
    documents = [json.loads(text) for text in rendered().values()]
    assert len(documents) == len(CONTRACTS)
    assert all(doc["$schema"] == DIALECT for doc in documents)


def test_schemas_forbid_unknown_fields() -> None:
    for text in rendered().values():
        assert json.loads(text)["additionalProperties"] is False
