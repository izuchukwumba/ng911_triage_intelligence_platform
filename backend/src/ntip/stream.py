"""Stream replay (design v1.2, section 10.2, mode 2).

Feeds a sequence of timed messages through a fresh pipeline in their original
order, with a simulated clock set to each message's original offset, and
records how the advisory queue evolved: the priority after each message, the
queue order at that moment, and how long each incident took to reach P0 in
simulated time. With a candidate ruleset the same stream is replayed again and
compared step by step (section 10.4). Nothing is written to any real store.

A stream is JSONL, one message per line, in order::

    {"offset_s": 0, "incident": "A", "text": "There is smoke next door."}

``offset_s`` is seconds since the start of the stream (non-decreasing) and
``incident`` a stream-local key that groups messages into one incident.
Stored traffic can be turned into a stream with ``stream_from_store``.

    python -m ntip.stream data/streams/escalation.jsonl [--candidate research-1.0.0] [--out DIR]
"""

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ntip.pipeline import Pipeline
from ntip.schema.source import SourceType
from ntip.store import EventStore, InMemoryEventStore
from ntip.triage.engine import ENGINE_VERSION
from ntip.triage.ruleset import DEFAULT_RULESET, RELEASED

#: Simulated start of every stream, so replays are identical run to run.
SIMULATION_START = datetime(2026, 1, 1, tzinfo=UTC)
INTERPRETATION = "Illustrative difference only; not a validated improvement."


class InvalidStream(ValueError):
    pass


@dataclass(frozen=True)
class StreamMessage:
    offset_s: float
    incident: str
    text: str
    source_type: SourceType = SourceType.SYNTHETIC_TRANSCRIPT


@dataclass(frozen=True)
class Step:
    """The state of the queue just after one message was processed."""

    offset_s: float
    incident: str
    advisory_priority: str | None
    severity_band: str
    reason_codes: list[str]
    # Incident keys, most urgent first (priority, then first arrival).
    queue: list[str]


@dataclass(frozen=True)
class StreamReplay:
    ruleset: str
    engine_version: str
    messages: int
    steps: list[Step]
    # Simulated seconds from an incident's first message to its first P0;
    # None if it never reached P0.
    time_to_p0_s: dict[str, float | None]
    final_queue: list[str]


@dataclass(frozen=True)
class StepDifference:
    step: int
    offset_s: float
    incident: str
    baseline: str | None
    candidate: str | None
    lowers_priority: bool


@dataclass(frozen=True)
class StreamComparison:
    baseline: StreamReplay
    candidate: StreamReplay
    differences: list[StepDifference]
    time_to_p0_changes: dict[str, tuple[float | None, float | None]]
    interpretation: str = field(default=INTERPRETATION)


def load_stream(path: Path) -> list[StreamMessage]:
    messages: list[StreamMessage] = []
    for number, line in enumerate(path.read_text("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            message = StreamMessage(
                offset_s=float(raw["offset_s"]),
                incident=str(raw["incident"]),
                text=str(raw["text"]),
                source_type=SourceType(raw.get("source_type", SourceType.SYNTHETIC_TRANSCRIPT)),
            )
        except (ValueError, KeyError, TypeError) as err:
            raise InvalidStream(f"line {number}: {err}") from None
        messages.append(message)
    validate(messages)
    return messages


def validate(messages: Sequence[StreamMessage]) -> None:
    if not messages:
        raise InvalidStream("the stream is empty")
    previous = 0.0
    for i, m in enumerate(messages):
        if m.offset_s < previous:
            raise InvalidStream(f"message {i + 1}: offsets must not decrease")
        if not m.incident or not m.text.strip():
            raise InvalidStream(f"message {i + 1}: incident and text are required")
        previous = m.offset_s


def stream_from_store(store: EventStore, incident_ids: Sequence[str]) -> list[StreamMessage]:
    """Stored messages of these incidents, in arrival order, as a stream."""
    events = sorted(
        (e for incident_id in incident_ids for e in store.source_events(incident_id)),
        key=lambda e: e.received_at,  # stable: keeps each incident's stored order on ties
    )
    if not events:
        raise InvalidStream("no stored messages for these incidents")
    start = events[0].received_at
    return [
        StreamMessage(
            offset_s=(e.received_at - start).total_seconds(),
            incident=e.incident_id,
            text=e.text,
            source_type=e.source_type,
        )
        for e in events
    ]


def _rank(priority: str | None) -> int:
    # A failed assessment (no priority) is treated as most urgent, as in review.
    return int(priority[1]) if priority else -1


def replay_stream(
    messages: Sequence[StreamMessage], *, ruleset: str = DEFAULT_RULESET
) -> StreamReplay:
    validate(messages)
    if ruleset not in RELEASED:
        raise InvalidStream(f"unknown ruleset {ruleset}")
    now = SIMULATION_START
    counter = 0

    def new_id(prefix: str) -> str:
        nonlocal counter
        counter += 1
        return f"{prefix}_stream{counter:06d}"

    pipeline = Pipeline(
        store=InMemoryEventStore(), ruleset_name=ruleset, clock=lambda: now, new_id=new_id
    )
    incident_ids: dict[str, str] = {}
    first_seen: dict[str, float] = {}
    current: dict[str, str | None] = {}
    time_to_p0: dict[str, float | None] = {}
    steps: list[Step] = []

    for m in messages:
        now = SIMULATION_START + timedelta(seconds=m.offset_s)
        result = pipeline.ingest(
            m.text, incident_id=incident_ids.get(m.incident), source_type=m.source_type
        )
        incident_ids.setdefault(m.incident, result.incident_id)
        first_seen.setdefault(m.incident, m.offset_s)
        time_to_p0.setdefault(m.incident, None)
        assessment = result.assessment
        priority = assessment.advisory_priority.value if assessment.advisory_priority else None
        current[m.incident] = priority
        if priority == "P0" and time_to_p0[m.incident] is None:
            time_to_p0[m.incident] = m.offset_s - first_seen[m.incident]
        queue = sorted(current, key=lambda k: (_rank(current[k]), first_seen[k]))
        steps.append(
            Step(
                offset_s=m.offset_s,
                incident=m.incident,
                advisory_priority=priority,
                severity_band=assessment.severity_band.value,
                reason_codes=[r.reason_code for r in assessment.reasons],
                queue=queue,
            )
        )

    return StreamReplay(
        ruleset=ruleset,
        engine_version=ENGINE_VERSION,
        messages=len(messages),
        steps=steps,
        time_to_p0_s=time_to_p0,
        final_queue=steps[-1].queue,
    )


def compare(
    messages: Sequence[StreamMessage], *, baseline: str, candidate: str
) -> StreamComparison:
    base = replay_stream(messages, ruleset=baseline)
    cand = replay_stream(messages, ruleset=candidate)
    differences = [
        StepDifference(
            step=i + 1,
            offset_s=b.offset_s,
            incident=b.incident,
            baseline=b.advisory_priority,
            candidate=c.advisory_priority,
            lowers_priority=_rank(c.advisory_priority) > _rank(b.advisory_priority),
        )
        for i, (b, c) in enumerate(zip(base.steps, cand.steps, strict=True))
        if b.advisory_priority != c.advisory_priority
    ]
    p0_changes = {
        k: (base.time_to_p0_s[k], cand.time_to_p0_s[k])
        for k in base.time_to_p0_s
        if base.time_to_p0_s[k] != cand.time_to_p0_s[k]
    }
    return StreamComparison(base, cand, differences, p0_changes)


def _clock(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def to_markdown(replay: StreamReplay, comparison: StreamComparison | None = None) -> str:
    lines = [
        f"# Stream replay ({replay.messages} messages, ruleset `{replay.ruleset}`, "
        f"engine `{replay.engine_version}`)",
        "",
        "> Synthetic messages on a simulated clock. Advisory output for research only.",
        "",
        "| t | Incident | Priority | Band | Queue after (most urgent first) |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| {_clock(s.offset_s)} | {s.incident} | {s.advisory_priority or 'failed'} "
        f"| {s.severity_band} | {' > '.join(s.queue)} |"
        for s in replay.steps
    ]
    lines += ["", "| Incident | Time to P0 |", "|---|---|"]
    lines += [
        f"| {k} | {_clock(v) if v is not None else 'never'} |"
        for k, v in replay.time_to_p0_s.items()
    ]
    if comparison is not None:
        lines += [
            "",
            f"## Candidate `{comparison.candidate.ruleset}` vs `{comparison.baseline.ruleset}`",
            "",
            f"> {comparison.interpretation}",
            "",
        ]
        if not comparison.differences:
            lines.append("No step changes priority.")
        else:
            lines += [
                "| Step | t | Incident | Baseline | Candidate | Lowers |",
                "|---|---|---|---|---|---|",
            ]
            lines += [
                f"| {d.step} | {_clock(d.offset_s)} | {d.incident} | {d.baseline} "
                f"| {d.candidate} | {'**yes**' if d.lowers_priority else 'no'} |"
                for d in comparison.differences
            ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay a timed message stream (design 10.2).")
    parser.add_argument("stream", type=Path)
    parser.add_argument("--ruleset", default=DEFAULT_RULESET)
    parser.add_argument("--candidate", help="released ruleset to compare against --ruleset")
    parser.add_argument("--out", type=Path, help="directory for stream-replay.json and .md")
    args = parser.parse_args()

    messages = load_stream(args.stream)
    comparison = None
    if args.candidate:
        comparison = compare(messages, baseline=args.ruleset, candidate=args.candidate)
        replay = comparison.baseline
    else:
        replay = replay_stream(messages, ruleset=args.ruleset)
    markdown = to_markdown(replay, comparison)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = asdict(comparison) if comparison else asdict(replay)
        (args.out / "stream-replay.json").write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        (args.out / "stream-replay.md").write_text(markdown, encoding="utf-8", newline="\n")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
