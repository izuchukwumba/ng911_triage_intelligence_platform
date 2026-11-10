"""Seeded, reproducible synthetic case generation (design v1.2, section 12).

Every case is a Situation phrasing plus perturbations drawn from a seeded RNG:
location form, who is affected (adult, child, several people), how the cue is
said (plain, uncertain, second-hand, negated, past tense), disfluency,
misspellings, a follow-up message, and Spanish. Labels follow the labelling
rubric and are marked ``label_source: generator``.
"""

import random
from collections.abc import Iterator
from dataclasses import dataclass

from ntip.evaluation.dataset import CaseLabels, EvalCase, LabelSource
from ntip.generator.scenarios import (
    ADULTS,
    CHILDREN,
    CROSS,
    LANDMARKS,
    NUMBER_WORDS,
    SITUATIONS,
    SPANISH_STREETS,
    STREETS,
    Situation,
)

GENERATOR_VERSION = "1.0.0"

_ORDER = ["low", "standard", "elevated", "high", "critical"]
_PRIORITY = {"critical": "P0", "high": "P1", "elevated": "P2", "standard": "P3", "low": "P4"}
_CRITICAL = {"NOT_BREATHING", "UNCONSCIOUS"}


def _escalate(severity: str) -> str:
    return _ORDER[min(_ORDER.index(severity) + 1, len(_ORDER) - 1)]


@dataclass
class _Draft:
    messages: list[str]
    severity: str
    cues: set[str]
    absent: set[str]
    location: str
    victims: int | str | None
    variant: list[str]


def _fill(template: str, who: str) -> str:
    text = template.replace("{Who}", who[:1].upper() + who[1:]).replace("{who}", who)
    return " ".join(text.split())


def _location(rng: random.Random, spanish: bool) -> tuple[str, str, str]:
    """(sentence, label, kind); also covers missing and caller-lost cases."""
    roll = rng.random()
    if spanish:
        street = rng.choice(SPANISH_STREETS)
        return f"Estamos en la {street} {rng.randint(10, 999)}.", "present", "numbered"
    if roll < 0.45:
        return f"We are at {rng.randint(10, 9999)} {rng.choice(STREETS)}.", "present", "numbered"
    if roll < 0.6:
        return f"We're near {rng.choice(CROSS)}.", "present", "intersection"
    if roll < 0.72:
        return f"I'm outside {rng.choice(LANDMARKS)}.", "present", "landmark"
    if roll < 0.86:
        return "I don't know where I am exactly.", "missing", "none"
    return "", "missing", "none"


_DISFLUENCIES = ("um,", "uh,", "like,", "I mean,", "oh god,")


def _disfluent(rng: random.Random, text: str) -> str:
    words = text.split()
    for _ in range(rng.randint(1, 2)):
        words.insert(rng.randrange(len(words) + 1), rng.choice(_DISFLUENCIES))
    return " ".join(words)


def _misspell(rng: random.Random, text: str) -> str:
    """Swap two adjacent letters in one or two longer words (cue words included)."""
    words = text.split()
    candidates = [i for i, w in enumerate(words) if len(w) > 4 and w.isalpha()]
    for i in rng.sample(candidates, k=min(len(candidates), rng.randint(1, 2))):
        w = words[i]
        j = rng.randrange(1, len(w) - 2)
        words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2 :]
    return " ".join(words)


def _draft(situation: Situation, rng: random.Random) -> _Draft:
    variant: list[str] = []
    severity = situation.severity
    cues = set(situation.cues)
    absent: set[str] = set()
    victims: int | str | None = None

    use_spanish = bool(situation.spanish) and rng.random() < 0.15
    if use_spanish:
        body = rng.choice(situation.spanish)
        variant.append("spanish")
        # Spanish phrasings name their own person; no child/multiple variants.
        if any(w in body.lower() for w in ("mi hijo", "mi hija")):
            cues.add("CHILD_INVOLVED")
            severity = _escalate(severity)
    else:
        who = rng.choice(ADULTS)
        template = rng.choice(situation.phrasings)
        # Only phrasings that mention the person can be about a child.
        if situation.personal and "{who}" in template.lower() and rng.random() < 0.2:
            who = rng.choice(CHILDREN)
            cues.add("CHILD_INVOLVED")
            severity = _escalate(severity)
            variant.append("child")
        mode = rng.random()
        if situation.denial and mode < 0.12:
            body = _fill(situation.denial, who)
            absent |= cues - {"CHILD_INVOLVED"}
            cues = cues & {"CHILD_INVOLVED"}
            severity = "low"
            variant.append("negated")
        elif situation.past and mode < 0.24:
            body = _fill(situation.past, who)
            absent |= cues - {"CHILD_INVOLVED"}
            cues = cues & {"CHILD_INVOLVED"}
            # A recovered critical event is elevated; any other past event is low.
            severity = "elevated" if set(situation.cues) & _CRITICAL else "low"
            variant.append("past")
        else:
            body = _fill(template, who)
            if mode < 0.36:
                body = "I think " + body[0].lower() + body[1:]
                variant.append("uncertain")
            elif mode < 0.46:
                body = "My neighbor told me " + body[0].lower() + body[1:]
                variant.append("second_hand")

    location, location_label, location_kind = _location(rng, use_spanish)
    messages = [f"{body} {location}".strip()]

    if (
        "negated" not in variant
        and "past" not in variant
        and not use_spanish
        and situation.personal
        and rng.random() < 0.15
    ):
        n = rng.choice(list(NUMBER_WORDS))
        messages[0] += f" There are {NUMBER_WORDS[n]} people hurt."
        cues |= {"MULTIPLE_VICTIMS", "INJURY_REPORTED"}
        severity = _escalate(severity)
        victims = n
        variant.append("multiple")

    # A correction conflicts with an earlier *numbered* address (design 6.3).
    if location_kind == "numbered" and not use_spanish and rng.random() < 0.1:
        messages.append(f"Sorry, I mean {rng.randint(10, 9999)} {rng.choice(STREETS)}.")
        location_label = "conflicting"
        variant.append("corrected_address")

    if not use_spanish and rng.random() < 0.15:
        messages[0] = _disfluent(rng, messages[0])
        variant.append("disfluent")
    if not use_spanish and rng.random() < 0.1:
        messages[0] = _misspell(rng, messages[0])
        variant.append("misspelled")

    return _Draft(messages, severity, cues, absent, location_label, victims, variant)


def generate(n: int, seed: int) -> Iterator[EvalCase]:
    """``n`` cases, cycling through families; identical for the same seed."""
    rng = random.Random(seed)
    for i in range(n):
        situation = SITUATIONS[i % len(SITUATIONS)]
        draft = _draft(situation, rng)
        yield EvalCase(
            case_id=f"g{seed}-{i:04d}",
            split=situation.split,
            family=situation.family,
            messages=draft.messages,
            label_source=LabelSource.GENERATOR,
            labels=CaseLabels.model_validate(
                {
                    "domain": situation.domain,
                    "severity": draft.severity,
                    "priority": _PRIORITY[draft.severity],
                    "cues": sorted(draft.cues),
                    "absent_cues": sorted(draft.absent),
                    "location": draft.location,
                    "victim_count": draft.victims,
                }
            ),
            notes=f"generator {GENERATOR_VERSION}, seed {seed}; "
            + (", ".join(draft.variant) or "plain"),
        )
