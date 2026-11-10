import pytest

pytest.importorskip("sklearn")

from ntip.ml.b1 import ABSTAIN_FROM, CANDIDATE_AT, B1Model
from ntip.ml.contract import InferenceMessage, InferenceRequest
from ntip.ml.service import load_model
from ntip.ml.verify import verify


@pytest.fixture(scope="module")
def model() -> B1Model:
    return B1Model()


def request(*texts: str) -> InferenceRequest:
    return InferenceRequest(
        request_id="r1",
        incident_id="inc_1",
        messages=[InferenceMessage(source_event_id=f"e{i}", text=t) for i, t in enumerate(texts)],
    )


def test_training_is_deterministic(model: B1Model) -> None:
    again = B1Model()
    assert again.model_version == model.model_version
    text = "Someone was stabbed and is bleeding."
    assert again.scores([text]) == model.scores([text])


def test_version_identifies_data_and_parameters(model: B1Model) -> None:
    assert model.model_version.startswith("1.0.0+")
    assert model.training_digest.startswith("sha256:")


def test_detects_a_misspelled_critical_cue_with_grounded_evidence(model: B1Model) -> None:
    text = "My father is not breathign and wont wake up. We are at 12 Oak Street."
    response = model.infer(request(text))
    codes = {c.code for c in response.candidates}
    assert "NOT_BREATHING" in codes
    verified = verify(response, {"e0": text})
    assert verified.rejections == []
    [cue] = [o for o in verified.observations if o.code == "NOT_BREATHING"]
    assert "breathign" in cue.evidence.text


def test_candidates_and_abstentions_respect_thresholds(model: B1Model) -> None:
    # No sentence punctuation, so each message is a single clause.
    texts = ["There is smoke coming out of the garage", "He might be hurt, I am not sure"]
    response = model.infer(request(*texts))
    best = {code: max(model.scores([t])[0][code] for t in texts) for code in model.codes}
    for candidate in response.candidates:
        assert best[candidate.code] >= CANDIDATE_AT
    for abstention in response.abstentions:
        assert ABSTAIN_FROM <= best[abstention.code] < CANDIDATE_AT
    assert {c.code for c in response.candidates}.isdisjoint(a.code for a in response.abstentions)
    assert not response.calibrated


def test_unrelated_text_yields_no_candidates(model: B1Model) -> None:
    assert model.infer(request("What time does the library open tomorrow?")).candidates == []


def test_service_can_load_b1() -> None:
    assert load_model("b1-tfidf-logreg").model_id == "b1-tfidf-logreg"
