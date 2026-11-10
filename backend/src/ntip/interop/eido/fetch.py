"""Fetch the pinned EIDO schema files and verify them.

Files come from the pinned commit only and must match their pinned sha256;
any mismatch is an error, never a warning. Verified files are cached as JSON
(the YAML originals take seconds to parse) under ``NTIP_EIDO_CACHE`` or
``~/.cache/ntip/eido/<commit>``. The cache is local and is never committed:
the upstream repository publishes no licence.

    python -m ntip.interop.eido.fetch     # prefetch and verify
"""

import hashlib
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml

from ntip.interop.eido.profile import PROFILE, EidoProfile


class SchemaUnavailable(Exception):
    """The pinned schema could not be obtained or did not verify."""


def cache_dir(profile: EidoProfile = PROFILE) -> Path:
    root = os.environ.get("NTIP_EIDO_CACHE")
    base = Path(root) if root else Path.home() / ".cache" / "ntip" / "eido"
    return base / profile.commit


def _download(url: str, timeout_s: float = 30.0) -> bytes:
    quoted = urllib.parse.quote(url, safe=":/")
    try:
        with urllib.request.urlopen(quoted, timeout=timeout_s) as resp:
            data: bytes = resp.read()
            return data
    except OSError as err:
        raise SchemaUnavailable(f"could not download {url}: {err}") from None


def _verified(path: str, expected: str, profile: EidoProfile) -> bytes:
    target = cache_dir(profile) / "raw" / path
    data = target.read_bytes() if target.exists() else _download(profile.raw_url(path))
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise SchemaUnavailable(f"{path}: sha256 {actual} does not match the pinned {expected}")
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return data


def load_documents(profile: EidoProfile = PROFILE) -> dict[str, Any]:
    """Every pinned schema document, keyed by its repository path."""
    documents: dict[str, Any] = {}
    for path, digest in profile.files.items():
        converted = cache_dir(profile) / "json" / f"{path}.{digest[:16]}.json"
        if converted.exists():
            documents[path] = json.loads(converted.read_text("utf-8"))
            continue
        document = yaml.safe_load(_verified(path, digest, profile))
        converted.parent.mkdir(parents=True, exist_ok=True)
        converted.write_text(json.dumps(document), encoding="utf-8")
        documents[path] = document
    return documents


def load_sample(profile: EidoProfile = PROFILE) -> Any:
    """NENA's published sample EIDO at the pinned commit (for conformance tests)."""
    path, digest = profile.sample
    return json.loads(_verified(path, digest, profile).decode("utf-8-sig"))


def main() -> int:
    documents = load_documents()
    load_sample()
    print(f"{PROFILE.standard_edition} @ {PROFILE.commit[:12]}: {len(documents)} files verified")
    print(f"cache: {cache_dir()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
