"""The pinned EIDO profile, the verifying fetcher and schema validation.

Tests that need NENA's schema fetch it from the pinned commit (or use the
local cache) and are skipped when it cannot be obtained, e.g. offline.
"""

import copy
import hashlib
import re
from pathlib import Path
from typing import Any

import pytest

from ntip.interop.eido.fetch import SchemaUnavailable, load_documents, load_sample
from ntip.interop.eido.profile import PROFILE, EidoProfile
from ntip.interop.eido.validate import validate


@pytest.fixture(scope="module")
def documents() -> dict[str, Any]:
    try:
        return load_documents()
    except SchemaUnavailable as err:
        pytest.skip(f"pinned EIDO schema unavailable: {err}")


@pytest.fixture(scope="module")
def sample(documents: dict[str, Any]) -> Any:
    return load_sample()


def test_profile_pins_an_exact_published_edition() -> None:
    assert PROFILE.standard_edition == "NENA-STA-021.1b"
    assert re.fullmatch(r"[0-9a-f]{40}", PROFILE.commit)
    assert all(re.fullmatch(r"[0-9a-f]{64}", d) for d in PROFILE.files.values())
    assert PROFILE.schema_artifact_digest.startswith("sha256:")


def test_pinned_files_cover_every_cross_file_reference(documents: dict[str, Any]) -> None:
    refs: set[str] = set()

    def walk(node: Any, here: str) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ".yaml" in ref:
                target = Path(here).parent.joinpath(ref.split("#")[0]).as_posix()
                refs.add(re.sub(r"/+", "/", target))
            for value in node.values():
                walk(value, here)
        elif isinstance(node, list):
            for value in node:
                walk(value, here)

    for path, document in documents.items():
        walk(document, path)
    assert refs <= set(PROFILE.files)


def test_tampered_files_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NTIP_EIDO_CACHE", str(tmp_path))
    pinned = hashlib.sha256(b"a: 1\n").hexdigest()
    profile = EidoProfile(
        profile_id="t", standard_edition="t", repository="none/none", commit="0" * 40,
        eido_version="1.0", root_schema="x.yaml", root_type="T", files={"x.yaml": pinned},
        sample=("s.json", pinned),
    )  # fmt: skip
    raw = tmp_path / profile.commit / "raw" / "x.yaml"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b"a: 2\n")  # not what was pinned
    with pytest.raises(SchemaUnavailable, match="does not match the pinned"):
        load_documents(profile)


class TestValidation:
    def test_nena_published_sample_is_valid(self, sample: Any) -> None:
        assert validate(sample) == []

    def test_unsupported_eido_version_is_invalid(self, sample: Any) -> None:
        bad = copy.deepcopy(sample)
        bad["eidoVersion"] = "2.0"
        assert any("eidoVersion" in p.pointer for p in validate(bad))

    def test_missing_required_component_is_invalid(self, sample: Any) -> None:
        bad = copy.deepcopy(sample)
        del bad["agencyComponent"]
        assert any("agencyComponent" in p.message for p in validate(bad))

    def test_wrong_type_is_reported_with_its_location(self, sample: Any) -> None:
        bad = copy.deepcopy(sample)
        bad["callComponent"] = "not a list"
        assert any(p.pointer == "$.callComponent" for p in validate(bad))
