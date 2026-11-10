"""Stream replay keeps order and relative timing (design v1.2, section 10.2)."""

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ntip.pipeline import Pipeline
from ntip.store import InMemoryEventStore
from ntip.stream import (
    InvalidStream,
    StreamMessage,
    compare,
    load_stream,
    main,
    replay_stream,
    stream_from_store,
    to_markdown,
)

STREAM = Path(__file__).resolve().parents[2] / "data" / "streams" / "escalation.jsonl"


@pytest.fixture
def messages() -> list[StreamMessage]:
    return load_stream(STREAM)


def test_the_queue_follows_the_conversation(messages: list[StreamMessage]) -> None:
    replay = replay_stream(messages)
    priorities = [(s.offset_s, s.incident, s.advisory_priority) for s in replay.steps]
    assert priorities[2] == (45, "A", "P0")  # flames and people trapped
    assert priorities[4] == (90, "B", "P0")  # no longer breathing
    # Simulated time from each incident's first message to its first P0.
    assert replay.time_to_p0_s == {"A": 45, "B": 70, "C": None, "D": None}
    assert replay.final_queue == ["A", "B", "D", "C"]


def test_replay_is_deterministic(messages: list[StreamMessage]) -> None:
    assert asdict(replay_stream(messages)) == asdict(replay_stream(messages))


def test_comparison_flags_a_candidate_that_lowers_priority(messages: list[StreamMessage]) -> None:
    # research-1.0.0 predates the unable-to-get-up rule.
    comparison = compare(messages, baseline="research-1.1.0", candidate="research-1.0.0")
    [difference] = comparison.differences
    assert (difference.incident, difference.baseline, difference.candidate) == ("B", "P2", "P3")
    assert difference.lowers_priority
    assert "not a validated improvement" in to_markdown(comparison.baseline, comparison)


def test_stored_traffic_replays_in_arrival_order() -> None:
    store = InMemoryEventStore()
    start = datetime(2026, 3, 1, 12, tzinfo=UTC)
    now = start
    pipeline = Pipeline(store=store, clock=lambda: now)
    first = pipeline.ingest("Smoke from the garage at 4 Cedar Court.")
    now = start + timedelta(seconds=30)
    other = pipeline.ingest("A cyclist has a cut on his arm at 8 Ash Street.")
    now = start + timedelta(seconds=75)
    pipeline.ingest("The fire is spreading to the house.", incident_id=first.incident_id)

    stream = stream_from_store(store, [first.incident_id, other.incident_id])
    assert [(m.offset_s, m.incident) for m in stream] == [
        (0, first.incident_id),
        (30, other.incident_id),
        (75, first.incident_id),
    ]
    replayed = [s.advisory_priority for s in replay_stream(stream).steps]
    stored = [
        a.advisory_priority.value if a.advisory_priority else None
        for a in sorted(
            store.assessments(first.incident_id) + store.assessments(other.incident_id),
            key=lambda a: a.assessed_at,
        )
    ]
    assert replayed == stored


@pytest.mark.parametrize(
    ("content", "error"),
    [
        ("", "empty"),
        ('{"offset_s": 5, "incident": "A", "text": "x"}\n'
         '{"offset_s": 1, "incident": "A", "text": "y"}', "must not decrease"),
        ('{"offset_s": 0, "text": "x"}', "line 1"),
        ('{"offset_s": 0, "incident": "A", "text": " "}', "required"),
    ],
)  # fmt: skip
def test_invalid_streams_are_rejected(tmp_path: Path, content: str, error: str) -> None:
    path = tmp_path / "stream.jsonl"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(InvalidStream, match=error):
        load_stream(path)


def test_cli_writes_the_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["ntip.stream", str(STREAM), "--candidate", "research-1.0.0", "--out", str(tmp_path)],
    )
    assert main() == 0
    assert "Time to P0" in (tmp_path / "stream-replay.md").read_text("utf-8")
    assert '"differences"' in (tmp_path / "stream-replay.json").read_text("utf-8")
