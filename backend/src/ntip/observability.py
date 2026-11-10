"""Structured logs and metrics (design v1.2, sections 5.3 and 13.3).

Logs are one JSON object per line, carrying the request's correlation id, so
an operator can follow one request across components. They never contain
transcript text: messages are written by this code base, and exceptions are
reported by type only (no tracebacks or exception messages, which could quote
input).

Metrics use the Prometheus text format, from a small in-process registry (no
extra dependency): request counts and latencies by route template, processing
outcomes, interop receipts and model degradation.
"""

import json
import logging
import math
import threading
from collections import defaultdict
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

correlation: ContextVar[str | None] = ContextVar("correlation", default=None)

# Fields a log call may add with ``extra=...``; anything else is dropped.
_EXTRA_FIELDS = ("event", "method", "route", "status", "duration_ms", "outcome", "tenant")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        cid = getattr(record, "correlation_id", None) or correlation.get()
        if cid:
            entry["correlation_id"] = cid
        for name in _EXTRA_FIELDS:
            if hasattr(record, name):
                entry[name] = getattr(record, name)
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = record.exc_info[0].__name__
        return json.dumps(entry, ensure_ascii=False)


def configure_logging(fmt: str = "json", level: str = "INFO") -> None:
    """Route all logging, including uvicorn's, through one handler."""
    handler = logging.StreamHandler()
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers[:] = []
        logging.getLogger(name).propagate = True
    # Requests are logged by the API itself, with route templates and
    # correlation ids; uvicorn's access log would repeat them with full paths.
    logging.getLogger("uvicorn.access").disabled = True


Labels = tuple[tuple[str, str], ...]
LATENCY_BUCKETS_S = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


def _labels(labels: dict[str, str]) -> Labels:
    return tuple(sorted(labels.items()))


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _render_labels(labels: Labels, extra: tuple[tuple[str, str], ...] = ()) -> str:
    items = labels + extra
    if not items:
        return ""
    return "{" + ",".join(f'{k}="{_escape(v)}"' for k, v in items) + "}"


def _number(value: float) -> str:
    return "+Inf" if math.isinf(value) else repr(float(value)) if value % 1 else str(int(value))


class Metrics:
    """Thread-safe counters and histograms, rendered in Prometheus text format."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._help: dict[str, tuple[str, str]] = {}
        self._counters: dict[str, dict[Labels, float]] = defaultdict(dict)
        self._histograms: dict[str, dict[Labels, list[float]]] = defaultdict(dict)
        self._info: dict[str, dict[str, str]] = {}

    def counter(self, name: str, help_text: str) -> None:
        self._help.setdefault(name, ("counter", help_text))

    def histogram(self, name: str, help_text: str) -> None:
        self._help.setdefault(name, ("histogram", help_text))

    def info(self, name: str, help_text: str, labels: dict[str, str]) -> None:
        self._help[name] = ("gauge", help_text)
        self._info[name] = labels

    def inc(self, name: str, amount: float = 1.0, **labels: str) -> None:
        key = _labels(labels)
        with self._lock:
            series = self._counters[name]
            series[key] = series.get(key, 0.0) + amount

    def observe(self, name: str, value: float, **labels: str) -> None:
        key = _labels(labels)
        with self._lock:
            # Per series: one count per bucket, then +Inf count, then sum.
            series = self._histograms[name].setdefault(key, [0.0] * (len(LATENCY_BUCKETS_S) + 2))
            for i, bound in enumerate(LATENCY_BUCKETS_S):
                if value <= bound:
                    series[i] += 1
            series[-2] += 1
            series[-1] += value

    def value(self, name: str, **labels: str) -> float:
        with self._lock:
            return self._counters[name].get(_labels(labels), 0.0)

    def render(self) -> str:
        lines: list[str] = []
        with self._lock:
            for name, (kind, help_text) in sorted(self._help.items()):
                lines += [f"# HELP {name} {help_text}", f"# TYPE {name} {kind}"]
                if name in self._info:
                    lines.append(f"{name}{_render_labels(_labels(self._info[name]))} 1")
                for key, count in sorted(self._counters.get(name, {}).items()):
                    lines.append(f"{name}{_render_labels(key)} {_number(count)}")
                for key, series in sorted(self._histograms.get(name, {}).items()):
                    for bound, count in zip(LATENCY_BUCKETS_S, series, strict=False):
                        le = (("le", repr(bound)),)
                        lines.append(f"{name}_bucket{_render_labels(key, le)} {_number(count)}")
                    inf = (("le", "+Inf"),)
                    lines.append(f"{name}_bucket{_render_labels(key, inf)} {_number(series[-2])}")
                    lines.append(f"{name}_count{_render_labels(key)} {_number(series[-2])}")
                    lines.append(f"{name}_sum{_render_labels(key)} {series[-1]!r}")
        return "\n".join(lines) + "\n"
