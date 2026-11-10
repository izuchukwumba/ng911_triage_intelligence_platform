"""Scenario families for the synthetic generator.

Each Situation is a family: one kind of incident with several phrasings. A
phrasing must actually express every cue listed for the situation, because
the generator's labels are taken from this table (design v1.2, section 12.3:
generated labels are *generator-intended*, not verified ground truth).

Severities follow the labelling rubric (docs/evaluation/labelling-guide.md),
not the triage engine, so evaluating the engine on generated data is not
circular.
"""

from dataclasses import dataclass

from ntip.evaluation.dataset import Split


@dataclass(frozen=True)
class Situation:
    family: str
    split: Split
    domain: str
    severity: str
    cues: tuple[str, ...]
    # "{who}" is replaced by a person, "{Who}" by the same, capitalised.
    phrasings: tuple[str, ...]
    # A sentence denying the situation, for negated variants ({who} allowed).
    denial: str | None = None
    # The same situation reported in the past tense.
    past: str | None = None
    # Spanish phrasings, if any.
    spanish: tuple[str, ...] = ()
    # Whether {who} may be a child or several people.
    personal: bool = True


D, R, T = Split.DEV, Split.REGRESSION, Split.TEST

SITUATIONS: tuple[Situation, ...] = (
    Situation(
        "gen_cardiac_arrest",
        R,
        "ems",
        "critical",
        ("NOT_BREATHING", "UNCONSCIOUS"),
        (
            "{Who} collapsed and is not breathing.",
            "{Who} just collapsed, I can't find a pulse and {who} is not breathing.",
            "{Who} is unconscious and not breathing at all.",
        ),
        past="{Who} was not breathing earlier but is breathing now and talking.",
        spanish=("Mi padre está inconsciente y no respira.",),
    ),
    Situation(
        "gen_unresponsive",
        T,
        "ems",
        "critical",
        ("UNCONSCIOUS",),
        (
            "{Who} is unresponsive and won't wake up.",
            "{Who} passed out and is not responding to me.",
            "I found {who} on the floor, unconscious.",
        ),
        past="{Who} passed out earlier but is awake now.",
        spanish=("Mi madre está inconsciente y no responde.",),
    ),
    Situation(
        "gen_shooting",
        R,
        "police",
        "critical",
        ("WEAPON_PRESENT", "ACTIVE_BLEEDING"),
        (
            "{Who} has been shot and is bleeding badly.",
            "Someone shot {who}, there is blood everywhere.",
            "{Who} was stabbed with a knife and is bleeding a lot.",
        ),
        personal=True,
    ),
    Situation(
        "gen_armed_threat",
        D,
        "police",
        "high",
        ("WEAPON_PRESENT",),
        (
            "A man is waving a gun around outside.",
            "There is someone with a knife outside the store.",
            "A guy just pulled a gun on people in the parking lot.",
        ),
        denial="I looked again and he does not have a gun, it was a phone.",
        personal=False,
    ),
    Situation(
        "gen_assault",
        T,
        "police",
        "high",
        ("ACTIVE_VIOLENCE",),
        (
            "Two men are fighting in the street and one is getting beaten.",
            "My neighbor is beating his wife, I can hear it through the wall.",
            "There is a big fight going on outside the bar.",
        ),
        past="There was a fight here last night, it's quiet now.",
        personal=False,
    ),
    Situation(
        "gen_chest_pain",
        D,
        "ems",
        "high",
        ("CARDIAC_SYMPTOMS",),
        (
            "{Who} is having chest pain and is sweating.",
            "{Who} says it feels like a heart attack, the chest pain won't stop.",
            "{Who} has chest pressure and feels dizzy.",
        ),
        denial="{Who} has no chest pain now, it went away an hour ago and {who} feels fine.",
        spanish=("Mi esposo tiene dolor de pecho.",),
    ),
    Situation(
        "gen_breathing",
        T,
        "ems",
        "high",
        ("BREATHING_DIFFICULTY",),
        (
            "{Who} is having trouble breathing.",
            "{Who} can't breathe properly and is gasping.",
            "{Who} is choking on something.",
        ),
        spanish=("Mi hijo no puede respirar bien.",),
    ),
    Situation(
        "gen_seizure",
        R,
        "ems",
        "high",
        ("SEIZURE",),
        (
            "{Who} is having a seizure right now.",
            "{Who} is seizing on the floor.",
            "{Who} started convulsing a minute ago and is still convulsing.",
        ),
    ),
    Situation(
        "gen_stroke",
        T,
        "ems",
        "high",
        ("STROKE_SYMPTOMS",),
        (
            "I think {who} is having a stroke, the face is drooping.",
            "{Who} has slurred speech and the face is drooping.",
            "{Who} might be having a stroke.",
        ),
    ),
    Situation(
        "gen_overdose",
        D,
        "ems",
        "high",
        ("OVERDOSE",),
        (
            "{Who} took too many pills.",
            "I think {who} overdosed on something.",
            "{Who} had an overdose, we have naloxone but I don't know how to use it.",
        ),
    ),
    Situation(
        "gen_house_fire_trapped",
        R,
        "fire",
        "critical",
        ("FIRE_REPORTED", "OCCUPANTS_TRAPPED"),
        (
            "The house is on fire and {who} is trapped upstairs.",
            "There's a fire in the building and people are trapped inside.",
            "Flames everywhere and {who} can't get out of the bedroom.",
        ),
        spanish=("Hay un incendio y hay personas atrapadas.",),
    ),
    Situation(
        "gen_smoke",
        D,
        "fire",
        "elevated",
        ("SMOKE_REPORTED",),
        (
            "There is smoke coming out of the garage.",
            "I can smell and see smoke coming from the apartment next door.",
            "Smoke is pouring out of a window in the building.",
        ),
        denial="There is no smoke, it was steam from the dryer vent.",
        spanish=("Sale humo del garaje.",),
        personal=False,
    ),
    Situation(
        "gen_spreading_fire",
        T,
        "fire",
        "high",
        ("FIRE_REPORTED", "FIRE_SPREADING"),
        (
            "The fire is spreading to the next house.",
            "The brush fire is out of control and spreading fast.",
            "The whole building is on fire now.",
        ),
        past="There was a fire here yesterday but it's out now.",
        personal=False,
    ),
    Situation(
        "gen_gas_leak",
        R,
        "hazmat",
        "high",
        ("HAZARDOUS_ENVIRONMENT",),
        (
            "There's a strong smell of gas in the kitchen.",
            "Our carbon monoxide alarm is going off.",
            "There's a chemical spill in the warehouse and the fumes are strong.",
        ),
        denial="It is not a gas leak, the smell was from the trash.",
        spanish=("Hay una fuga de gas en la cocina.",),
        personal=False,
    ),
    Situation(
        "gen_fall_unable",
        T,
        "ems",
        "elevated",
        ("INJURY_REPORTED", "UNABLE_TO_GET_UP"),
        (
            "{Who} fell and can't get up, the hip hurts.",
            "{Who} slipped in the bathroom, is hurt and unable to get up.",
            "{Who} fell down the stairs, is in pain and can't stand.",
        ),
    ),
    Situation(
        "gen_minor_injury",
        D,
        "ems",
        "standard",
        ("INJURY_REPORTED",),
        (
            "{Who} twisted an ankle and it hurts.",
            "{Who} cut a finger while cooking, it hurts but it's okay.",
            "{Who} hurt a wrist playing basketball.",
        ),
        denial="Nobody is hurt, we just need someone to check the car.",
    ),
    Situation(
        "gen_property_crime",
        T,
        "police",
        "standard",
        (),
        (
            "Someone broke into my car overnight.",
            "My bike was stolen from the porch.",
            "Someone vandalized the mailboxes on our street.",
        ),
        personal=False,
    ),
)

ADULTS = ("my father", "my husband", "my wife", "my mother", "my brother", "my neighbor",
          "a man", "a woman", "my grandfather", "my roommate")  # fmt: skip
CHILDREN = ("my baby", "my toddler", "my little girl, she's a child,", "my son, he's just a kid,")

STREETS = ("Oak Street", "Maple Avenue", "Pine Road", "Cedar Lane", "Elm Drive", "Birch Court",
           "Willow Way", "Lakeview Boulevard", "Hill Road", "Main Street")  # fmt: skip
CROSS = ("5th and Main", "Oak Street and 3rd", "Elm Drive and Pine Road", "1st and Market")
LANDMARKS = ("the library", "the gas station", "the high school", "the shopping mall",
             "the bus station", "the park")  # fmt: skip
SPANISH_STREETS = ("Calle Pino", "Calle Luna", "Calle Sol", "Avenida Central")

NUMBER_WORDS = {2: "two", 3: "three", 4: "four", 5: "five"}
