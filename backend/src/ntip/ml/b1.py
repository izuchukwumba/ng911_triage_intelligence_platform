"""B1: a small, openly licensed learned baseline (design v1.2, section 3A.4).

One logistic-regression classifier per cue over character and word n-gram
TF-IDF features (scikit-learn, BSD-3). Character n-grams make it tolerant of
the misspellings and disfluencies that defeat exact phrase matching.

- Trained deterministically at load time from a committed synthetic dataset
  with pinned hyperparameters, so no opaque weight files are shipped and the
  model version identifies data, parameters and library version.
- Each clause of each message is scored; a cue's score is its best clause
  (max pooling) and that clause is the quoted evidence, so every candidate
  is grounded in the source and passes verification.
- Pre-declared thresholds: a candidate at score >= 0.5; abstain between 0.35
  and 0.5; nothing below. Scores are not calibrated probabilities.
"""

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ntip.ml.contract import (
    Abstention,
    Candidate,
    InferenceMessage,
    InferenceRequest,
    InferenceResponse,
)
from ntip.parser.text import Segment, clause_around
from ntip.schema.base import SourceSpan, sha256_digest
from ntip.schema.canonical import Polarity

MODEL_ID = "b1-tfidf-logreg"
MODEL_SERIES = "1.0.0"
CANDIDATE_AT = 0.5
ABSTAIN_FROM = 0.35
SEED = 20261109
PARAMS: dict[str, Any] = {
    "char_ngrams": [2, 5],
    "word_ngrams": [1, 2],
    "C": 4.0,
    "class_weight": "balanced",
    "max_iter": 2000,
    "solver": "liblinear",
}
TRAINING_SPLITS = ("dev", "regression")

_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_TRAINING_DATA = _REPO_ROOT / "data" / "eval" / "generated-1.0.0-seed42.jsonl"


def _training_path() -> Path:
    return Path(os.environ.get("NTIP_B1_TRAINING_DATA", DEFAULT_TRAINING_DATA))


@dataclass(frozen=True)
class TrainingSet:
    texts: list[str]
    labels: list[list[str]]
    digest: str


def load_training_set(path: Path | None = None) -> TrainingSet:
    path = path or _training_path()
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    texts, labels = [], []
    for line in raw.splitlines():
        case = json.loads(line)
        if case["split"] not in TRAINING_SPLITS:
            continue
        texts.append("\n".join(case["messages"]))
        labels.append(sorted(case["labels"].get("cues", [])))
    return TrainingSet(texts, labels, sha256_digest(raw))


def _clauses(text: str) -> list[Segment]:
    """Non-empty clauses of ``text``, in order."""
    segments: list[Segment] = []
    pos = 0
    while pos < len(text):
        seg = clause_around(text, pos, pos + 1)
        if text[seg.start : seg.end].strip():
            segments.append(seg)
        pos = max(seg.end + 1, pos + 1)
    return segments


def _trim(text: str, seg: Segment) -> SourceSpan:
    start, end = seg.start, seg.end
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return SourceSpan(start=start, end=end)


class B1Model:
    model_id = MODEL_ID

    def __init__(
        self, training: TrainingSet | None = None, *, candidate_at: float = CANDIDATE_AT
    ) -> None:
        # candidate_at is overridable only for ablations; the default is pre-declared.
        self.candidate_at = candidate_at
        import sklearn
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.multiclass import OneVsRestClassifier
        from sklearn.pipeline import FeatureUnion, make_pipeline
        from sklearn.preprocessing import MultiLabelBinarizer

        training = training or load_training_set()
        self.binarizer = MultiLabelBinarizer()
        y = self.binarizer.fit_transform(training.labels)
        char = TfidfVectorizer(
            analyzer="char_wb", ngram_range=tuple(PARAMS["char_ngrams"]), sublinear_tf=True
        )
        word = TfidfVectorizer(
            analyzer="word", ngram_range=tuple(PARAMS["word_ngrams"]), sublinear_tf=True
        )
        features = FeatureUnion([("char", char), ("word", word)])
        classifier = OneVsRestClassifier(
            LogisticRegression(
                C=PARAMS["C"],
                class_weight=PARAMS["class_weight"],
                max_iter=PARAMS["max_iter"],
                solver=PARAMS["solver"],
                random_state=SEED,
            )
        )
        self.pipeline = make_pipeline(features, classifier)
        self.pipeline.fit(training.texts, y)
        self.codes: list[str] = list(self.binarizer.classes_)
        fingerprint = sha256_digest(
            json.dumps(
                {
                    "data": training.digest,
                    "params": PARAMS,
                    "seed": SEED,
                    "sklearn": sklearn.__version__,
                },
                sort_keys=True,
            )
        )
        self.model_version = f"{MODEL_SERIES}+{fingerprint.removeprefix('sha256:')[:12]}"
        self.training_digest = training.digest

    def scores(self, texts: list[str]) -> list[dict[str, float]]:
        """Per-cue scores for each text (higher means more likely present)."""
        probabilities = self.pipeline.predict_proba(texts)
        return [dict(zip(self.codes, map(float, row), strict=True)) for row in probabilities]

    def _clause_scores(
        self, messages: list[InferenceMessage]
    ) -> tuple[list[tuple[InferenceMessage, SourceSpan]], list[dict[str, float]]]:
        clauses = [(m, _trim(m.text, seg)) for m in messages for seg in _clauses(m.text)]
        texts = [m.text[s.start : s.end] for m, s in clauses]
        return clauses, (self.scores(texts) if texts else [])

    def cue_scores(self, messages: list[InferenceMessage]) -> dict[str, float]:
        """Each cue's score for a conversation: its best clause (used for calibration)."""
        _, clause_scores = self._clause_scores(messages)
        return {c: max((s[c] for s in clause_scores), default=0.0) for c in self.codes}

    def infer(self, request: InferenceRequest) -> InferenceResponse:
        started = time.perf_counter()
        # Cues are local, so a cue's score is its best clause score (max
        # pooling); scoring the whole conversation at once dilutes a short cue
        # in a long call.
        clauses, clause_scores = self._clause_scores(request.messages)

        candidates: list[Candidate] = []
        abstentions: list[Abstention] = []
        for code in self.codes:
            if not clauses:
                break
            best = max(range(len(clauses)), key=lambda i: clause_scores[i][code])
            score = clause_scores[best][code]
            if score >= self.candidate_at:
                message, span = clauses[best]
                candidates.append(
                    Candidate(
                        code=code,
                        polarity=Polarity.AFFIRMED,
                        source_event_id=message.source_event_id,
                        span=span,
                        evidence_text=message.text[span.start : span.end],
                        confidence=round(score, 4),
                    )
                )
            elif score >= ABSTAIN_FROM:
                abstentions.append(
                    Abstention(code=code, reason=f"score {score:.2f} between thresholds")
                )
        return InferenceResponse(
            request_id=request.request_id,
            model_id=self.model_id,
            model_version=self.model_version,
            candidates=candidates,
            abstentions=abstentions,
            calibrated=False,
            runtime_ms=(time.perf_counter() - started) * 1000,
        )
