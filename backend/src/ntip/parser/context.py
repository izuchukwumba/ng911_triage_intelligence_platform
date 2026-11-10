"""Context around a matched cue: polarity, temporality and attribution.

A keyword hit is not a fact. "There is no fire", "I think I heard a gunshot",
"there was a fire yesterday" and "someone said there was a fire" all contain a
cue word, and each means something different (design v1.2, section 6.3). This
module classifies the context of each hit with small, inspectable rules in the
spirit of NegEx; it is deliberately simple so the ML baselines have a clear
reference point to beat.
"""

import re
from dataclasses import dataclass

from ntip.parser.text import Match, clause_around, last_words, sentence_around
from ntip.schema.canonical import Attribution, Polarity, Temporality

# How many words before a cue a negation or uncertainty marker may appear.
NEGATION_WINDOW = 6

_NEGATION = re.compile(
    r"(?<![\w'])(?:not|no|never|none|nobody|neither|nor|without|cannot"
    r"|den(?:y|ies|ied|ying)|[a-z]+n't|ruled out|negative for|free of|no longer"
    r"|sin|nunca|ning[uú]n[oa]?|tampoco)(?![\w'])"
)
# Negation words that do not negate what follows ("can't stop bleeding",
# "not only ...", "no doubt").
_PSEUDO_NEGATION = re.compile(r"^\s*(?:stop\w*|only|doubt|just|quite)\b")
# "not sure" / "not certain" express uncertainty, handled below.
_UNCERTAIN_NEGATION = re.compile(r"^\s*(?:sure|certain)\b")
# Negation scope ends at a comma or a coordinating "and": in "no smoke, my
# mother fell" the fall is not negated. When unsure, erring towards affirming a
# cue is the safe direction; a wrongly negated cue can hide an emergency.
_SCOPE_END = re.compile(r"[,:]|(?<![\w'])(?:and|y)(?![\w'])")

_UNCERTAINTY = re.compile(
    r"(?<![\w'])(?:i think|i thought|i guess|i believe|maybe|might|possibly|probably"
    r"|perhaps|not sure|not certain|unsure|sounds like|sounded like|looks like"
    r"|looked like|seems like|seems|could be|may be|may have|might have"
    r"|creo que|tal vez|quiz[aá]s|parece)(?![\w'])"
)

_HISTORICAL = re.compile(
    r"(?<![\w'])(?:earlier|yesterday|last (?:night|week|month|year|time)|ago|used to"
    r"|previously|the other day|before but|ayer|antes)(?![\w'])"
)
# "if" after sure/know/tell/... asks a question ("not sure if he's breathing")
# rather than stating a condition, so it does not make the clause hypothetical.
_QUESTION_IF = "".join(
    f"(?<!{w} )" for w in ("sure", "know", "tell", "check", "see", "wonder", "ask")
)
_HYPOTHETICAL = re.compile(
    rf"(?<![\w'])(?:{_QUESTION_IF}if|in case|what if|unless|worried (?:that|he|she|it|they)"
    r"|afraid (?:that|he|she|it|they)|could start|might start|si)(?![\w'])"
)

# "He might have a heart attack if he keeps shoveling": a modal before the cue
# and a condition after it describe something that has not happened. Without
# the condition ("he might be having a heart attack") the cue stays current
# and uncertain, so it still counts.
_MODAL = re.compile(r"(?<![\w'])(?:might|could|may|would|will)(?![\w'])")
_CONDITION = re.compile(r"(?<![\w'])(?:if|unless|once)(?![\w'])")

_SECOND_HAND = re.compile(
    r"(?<![\w'])(?:someone said|somebody said|they said|he said|she said|people said"
    r"|people are saying|i was told|we were told|i heard that|i heard there"
    r"|apparently|reportedly|according to|my \w+ (?:said|told me)|me dijeron|dicen que)"
    r"(?![\w'])"
)
_FIRST_HAND = re.compile(
    r"(?<![\w'])(?:i see|i can see|i saw|i'm looking at|i am looking at|in front of me"
    r"|i'm watching|i am watching|right here|veo)(?![\w'])"
)


@dataclass(frozen=True)
class CueContext:
    polarity: Polarity
    temporality: Temporality
    attribution: Attribution


def _is_negated(prefix: str) -> bool:
    for m in _NEGATION.finditer(prefix):
        rest = prefix[m.end() :]
        if _SCOPE_END.search(rest):
            continue  # also covers the interjection "No, he's bleeding"
        if _PSEUDO_NEGATION.match(rest) or _UNCERTAIN_NEGATION.match(rest):
            continue
        return True
    return False


def analyse(text: str, match: Match) -> CueContext:
    """Classify the context of ``match`` within ``text``."""
    clause = clause_around(text, match.start, match.end)
    sentence = sentence_around(text, match.start, match.end)

    before_in_clause = text[clause.start : match.start].lower()
    whole_clause = text[clause.start : clause.end].lower()
    after_in_clause = text[match.end : clause.end].lower()
    before_in_sentence = text[sentence.start : match.start].lower()
    window = last_words(before_in_clause, NEGATION_WINDOW)

    if _is_negated(window):
        polarity = Polarity.NEGATED
    elif _UNCERTAINTY.search(before_in_clause):
        polarity = Polarity.UNCERTAIN
    else:
        polarity = Polarity.AFFIRMED

    conditional = _MODAL.search(before_in_clause) and _CONDITION.search(after_in_clause)
    if _HYPOTHETICAL.search(before_in_clause) or conditional:
        temporality = Temporality.HYPOTHETICAL
    elif _HISTORICAL.search(whole_clause):
        temporality = Temporality.HISTORICAL
    else:
        temporality = Temporality.CURRENT

    if _SECOND_HAND.search(before_in_sentence):
        attribution = Attribution.SECOND_HAND
    elif _FIRST_HAND.search(before_in_sentence):
        attribution = Attribution.FIRST_HAND
    else:
        attribution = Attribution.UNSPECIFIED

    return CueContext(polarity, temporality, attribution)
