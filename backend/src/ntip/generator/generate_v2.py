"""Generator 2.0: broader synthetic calls with evidence spans (ML layer design, 4.3).

Differences from generator 1.0 (which stays unchanged, so the 1.0.0 dataset
and every report built on it remain reproducible):

- 66 scenario families with 3 to 6 phrasings each, covering all 32 labelled
  cue codes, every code in both a training and a test family
  (``scenarios_v2``);
- label schema 2.0: each cue's status and the exact characters that support
  it, and the location components the caller gave. Text is kept as
  characters tagged with the codes they support, so spans survive every
  perturbation: a misspelled cue word stays inside its span, and an inserted
  "um," between two cue words becomes part of the evidence, as it is written;
- a speech-recognition-style variant: lower case, no punctuation, and a few
  homophone substitutions.

Seeded and reproducible; labels are generator-intended.
"""

import random
import re
from collections.abc import Iterator
from dataclasses import dataclass, field

from ntip.evaluation.dataset import (
    CaseLabels,
    CaseUncertainty,
    CueAnnotation,
    CueStatus,
    EvalCase,
    LabelSource,
    LocationComponents,
    TextSpan,
)
from ntip.generator.scenarios import (
    ADULTS,
    CHILDREN,
    CROSS,
    LANDMARKS,
    NUMBER_WORDS,
    SPANISH_STREETS,
    STREETS,
    Situation,
)
from ntip.generator.scenarios_v2 import SITUATIONS

GENERATOR_VERSION = "2.0.0"

_ORDER = ["low", "standard", "elevated", "high", "critical"]
_PRIORITY = {"critical": "P0", "high": "P1", "elevated": "P2", "standard": "P3", "low": "P4"}
_CRITICAL = {"NOT_BREATHING", "UNCONSCIOUS"}
# Children whose description reads correctly before "'s".
_POSSESSIVE_CHILDREN = ("my baby", "my toddler")
_MARK = re.compile(r"\[([A-Z_]+)\|([^\]]+)\]")
_LOC = "loc:"


def _escalate(severity: str) -> str:
    return _ORDER[min(_ORDER.index(severity) + 1, len(_ORDER) - 1)]


@dataclass
class Tagged:
    """Text as characters, each tagged with the labels it is evidence for."""

    chars: list[str] = field(default_factory=list)
    tags: list[frozenset[str]] = field(default_factory=list)

    @classmethod
    def of(cls, text: str, *tags: str) -> "Tagged":
        return cls(list(text), [frozenset(tags)] * len(text))

    def __add__(self, other: "Tagged") -> "Tagged":
        return Tagged(self.chars + other.chars, self.tags + other.tags)

    @property
    def text(self) -> str:
        return "".join(self.chars)

    def span(self, tag: str) -> tuple[int, int] | None:
        where = [i for i, t in enumerate(self.tags) if tag in t]
        return (where[0], where[-1] + 1) if where else None

    def tag_names(self) -> set[str]:
        return {t for tags in self.tags for t in tags}

    def strip(self) -> "Tagged":
        start, end = 0, len(self.chars)
        while start < end and self.chars[start] == " ":
            start += 1
        while end > start and self.chars[end - 1] == " ":
            end -= 1
        return Tagged(self.chars[start:end], self.tags[start:end])


def render(template: str, who: str, who_tags: tuple[str, ...] = ()) -> Tagged:
    """Fill ``{Who}``/``{who}`` and turn ``[CODE|words]`` marks into tagged text."""

    def fill(text: str, extra: tuple[str, ...]) -> Tagged:
        out = Tagged()
        for i, part in enumerate(re.split(r"(\{[Ww]ho\})", text)):
            if i % 2:
                person = who[:1].upper() + who[1:] if part == "{Who}" else who
                out = out + Tagged.of(person, *extra, *who_tags)
            elif part:
                out = out + Tagged.of(part, *extra)
        return out

    out, pos = Tagged(), 0
    for mark in _MARK.finditer(template):
        out = out + fill(template[pos : mark.start()], ())
        out = out + fill(mark.group(2), (mark.group(1),))
        pos = mark.end()
    out = out + fill(template[pos:], ())
    # Collapse doubled spaces (an empty {who} never occurs, but be safe).
    keep = [i for i, c in enumerate(out.chars) if not (c == " " and i and out.chars[i - 1] == " ")]
    return Tagged([out.chars[i] for i in keep], [out.tags[i] for i in keep])


def marked_codes(template: str) -> list[str]:
    return [m.group(1) for m in _MARK.finditer(template)]


def _lower_first(t: Tagged) -> Tagged:
    return Tagged([t.chars[0].lower(), *t.chars[1:]], list(t.tags)) if t.chars else t


def _word_starts(t: Tagged) -> list[int]:
    return [i for i, c in enumerate(t.chars) if c != " " and (i == 0 or t.chars[i - 1] == " ")]


_DISFLUENCIES = ("um,", "uh,", "like,", "I mean,", "oh god,")


def _disfluent(rng: random.Random, t: Tagged) -> Tagged:
    for _ in range(rng.randint(1, 2)):
        starts = _word_starts(t)
        at = rng.choice(starts[1:] or starts)
        # An inserted word takes the tags shared by both neighbours, so a filler
        # inside a cue phrase becomes part of its evidence.
        inherited = t.tags[at] & t.tags[at - 1] if at else frozenset()
        filler = rng.choice(_DISFLUENCIES) + " "
        t = Tagged(
            t.chars[:at] + list(filler) + t.chars[at:],
            t.tags[:at] + [inherited] * len(filler) + t.tags[at:],
        )
    return t


def _misspell(rng: random.Random, t: Tagged) -> Tagged:
    """Swap two adjacent letters in one or two longer words; tags move with them."""
    chars, tags = list(t.chars), list(t.tags)
    words = []
    for start in _word_starts(t):
        end = start
        while end < len(chars) and chars[end] != " ":
            end += 1
        if end - start > 4 and all(c.isalpha() for c in chars[start:end]):
            words.append((start, end))
    for start, end in rng.sample(words, k=min(len(words), rng.randint(1, 2))):
        j = rng.randrange(start + 1, end - 2)
        chars[j], chars[j + 1] = chars[j + 1], chars[j]
        tags[j], tags[j + 1] = tags[j + 1], tags[j]
    return Tagged(chars, tags)


_HOMOPHONES = {"there": "their", "to": "too", "breathing": "breeding", "for": "four"}


def _speech_recognition(rng: random.Random, t: Tagged) -> Tagged:
    """Lower case, no punctuation, and an occasional homophone, like raw ASR output."""
    keep = [i for i, c in enumerate(t.chars) if c not in ".,!?;:"]
    chars = [t.chars[i].lower() for i in keep]
    tags = [t.tags[i] for i in keep]
    text = "".join(chars)
    out_chars: list[str] = []
    out_tags: list[frozenset[str]] = []
    pos = 0
    for m in re.finditer(r"[a-z']+", text):
        out_chars += chars[pos : m.start()]
        out_tags += tags[pos : m.start()]
        word = m.group(0)
        if word in _HOMOPHONES and rng.random() < 0.5:
            word = _HOMOPHONES[word]
        out_chars += list(word)
        out_tags += [tags[m.start()]] * len(word)
        pos = m.end()
    out_chars += chars[pos:]
    out_tags += tags[pos:]
    # Removing punctuation can leave doubled spaces.
    keep = [i for i, c in enumerate(out_chars) if not (c == " " and i and out_chars[i - 1] == " ")]
    return Tagged([out_chars[i] for i in keep], [out_tags[i] for i in keep]).strip()


def _location(rng: random.Random, spanish: bool) -> tuple[Tagged, str, str]:
    """(tagged sentence, label, kind)."""
    roll = rng.random()
    if spanish:
        street, number = rng.choice(SPANISH_STREETS), str(rng.randint(10, 999))
        sentence = (
            Tagged.of("Estamos en la ")
            + Tagged.of(street, _LOC + "street")
            + Tagged.of(" ")
            + Tagged.of(number, _LOC + "house_number")
            + Tagged.of(".")
        )
        return sentence, "present", "numbered"
    if roll < 0.45:
        number, street = str(rng.randint(10, 9999)), rng.choice(STREETS)
        sentence = (
            Tagged.of("We are at ")
            + Tagged.of(number, _LOC + "house_number")
            + Tagged.of(" ")
            + Tagged.of(street, _LOC + "street")
            + Tagged.of(".")
        )
        return sentence, "present", "numbered"
    if roll < 0.6:
        cross = rng.choice(CROSS)
        return (
            Tagged.of("We're near ") + Tagged.of(cross, _LOC + "intersection") + Tagged.of("."),
            "present",
            "intersection",
        )
    if roll < 0.72:
        landmark = rng.choice(LANDMARKS)
        return (
            Tagged.of("I'm outside ") + Tagged.of(landmark, _LOC + "landmark") + Tagged.of("."),
            "present",
            "landmark",
        )
    if roll < 0.86:
        return Tagged.of("I don't know where I am exactly."), "missing", "none"
    return Tagged(), "missing", "none"


@dataclass
class _Draft:
    messages: list[Tagged]
    severity: str
    statuses: dict[str, CueStatus]
    location: str
    victims: int | str | None
    variant: list[str]


def _draft(situation: Situation, rng: random.Random) -> _Draft:
    variant: list[str] = []
    severity = situation.severity
    status = CueStatus.AFFIRMED
    victims: int | str | None = None
    child = False

    use_spanish = bool(situation.spanish) and rng.random() < 0.15
    if use_spanish:
        body = render(rng.choice(situation.spanish), "")
        variant.append("spanish")
        if any(w in body.text.lower() for w in ("mi hijo", "mi hija", "mi bebé")):
            # Spanish phrasings name their own person; tag it as the child.
            lowered = body.text.lower()
            for word in ("mi hijo", "mi hija", "mi bebé"):
                at = lowered.find(word)
                if at >= 0:
                    tags = list(body.tags)
                    for i in range(at, at + len(word)):
                        tags[i] = tags[i] | {"CHILD_INVOLVED"}
                    body = Tagged(list(body.chars), tags)
                    break
            child = True
    else:
        template = rng.choice(situation.phrasings)
        mode = rng.random()
        if situation.denial and mode < 0.12:
            template, status = situation.denial, CueStatus.NEGATED
            variant.append("negated")
        elif situation.past and mode < 0.24:
            template, status = situation.past, CueStatus.HISTORICAL
            variant.append("past")
        who = rng.choice(ADULTS)
        if situation.personal and "{who}" in template.lower() and rng.random() < 0.2:
            possessive = "{who}'s" in template.lower()
            who = rng.choice(_POSSESSIVE_CHILDREN if possessive else CHILDREN)
            child = True
            variant.append("child")
        body = render(template, who, ("CHILD_INVOLVED",) if child else ())
        if status is CueStatus.AFFIRMED:
            if mode < 0.36:
                body = Tagged.of("I think ") + _lower_first(body)
                status = CueStatus.UNCERTAIN
                variant.append("uncertain")
            elif mode < 0.46:
                body = Tagged.of("My neighbor told me ") + _lower_first(body)
                variant.append("second_hand")

    statuses = {code: status for code in situation.cues}
    if status in (CueStatus.NEGATED, CueStatus.HISTORICAL):
        # A recovered critical event is elevated; any other past or denied one is low.
        recovered = status is CueStatus.HISTORICAL and set(situation.cues) & _CRITICAL
        severity = "elevated" if recovered else "low"
    if child:
        statuses["CHILD_INVOLVED"] = CueStatus.AFFIRMED
        if status not in (CueStatus.NEGATED, CueStatus.HISTORICAL):
            severity = _escalate(severity)

    location, location_label, location_kind = _location(rng, use_spanish)
    first = body + (Tagged.of(" ") + location if location.chars else Tagged())

    live = status not in (CueStatus.NEGATED, CueStatus.HISTORICAL)
    if live and not use_spanish and situation.personal and rng.random() < 0.15:
        n = rng.choice(list(NUMBER_WORDS))
        first = (
            first
            + Tagged.of(" There are ")
            + Tagged.of(f"{NUMBER_WORDS[n]} people ", "MULTIPLE_VICTIMS")
            + Tagged.of("hurt", "MULTIPLE_VICTIMS", "INJURY_REPORTED")
            + Tagged.of(".")
        )
        statuses["MULTIPLE_VICTIMS"] = CueStatus.AFFIRMED
        statuses.setdefault("INJURY_REPORTED", CueStatus.AFFIRMED)
        if statuses["INJURY_REPORTED"] is not CueStatus.AFFIRMED:
            statuses["INJURY_REPORTED"] = CueStatus.AFFIRMED
        severity = _escalate(severity)
        victims = n
        variant.append("multiple")

    messages = [first]
    if location_kind == "numbered" and not use_spanish and rng.random() < 0.1:
        number, street = str(rng.randint(10, 9999)), rng.choice(STREETS)
        # The final address is the correction; the first one is no longer a component.
        first.tags = [frozenset(t for t in tags if not t.startswith(_LOC)) for tags in first.tags]
        messages.append(
            Tagged.of("Sorry, I mean ")
            + Tagged.of(number, _LOC + "house_number")
            + Tagged.of(" ")
            + Tagged.of(street, _LOC + "street")
            + Tagged.of(".")
        )
        location_label = "conflicting"
        variant.append("corrected_address")

    if not use_spanish:
        roll = rng.random()
        if roll < 0.08:
            messages[0] = _speech_recognition(rng, messages[0])
            variant.append("speech_recognition")
        else:
            if rng.random() < 0.15:
                messages[0] = _disfluent(rng, messages[0])
                variant.append("disfluent")
            if rng.random() < 0.1:
                messages[0] = _misspell(rng, messages[0])
                variant.append("misspelled")

    return _Draft(messages, severity, statuses, location_label, victims, variant)


def _labels(situation: Situation, draft: _Draft) -> CaseLabels:
    texts = [m.text for m in draft.messages]
    annotations = []
    for code, status in sorted(draft.statuses.items()):
        evidence = None
        for index, message in enumerate(draft.messages):
            if (span := message.span(code)) is not None:
                start, end = span
                evidence = TextSpan(
                    message=index, start=start, end=end, text=texts[index][start:end]
                )
                break
        annotations.append(CueAnnotation(code=code, status=status, evidence=evidence))
    components: dict[str, TextSpan] = {}
    for index, message in enumerate(draft.messages):
        for tag in sorted(message.tag_names()):
            if tag.startswith(_LOC) and (span := message.span(tag)) is not None:
                start, end = span
                components[tag.removeprefix(_LOC)] = TextSpan(
                    message=index, start=start, end=end, text=texts[index][start:end]
                )
    return CaseLabels.model_validate(
        {
            "domain": situation.domain,
            "severity": draft.severity,
            "priority": _PRIORITY[draft.severity],
            "location": draft.location,
            "victim_count": draft.victims,
            "cue_annotations": annotations,
            "location_components": LocationComponents(**components) if components else None,
            "case_uncertainty": CaseUncertainty.CLEAR,
        }
    )


def generate(n: int, seed: int) -> Iterator[EvalCase]:
    """``n`` cases, cycling through families; identical for the same seed."""
    rng = random.Random(seed)
    for i in range(n):
        situation = SITUATIONS[i % len(SITUATIONS)]
        draft = _draft(situation, rng)
        yield EvalCase(
            case_id=f"g2s{seed}-{i:04d}",
            split=situation.split,
            family=situation.family,
            messages=[m.text for m in draft.messages],
            label_source=LabelSource.GENERATOR,
            labels=_labels(situation, draft),
            notes=f"generator {GENERATOR_VERSION}, seed {seed}; "
            + (", ".join(draft.variant) or "plain"),
        )
