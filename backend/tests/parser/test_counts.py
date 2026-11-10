import pytest

from ntip.parser.counts import victim_count
from ntip.schema.base import FactStatus


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("There are four people injured at the scene on Route 9.", 4),
        ("3 people hurt near the station.", 3),
        ("I can see at least five or six people on the ground, they look injured.", 6),
        ("At least three or four people down at 88 Lincoln Drive.", 4),
        ("Two injured, both conscious.", 2),
        ("Hay 2 heridos en la calle.", 2),
    ],
)
def test_reported_counts(text: str, expected: int) -> None:
    fact = victim_count(text)
    assert fact.status is FactStatus.REPORTED
    assert fact.value == expected
    span = fact.source_spans[0]
    assert span.slice(text)  # the quoted count is grounded in the text


def test_unstated_count_is_not_reported_rather_than_one() -> None:
    fact = victim_count("My father collapsed and is not breathing at 456 Elm Road.")
    assert fact.status is FactStatus.NOT_REPORTED
    assert fact.value is None


def test_indefinite_plural_is_unknown() -> None:
    fact = victim_count("There are several people hurt, I can't count them.")
    assert fact.status is FactStatus.UNKNOWN
    assert fact.value is None


def test_different_counts_conflict() -> None:
    fact = victim_count("Two people are hurt. Wait, no, three people are hurt.")
    assert fact.status is FactStatus.CONFLICTING
    assert fact.candidates == [2, 3]


def test_repeated_identical_counts_agree() -> None:
    fact = victim_count("Two people hurt. Yes, two people hurt.")
    assert fact.status is FactStatus.REPORTED
    assert fact.value == 2
    assert len(fact.source_spans) == 2


def test_numbers_in_addresses_are_not_counts() -> None:
    assert victim_count("Apartment 4B at 12 Oak Street.").status is FactStatus.NOT_REPORTED


def test_negated_count_is_ignored() -> None:
    assert victim_count("There are no two people hurt here.").status is FactStatus.NOT_REPORTED
