from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from ntip.schema.base import Fact, FactStatus, SourceSpan, UtcDatetime, sha256_digest


class TestSourceSpan:
    def test_slices_the_covered_text(self) -> None:
        assert SourceSpan(start=3, end=8).slice("He is not breathing") == "is no"

    def test_rejects_empty_or_reversed_span(self) -> None:
        with pytest.raises(ValidationError):
            SourceSpan(start=5, end=5)
        with pytest.raises(ValidationError):
            SourceSpan(start=6, end=2)

    def test_slice_rejects_span_beyond_text(self) -> None:
        with pytest.raises(ValueError, match="exceeds text length"):
            SourceSpan(start=0, end=50).slice("short")

    def test_is_immutable(self) -> None:
        span = SourceSpan(start=0, end=1)
        with pytest.raises(ValidationError):
            span.start = 2  # type: ignore[misc]


class TestFact:
    def test_reported_fact_requires_a_value(self) -> None:
        with pytest.raises(ValidationError, match="requires a value"):
            Fact[int](status=FactStatus.REPORTED)

    @pytest.mark.parametrize(
        "status",
        [
            FactStatus.UNKNOWN,
            FactStatus.NOT_REPORTED,
            FactStatus.NEGATED,
            FactStatus.NOT_APPLICABLE,
        ],
    )
    def test_states_without_a_value_reject_one(self, status: FactStatus) -> None:
        # e.g. an unknown victim count must not be stored as 0
        with pytest.raises(ValidationError, match="must not carry a value"):
            Fact[int](status=status, value=0)

    def test_unknown_and_negated_are_distinct(self) -> None:
        assert Fact[bool](status=FactStatus.UNKNOWN) != Fact[bool](status=FactStatus.NEGATED)

    def test_conflicting_fact_keeps_all_candidates(self) -> None:
        fact = Fact[int](status=FactStatus.CONFLICTING, candidates=[2, 3])
        assert fact.value is None
        assert fact.candidates == [2, 3]

    def test_conflicting_fact_needs_two_candidates(self) -> None:
        with pytest.raises(ValidationError, match="at least two candidates"):
            Fact[int](status=FactStatus.CONFLICTING, candidates=[2])

    def test_only_conflicting_facts_list_candidates(self) -> None:
        with pytest.raises(ValidationError, match="only a conflicting fact"):
            Fact[int](status=FactStatus.REPORTED, value=2, candidates=[2, 3])


class TestUtcDatetime:
    adapter = TypeAdapter(UtcDatetime)

    def test_normalises_offsets_to_utc(self) -> None:
        local = datetime(2026, 11, 9, 7, 0, tzinfo=timezone(timedelta(hours=-5)))
        assert self.adapter.validate_python(local) == datetime(2026, 11, 9, 12, 0, tzinfo=UTC)

    def test_rejects_naive_datetimes(self) -> None:
        with pytest.raises(ValidationError):
            self.adapter.validate_python(datetime(2026, 11, 9, 12, 0))


def test_sha256_digest_format() -> None:
    assert sha256_digest("abc") == (
        "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
