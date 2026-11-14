"""B1e: a small encoder run locally, the primary ML model (DDL-020).

A pretrained multilingual encoder, fine-tuned on the project's synthetic data,
scores each clause of a call. Two outputs per cue code:

- **live**: the clause reports the cue as happening now (affirmed or
  uncertain);
- **absent**: the clause mentions the cue but denies it, or places it in the
  past or a hypothetical.

Case labels say which cues a call contains, not which clause contains them,
so training is multiple-instance: a call's score for an output is its best
clause's score. The absent output teaches the encoder that "no fire" and "he
wasn't breathing earlier" are not live cues, which B1's n-grams cannot learn.
Only live cues become candidates; the best clause is the quoted evidence, so
every candidate is grounded and passes verification.

Runs on CPU. Weights are not committed: ``python -m ntip.ml.train_b1e``
produces a directory with a manifest of file digests, and ``B1eModel`` refuses
any directory whose files do not match it. Needs the ``ml-encoder`` extra.
"""

import json
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ntip.ml.b1 import _clauses, _trim
from ntip.ml.contract import (
    Abstention,
    Candidate,
    InferenceMessage,
    InferenceRequest,
    InferenceResponse,
)
from ntip.parser.lexicon import OBSERVATION_CUES
from ntip.schema.base import SourceSpan, sha256_digest
from ntip.schema.canonical import Polarity

if TYPE_CHECKING:
    import torch

MODEL_ID = "b1e-encoder"
MODEL_SERIES = "0.1.0"
# Apache-2.0; 6 layers; covers English and Spanish. Pinned to an exact revision.
BASE_MODEL = "distilbert/distilbert-base-multilingual-cased"
BASE_REVISION = "45c032ab32cc946ad88a166f7cb282f58c753c2e"
# Pre-declared, the same as B1's, so the two are comparable.
CANDIDATE_AT = 0.5
ABSTAIN_FROM = 0.35
CODES: tuple[str, ...] = tuple(sorted(OBSERVATION_CUES))
MANIFEST = "manifest.json"
ENCODER_DIR = "encoder"
HEAD_FILE = "head.safetensors"


class InvalidModel(Exception):
    """A B1e directory is missing files or does not match its manifest."""


@dataclass(frozen=True)
class Example:
    """One training call: its clauses and its case-level targets."""

    clauses: list[str]
    live: frozenset[str]
    absent: frozenset[str]


def clause_texts(messages: Sequence[str]) -> list[str]:
    return [m[s.start : s.end] for m in messages for s in (_trim(m, seg) for seg in _clauses(m))]


def load_examples(path: Path, splits: Sequence[str]) -> tuple[list[Example], str]:
    """Training examples from a dataset file, and the file's digest."""
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    examples = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        if case["split"] not in splits:
            continue
        clauses = clause_texts(case["messages"])
        if clauses:
            labels = case["labels"]
            examples.append(
                Example(
                    clauses,
                    frozenset(labels.get("cues", [])) & set(CODES),
                    frozenset(labels.get("absent_cues", [])) & set(CODES),
                )
            )
    return examples, sha256_digest(raw)


def targets(example: Example) -> list[float]:
    """Live outputs for every code, then absent outputs for every code."""
    return [float(c in example.live) for c in CODES] + [float(c in example.absent) for c in CODES]


def file_digests(directory: Path) -> dict[str, str]:
    """sha256 of every file in a model directory except the manifest."""
    return {
        p.relative_to(directory).as_posix(): sha256_digest(p.read_bytes())
        for p in sorted(directory.rglob("*"))
        if p.is_file() and p.name != MANIFEST
    }


def weights_digest(files: dict[str, str]) -> str:
    return sha256_digest(json.dumps(files, sort_keys=True))


def build_scorer(encoder: Any) -> "torch.nn.Module":
    """The encoder plus one linear layer giving live and absent logits per code."""
    import torch

    class ClauseScorer(torch.nn.Module):  # type: ignore[misc,unused-ignore]
        def __init__(self) -> None:
            super().__init__()
            self.encoder = encoder
            self.head = torch.nn.Linear(encoder.config.hidden_size, 2 * len(CODES))

        def forward(self, **inputs: "torch.Tensor") -> "torch.Tensor":
            hidden = self.encoder(**inputs).last_hidden_state[:, 0]  # first token
            result: torch.Tensor = self.head(hidden)
            return result

    return ClauseScorer()


class B1eModel:
    model_id = MODEL_ID

    def __init__(self, directory: Path, *, candidate_at: float = CANDIDATE_AT) -> None:
        import torch
        from safetensors.torch import load_file
        from transformers import AutoModel, AutoTokenizer

        self.candidate_at = candidate_at  # overridable only for ablations
        manifest_path = directory / MANIFEST
        if not manifest_path.is_file():
            raise InvalidModel(f"{directory} has no {MANIFEST}")
        self.manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = file_digests(directory)
        if files != self.manifest["files"]:
            changed = sorted(set(files.items()) ^ set(self.manifest["files"].items()))
            raise InvalidModel(f"files do not match the manifest: {[n for n, _ in changed]}")
        if self.manifest["codes"] != list(CODES):
            raise InvalidModel("the model was trained for a different set of cue codes")
        digest = weights_digest(files)
        if digest != self.manifest["weights_digest"]:
            raise InvalidModel("weights digest does not match the manifest")
        self.model_version = f"{MODEL_SERIES}+{digest.removeprefix('sha256:')[:12]}"
        self.max_length = int(self.manifest["params"]["max_length"])

        torch.manual_seed(0)  # nothing is random at inference; fixed for certainty
        self.tokenizer = AutoTokenizer.from_pretrained(directory / ENCODER_DIR)
        encoder = AutoModel.from_pretrained(directory / ENCODER_DIR)
        self.scorer = build_scorer(encoder)
        head: Any = self.scorer.head
        head.load_state_dict(load_file(str(directory / HEAD_FILE)))
        self.scorer.eval()

    def clause_scores(self, clauses: list[str]) -> list[dict[str, float]]:
        """Sigmoid live scores per clause for every code."""
        import torch

        if not clauses:
            return []
        inputs = self.tokenizer(
            clauses,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        with torch.inference_mode():
            live = torch.sigmoid(self.scorer(**inputs))[:, : len(CODES)]
        return [dict(zip(CODES, map(float, row), strict=True)) for row in live.tolist()]

    def _scored(
        self, messages: list[InferenceMessage]
    ) -> tuple[list[tuple[InferenceMessage, SourceSpan]], list[dict[str, float]]]:
        clauses = [(m, _trim(m.text, seg)) for m in messages for seg in _clauses(m.text)]
        return clauses, self.clause_scores([m.text[s.start : s.end] for m, s in clauses])

    def cue_scores(self, messages: list[InferenceMessage]) -> dict[str, float]:
        """Each code's score for a conversation: its best clause (for calibration)."""
        _, scores = self._scored(messages)
        return {c: max((s[c] for s in scores), default=0.0) for c in CODES}

    def infer(self, request: InferenceRequest) -> InferenceResponse:
        started = time.perf_counter()
        clauses, scores = self._scored(request.messages)
        candidates: list[Candidate] = []
        abstentions: list[Abstention] = []
        for code in CODES if clauses else ():
            best = max(range(len(clauses)), key=lambda i: scores[i][code])
            score = scores[best][code]
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
