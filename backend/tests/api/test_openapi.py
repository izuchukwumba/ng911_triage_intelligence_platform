from ntip.api.openapi import PATH, render


def test_committed_openapi_document_is_current() -> None:
    assert PATH.read_text(encoding="utf-8") == render(), (
        "backend/openapi.json is stale. Run `python -m ntip.api.openapi`, then "
        "`npm run gen:api` in apps/dashboard, and commit both."
    )
