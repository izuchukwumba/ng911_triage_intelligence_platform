"""Additions for generator 2.1 (ML layer design, section 4.3).

B1e trained on generator 2.0 showed four failure patterns on the curated dev
split (results README, "B1e on generator 2.0"). Each traces back to a gap in
the generated training data, closed here:

1. **Denials of side-effect cues.** Generator 2.0 never denies a cue on its own
   ("Nobody is hurt.", "There's no fire.", "He is still conscious."), so the
   model scored such denials live. ``REASSURANCES`` adds them as negated cues
   next to an unrelated live situation.
2. **Shouting.** No phrasing was ever in capitals, and the base model is
   case-sensitive. Generator 2.1 adds an all-capitals variant.
3. **Cues that always appeared together.** Every training family with
   ``NOT_BREATHING`` also had ``UNCONSCIOUS`` or ``DROWNING``. A training family
   with ``NOT_BREATHING`` alone is added, and unconscious patients are sometimes
   reported as still breathing (a negated ``NOT_BREATHING``).
4. **Spanish family words.** Each Spanish phrasing named one fixed person, so
   the person and the cue were confounded ("mi esposo" was read as a child).
   Generator 2.1 draws the family word at random, keeping its gender.

The phrasings were written after looking at the curated dev errors, so curated
dev is no longer an independent check of these four patterns; the held-out
test splits are (ML-10).
"""

from dataclasses import dataclass

from ntip.generator.scenarios import Situation
from ntip.generator.scenarios_v2 import SITUATIONS as SITUATIONS_V2
from ntip.generator.scenarios_v2 import D, S

NB, UC = "NOT_BREATHING", "UNCONSCIOUS"

NEW_SITUATIONS: tuple[Situation, ...] = (
    S(
        "not_breathing_only",
        D,
        "ems",
        "critical",
        (NB,),
        (
            "{Who} [NOT_BREATHING|is not breathing], please send someone.",
            "{Who} [NOT_BREATHING|stopped breathing] and I'm doing CPR.",
            "I [NOT_BREATHING|don't think {who} is breathing] at all.",
            "{Who} [NOT_BREATHING|has no pulse] and I'm pushing on the chest.",
            "{Who} [NOT_BREATHING|is turning blue and not breathing].",
        ),
        denial="{Who} [NOT_BREATHING|is breathing fine], just very dizzy.",
        past="{Who} [NOT_BREATHING|wasn't breathing] for a few seconds but is fine now.",
        spanish=(
            "Mi esposo [NOT_BREATHING|no respira].",
            "Mi madre [NOT_BREATHING|no está respirando].",
        ),
    ),
)

SITUATIONS: tuple[Situation, ...] = SITUATIONS_V2 + NEW_SITUATIONS


@dataclass(frozen=True)
class Reassurance:
    """A sentence denying ``code``, added to a live call where it applies."""

    code: str
    # ``{P}`` is the pronoun for the person, ``{be}`` its form of "to be".
    phrasings: tuple[str, ...]
    # Refers to the caller's person by pronoun, so needs a named person first.
    personal: bool


REASSURANCES: tuple[Reassurance, ...] = (
    Reassurance(
        "INJURY_REPORTED",
        (
            "[INJURY_REPORTED|Nobody is hurt].",
            "[INJURY_REPORTED|No one is injured].",
            "[INJURY_REPORTED|Nobody seems to be hurt].",
            "Everyone is okay, [INJURY_REPORTED|nobody got hurt].",
            "[INJURY_REPORTED|No injuries] as far as I can see.",
        ),
        personal=False,
    ),
    Reassurance(
        "FIRE_REPORTED",
        (
            "[FIRE_REPORTED|There's no fire] that I can see.",
            "[FIRE_REPORTED|No flames], just the smell.",
            "[FIRE_REPORTED|Nothing is on fire].",
        ),
        personal=False,
    ),
    Reassurance(
        UC,
        (
            "{P} [UNCONSCIOUS|{be} still conscious].",
            "{P} [UNCONSCIOUS|{be} awake] and talking to me.",
            "{P} [UNCONSCIOUS|{be} conscious] for now.",
        ),
        personal=True,
    ),
    Reassurance(
        NB,
        (
            "{P} [NOT_BREATHING|{be} still breathing].",
            "{P} [NOT_BREATHING|{be} breathing], just not waking up.",
            "[NOT_BREATHING|I can see {p} breathing] though.",
        ),
        personal=True,
    ),
)

# Families where "nobody is hurt" or "there's no fire" is a natural thing to add.
_NO_INJURY_WITH = {
    "TRAFFIC_COLLISION", "INTRUDER_PRESENT", "SMOKE_REPORTED", "FIRE_REPORTED",
    "HAZARDOUS_ENVIRONMENT", "EXPLOSION_REPORTED", "WEAPON_PRESENT",
}  # fmt: skip
_NO_FIRE_WITH = {
    "SMOKE_REPORTED",
    "HAZARDOUS_ENVIRONMENT",
    "EXPLOSION_REPORTED",
    "TRAFFIC_COLLISION",
}
# Conditions in which a conscious patient is ordinary.
_CONSCIOUS_WITH = {
    "WEAPON_PRESENT", "ACTIVE_BLEEDING", "BURN_INJURY", "FALL_FROM_HEIGHT", "ELECTROCUTION",
    "CARDIAC_SYMPTOMS", "BREATHING_DIFFICULTY", "STROKE_SYMPTOMS", "ALLERGIC_REACTION",
    "OVERDOSE", "POISONING", "INJURY_REPORTED", "DIABETIC_EMERGENCY", "UNABLE_TO_GET_UP",
}  # fmt: skip
_NOT_CONSCIOUS_WITH = {NB, UC, "SEIZURE", "DROWNING"}


def applies(reassurance: Reassurance, situation: Situation, names_person: bool) -> bool:
    cues = set(situation.cues)
    if reassurance.code in cues:
        return False
    if reassurance.personal and not (situation.personal and names_person):
        return False
    match reassurance.code:
        case "INJURY_REPORTED":
            return situation.domain != "ems" and cues <= _NO_INJURY_WITH
        case "FIRE_REPORTED":
            return bool(cues & _NO_FIRE_WITH) and not cues & {"FIRE_SPREADING"}
        case "UNCONSCIOUS":
            return bool(cues & _CONSCIOUS_WITH) and not cues & _NOT_CONSCIOUS_WITH
        case "NOT_BREATHING":
            return UC in cues
    return False


# Pronouns for the people in ``scenarios.ADULTS`` and ``scenarios.CHILDREN``.
PRONOUNS = {
    "my father": "he", "my husband": "he", "my brother": "he", "my grandfather": "he",
    "a man": "he", "my wife": "she", "my mother": "she", "a woman": "she",
    "my neighbor": "they", "my roommate": "they", "my baby": "they", "my toddler": "they",
    "my little girl, she's a child,": "she", "my son, he's just a kid,": "he",
}  # fmt: skip

# Spanish family words by grammatical gender; a phrasing's word is replaced by
# one of the same gender, so the rest of the sentence still agrees.
SPANISH_KIN = {
    "m": ("padre", "papá", "esposo", "hermano", "abuelo", "hijo", "tío", "amigo", "vecino"),
    "f": ("madre", "mamá", "esposa", "hermana", "abuela", "hija", "tía", "amiga", "vecina"),
}
